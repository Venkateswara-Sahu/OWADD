"""Does the exchangeability caveat matter? Block permutations on temporal windows.

The permutation null in ``vigil/calibration.py`` is valid when rows are
exchangeable within a window. Real flow tables are not: consecutive records
share hosts, sessions and short-lived bursts, so adjacent rows are correlated.
``experiments/calibrated_data.py::real_window`` sidesteps this by permuting rows
inside the block before splitting, which enforces exchangeability by
construction. That is fine for measuring the *level* of the calibrated test, but
it leaves the caveat untested: nobody has measured what the i.i.d. null does on
windows that keep their real time order.

This module runs that measurement. Two adjacent, **unshuffled** 400-row windows
are cut from a real block, so the pair is a genuine null (nothing was injected)
with its temporal dependence intact. The same null is evaluated with

* ``block_size=1`` -- i.i.d. row permutation, the default policy, and
* ``block_size=10/25/50`` -- permutations of contiguous runs of that many rows.

If the i.i.d. null is anti-conservative on temporally ordered windows its
family-wise rejection rate climbs above ``alpha``; a block-permutation null that
keeps runs together should hold the level. A drifted condition is included so
that the level is not bought by destroying power.

Synthetic pools (i.i.d. by construction) are the negative control: block size
must not matter there.

Run:
    python -m experiments.calibrated_blocknull \
        --output artifacts/runs/calibrated-blocknull-v1 \
        --prepared artifacts/prepared/cicids2017-prepared-v1 --trials 500
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from experiments.calibrated_data import Injection, apply_injection, synthetic_pool
from experiments.calibrated_study import DEFAULT_ALPHA, DEFAULT_PERMUTATIONS
from experiments.provenance import capture_provenance
from vigil.calibration import compute_calibrated_scores

WINDOW = 400
PAIR_ROWS = 2 * WINDOW
SYNTHETIC_POOLS = ("gaussian", "multivariate_t3")
REAL_POOLS = ("real_tuesday", "real_heldout")
NSL_KDD_POOL = "nsl_kdd"
BLOCK_SIZES = (1, 10, 25, 50)
DEFAULT_TRIALS = 500
CONDITIONS = ("null", "mean_0.5")
LAG_MAX = 8


@dataclass(frozen=True)
class Window:
    """One reference/current pair plus the truth features that were moved."""

    ref: np.ndarray
    cur: np.ndarray
    truth: tuple[int, ...]


def _temporal_window(rows: np.ndarray, *, seed: int, window: int, block_rows: int):
    """Adjacent unshuffled windows: this is the point of the exercise."""
    n_blocks = len(rows) // block_rows
    if n_blocks < 1:
        raise ValueError("pool smaller than one block")
    block = int(seed) % n_blocks
    start = block * block_rows
    chunk = np.asarray(rows[start : start + block_rows], dtype=float)
    if len(chunk) < 2 * window:
        raise ValueError("block must hold two windows")
    return chunk[:window], chunk[window : 2 * window]


def _lagged_dependence(ref: np.ndarray, cur: np.ndarray, lag_max: int) -> dict:
    """Mean |lag-k autocorrelation| per column, averaged over features.

    A value near zero says the temporal-order experiment is the same as the
    shuffled one; a large value says i.i.d. permutation has something to break.
    """
    pooled = np.vstack([ref, cur])
    sd = pooled.std(axis=0)
    keep = sd > 0
    z = (pooled[:, keep] - pooled[:, keep].mean(axis=0)) / sd[keep]
    out: dict[str, float] = {}
    for lag in range(1, lag_max + 1):
        a = z[:-lag]
        b = z[lag:]
        denom = np.sqrt((a**2).sum(axis=0) * (b**2).sum(axis=0))
        denom[denom == 0] = np.inf
        out[str(lag)] = float(np.mean(np.abs((a * b).sum(axis=0) / denom)))
    return out


def load_nslkdd_pool(n_features: int = 20, split: str = "train") -> np.ndarray:
    """NSL-KDD rows as a second real corpus, in the file's recorded order.

    ``KDDTrain+`` is a random sample rather than a time series, so this pool is
    not autocorrelated: it is the check that the calibrated level also holds on
    a real corpus with different encoding, ties and zero inflation. The 20
    most-variable encoded columns are kept so the cost matches the other pools.
    """
    import contextlib
    import io

    from data.nsl_kdd_loader import load_nsl_kdd

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        X, _labels, _names = load_nsl_kdd(split=split)
    X = np.asarray(X, dtype=float)
    variance = X.var(axis=0)
    keep = np.sort(np.argsort(variance)[-n_features:])
    return X[:, keep]


def _decision(cal, alpha: float) -> bool:
    """The calibrated policy's family-wise decision (same rule as the study)."""
    alpha_marg = float(cal.metadata.get("alpha_marginal", alpha))
    alpha_rel = float(cal.metadata.get("alpha_relational", alpha))
    return bool(
        np.any(cal.marginal_pvalues <= alpha_marg)
        or cal.edge_pvalues.min(axis=1).min() <= alpha_rel
    )


def _draw(
    pool: str,
    *,
    seed: int,
    condition: str,
    prepared: Path | None,
    pools: dict | None,
    extra: dict[str, np.ndarray] | None = None,
) -> Window:
    """Reference/current pair for one trial, without reshuffling real rows."""
    if extra and pool in extra:
        ref, cur = _temporal_window(
            extra[pool], seed=seed, window=WINDOW, block_rows=PAIR_ROWS
        )
    elif pool in SYNTHETIC_POOLS:
        rng = np.random.default_rng([seed, 11])
        data = synthetic_pool(pool, rng, PAIR_ROWS, 20)
        ref, cur = data[:WINDOW], data[WINDOW:]
    else:
        key = _pool_split(pool)
        if pools is None or key not in pools:
            raise ValueError(f"pool {pool} needs prepared data with a {key} split")
        ref, cur = _temporal_window(
            pools[key], seed=seed, window=WINDOW, block_rows=PAIR_ROWS
        )
    if condition == "null":
        return Window(ref, cur.copy(), ())
    injection = Injection(kind="mean", magnitude=0.5, n_features=1, sparse=1.0)
    moved, truth = apply_injection(ref, cur, injection, np.random.default_rng(seed))
    return Window(ref, moved, tuple(int(i) for i in truth))


def _pool_split(name: str) -> str:
    """Which prepared split a real pool reads from."""
    return "validation" if name == "real_tuesday" else "test"


def _dependence_case(
    name: str,
    pools: dict | None,
    extra: dict[str, np.ndarray] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """The window pair whose autocorrelation documents the caveat."""
    if extra and name in extra:
        return _temporal_window(
            extra[name], seed=0, window=WINDOW, block_rows=PAIR_ROWS
        )
    if name in REAL_POOLS:
        if pools is None:
            raise ValueError(f"pool {name} needs prepared data")
        key = _pool_split(name)
        return _temporal_window(pools[key], seed=0, window=WINDOW, block_rows=PAIR_ROWS)
    rng = np.random.default_rng([0, 11])
    data = synthetic_pool(name, rng, PAIR_ROWS, 20)
    return data[:WINDOW], data[WINDOW:]


def run(
    output: Path,
    *,
    trials: int,
    n_permutations: int,
    alpha: float,
    prepared: Path | None,
    block_sizes: tuple[int, ...] = BLOCK_SIZES,
    conditions: tuple[str, ...] = CONDITIONS,
    nslkdd: bool = False,
) -> dict:
    extra: dict[str, np.ndarray] = {}
    if nslkdd:
        extra[NSL_KDD_POOL] = load_nslkdd_pool()
    pools = None
    usable_real: tuple[str, ...] = ()
    if prepared is not None:
        from experiments.mechanism_data import load_real_pools

        pools = load_real_pools(prepared)
        # ``load_real_pools`` only covers the reference/validation days. The
        # held-out days need their own manifest and files, so a machine without
        # them still gets the validation pool instead of no run at all.
        try:
            from experiments.decomposed_study import load_heldout_pools

            pools.update(load_heldout_pools(prepared))
        except (FileNotFoundError, KeyError, ValueError):
            pass
        usable_real = tuple(name for name in REAL_POOLS if _pool_split(name) in pools)
    names = (*SYNTHETIC_POOLS, *usable_real, *extra.keys())
    started = time.perf_counter()
    table: dict[str, dict] = {}
    for name in names:
        table[name] = {}
        for condition in conditions:
            table[name][condition] = {}
            for block_size in block_sizes:
                flags: list[int] = []
                for trial in range(trials):
                    case = _draw(
                        name,
                        seed=trial,
                        condition=condition,
                        prepared=prepared,
                        pools=pools,
                        extra=extra,
                    )
                    cal = compute_calibrated_scores(
                        case.ref,
                        case.cur,
                        n_permutations=n_permutations,
                        alpha=alpha,
                        seed=trial,
                        block_size=block_size,
                    )
                    flags.append(int(_decision(cal, alpha)))
                rate = sum(flags) / len(flags)
                table[name][condition][str(block_size)] = {
                    "rejections": int(sum(flags)),
                    "trials": len(flags),
                    "rate": rate,
                }
                print(
                    f"[{name}] {condition} block={block_size}: {100 * rate:.1f}% "
                    f"({sum(flags)}/{len(flags)})",
                    flush=True,
                )
        reference, current = _dependence_case(name, pools, extra)
        table[name]["lag_dependence"] = _lagged_dependence(reference, current, LAG_MAX)

    elapsed = time.perf_counter() - started
    payload = {
        "window": WINDOW,
        "d": 20,
        "alpha": alpha,
        "n_permutations": n_permutations,
        "trials": trials,
        "block_sizes": list(block_sizes),
        "conditions": list(conditions),
        "real_windows_are_temporal": True,
        "extra_pools": sorted(extra),
        "real_pools_available": list(usable_real),
        "real_pools_missing": [n for n in REAL_POOLS if n not in usable_real],
        "pools": table,
        "wall_seconds": elapsed,
    }
    output.mkdir(parents=True, exist_ok=True)
    payload["provenance"] = capture_provenance(()).canonical_dict()
    (output / "summary.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    markdown = render(payload)
    (output / "summary.md").write_text(markdown, encoding="utf-8")
    return payload


def _pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def render(payload: dict) -> str:
    """Markdown: family-wise rejection rate by pool, condition and block size."""
    sizes = payload["block_sizes"]
    lines = [
        "Block-permutation null on temporally ordered windows "
        f"(n={payload['window']}, d={payload['d']}, "
        f"alpha={payload['alpha']}, B={payload['n_permutations']}, "
        f"{payload['trials']} trials per cell)",
        "",
        "| pool | condition | " + " | ".join(f"block={b}" for b in sizes) + " |",
        "| --- | --- | " + " | ".join("---" for _ in sizes) + " |",
    ]
    for name, per_condition in payload["pools"].items():
        for condition in payload["conditions"]:
            cells = [_pct(per_condition[condition][str(b)]["rate"]) for b in sizes]
            lines.append(f"| {name} | {condition} | " + " | ".join(cells) + " |")
    lines += ["", "Mean |lag-k| autocorrelation of the pooled windows:", ""]
    lags = " | ".join(f"lag {k}" for k in range(1, LAG_MAX + 1))
    lines.append(f"| pool | {lags} |")
    lines.append("| --- | " + " | ".join("---" for _ in range(LAG_MAX)) + " |")
    for name, per_condition in payload["pools"].items():
        dep = per_condition["lag_dependence"]
        cells = [f"{dep[str(k)]:.3f}" for k in range(1, LAG_MAX + 1)]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Synthetic pools are i.i.d. by construction and act as the negative "
        "control: the block size must not move their rate. The real pools keep the "
        "row order of the recorded traffic, so block sizes above one are the only "
        "honest nulls there.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, default=None)
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--n-permutations", type=int, default=DEFAULT_PERMUTATIONS)
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    parser.add_argument("--block-sizes", default=None)
    parser.add_argument(
        "--conditions",
        default=",".join(CONDITIONS),
        help="comma-separated subset of: " + ", ".join(CONDITIONS),
    )
    parser.add_argument(
        "--nslkdd",
        action="store_true",
        help="add NSL-KDD (KDDTrain+) as a second real corpus, uncorrelated rows",
    )
    args = parser.parse_args(argv)
    sizes = (
        tuple(int(part) for part in args.block_sizes.split(","))
        if args.block_sizes
        else BLOCK_SIZES
    )
    payload = run(
        args.output,
        trials=args.trials,
        n_permutations=args.n_permutations,
        alpha=args.alpha,
        prepared=args.prepared,
        block_sizes=sizes,
        conditions=tuple(part.strip() for part in args.conditions.split(",")),
        nslkdd=args.nslkdd,
    )
    print(render(payload), flush=True)
    return payload


if __name__ == "__main__":
    main()
