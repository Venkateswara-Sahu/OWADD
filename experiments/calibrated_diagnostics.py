"""Why the asymptotic relational null fails.

The published relational pathway turns each feature into van der Waerden ranks and
tests ``|Delta z|`` against the Fisher-``z`` standard error
``sqrt(1/(n_1-3) + 1/(n_2-3))``. That standard error is exact only for a *bivariate
Gaussian* pair. The rank transform guarantees Gaussian marginals, but it guarantees
nothing about the joint distribution: tail dependence, a non-elliptical copula, or
heavy tails leave the sampling variance of ``Delta z`` larger than Fisher's formula.
The analytic ``p`` is then too small, and with ``d(d-1)/2`` pairs the family-wise
rejection follows even at a modest per-edge inflation.

This script measures the failure and separates the two candidate explanations.
For every edge it records

* ``min_unique`` --- the smaller distinct-value fraction of the two features
  (the *tie* hypothesis), divided into bins,
* ``analytic_p`` --- the Fisher-``z`` family-wise ``p`` (Bonferroni over all pairs),
* ``permutation_p`` --- the Westfall-Young max-statistic ``p`` from
  ``compute_calibrated_scores`` on the same pooled windows.

If ties were the driver, analytic rejections would concentrate in the low bins. If the
joint/dependence assumption is the driver, they spread across bins, appear at unique
fractions near 1, and reappear on tie-free populations such as a multivariate
$t_3$ --- which is what the shipped artifact shows.")

Usage:
    python -m experiments.calibrated_diagnostics \
        --output artifacts/runs/calibrated-diagnostics-v1 \
        --prepared artifacts/prepared/cicids2017-prepared-v1

Writes one result per (dataset, seed) plus ``summary.json`` with the binned table.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

from experiments.calibrated_data import real_window, synthetic_pool
from experiments.calibrated_study import (
    BLOCK_SIZE,
    N_BLOCKS,
    N_FEATURES,
    WINDOW,
    _dataset_specs,
    _load_pools,
)
from experiments.config import ExperimentConfig
from experiments.io import ResultEnvelope, load_completed_result, write_result_atomic
from experiments.provenance import capture_provenance
from vigil.calibration import compute_calibrated_scores

DIAGNOSTIC_VERSION = 2
DEFAULT_SEEDS = tuple(range(20))
UNIQUE_BINS = ((0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0001))
BIN_LABELS = ("<25%", "25-50%", "50-75%", ">75%")


@dataclass(frozen=True)
class Edge:
    """One feature pair and its two competing p-values."""

    i: int
    j: int
    min_unique: float
    abs_z: float
    analytic_p: float
    permutation_p: float


def _rank_transform(matrix: np.ndarray) -> np.ndarray:
    n = matrix.shape[0]
    return stats.norm.ppf(stats.rankdata(matrix, axis=0) / (n + 1.0))


def _corr(matrix: np.ndarray) -> np.ndarray:
    corr = np.corrcoef(matrix, rowvar=False)
    return np.clip(np.nan_to_num(corr, nan=0.0), -1.0 + 1e-12, 1.0 - 1e-12)


def _unique_fraction(matrix: np.ndarray) -> np.ndarray:
    return np.array(
        [len(np.unique(matrix[:, k])) for k in range(matrix.shape[1])]
    ) / len(matrix)


def analytic_edge_pvalues(
    ref: np.ndarray, cur: np.ndarray, *, n_pairs: int
) -> np.ndarray:
    """Fisher-``z`` family-wise p-values, exactly as the published pathway."""

    z_ref = np.arctanh(_corr(_rank_transform(ref)))
    z_cur = np.arctanh(_corr(_rank_transform(cur)))
    se = math.sqrt(1.0 / (len(ref) - 3) + 1.0 / (len(cur) - 3))
    pvalues = 2.0 * (1.0 - stats.norm.cdf(np.abs(z_cur - z_ref) / se))
    np.fill_diagonal(pvalues, 1.0)
    return np.clip(pvalues * n_pairs, 0.0, 1.0)


def edge_records(
    ref: np.ndarray,
    cur: np.ndarray,
    *,
    n_permutations: int,
    seed: int,
) -> list[Edge]:
    n_features = ref.shape[1]
    pairs = n_features * (n_features - 1) // 2
    analytic = analytic_edge_pvalues(ref, cur, n_pairs=pairs)
    calibrated = compute_calibrated_scores(
        ref, cur, n_permutations=n_permutations, seed=seed
    )
    permutation = np.clip(calibrated.edge_pvalues, 0.0, 1.0)
    unique = np.minimum.outer(_unique_fraction(ref), _unique_fraction(cur))
    z_ref = np.arctanh(_corr(_rank_transform(ref)))
    z_cur = np.arctanh(_corr(_rank_transform(cur)))
    abs_z = np.abs(z_cur - z_ref)

    records: list[Edge] = []
    for i in range(n_features):
        for j in range(i + 1, n_features):
            records.append(
                Edge(
                    i=i,
                    j=j,
                    min_unique=float(unique[i, j]),
                    abs_z=float(abs_z[i, j]),
                    analytic_p=float(analytic[i, j]),
                    permutation_p=float(permutation[i, j]),
                )
            )
    return records


def _bin_counts(records: Sequence[Edge], alpha: float) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for label, (low, high) in zip(BIN_LABELS, UNIQUE_BINS):
        members = [r for r in records if low <= r.min_unique < high]
        n = len(members)
        out[label] = {
            "n_edges": n,
            "analytic_rate": (
                sum(1 for r in members if r.analytic_p <= alpha) / n
                if n
                else float("nan")
            ),
            "permutation_rate": (
                sum(1 for r in members if r.permutation_p <= alpha) / n
                if n
                else float("nan")
            ),
            "median_abs_z": (
                float(np.median([r.abs_z for r in members])) if n else float("nan")
            ),
        }
    return out


def analyse(
    ref: np.ndarray,
    cur: np.ndarray,
    *,
    n_permutations: int,
    alpha: float,
    seed: int,
) -> dict[str, Any]:
    records = edge_records(ref, cur, n_permutations=n_permutations, seed=seed)
    return {
        "bins": _bin_counts(records, alpha),
        "n_edges": len(records),
        "analytic_family_reject": any(r.analytic_p <= alpha for r in records),
        "permutation_family_reject": any(r.permutation_p <= alpha for r in records),
        "top_analytic": [
            {
                "i": r.i,
                "j": r.j,
                "min_unique": r.min_unique,
                "abs_z": r.abs_z,
                "analytic_p": r.analytic_p,
                "permutation_p": r.permutation_p,
            }
            for r in sorted(records, key=lambda r: r.analytic_p)[:5]
        ],
        "unique_fraction": sorted(_unique_fraction(ref).tolist()),
    }


def _json_safe(value: Any) -> Any:
    """Replace non-finite floats with ``None`` so the envelope can be written."""
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _aggregate(per_seed: Sequence[dict[str, Any]], alpha: float) -> dict[str, Any]:
    bins: dict[str, Any] = {}
    for label in BIN_LABELS:
        rows = [m["bins"][label] for m in per_seed]
        total_edges = sum(int(row["n_edges"]) for row in rows)
        analytic_hits = sum(
            row["analytic_rate"] * row["n_edges"] for row in rows if row["n_edges"]
        )
        permutation_hits = sum(
            row["permutation_rate"] * row["n_edges"] for row in rows if row["n_edges"]
        )
        bins[label] = {
            "n_edges": total_edges,
            "analytic_rate": analytic_hits / total_edges
            if total_edges
            else float("nan"),
            "permutation_rate": (
                permutation_hits / total_edges if total_edges else float("nan")
            ),
        }
    top = [edge for m in per_seed for edge in m["top_analytic"]]
    return {
        "alpha": alpha,
        "seeds": len(per_seed),
        "family_reject_rate": {
            "analytic": sum(m["analytic_family_reject"] for m in per_seed)
            / max(1, len(per_seed)),
            "permutation": sum(m["permutation_family_reject"] for m in per_seed)
            / max(1, len(per_seed)),
        },
        "bins": bins,
        "top_edges": {
            "n": len(top),
            "mean_min_unique": float(np.mean([e["min_unique"] for e in top]))
            if top
            else float("nan"),
            "mean_analytic_p": float(np.mean([e["analytic_p"] for e in top]))
            if top
            else float("nan"),
            "mean_permutation_p": float(np.mean([e["permutation_p"] for e in top]))
            if top
            else float("nan"),
        },
        "median_unique_fraction": float(
            np.median([u for m in per_seed for u in m["unique_fraction"]])
        )
        if per_seed
        else float("nan"),
    }


def _pct(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "-"
    return f"{value:.1%}"


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Why the asymptotic relational null fails (calibrated diagnostics)",
        "",
        f"alpha = {summary['alpha']}, seeds = {len(summary['seeds'])}",
        "",
        "| dataset | median unique frac | analytic FWER reject "
        "| permutation FWER reject |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, block in summary["datasets"].items():
        fam = block["family_reject_rate"]
        median_unique = block["median_unique_fraction"]
        median_text = "-" if median_unique is None else f"{median_unique:.3f}"
        lines.append(
            f"| {name} | {median_text} | {_pct(fam['analytic'])} | "
            f"{_pct(fam['permutation'])} |"
        )
    lines += [
        "",
        "| dataset | min unique > | edges | analytic | permutation |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for name, block in summary["datasets"].items():
        for label in BIN_LABELS:
            row = block["bins"][label]
            lines.append(
                f"| {name} | {label} | {row['n_edges']} | "
                f"{_pct(row['analytic_rate'])} | {_pct(row['permutation_rate'])} |"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, default=None)
    parser.add_argument("--seeds", type=int, default=len(DEFAULT_SEEDS))
    parser.add_argument("--n-permutations", type=int, default=199)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--datasets", default="")
    args = parser.parse_args(argv)

    output = Path(args.output)
    selected = tuple(x for x in args.datasets.split(",") if x) or None
    specs = _dataset_specs(args.prepared)
    names = list(selected) if selected else list(specs)
    seeds = DEFAULT_SEEDS[: args.seeds]

    dataset_paths = []
    if args.prepared is not None:
        root = Path(args.prepared)
        dataset_paths = [root / "manifest.json", *sorted(root.glob("*.npy"))]
    provenance = capture_provenance(dataset_paths)

    summary: dict[str, Any] = {
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "n_permutations": args.n_permutations,
        "alpha": args.alpha,
        "seeds": list(seeds),
        "datasets": {},
    }
    for name in names:
        spec = specs[name]
        pools = (
            _load_pools(args.prepared, spec["split"])
            if spec["kind"] == "real"
            else None
        )
        per_seed: list[dict[str, Any]] = []
        for seed in seeds:
            config = ExperimentConfig(
                dataset="calibrated_diagnostics",
                method=name,
                seed=seed,
                params={
                    "diagnostic_version": DIAGNOSTIC_VERSION,
                    "n_permutations": args.n_permutations,
                    "alpha": args.alpha,
                    "window": WINDOW,
                    "n_features": N_FEATURES,
                },
            )
            cached = load_completed_result(output, config, provenance)
            if cached is not None:
                per_seed.append(cached.metrics)
                continue
            if spec["kind"] == "real":
                assert pools is not None
                ref, cur = real_window(
                    pools,
                    seed=seed,
                    window=WINDOW,
                    block_size=BLOCK_SIZE,
                    n_blocks=N_BLOCKS,
                )
            else:
                rng = np.random.default_rng(seed)
                pool = synthetic_pool(name, rng, 2 * WINDOW, N_FEATURES)
                ref, cur = pool[:WINDOW], pool[WINDOW:]
            metrics = analyse(
                ref,
                cur,
                n_permutations=args.n_permutations,
                alpha=args.alpha,
                seed=seed,
            )
            write_result_atomic(
                output,
                ResultEnvelope(
                    config=config.canonical_dict(),
                    provenance=provenance,
                    metrics=_json_safe(metrics),
                ),
            )
            per_seed.append(metrics)
            print(f"[diag] {name} seed={seed}", flush=True)
        summary["datasets"][name] = _aggregate(per_seed, args.alpha)

    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "summary.md").write_text(_markdown(summary) + "\n", encoding="utf-8")
    print(_markdown(summary), flush=True)
    return output / "summary.json"


if __name__ == "__main__":
    main()
