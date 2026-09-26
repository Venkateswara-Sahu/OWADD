"""Independent Gaussian-window localization screen, not the full study."""

import argparse
from collections import defaultdict
from hashlib import sha256
from pathlib import Path

import numpy as np
import torch

from experiments.attribution.discriminative import DiscriminativeAttributor
from experiments.attribution.statistical import (
    KSAttributor,
    MeanDifferenceAttributor,
    StandardizedMeanDifferenceAttributor,
    WassersteinAttributor,
)
from experiments.config import ExperimentConfig
from experiments.io import ResultEnvelope, load_completed_result, write_result_atomic
from experiments.metrics.attribution import evaluate_ranking
from experiments.metrics.stats import bootstrap_mean_ci
from experiments.provenance import capture_provenance
from vigil.attribution import DriftAttributor
from vigil.core.autoencoder import Autoencoder, train_autoencoder

N_FEATURES = 20
MIN_SEEDS = 2
PROTOCOL_EPOCHS = 20
PROTOCOL_SEEDS = tuple(range(10))


def make_cases(seed):
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(5)]
    train = streams[0].normal(size=(2000, 20))
    reference = streams[1].normal(size=(200, 20))
    base = streams[2].normal(size=(200, 20))
    truth = tuple(int(i) for i in streams[3].choice(20, size=2, replace=False))
    order = streams[4].permutation(20)
    cases = [("stable", (), base.copy())]
    for magnitude in (0.5, 2):
        current = base.copy()
        current[:, truth] += magnitude
        cases.append((f"mean_{magnitude}", truth, current))
    for multiplier in (0.5, 2):
        current = base.copy()
        current[:, truth] *= multiplier
        cases.append((f"std_{multiplier}", truth, current))
    a = (np.sqrt(1.8) + np.sqrt(0.2)) / 2
    b = (np.sqrt(1.8) - np.sqrt(0.2)) / 2
    current = base.copy()
    current[:, truth] = base[:, truth] @ np.array([[a, b], [b, a]])
    cases.append(("correlation_0.8", truth, current))
    return train, reference, cases, order


def _run_seed(seed, epochs):
    train, reference, cases, order = make_cases(seed)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model = Autoencoder(N_FEATURES, hidden_dim=10)
        train_autoencoder(model, train, epochs=epochs)
    model_hash = sha256(
        b"".join(
            name.encode() + value.detach().numpy().tobytes()
            for name, value in model.state_dict().items()
        )
    ).hexdigest()
    baselines = [
        MeanDifferenceAttributor(),
        StandardizedMeanDifferenceAttributor(),
        KSAttributor(),
        WassersteinAttributor(),
        DiscriminativeAttributor(seed=seed),
    ]
    random_scores = np.random.default_rng(np.random.SeedSequence([seed, 917])).random(
        N_FEATURES
    )
    records = []
    for name, truth, current in cases:
        public = DriftAttributor(top_k=N_FEATURES).attribute(model, reference, current)
        scores = {
            "vigil_positive_delta": public.feature_contributions,
            "random": random_scores,
        }
        for method in baselines:
            ranked = method.rank(reference, current, ("numerical",) * N_FEATURES)
            scores[ranked.method] = ranked.scores
        # Shared independent tie order avoids privileging low feature indices.
        permuted_truth = tuple(i for i, feature in enumerate(order) if feature in truth)
        for method, values in scores.items():
            records.append(
                {
                    "case": name,
                    "method": method,
                    "shifted_features": list(truth),
                    "scores": values.tolist(),
                    "current_sha256": sha256(current.tobytes()).hexdigest(),
                    "metrics": evaluate_ranking(values[order], permuted_truth),
                }
            )
    return records, {
        "train_sha256": sha256(train.tobytes()).hexdigest(),
        "reference_sha256": sha256(reference.tobytes()).hexdigest(),
        "model_sha256": model_hash,
        "tie_order": order.tolist(),
        "stage": "numerical_window_development_screen",
        "adaptation": False,
    }


def run_screen(output, *, seeds=PROTOCOL_SEEDS, epochs=PROTOCOL_EPOCHS):
    if (
        len(seeds) < MIN_SEEDS
        or len(set(seeds)) != len(seeds)
        or any(type(seed) is not int or seed < 0 for seed in seeds)
        or type(epochs) is not int
        or epochs < 1
    ):
        raise ValueError("distinct nonnegative seeds and positive epochs required")
    output = Path(output)
    protocol_complete = set(seeds) == set(PROTOCOL_SEEDS) and epochs == PROTOCOL_EPOCHS
    provenance = capture_provenance([])
    groups = defaultdict(list)
    threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        for seed in seeds:
            print(f"Attribution screen seed {seed}", flush=True)
            config = ExperimentConfig(
                dataset="independent_gaussian_windows",
                method="paired_attribution",
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
            for row in result.metrics["records"]:
                groups[row["case"], row["method"]].append(row["metrics"])
    finally:
        torch.set_num_threads(threads)

    def summarize(values):
        if all(value is None for value in values):
            return {"mean": None, "ci95": None}
        if any(value is None for value in values):
            raise ValueError("inconsistent undefined metric")
        return {"mean": float(np.mean(values)), "ci95": list(bootstrap_mean_ci(values))}

    summary = []
    for (case, method), metrics in groups.items():
        if len(metrics) != len(seeds):
            raise ValueError("incomplete seed group")
        summary.append(
            {
                "case": case,
                "method": method,
                "n_seeds": len(seeds),
                "metrics": {
                    key: summarize([m[key] for m in metrics]) for key in metrics[0]
                },
            }
        )
    config = ExperimentConfig(
        dataset="independent_gaussian_windows",
        method="attribution_summary",
        seed=0,
        split="validation",
        params={"epochs": epochs, "seeds": list(seeds), "protocol_version": 1},
    )
    root = output / "summary"
    completed = load_completed_result(root, config, provenance)
    if completed is not None:
        if completed.metrics != {"groups": summary}:
            raise ValueError("summary mismatch")
        return root / config.config_hash / provenance.identity_hash / "result.json"
    return write_result_atomic(
        root,
        ResultEnvelope(
            config.canonical_dict(),
            provenance,
            {"groups": summary},
            metadata={
                "stage": "numerical_window_development_screen",
                "not_full_study": True,
                "protocol_complete": protocol_complete,
            },
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(run_screen(args.output), flush=True)
