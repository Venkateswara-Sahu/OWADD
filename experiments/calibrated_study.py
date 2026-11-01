"""Permutation-calibrated attribution: null calibration, localization, ablations.

Three questions the mechanism investigation left open, answered by one study:

**Q1 -- Is the permutation calibration valid?** The published decomposed path
uses asymptotic two-sample p-values (KS, Fisher-z). Those are wrong under ties,
heavy tails and dependence, so its family-wise error rate is only nominal on
Gaussian data. The calibrated path re-splits the pooled windows at random and
compares each statistic against the maximum over its whole family (maxT). This
stage measures the realised family-wise error rate per null population with a
Wilson interval, against the nominal level.

**Q2 -- Does calibration fix localization?** A calibrated *decision* says
"something changed"; it does not say which feature. Permuting a column destroys
every dependency of that feature while leaving its marginal untouched, and the
max-edge aggregation used by the published path then credits the wrong endpoint
of the changed edge. Greedy edge peeling plus an explained-partner tier is
supposed to fix that. This stage measures recall@1/3/5, MRR, NDCG and
precision against a uniform-random chance line, with paired Wilcoxon tests
(Holm-corrected) against the new method.

**Q3 -- Which part of the change matters?** Ablations over the same instances:
permutation vs asymptotic calibration, peeling vs max-edge aggregation, joint
alpha-splitting vs double dipping, Gaussian-copula normal scores vs raw ranks vs
raw Pearson, and marginal-only vs relational-only.

Everything is paired by seed: each method sees the exact same reference and
current windows. Chance is computed analytically from ``(d, |truth|)``.

Usage::

    python -m experiments.calibrated_study --output results/calibrated
    python -m experiments.calibrated_study --output results/calibrated \
        --prepared data/processed/cicids2017_improved
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

from experiments.calibrated_data import (
    LOCALIZATION_CONDITIONS,
    Injection,
    apply_injection,
    real_window,
    synthetic_pool,
)
from experiments.config import ExperimentConfig
from experiments.io import ResultEnvelope, load_completed_result, write_result_atomic
from experiments.metrics.attribution import evaluate_ranking
from experiments.provenance import capture_provenance
from experiments.stats import (
    PairedComparison,
    block_sizes,
    chance_line,
    holm_bonferroni,
    null_rejection_metrics,
    paired_comparison,
)
from vigil.attribution import compute_decomposed_scores
from vigil.calibration import compute_calibrated_scores

# scipy falls back from the exact to the asymptotic KS null whenever the exact
# recursion fails (it does, routinely, on tied columns of this size). The fallback
# is the documented behaviour we rely on, so the warning is noise in the log.
warnings.filterwarnings(
    "ignore",
    message="ks_2samp: Exact calculation unsuccessful",
    category=RuntimeWarning,
)

STUDY_VERSION = 2
N_FEATURES = 20
WINDOW = 400
BLOCK_SIZE = 800
N_BLOCKS = 20
DEFAULT_NULL_TRIALS = 500
DEFAULT_TRIALS = 20
DEFAULT_PERMUTATIONS = 199
DEFAULT_ALPHA = 0.05
KS = (1, 3, 5, 10)
DEFAULT_SEEDS = tuple(range(100, 100 + DEFAULT_TRIALS))
MIN_CORRELATION_SAMPLES = 4
NDIM = 2
SYNTHETIC_POPULATIONS = ("gaussian", "zero_inflated_tied", "multivariate_t3")
REAL_DATASETS = {"real_tuesday": "validation", "real_heldout": "test"}

# Method registry. Ordered so that tables read baseline -> ablation -> proposed.
# Canonical reporting order: published pathway first, then the three null-control
# alternatives, then the calibrated decision policies, then the optional
# rank-copula variant (present only when the transform is enabled).
METHODS: tuple[str, ...] = (
    "decomposed_asymptotic",
    "decomposed_bonferroni",
    "ks_asymptotic",
    "copula_asymptotic",
    "ks_pearson_asymptotic",
    "pearson_asymptotic",
    "peeling_joint",
    "maxedge_joint",
    "peeling_separate",
    "peeling_rank_transform",
)
BASELINE_METHOD = "decomposed_asymptotic"
PROPOSED_METHOD = "peeling_joint"


@dataclass(frozen=True)
class Bundle:
    """Every score vector computed once per (reference, current) pair."""

    cal: object
    cal_rank: object | None
    decomposed: tuple[np.ndarray, np.ndarray, np.ndarray]
    ks_pearson: tuple[np.ndarray, np.ndarray, np.ndarray]


def _evidence_threshold(alpha: float) -> float:
    return float(-np.log10(alpha))


def _bonferroni_evidence(statistic: np.ndarray, p_value: np.ndarray, m: float):
    """``-log10(min(1, m * p))`` with a monotone statistic tie-break."""
    adjusted = np.clip(m * p_value, 1e-300, 1.0)
    return -np.log10(adjusted) + 1e-9 * statistic


def _ks_pearson_scores(
    ref: np.ndarray, cur: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """KS plus *raw* Pearson: the missing ablation from the review.

    Identical protocol to the published decomposed path except that the
    relational statistic is the plain Pearson correlation of the raw values
    instead of the Gaussian-copula (rank-normal) correlation. If the two agree,
    the normal-score transform is doing no work and should be dropped from the
    story; if they diverge, the transform is load-bearing.
    """
    n_ref, d = ref.shape
    n_cur = cur.shape[0]
    if n_ref < MIN_CORRELATION_SAMPLES or n_cur < MIN_CORRELATION_SAMPLES or d < NDIM:
        zeros = np.zeros(d)
        return zeros, zeros.copy(), zeros.copy()
    p_ks = np.array(
        [stats.ks_2samp(ref[:, j], cur[:, j]).pvalue for j in range(d)], dtype=float
    )
    marginal_ev = _bonferroni_evidence(np.zeros(d), p_ks, float(d))
    rows, cols = np.triu_indices(d, 1)
    r_ref = np.corrcoef(ref, rowvar=False)[rows, cols]
    r_cur = np.corrcoef(cur, rowvar=False)[rows, cols]
    clip = 0.999999
    z_ref = np.arctanh(np.clip(np.nan_to_num(r_ref), -clip, clip))
    z_cur = np.arctanh(np.clip(np.nan_to_num(r_cur), -clip, clip))
    se = np.sqrt(1.0 / (n_ref - 3.0) + 1.0 / (n_cur - 3.0))
    z_stat = np.abs(z_cur - z_ref) / se
    p_pair = 2.0 * stats.norm.sf(z_stat)
    n_pairs = float(len(rows))
    pair_ev = _bonferroni_evidence(z_stat, p_pair, n_pairs)
    relational_ev = np.zeros(d)
    np.maximum.at(relational_ev, rows, pair_ev)
    np.maximum.at(relational_ev, cols, pair_ev)
    return marginal_ev, relational_ev, np.maximum(marginal_ev, relational_ev)


def build_bundle(
    ref: np.ndarray,
    cur: np.ndarray,
    *,
    n_permutations: int,
    seed: int,
    include_rank_transform: bool = True,
    alpha: float = DEFAULT_ALPHA,
) -> Bundle:
    """Compute every statistic once; all methods are derived from this.

    ``alpha`` is threaded into the calibrated path as well, so ``--alpha`` moves
    every method and not only the asymptotic ones.
    """
    cal = compute_calibrated_scores(
        ref, cur, alpha=alpha, n_permutations=n_permutations, seed=seed
    )
    cal_rank = (
        compute_calibrated_scores(
            ref,
            cur,
            alpha=alpha,
            n_permutations=n_permutations,
            seed=seed,
            copula_transform="ranks",
        )
        if include_rank_transform
        else None
    )
    decomposed = compute_decomposed_scores(ref, cur)
    ks_pearson = _ks_pearson_scores(ref, cur)
    return Bundle(
        cal=cal, cal_rank=cal_rank, decomposed=decomposed, ks_pearson=ks_pearson
    )


def _asymptotic_outputs(
    bundle: Bundle, *, alpha: float
) -> dict[str, tuple[np.ndarray, bool]]:
    """Published-pathway variants: asymptotic p-values, three statistic choices."""
    thr = _evidence_threshold(alpha)
    marg, rel, dec_combined = bundle.decomposed
    _, kp_rel, kp_combined = bundle.ks_pearson
    return {
        "decomposed_asymptotic": (dec_combined, bool(np.any(dec_combined >= thr))),
        "decomposed_bonferroni": (
            dec_combined,
            bool(np.any(dec_combined >= _evidence_threshold(alpha / 2.0))),
        ),
        "ks_asymptotic": (marg, bool(np.any(marg >= thr))),
        "copula_asymptotic": (rel, bool(np.any(rel >= thr))),
        "ks_pearson_asymptotic": (
            kp_combined,
            bool(np.any(kp_combined >= thr)),
        ),
        "pearson_asymptotic": (kp_rel, bool(np.any(kp_rel >= thr))),
    }


def _calibrated_outputs(
    bundle: Bundle, *, alpha: float
) -> dict[str, tuple[np.ndarray, bool]]:
    """Permutation-calibrated variants: peeling, aggregation, alpha policy."""
    cal = bundle.cal
    alpha_marg = float(cal.metadata.get("alpha_marginal", alpha))
    alpha_rel = float(cal.metadata.get("alpha_relational", alpha))
    joint_reject = bool(
        np.any(cal.marginal_pvalues <= alpha_marg)
        or cal.edge_pvalues.min(axis=1).min() <= alpha_rel
    )
    separate_reject = bool(
        np.any(np.asarray(cal.metadata["marginal_pvalues"]) <= alpha)
        or cal.metadata["separate_selected_features"]
    )
    out: dict[str, tuple[np.ndarray, bool]] = {
        "peeling_joint": (cal.combined_scores, joint_reject),
        "maxedge_joint": (cal.maxedge_scores, joint_reject),
        "peeling_separate": (cal.separate_scores, separate_reject),
    }
    if bundle.cal_rank is not None:
        rank = bundle.cal_rank
        out["peeling_rank_transform"] = (
            rank.combined_scores,
            bool(
                np.any(rank.marginal_pvalues <= rank.metadata["alpha_marginal"])
                or rank.edge_pvalues.min(axis=1).min()
                <= rank.metadata["alpha_relational"]
            ),
        )
    return out


def method_outputs(
    bundle: Bundle, *, alpha: float = DEFAULT_ALPHA
) -> dict[str, tuple[np.ndarray, bool]]:
    """Ranking scores and the family-wise decision for every registered method.

    A method "rejects" when any feature survives its own threshold policy. The
    decision and the ranking are separate: calibration changes both, peeling
    changes only the ranking, and alpha-splitting changes only the decision.
    """
    return {
        **_asymptotic_outputs(bundle, alpha=alpha),
        **_calibrated_outputs(bundle, alpha=alpha),
    }


def _dataset_specs(prepared: Path | None) -> dict[str, dict]:
    """Named datasets, loaded lazily so a synthetic-only run needs no data."""
    specs: dict[str, dict] = {
        name: {"kind": "synthetic", "name": name} for name in SYNTHETIC_POPULATIONS
    }
    if prepared is None:
        return specs
    for name, split in REAL_DATASETS.items():
        specs[name] = {"kind": "real", "split": split}
    return specs


def _load_pools(prepared: Path | None, split: str) -> dict | None:
    if prepared is None:
        return None
    if split == "validation":
        from experiments.mechanism_data import load_real_pools

        return load_real_pools(prepared)
    from experiments.decomposed_study import load_heldout_pools

    return load_heldout_pools(prepared)


def _instance(
    spec: dict,
    pools: dict | None,
    injection: Injection,
    seed: int,
    *,
    n_blocks: int = N_BLOCKS,
) -> tuple[np.ndarray, np.ndarray, tuple[int, ...]]:
    """Build one paired (reference, current, truth) instance."""
    rng = np.random.default_rng([int(seed), 11])
    if spec["kind"] == "synthetic":
        pool = synthetic_pool(spec["name"], rng, 2 * WINDOW, N_FEATURES)
        ref, cur = pool[:WINDOW], pool[WINDOW:]
    else:
        if pools is None:
            raise ValueError("real dataset requested without pools")
        ref, cur = real_window(
            pools, seed=seed, window=WINDOW, block_size=BLOCK_SIZE, n_blocks=n_blocks
        )
    return (ref, *apply_injection(ref, cur, injection, rng))


def _available_blocks(pools: dict, cap: int) -> int:
    """How many disjoint blocks the real pool can supply, up to ``cap``."""
    rows = np.asarray(pools["validation"]).shape[0]
    return max(1, min(cap, rows // BLOCK_SIZE))


def run_null_stage(
    output: Path,
    provenance,
    *,
    trials: int,
    n_permutations: int,
    prepared: Path | None,
    alpha: float,
    include_real: bool,
    include_rank_transform: bool,
) -> dict:
    """Family-wise error rate per null population (nothing injected)."""
    specs = _dataset_specs(prepared if include_real else None)
    results: dict[str, dict] = {}
    for name, spec in specs.items():
        config = ExperimentConfig(
            dataset="calibrated_study_null",
            method=name,
            seed=0,
            params={
                "study_version": STUDY_VERSION,
                "trials": trials,
                "n_permutations": n_permutations,
                "alpha": alpha,
                "window": WINDOW,
                "n_features": N_FEATURES,
                "rank_transform": include_rank_transform,
                "dataset_kind": spec["kind"],
            },
        )
        completed = load_completed_result(output, config, provenance)
        if completed is not None:
            results[name] = completed.metrics
            print(f"[null] {name}: cached", flush=True)
            continue
        pools = None
        if spec["kind"] == "real":
            pools = _load_pools(prepared, spec["split"])
        n_blocks = (
            _available_blocks(pools, cap=trials) if pools is not None else N_BLOCKS
        )
        outcomes: dict[str, list[int]] = {}
        blocks: list[int] = []
        started = time.perf_counter()
        for trial in range(trials):
            seed = 10_000 + trial
            ref, cur, _ = _instance(
                spec, pools, Injection("none"), seed=seed, n_blocks=n_blocks
            )
            blocks.append(seed % n_blocks)
            bundle = build_bundle(
                ref,
                cur,
                n_permutations=n_permutations,
                seed=trial,
                include_rank_transform=include_rank_transform,
                alpha=alpha,
            )
            for method, (_, rejected) in method_outputs(bundle, alpha=alpha).items():
                outcomes.setdefault(method, []).append(int(rejected))
        elapsed = time.perf_counter() - started
        metrics = {
            "trials": trials,
            "blocks": {
                "distinct": len(set(blocks)),
                "per_block": block_sizes(blocks),
                "nominal_window": N_BLOCKS,
            },
            "methods": {
                method: null_rejection_metrics(flags, blocks, alpha)
                for method, flags in outcomes.items()
            },
        }

        write_result_atomic(
            output,
            ResultEnvelope(
                config.canonical_dict(),
                provenance,
                metrics,
                metadata={
                    "stage": "null_calibration",
                    "population": name,
                    "timings": {"seconds_per_trial": elapsed / trials},
                },
            ),
        )
        results[name] = metrics
        joint = metrics["methods"]["peeling_joint"]["fwer"]
        decomposed = metrics["methods"]["decomposed_asymptotic"]["fwer"]
        print(
            f"[null] {name}: joint={joint:.3f} decomposed={decomposed:.3f} "
            f"blocks={metrics['blocks']['distinct']} ({elapsed / trials:.2f}s/trial)",
            flush=True,
        )
    return {
        "populations": results,
        "alpha": alpha,
        "n_permutations": n_permutations,
    }


def run_localization_stage(
    output: Path,
    provenance,
    *,
    seeds: tuple[int, ...],
    n_permutations: int,
    prepared: Path | None,
    alpha: float,
    include_real: bool,
    include_rank_transform: bool,
    conditions: tuple[Injection, ...] = LOCALIZATION_CONDITIONS,
) -> dict:
    """Recall/MRR/NDCG per (dataset, condition, method), paired by seed."""
    specs = _dataset_specs(prepared if include_real else None)
    instances: list[dict] = []
    for name, spec in specs.items():
        pools = _load_pools(prepared, spec["split"]) if spec["kind"] == "real" else None
        for injection in conditions:
            for seed in seeds:
                config = ExperimentConfig(
                    dataset="calibrated_study_localization",
                    method=f"{name}|{injection.label}",
                    seed=seed,
                    params={
                        "study_version": STUDY_VERSION,
                        "condition": injection.label,
                        "n_permutations": n_permutations,
                        "alpha": alpha,
                        "window": WINDOW,
                        "n_features": N_FEATURES,
                        "rank_transform": include_rank_transform,
                        "dataset_kind": spec["kind"],
                    },
                )
                completed = load_completed_result(output, config, provenance)
                if completed is not None:
                    instances.append(completed.metrics["instance"])
                    continue
                ref, cur, truth = _instance(spec, pools, injection, seed=seed)
                bundle = build_bundle(
                    ref,
                    cur,
                    n_permutations=n_permutations,
                    seed=seed,
                    include_rank_transform=include_rank_transform,
                )
                record = {
                    "dataset": name,
                    "condition": injection.label,
                    "seed": int(seed),
                    "truth": list(truth),
                    "truth_size": len(truth),
                    "methods": {},
                }
                for method, (scores, rejected) in method_outputs(
                    bundle, alpha=alpha
                ).items():
                    ranking = evaluate_ranking(scores, truth, ks=KS) if truth else None
                    record["methods"][method] = {
                        "rejected": bool(rejected),
                        "ranking": ranking,
                    }
                write_result_atomic(
                    output,
                    ResultEnvelope(
                        config.canonical_dict(),
                        provenance,
                        {"instance": record},
                        # Timing is metadata, never metrics: two identical
                        # re-runs have to compare equal on the metrics payload.
                        metadata={
                            "stage": "localization",
                            "timings": dict(bundle.cal.timings()),
                        },
                    ),
                )
                instances.append(record)
        print(
            f"[localization] {name}: {len(conditions)} conditions x {len(seeds)} seeds",
            flush=True,
        )
    return aggregate_localization(instances, alpha=alpha)


def _cell_means(
    records: list[dict], metric_names: list[str]
) -> tuple[dict[str, dict], dict[str, int], dict[str, np.ndarray]]:
    """Per-method mean metric values, rejection counts and recall@3 vectors."""
    seen = {method for record in records for method in record["methods"]}
    # Sorted so that aggregation, comparisons and the rendered tables do not depend
    # on set-iteration order, which changes with PYTHONHASHSEED between runs.
    ordered = sorted(seen)
    values: dict[str, dict[str, list[float]]] = {
        method: {m: [] for m in metric_names} for method in ordered
    }
    recall3: dict[str, list[float]] = {method: [] for method in ordered}
    rejections = dict.fromkeys(ordered, 0)
    for record in records:
        for method, payload in record["methods"].items():
            rejections[method] += int(payload["rejected"])
            ranking = payload["ranking"]
            if not ranking:
                continue
            for metric in metric_names:
                value = ranking.get(metric)
                if value is not None:
                    values[method][metric].append(float(value))
            top3 = ranking.get(f"recall@{KS[1]}")
            if top3 is not None:
                recall3[method].append(float(top3))
    means = {
        method: {
            metric: (float(np.mean(vals)) if vals else None)
            for metric, vals in per_metric.items()
        }
        for method, per_metric in values.items()
    }
    for method in means:
        # Every record in a cell carries the same methods, so this denominator
        # equals the number of instances that actually produced a decision.
        means[method]["detection_rate"] = rejections[method] / len(records)
    vectors = {method: np.asarray(recall3[method], dtype=float) for method in ordered}
    return means, rejections, vectors


def _cell_comparisons(
    vectors: dict[str, np.ndarray],
    *,
    label: str,
    dataset: str,
    condition: str,
    alpha: float,
) -> list[dict]:
    """Paired recall@3 comparisons against the proposed method, Holm-corrected."""
    candidate = vectors[PROPOSED_METHOD]
    if candidate.size == 0:
        return []
    p_values: dict[str, float] = {}
    pending: list[tuple[str, PairedComparison]] = []
    for method, baseline in vectors.items():
        if method == PROPOSED_METHOD or baseline.size != candidate.size:
            continue
        comparison = paired_comparison(
            candidate, baseline, candidates=PROPOSED_METHOD, baseline_name=method
        )
        p_values[method] = comparison.p_value
        pending.append((method, comparison))
    adjusted = holm_bonferroni(p_values)
    output: list[dict] = []
    for method, comparison in pending:
        payload = comparison.as_dict()
        payload.update(
            {
                "cell": label,
                "dataset": dataset,
                "condition": condition,
                "metric": f"recall@{KS[1]}",
                "holm_p_value": adjusted.get(method),
                "rejected": adjusted.get(method, 1.0) <= alpha,
            }
        )
        output.append(payload)
    return output


def aggregate_localization(
    instances: list[dict], *, alpha: float = DEFAULT_ALPHA
) -> dict:
    """Mean metrics per cell plus paired Holm-corrected comparisons."""
    metric_names = [f"recall@{k}" for k in KS] + [
        "mrr",
        f"precision@{KS[0]}",
        f"ndcg@{KS[1]}",
    ]
    cells: dict[tuple[str, str], list[dict]] = {}
    for record in instances:
        cells.setdefault((record["dataset"], record["condition"]), []).append(record)
    # Aggregate in seed order so the floating-point means are bit-identical no matter
    # how the cached instances arrived (glob order, resumed runs, parallel stages).
    for records in cells.values():
        records.sort(key=lambda record: int(record["seed"]))

    aggregated: dict[str, dict] = {}
    comparisons: list[dict] = []
    for (dataset, condition), records in cells.items():
        truth_size = records[0]["truth_size"]
        label = f"{dataset}:{condition}"
        means, _, vectors = _cell_means(records, metric_names)
        aggregated[label] = {
            "truth_size": truth_size,
            "n_instances": len(records),
            "chance": chance_line(N_FEATURES, truth_size, KS) if truth_size else {},
            "methods": means,
        }
        if truth_size:
            comparisons.extend(
                _cell_comparisons(
                    vectors,
                    label=label,
                    dataset=dataset,
                    condition=condition,
                    alpha=alpha,
                )
            )
    return {
        "cells": aggregated,
        "comparisons": comparisons,
        "alpha": alpha,
        "d": N_FEATURES,
        "proposed": PROPOSED_METHOD,
        "baseline": BASELINE_METHOD,
        "n_datasets": len({key[0] for key in cells}),
        "n_conditions": len({key[1] for key in cells}),
    }


def _markdown(results: dict) -> str:
    """Render the headline tables as markdown for the docs page."""
    lines: list[str] = []
    null = results.get("null", {}).get("populations", {})
    if null:
        lines += [
            "### Family-wise error rate with nothing injected (nominal 5%)",
            "",
            "| null population | decomposed (asymptotic) | calibrated joint "
            "| calibrated, alpha not split |",
            "| --- | --- | --- | --- |",
        ]
        for name, payload in null.items():
            methods = payload["methods"]
            row = [name]
            for method in (
                "decomposed_asymptotic",
                "peeling_joint",
                "peeling_separate",
            ):
                entry = methods[method]
                row.append(
                    f"{100 * entry['fwer']:.1f}% "
                    f"[{100 * entry['ci95'][0]:.1f}, {100 * entry['ci95'][1]:.1f}]"
                )
            lines.append("| " + " | ".join(row) + " |")
        distinct = {
            name: payload["blocks"]["distinct"] for name, payload in null.items()
        }
        counts = ", ".join(f"{name}={count}" for name, count in distinct.items())
        lines += [
            "",
            f"Brackets are 95% Wilson intervals over {results['null_trials']} draws.",
            "Real-data trials resample a fixed set of disjoint blocks, so those",
            f"draws are not independent: the distinct block counts are {counts},",
            "and `ci95_block` in `summary.json` is the cluster bootstrap over",
            "blocks (the interval to prefer for the real rows).",
            "",
        ]
    loc = results.get("localization", {}).get("cells", {})
    if loc:
        lines += [
            "### Recall@3 by condition (mean over seeds)",
            "",
            "| dataset | condition | chance r@1 | chance r@3 | decomposed "
            "| max-edge | peeling | peeling r@1 | rank transform |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for label, entry in loc.items():
            dataset, condition = label.split(":", 1)
            chance1 = entry["chance"].get("recall@1")
            chance3 = entry["chance"].get("recall@3")

            def _fmt(value):
                return f"{value:.3f}" if value is not None else "-"

            methods = entry["methods"]
            cells = [
                dataset,
                condition,
                _fmt(chance1),
                _fmt(chance3),
                _fmt(methods["decomposed_asymptotic"]["recall@3"]),
                _fmt(methods["maxedge_joint"]["recall@3"]),
                _fmt(methods["peeling_joint"]["recall@3"]),
                _fmt(methods["peeling_joint"]["recall@1"]),
                _fmt(methods.get("peeling_rank_transform", {}).get("recall@3")),
            ]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
        lines += [
            "Per-instance cost is recorded in each result envelope's metadata",
            "(`timings.total_s`), never in the metrics payload, so identical",
            "re-runs compare equal.",
            "",
        ]
    return "\n".join(lines)


_TIMING_KEYS = frozenset({"wall_seconds", "markdown", "timings"})


def _comparable(value: Any) -> Any:
    """Strip wall-clock fields throughout: a resumed run disagrees on those."""
    if isinstance(value, dict):
        return {
            key: _comparable(item)
            for key, item in value.items()
            if key not in _TIMING_KEYS
        }
    if isinstance(value, list):
        return [_comparable(item) for item in value]
    return value


def _check_resume(cached: dict, fresh: dict) -> None:
    """Fail loudly if a cached population disagrees with the recomputed one.

    Only keys present in both summaries are compared: a partial summary (for
    example one written by a ``--skip-null`` run) is completed, not rejected, and
    the wall-clock fields are excluded because they legitimately differ.
    """
    comparable_cached = _comparable(cached)
    comparable_fresh = _comparable(fresh)
    for key, value in comparable_cached.items():
        if key not in comparable_fresh:
            continue
        if comparable_fresh[key] != value:
            raise ValueError(f"summary mismatch for an existing result: {key}")


def run_study(
    output: Path,
    *,
    null_trials: int = DEFAULT_NULL_TRIALS,
    trials: int = DEFAULT_TRIALS,
    n_permutations: int = DEFAULT_PERMUTATIONS,
    prepared: Path | None = None,
    alpha: float = DEFAULT_ALPHA,
    seeds: tuple[int, ...] | None = None,
    include_real: bool = True,
    include_rank_transform: bool = True,
    skip_null: bool = False,
    skip_localization: bool = False,
) -> Path:
    """Run both stages and write one summary result plus a markdown render."""
    if seeds is None:
        seeds = tuple(range(100, 100 + trials))
    if len(set(seeds)) != len(seeds) or any(int(s) < 0 for s in seeds):
        raise ValueError("seeds must be distinct and non-negative")
    if null_trials < 1 or n_permutations < 1:
        raise ValueError("trials and permutations must be positive")
    # The joint calibrated policy splits alpha between the marginal and the
    # relational families, so the smallest attainable Monte-Carlo p-value
    # 1/(B+1) has to fit under alpha/2 or no calibrated method can ever reject.
    smallest_p = 1.0 / (n_permutations + 1)
    if smallest_p > alpha / 2.0:
        raise ValueError(
            f"n_permutations={n_permutations} is too small: the smallest "
            f"attainable p-value {smallest_p:.4f} exceeds alpha/2={alpha / 2.0:.4f}"
        )
    output = Path(output)
    provenance = capture_provenance(
        [Path(prepared) / "manifest.json"] if prepared is not None else []
    )
    started = time.perf_counter()
    results: dict = {
        "study_version": STUDY_VERSION,
        "n_permutations": n_permutations,
        "alpha": alpha,
        "null_trials": null_trials,
        "seeds": list(seeds),
        # The renderer reads summary.json only, so the facts needed to say what
        # produced these numbers have to travel with the numbers.
        "prepared": str(prepared) if prepared is not None else None,
        "include_real": include_real,
        "rank_transform": include_rank_transform,
        "window": WINDOW,
        "n_features": N_FEATURES,
        "provenance": {
            "identity_hash": provenance.identity_hash,
            "git_commit": provenance.git_commit,
            "git_dirty": provenance.git_dirty,
            "source_tree_hash": provenance.source_tree_hash,
            "python_version": provenance.python_version,
            "dataset_checksums": provenance.dataset_checksums,
        },
    }
    if not skip_null:
        results["null"] = run_null_stage(
            output,
            provenance,
            trials=null_trials,
            n_permutations=n_permutations,
            prepared=prepared,
            alpha=alpha,
            include_real=include_real,
            include_rank_transform=include_rank_transform,
        )
    if not skip_localization:
        results["localization"] = run_localization_stage(
            output,
            provenance,
            seeds=seeds,
            n_permutations=n_permutations,
            prepared=prepared,
            alpha=alpha,
            include_real=include_real,
            include_rank_transform=include_rank_transform,
        )
    results["wall_seconds"] = time.perf_counter() - started
    results["markdown"] = _markdown(results)

    config = ExperimentConfig(
        dataset="calibrated_study",
        method="summary",
        seed=0,
        params={
            "study_version": STUDY_VERSION,
            "n_permutations": n_permutations,
            "alpha": alpha,
            "null_trials": null_trials,
            "seeds": list(seeds),
            "include_real": include_real and prepared is not None,
            "rank_transform": include_rank_transform,
        },
    )
    root = output / "summary"
    completed = load_completed_result(root, config, provenance)
    if completed is not None:
        _check_resume(completed.metrics, results)
    if completed is None:
        write_result_atomic(
            root,
            ResultEnvelope(
                config.canonical_dict(),
                provenance,
                results,
                metadata={
                    "stage": "calibrated_attribution_study",
                    "protocol_complete": prepared is not None
                    and null_trials >= DEFAULT_NULL_TRIALS
                    and len(seeds) >= DEFAULT_TRIALS,
                },
            ),
        )
    (output / "summary.md").write_text(_markdown(results) + "\n", encoding="utf-8")
    (output / "summary.json").write_text(
        json.dumps(results, indent=2, sort_keys=True), encoding="utf-8"
    )
    return root / config.config_hash / provenance.identity_hash / "result.json"


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, default=None)
    parser.add_argument("--null-trials", type=int, default=DEFAULT_NULL_TRIALS)
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--n-permutations", type=int, default=DEFAULT_PERMUTATIONS)
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    parser.add_argument("--no-real", action="store_true")
    parser.add_argument("--no-rank-transform", action="store_true")
    parser.add_argument("--skip-null", action="store_true")
    parser.add_argument(
        "--skip-localization",
        action="store_true",
        help="run only the error-rate stage (long runs are easier to resume split)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="tiny run for smoke testing (not paper numbers)",
    )
    args = parser.parse_args(argv)
    null_trials, trials, permutations = (
        args.null_trials,
        args.trials,
        args.n_permutations,
    )
    if args.quick:
        null_trials, trials, permutations = 6, 2, 49
    return run_study(
        args.output,
        null_trials=null_trials,
        trials=trials,
        n_permutations=permutations,
        prepared=args.prepared,
        alpha=args.alpha,
        include_real=not args.no_real,
        include_rank_transform=not args.no_rank_transform,
        skip_null=args.skip_null,
        skip_localization=args.skip_localization,
    )


if __name__ == "__main__":
    print(main(), flush=True)
