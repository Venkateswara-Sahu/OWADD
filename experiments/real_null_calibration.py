"""Null calibration of the attribution pathways on real network flow records.

The synthetic null populations in ``experiments/calibrated_study.py`` are models of
telemetry with the pathologies that motivate the permutation null. This module asks
the same question on recorded traffic --- does a pathway reject when nothing has
changed? NSL-KDD connection records are restricted to the ``normal`` label, so a
reference/current pair is a genuine null: no injected shift, no class-mix drift.

Two disjoint windows are drawn from the same normal-traffic pool per trial. Any
family-wise rejection is therefore a false alarm, and the tie structure that motivates
the permutation null is measured instead of assumed.

Run:
    python -m experiments.real_null_calibration --output artifacts/runs/real-null-v1
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from data.nsl_kdd_loader import DATA_DIR, FEATURE_COLS
from experiments.calibrated_study import build_bundle, method_outputs
from experiments.config import ExperimentConfig
from experiments.io import ResultEnvelope, write_result_atomic
from experiments.provenance import capture_provenance
from experiments.stats import block_sizes, null_rejection_metrics

WINDOW = 400
BLOCK = 800
PAIR_ROWS = 2 * WINDOW
MIN_BLOCKS = 2
DEFAULT_ALPHA = 0.05
DEFAULT_PERMUTATIONS = 199
DEFAULT_TRIALS = 500
DEFAULT_LABEL = "normal"
HEAVY_TIE_MASS = 0.5
TRAIN_FILE = "KDDTrain+.txt"

# Integer counters and rates, chosen because a real flow table is mostly zeros and
# repeated values: that tie structure is exactly what an asymptotic null ignores.
FEATURES = [
    "duration",
    "src_bytes",
    "dst_bytes",
    "wrong_fragment",
    "urgent",
    "hot",
    "num_failed_logins",
    "logged_in",
    "num_compromised",
    "root_shell",
    "su_attempted",
    "num_root",
    "num_file_creations",
    "num_shells",
    "num_access_files",
    "count",
    "srv_count",
    "serror_rate",
    "rerror_rate",
    "same_srv_rate",
]


@dataclass(frozen=True)
class NullPool:
    """The drift-free pool plus the tie structure it exhibits."""

    values: np.ndarray
    names: list[str]
    modal_mass: dict[str, float]
    dropped: list[str]
    n_rows: int
    source: str

    @property
    def mean_modal_mass(self) -> float:
        if not self.modal_mass:
            return float("nan")
        return float(np.mean(list(self.modal_mass.values())))

    @property
    def heavy_tie_features(self) -> list[str]:
        return sorted(
            name
            for name, mass in self.modal_mass.items()
            if mass >= HEAVY_TIE_MASS
        )


def load_null_pool(
    path: Path | None = None, *, label: str = DEFAULT_LABEL
) -> NullPool:
    """Read NSL-KDD records, keep one label, and measure modal mass per feature."""
    path = Path(path) if path is not None else DATA_DIR / TRAIN_FILE
    if not path.is_file():
        raise FileNotFoundError(f"NSL-KDD training split not found at {path}")
    frame = pd.read_csv(path, header=None, names=[*FEATURE_COLS, "label", "difficulty"])
    if label not in set(frame["label"].unique()):
        raise ValueError(f"label {label!r} not present in {path.name}")
    selected = frame.loc[frame["label"] == label, FEATURES]
    values = selected.to_numpy(dtype=float)

    modal_mass: dict[str, float] = {}
    dropped: list[str] = []
    keep: list[int] = []
    for index, name in enumerate(FEATURES):
        column = values[:, index]
        if float(np.var(column)) == 0.0:
            dropped.append(name)
            continue
        _, counts = np.unique(column, return_counts=True)
        modal_mass[name] = float(counts.max() / column.size)
        keep.append(index)

    kept_names = [FEATURES[index] for index in keep]
    return NullPool(
        values=values[:, keep],
        names=kept_names,
        modal_mass={name: modal_mass[name] for name in kept_names},
        dropped=dropped,
        n_rows=int(values.shape[0]),
        source=f"{path.name}:{label}",
    )


def draw_pair(
    pool: NullPool, rng: np.random.Generator, blocks: int
) -> tuple[np.ndarray, np.ndarray, int]:
    """Draw two disjoint windows from one block, i.e. a null pair."""
    block = int(rng.integers(0, blocks))
    chunk = pool.values[block * BLOCK : (block + 1) * BLOCK]
    if chunk.shape[0] < PAIR_ROWS:
        raise ValueError(
            f"block {block} holds {chunk.shape[0]} rows, need {PAIR_ROWS}"
        )
    order = rng.permutation(chunk.shape[0])
    return chunk[order[:WINDOW]], chunk[order[WINDOW : 2 * WINDOW]], block


def run(
    output: Path,
    *,
    trials: int = DEFAULT_TRIALS,
    n_permutations: int = DEFAULT_PERMUTATIONS,
    alpha: float = DEFAULT_ALPHA,
    pool_path: Path | None = None,
    label: str = DEFAULT_LABEL,
    write: bool = True,
) -> dict:
    """Measure the false-alarm rate of every pathway on drift-free real traffic."""
    if trials < 1 or n_permutations < 1:
        raise ValueError("trials and permutations must be positive")
    smallest_p = 1.0 / (n_permutations + 1)
    if smallest_p > alpha / 2.0:
        raise ValueError(
            f"n_permutations={n_permutations} is too small: {smallest_p:.4f} > "
            f"alpha/2={alpha / 2.0:.4f}"
        )
    pool = load_null_pool(pool_path, label=label)
    capacity = pool.values.shape[0] // BLOCK
    if capacity < MIN_BLOCKS:
        raise ValueError(
            f"pool of {pool.values.shape[0]} rows yields {capacity} blocks; "
            f"need >= {MIN_BLOCKS}"
        )
    blocks = min(capacity, trials)

    outcomes: dict[str, list[int]] = {}
    block_ids: list[int] = []
    started = time.perf_counter()
    for trial in range(trials):
        rng = np.random.default_rng([7_000, trial])
        reference, current, block = draw_pair(pool, rng, blocks)
        block_ids.append(block)
        bundle = build_bundle(
            reference, current, n_permutations=n_permutations, seed=trial, alpha=alpha
        )
        for method, (_, rejected) in method_outputs(bundle, alpha=alpha).items():
            outcomes.setdefault(method, []).append(int(bool(rejected)))
    elapsed = time.perf_counter() - started

    metrics = {
        "trials": trials,
        "alpha": alpha,
        "n_permutations": n_permutations,
        "d": len(pool.names),
        "window": WINDOW,
        "blocks": {
            "distinct": len(set(block_ids)),
            "per_block": block_sizes(block_ids),
            "block_rows": BLOCK,
        },
        "pool": {
            "source": pool.source,
            "n_rows": pool.n_rows,
            "features": pool.names,
            "dropped_constant": pool.dropped,
            "modal_mass": pool.modal_mass,
            "mean_modal_mass": pool.mean_modal_mass,
            "heavy_tie_features": pool.heavy_tie_features,
        },
        "methods": {
            method: null_rejection_metrics(flags, block_ids, alpha)
            for method, flags in outcomes.items()
        },
        "seconds_per_trial": elapsed / trials,
    }

    if write:
        source = Path(pool_path) if pool_path is not None else DATA_DIR / TRAIN_FILE
        provenance = capture_provenance([source])
        config = ExperimentConfig(
            dataset="nsl_kdd_normal_null",
            method="null_calibration",
            seed=0,
            params={
                "trials": trials,
                "n_permutations": n_permutations,
                "alpha": alpha,
                "window": WINDOW,
                "block_rows": BLOCK,
                "label": label,
                "features": pool.names,
            },
        )
        write_result_atomic(
            Path(output),
            ResultEnvelope(
                config.canonical_dict(),
                provenance,
                {"null": metrics},
                metadata={"stage": "real_null"},
            ),
        )
    return metrics


def _fmt_ci(interval: list[float | None]) -> str:
    low, high = interval
    if low is None or high is None:
        return "-"
    return f"[{100 * low:.1f}, {100 * high:.1f}]"


def render(metrics: dict) -> str:
    """Markdown table of the real-traffic false-alarm rates."""
    lines = [
        f"Real-traffic null: `{metrics['pool']['source']}`, "
        f"{metrics['trials']} trials, d={metrics['d']}, "
        f"alpha={metrics['alpha']}, B={metrics['n_permutations']}",
        "",
        "| pathway | rejections | FWER | 95% CI (trials) | 95% CI (blocks) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for method, payload in sorted(
        metrics["methods"].items(), key=lambda item: -item[1]["fwer"]
    ):
        lines.append(
            f"| {method} | {payload['rejections']}/{payload['trials']} "
            f"| {100 * payload['fwer']:.1f}% "
            f"| {_fmt_ci(payload['ci95'])} "
            f"| {_fmt_ci(payload['ci95_block'])} |"
        )
    pool = metrics["pool"]
    lines += [
        "",
        f"Mean modal mass across the {metrics['d']} features: "
        f"{100 * pool['mean_modal_mass']:.1f}%",
        "Features with at least half their rows at the modal value: "
        + (", ".join(f"`{name}`" for name in pool["heavy_tie_features"]) or "none"),
        f"Constant features dropped: {pool['dropped_constant'] or 'none'}",
        f"Distinct blocks behind the trials: {metrics['blocks']['distinct']}; "
        f"{metrics['seconds_per_trial']:.2f}s/trial",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--n-permutations", type=int, default=DEFAULT_PERMUTATIONS)
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--pool", type=Path, default=None)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    metrics = run(
        args.output,
        trials=args.trials,
        n_permutations=args.n_permutations,
        alpha=args.alpha,
        pool_path=args.pool,
        label=args.label,
        write=not args.no_write,
    )
    table = render(metrics)
    print(table, flush=True)
    return table


if __name__ == "__main__":
    main()
