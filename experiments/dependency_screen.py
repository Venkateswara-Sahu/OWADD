"""Dependency-focused Gaussian development screen, not a network benchmark."""

import argparse
from hashlib import sha256
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from threadpoolctl import threadpool_limits

from experiments.attribution.dependency import (
    CorrelationChangeAttributor,
    NonlinearPermutationAttributor,
)
from experiments.attribution.discriminative import DiscriminativeAttributor
from experiments.attribution.statistical import (
    KSAttributor,
    MeanDifferenceAttributor,
    StandardizedMeanDifferenceAttributor,
    WassersteinAttributor,
)
from experiments.attribution.two_sided import two_sided_scores
from experiments.config import ExperimentConfig
from experiments.dependency_data import (
    BACKGROUNDS,
    STRENGTHS,
    WINDOW_SIZES,
    case_name,
    make_dependency_cases,
)
from experiments.io import ResultEnvelope, load_completed_result, write_result_atomic
from experiments.metrics.attribution import evaluate_ranking
from experiments.metrics.stats import bootstrap_mean_ci
from experiments.provenance import capture_provenance
from vigil.attribution import DriftAttributor
from vigil.core.autoencoder import Autoencoder, train_autoencoder

RECONSTRUCTION = (
    "vigil_positive_delta",
    "vigil_absolute_delta",
    "vigil_standardized_absolute_delta",
)
DEPENDENCY = ("max_correlation_change", "nonlinear_permutation")
METHODS = (
    RECONSTRUCTION
    + DEPENDENCY
    + (
        "random",
        "absolute_mean_difference",
        "standardized_mean_difference",
        "kolmogorov_smirnov",
        "wasserstein",
        "discriminative_permutation",
    )
)
EXPECTED_KEYS = {
    (case_name(bg, n, strength), method)
    for bg in BACKGROUNDS
    for n in WINDOW_SIZES
    for strength in STRENGTHS
    for method in METHODS
}
SEEDS = tuple(range(30, 50))
EPOCHS = 20
MIN_SEEDS = 2


def _summary(values):
    if all(value is None for value in values):
        return {"mean": None, "ci95": None}
    if any(value is None for value in values):
        raise ValueError("inconsistent undefined metric")
    return {"mean": float(np.mean(values)), "ci95": list(bootstrap_mean_ci(values))}


def aggregate_runs(runs):
    by_seed = {}
    for seed, records in runs.items():
        indexed = {(row["case"], row["method"]): row for row in records}
        if set(indexed) != EXPECTED_KEYS or len(records) != len(EXPECTED_KEYS):
            raise ValueError("incomplete or duplicate case/method grid")
        by_seed[seed] = indexed
    groups = []
    for case, method in sorted(EXPECTED_KEYS):
        rows = [by_seed[seed][case, method] for seed in sorted(by_seed)]
        groups.append(
            {
                "case": case,
                "method": method,
                "n_seeds": len(runs),
                "metrics": {
                    key: _summary([row["metrics"][key] for row in rows])
                    for key in rows[0]["metrics"]
                },
                "elapsed_ms": _summary([row["elapsed_ms"] for row in rows]),
            }
        )
    paired = []
    for case in sorted({case for case, _ in EXPECTED_KEYS}):
        for candidate in RECONSTRUCTION:
            for baseline in DEPENDENCY:
                rows = [
                    (by_seed[s][case, candidate], by_seed[s][case, baseline])
                    for s in sorted(by_seed)
                ]
                paired.append(
                    {
                        "case": case,
                        "candidate": candidate,
                        "baseline": baseline,
                        "n_seeds": len(runs),
                        "metrics": {
                            key: _summary(
                                [
                                    (
                                        None
                                        if a["metrics"][key] is None
                                        and b["metrics"][key] is None
                                        else a["metrics"][key] - b["metrics"][key]
                                    )
                                    for a, b in rows
                                ]
                            )
                            for key in rows[0][0]["metrics"]
                        },
                    }
                )
    return {"groups": groups, "paired_differences": paired}


def _hash(array):
    return sha256(array.tobytes()).hexdigest()


def _run_seed(seed, epochs):
    models, model_metadata, records = {}, {}, []
    baselines = [
        MeanDifferenceAttributor(),
        StandardizedMeanDifferenceAttributor(),
        KSAttributor(),
        WassersteinAttributor(),
        DiscriminativeAttributor(seed=seed),
        CorrelationChangeAttributor(),
        NonlinearPermutationAttributor(seed=seed),
    ]
    for case in make_dependency_cases(seed):
        background = case["background"]
        if background not in models:
            started = perf_counter()
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(seed)
                model = Autoencoder(20, hidden_dim=10)
                train_autoencoder(model, case["train"], epochs=epochs)
            elapsed = (perf_counter() - started) * 1000
            models[background] = model
            model_metadata[str(background)] = {
                "train_sha256": _hash(case["train"]),
                "training_ms": elapsed,
                "model_sha256": sha256(
                    b"".join(
                        name.encode() + tensor.detach().numpy().tobytes()
                        for name, tensor in model.state_dict().items()
                    )
                ).hexdigest(),
            }
        model = models[background]
        reference, current = case["reference"], case["current"]
        order, truth = case["tie_order"], case["truth"]
        scores = {}
        for method in RECONSTRUCTION:
            started = perf_counter()
            if method == "vigil_standardized_absolute_delta":
                variants, details = two_sided_scores(model, reference, current)
                values = variants[method]
            else:
                result = DriftAttributor(top_k=20).attribute(model, reference, current)
                values = (
                    result.feature_contributions
                    if method == "vigil_positive_delta"
                    else np.abs(result.feature_error_delta)
                )
                details = {"signed_delta": result.feature_error_delta.tolist()}
            scores[method] = (values, (perf_counter() - started) * 1000, details)
        started = perf_counter()
        random_scores = np.random.default_rng(
            np.random.SeedSequence([seed, 917])
        ).random(20)
        scores["random"] = (random_scores, (perf_counter() - started) * 1000, {})
        for method in baselines:
            started = perf_counter()
            result = method.rank(reference, current, ("numerical",) * 20)
            scores[result.method] = (
                result.scores,
                (perf_counter() - started) * 1000,
                result.metadata,
            )
        permuted_truth = tuple(i for i, feature in enumerate(order) if feature in truth)
        for method, (values, elapsed, details) in scores.items():
            records.append(
                {
                    "case": case["case"],
                    "method": method,
                    "background": background,
                    "window_size": case["window_size"],
                    "strength": case["strength"],
                    "shifted_features": list(truth),
                    "tie_order": order.tolist(),
                    "pairs": case["pairs"],
                    "reference_sha256": _hash(reference),
                    "current_sha256": _hash(current),
                    "scores": values.tolist(),
                    "elapsed_ms": elapsed,
                    "details": details,
                    "metrics": evaluate_ranking(values[order], permuted_truth),
                }
            )
    return records, {
        "models": model_metadata,
        "adaptation": False,
        "stage": "dependency_development_screen",
    }


def run_screen(output, *, seeds=SEEDS, epochs=EPOCHS):
    if (
        len(seeds) < MIN_SEEDS
        or len(set(seeds)) != len(seeds)
        or any(type(s) is not int or s < 0 for s in seeds)
        or type(epochs) is not int
        or epochs < 1
    ):
        raise ValueError("distinct nonnegative seeds and positive epochs required")
    output, provenance = Path(output), capture_provenance([])
    runs = {}
    threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        with threadpool_limits(limits=1):
            for seed in seeds:
                print(f"Dependency screen seed {seed}", flush=True)
                config = ExperimentConfig(
                    dataset="paired_gaussian_dependencies",
                    method="dependency_screen",
                    seed=seed,
                    split="validation",
                    params={"epochs": epochs, "protocol_version": 1},
                )
                result = load_completed_result(output, config, provenance)
                if result is None:
                    records, metadata = _run_seed(seed, epochs)
                    result = ResultEnvelope(
                        config.canonical_dict(),
                        provenance,
                        {"records": records},
                        metadata=metadata,
                    )
                    write_result_atomic(output, result)
                runs[seed] = result.metrics["records"]
    finally:
        torch.set_num_threads(threads)
    metrics = aggregate_runs(runs)
    config = ExperimentConfig(
        dataset="paired_gaussian_dependencies",
        method="dependency_summary",
        seed=0,
        split="validation",
        params={"epochs": epochs, "seeds": list(seeds), "protocol_version": 1},
    )
    root = output / "summary"
    existing = load_completed_result(root, config, provenance)
    if existing is not None:
        if existing.metrics != metrics:
            raise ValueError("summary mismatch")
        return root / config.config_hash / provenance.identity_hash / "result.json"
    return write_result_atomic(
        root,
        ResultEnvelope(
            config.canonical_dict(),
            provenance,
            metrics,
            metadata={
                "protocol_complete": set(seeds) == set(SEEDS) and epochs == EPOCHS,
                "not_full_study": True,
                "stage": "dependency_development_screen",
            },
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(run_screen(parser.parse_args().output), flush=True)
