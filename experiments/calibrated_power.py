"""Analytic power bound for the decomposed marginal pathway.

The published ``decomposed`` mode declares attribution at ``E_marg >= 1.30`` and
per-feature drift at ``E_marg >= 2.60`` (``_evidence_threshold`` of
``vigil/attribution.py`` for ``alpha = 0.5`` and ``0.05``). ``E_marg`` is nothing
but ``-log10(clip(p_KS * d, 1e-300, 1)) + 1e-3 * D``, so whether that pathway
*can* attribute a real univariate shift is a question about KS power alone, not
about autoencoders. This script answers it:

* ``k`` of the ``d`` features is shifted by ``delta`` standard deviations;
* only ``fraction_rows`` of the current window is shifted -- a sub-population
  shift, as in the ``sparse`` conditions of ``experiments/attribution_datasets``,
  which is where the pathway loses the evidence it needs to attribute;
* a draw is *detectable* when the strongest shifted feature reaches the evidence
  threshold. With no shift at all the same statistic is a false alarm, whose rate
  is what the permutation calibration of ``vigil/calibration.py`` controls.

Every cell also reports the calibrated joint detection rate at ``alpha = 0.05``,
so the table separates "the statistic cannot reach the threshold" from "the
calibration was wrong".

Run::

    python -m experiments.calibrated_power --output artifacts/runs/calibrated-power-v1
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import stats

from experiments.calibrated_study import DEFAULT_ALPHA
from experiments.provenance import capture_provenance
from vigil.calibration import compute_calibrated_scores

STUDY_VERSION = 1
DEFAULT_TRIALS = 200
# The study compares methods by moving a nominal alpha through
# ``-log10(alpha)``; the loose row is the decomposition's own synthesis policy.
LOOSE_ALPHA = 0.5


def evidence_threshold(alpha: float) -> float:
    """Evidence level that a Bonferroni-corrected p-value ``<= alpha`` reaches."""
    return float(-np.log10(alpha))


warnings.filterwarnings(
    "ignore", message=".*Exact calculation unsuccessful.*", category=RuntimeWarning
)
warnings.filterwarnings(
    "ignore", message=".*invalid value encountered in divide.*", category=RuntimeWarning
)


@dataclass(frozen=True)
class Cell:
    """One row of the power grid."""

    fraction_rows: float
    delta: float
    n_shifted_features: int = 2

    @property
    def name(self) -> str:
        return (
            f"rows{self.fraction_rows:g}_delta{self.delta:g}_k{self.n_shifted_features}"
        )


GRID = tuple(
    Cell(fraction_rows=fraction, delta=delta)
    for fraction in (0.05, 0.1, 0.2, 0.5, 1.0)
    for delta in (0.2, 0.5)
)


def make_case(
    cell: Cell, *, seed: int, window: int, d: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reference/current pair with a sub-population mean shift on ``k`` features."""
    rng = np.random.default_rng(seed)
    ref = rng.standard_normal((window, d))
    cur = ref.copy()
    features = rng.choice(d, size=cell.n_shifted_features, replace=False)
    moved = max(1, round(cell.fraction_rows * window))
    rows = rng.choice(window, size=moved, replace=False)
    cur[np.ix_(rows, sorted(features))] += cell.delta
    return ref, cur, np.sort(features)


def marginal_evidence(ref: np.ndarray, cur: np.ndarray) -> np.ndarray:
    """Mirror of the marginal term of ``compute_decomposed_scores``."""
    d = ref.shape[1]
    pairs = np.asarray(
        [stats.ks_2samp(ref[:, j], cur[:, j]) for j in range(d)], dtype=float
    )
    # ``ks_2samp`` returns ``(statistic, pvalue)`` per feature; stacking the
    # results keeps the two columns typed across scipy versions.
    statistics = pairs[:, 0]
    pvalues = pairs[:, 1]
    return (
        np.maximum(-np.log10(np.clip(pvalues * max(d, 1), 1e-300, 1.0)), 0.0)
        + 1e-3 * statistics
    )


def joint_rejects(ref: np.ndarray, cur: np.ndarray, *, seed: int, n_permutations: int):
    """Permutation-calibrated joint decision at ``alpha = 0.05``."""
    cal = compute_calibrated_scores(
        ref,
        cur,
        alpha=DEFAULT_ALPHA,
        n_permutations=n_permutations,
        seed=seed,
    )
    alpha_marg = float(cal.metadata.get("alpha_marginal", DEFAULT_ALPHA))
    alpha_rel = float(cal.metadata.get("alpha_relational", DEFAULT_ALPHA))
    return bool(
        np.any(cal.marginal_pvalues <= alpha_marg)
        or cal.edge_pvalues.min(axis=1).min() <= alpha_rel
    )


def run_cell(
    cell: Cell,
    *,
    trials: int,
    seed: int,
    window: int,
    d: int,
    n_permutations: int,
) -> dict:
    """Simulate one grid cell over ``trials`` independent draws."""
    thresholds = {
        "declared": evidence_threshold(DEFAULT_ALPHA),
        "loose": evidence_threshold(LOOSE_ALPHA),
    }
    hits = {name: 0 for name in thresholds}
    calibrated = 0
    best_ranks: list[int] = []
    max_evidence: list[float] = []
    for trial in range(trials):
        case_seed = seed + trial
        ref, cur, truth = make_case(cell, seed=case_seed, window=window, d=d)
        evidence = marginal_evidence(ref, cur)
        peak = float(evidence[truth].max())
        max_evidence.append(peak)
        for name, threshold in thresholds.items():
            hits[name] += int(peak >= threshold)
        order = np.argsort(-evidence, kind="stable")
        best_ranks.append(int(np.flatnonzero(np.isin(order, truth))[0]) + 1)
        calibrated += int(
            joint_rejects(ref, cur, seed=case_seed, n_permutations=n_permutations)
        )
    return {
        "cell": cell.name,
        "fraction_rows": cell.fraction_rows,
        "delta": cell.delta,
        "n_shifted_features": cell.n_shifted_features,
        "rows_moved": max(1, round(cell.fraction_rows * window)),
        "thresholds": thresholds,
        "detection": {name: hits[name] / trials for name in thresholds},
        "calibrated_joint": calibrated / trials,
        "mean_max_evidence": float(np.mean(max_evidence)),
        "median_best_rank": float(np.median(best_ranks)),
    }


def run_study(
    output: Path,
    *,
    trials: int,
    seed: int,
    window: int,
    n_features: int,
    n_permutations: int,
    grid: tuple[Cell, ...] = GRID,
) -> dict:
    """Run the grid; an identical cached grid is reused instead of recomputed."""
    provenance = capture_provenance(())
    config = {
        "study_version": STUDY_VERSION,
        "trials": trials,
        "seed": seed,
        "window": window,
        "n_features": n_features,
        "n_permutations": n_permutations,
        "alpha": DEFAULT_ALPHA,
        "loose_alpha": LOOSE_ALPHA,
        "cells": [cell.name for cell in grid],
        "data": "gaussian_reference_plus_copied_current_window",
    }
    path = output / "power.json"
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached.get("config") == config:
            print(f"reusing cached grid: {path}", flush=True)
            return cached

    started = time.time()
    cells: dict[str, dict] = {}
    for index, cell in enumerate(grid):
        cells[cell.name] = run_cell(
            cell,
            trials=trials,
            seed=seed + index * 100_000,
            window=window,
            d=n_features,
            n_permutations=n_permutations,
        )
        result = cells[cell.name]
        print(
            f"[power] {cell.name}: declared={result['detection']['declared']:.3f} "
            f"loose={result['detection']['loose']:.3f} "
            f"calibrated={result['calibrated_joint']:.3f} "
            f"maxE={result['mean_max_evidence']:.2f}",
            flush=True,
        )

    payload = {
        "study_version": STUDY_VERSION,
        "config": config,
        "provenance": provenance.canonical_dict(),
        "wall_seconds": round(time.time() - started, 3),
        "cells": cells,
        "summary": summarize(cells),
    }
    store_json(path, payload)
    return payload


def store_json(path: Path, payload: dict) -> None:
    """Write the artifact in one step so a crash cannot leave a partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    temporary.replace(path)


def summarize(cells: dict[str, dict]) -> dict:
    """Rows the paper quotes: detection per shifted-row fraction."""
    rows: dict[str, dict] = {}
    for cell in cells.values():
        key = f"{cell['fraction_rows']:g}"
        rows.setdefault(key, {"delta_0.2": None, "delta_0.5": None})
        rows[key][f"delta_{cell['delta']:g}"] = {
            "declared": round(cell["detection"]["declared"], 4),
            "loose": round(cell["detection"]["loose"], 4),
            "max_evidence": round(cell["mean_max_evidence"], 3),
        }
    return {
        "rows_by_fraction": rows,
        "thresholds": {
            "declared_0.05": round(evidence_threshold(DEFAULT_ALPHA), 3),
            "loose_0.5": round(evidence_threshold(LOOSE_ALPHA), 3),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--window", type=int, default=400)
    parser.add_argument("--n-features", type=int, default=20)
    parser.add_argument("--n-permutations", type=int, default=199)
    parser.add_argument(
        "--fractions",
        default=None,
        help="comma-separated subset of shifted-row fractions, e.g. 0.05,0.1",
    )
    args = parser.parse_args(argv)
    grid = GRID
    if args.fractions:
        keep = {float(part) for part in args.fractions.split(",")}
        grid = tuple(cell for cell in GRID if cell.fraction_rows in keep)
        if not grid:
            raise SystemExit(f"no grid cell matches --fractions {args.fractions}")

    payload = run_study(
        args.output,
        trials=args.trials,
        seed=args.seed,
        window=args.window,
        n_features=args.n_features,
        n_permutations=args.n_permutations,
        grid=grid,
    )
    print(json.dumps(payload["summary"], indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
