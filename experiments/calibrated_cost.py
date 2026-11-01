"""Wall-clock cost of the calibrated attribution statistic.

The paper quotes two latencies for the same windows: the asymptotic decomposed
pass, and the permutation-calibrated statistic.  Both are measured here on the
study populations so the numbers in `README.md` and `paper/main.tex` can be
regenerated instead of transcribed.

Usage::

    python -m experiments.calibrated_cost --d 20 \
        --output artifacts/benchmarks/calibrated_cost.json
    python -m experiments.calibrated_cost --d 78 \
        --output artifacts/benchmarks/calibrated_cost_d78.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np

from experiments.calibrated_data import synthetic_pool
from experiments.provenance import capture_provenance
from vigil import DriftAttributor, compute_calibrated_scores

POPULATIONS = ("gaussian", "zero_inflated_tied", "multivariate_t3")
ASYMPTOTIC_POPULATION = "gaussian"


def _windows(
    population: str, *, d: int, n: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    reference = synthetic_pool(population, rng, n, d)
    current = synthetic_pool(population, rng, n, d)
    return reference, current


def _time_calls(calls: int, run) -> list[float]:
    wall: list[float] = []
    for _ in range(calls):
        start = time.perf_counter()
        run()
        wall.append(time.perf_counter() - start)
    return wall


def _summary(wall: list[float], calls: int) -> dict:
    return {
        "median_seconds": round(statistics.median(wall), 4),
        "min": round(min(wall), 4),
        "max": round(max(wall), 4),
        "calls": calls,
    }


def benchmark(*, d: int, n: int, n_permutations: int, calls: int, seed: int) -> dict:
    """Time the permutation statistic and the asymptotic pass on one d."""
    results = {}
    for population in POPULATIONS:
        reference, current = _windows(population, d=d, n=n, seed=seed)

        def run(
            reference: np.ndarray = reference,
            current: np.ndarray = current,
        ) -> None:
            compute_calibrated_scores(
                reference,
                current,
                n_permutations=n_permutations,
                seed=seed,
            )

        results[population] = _summary(_time_calls(calls, run), calls)

    reference, current = _windows(ASYMPTOTIC_POPULATION, d=d, n=n, seed=seed)
    attributor = DriftAttributor(mode="decomposed")
    names = [f"f{index}" for index in range(d)]

    def run_asymptotic() -> None:
        attributor.attribute(
            reference_data=reference,
            current_batch=current,
            feature_names=names,
        )

    asymptotic_ms = round(
        1000 * statistics.median(_time_calls(calls, run_asymptotic)), 2
    )

    return {
        "d": d,
        "n": n,
        "n_permutations": n_permutations,
        "seed": seed,
        "results": results,
        "asymptotic_decomposed_ms": asymptotic_ms,
        "asymptotic_calls": calls,
    }


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--d", type=int, default=20)
    parser.add_argument("--n", type=int, default=400)
    parser.add_argument("--n-permutations", type=int, default=199)
    parser.add_argument("--calls", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    payload = benchmark(
        d=args.d,
        n=args.n,
        n_permutations=args.n_permutations,
        calls=args.calls,
        seed=args.seed,
    )
    payload["provenance"] = capture_provenance(()).canonical_dict()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("d", "n", "n_permutations")}))
    for population, stats in payload["results"].items():
        print(
            f"{population}: {stats['median_seconds']} s median ({stats['calls']} calls)"
        )
    print(f"asymptotic: {payload['asymptotic_decomposed_ms']} ms median")
    return args.output


if __name__ == "__main__":
    main()
