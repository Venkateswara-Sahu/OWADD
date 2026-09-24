"""Training-file-only novelty development. Never reads the official test file."""

import argparse
import pickle
from collections import Counter
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import IsolationForest

from experiments.config import ExperimentConfig
from experiments.datasets.base import DatasetSplit
from experiments.datasets.nsl_kdd import prepare_frames
from experiments.io import ResultEnvelope, load_completed_result, write_result_atomic
from experiments.metrics.stats import bootstrap_mean_ci
from experiments.novelty_model import FrozenNoveltyScorer
from experiments.novelty_protocol import (
    ScoredPool,
    evaluate_frozen,
    freeze_threshold,
    make_protocol,
    score_pool,
)
from experiments.novelty_scores import load_scores, save_scores
from experiments.provenance import capture_provenance
from vigil import Vigil

MIN_REFERENCE = 2
METHODS = ("vigil_kde", "isolation_forest", "constant")
NOVEL_CLASSES = (
    "back",
    "buffer_overflow",
    "ftp_write",
    "guess_passwd",
    "imap",
    "ipsweep",
    "land",
    "loadmodule",
    "multihop",
    "neptune",
    "nmap",
    "perl",
    "phf",
    "pod",
    "portsweep",
    "rootkit",
    "satan",
    "smurf",
    "spy",
    "teardrop",
    "warezclient",
    "warezmaster",
)


def _subset(split, indices):
    return DatasetSplit(
        split.X[indices], split.y[indices], tuple(split.row_ids[i] for i in indices)
    )


def development_protocol(dataset, *, n_reference, novel_classes, split_seed=42):
    """Generic test role is development-report, NOT the official test partition."""
    if (
        type(n_reference) is not int
        or n_reference < MIN_REFERENCE
        or n_reference > len(dataset.reference.X)
    ):
        raise ValueError("insufficient reference or invalid reference size")
    if len(dataset.test.X) or dataset.audit.get("test_loaded") is not False:
        raise ValueError("development requires preparation without official test data")
    if set(dataset.validation.y) != {"normal", *novel_classes}:
        raise ValueError("declared novel classes must match development source classes")
    rng = np.random.default_rng(split_seed)
    ref = rng.permutation(np.argsort(dataset.reference.row_ids))[:n_reference]
    calibration, development = [], []
    for label in sorted(set(dataset.validation.y)):
        indices = np.flatnonzero(dataset.validation.y == label)
        indices = sorted(indices, key=lambda i: dataset.validation.row_ids[i])
        shuffled = rng.permutation(indices)
        middle = len(shuffled) // 2
        calibration.extend(shuffled[:middle])
        development.extend(shuffled[middle:])
    return make_protocol(
        _subset(dataset.reference, ref),
        _subset(dataset.validation, np.array(calibration)),
        _subset(dataset.validation, np.array(development)),
        known_classes=("normal",),
        novel_classes=novel_classes,
    )


def _fit_scorer(method, protocol, preprocessing_id, seed, epochs):
    if method == "vigil_kde":
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            model = Vigil(hidden_dim=10, initial_epochs=epochs)
            model.fit(protocol.reference.X, verbose=False)
        scorer = FrozenNoveltyScorer.from_vigil(
            model,
            preprocessing_id=preprocessing_id,
            reference_id=protocol.reference.identity,
        )
        return scorer, scorer.model_id
    if method == "isolation_forest":
        model = IsolationForest(
            n_estimators=100,
            max_samples=min(256, len(protocol.reference.X)),
            random_state=seed,
            n_jobs=1,
        ).fit(protocol.reference.X)
        identity = sha256(pickle.dumps(model, protocol=5)).hexdigest()
        return lambda X: -model.score_samples(X), identity
    return lambda X: np.zeros(len(X)), "constant-zero-v1"


def _resume_evidence(output, envelope, protocol):
    relative = Path(envelope.metadata["evidence_dir"])
    evidence = (output / relative).resolve()
    if not evidence.is_relative_to(output.resolve()):
        raise ValueError("invalid evidence directory")
    labels, values = load_scores(
        evidence / "development.npz", envelope.metadata["development_scores"]
    )
    if not np.array_equal(labels, protocol.test.labels):
        raise ValueError("development labels mismatch")
    metrics = evaluate_frozen(
        evidence / "freeze.json",
        protocol,
        ScoredPool(protocol.test.identity, "test", values),
        model_id=envelope.metadata["model_id"],
    )
    if asdict(metrics) != envelope.metrics:
        raise ValueError("development metrics mismatch")


def run_seed(protocol, *, preprocessing_id, seed, epochs, output, provenance):
    """One paired seed; save calibration before scoring the development holdout."""
    if type(seed) is not int or seed < 0 or type(epochs) is not int or epochs < 1:
        raise ValueError(
            "nonnegative integer seed and positive integer epochs required"
        )
    output = Path(output)
    provenance = replace(
        provenance,
        dataset_checksums={
            **provenance.dataset_checksums,
            "development_protocol": protocol.identity,
            "preprocessing": preprocessing_id,
        },
    )
    results = {}
    old_threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        for method in METHODS:
            config = ExperimentConfig(
                dataset="nsl_kdd_novelty_development",
                method=method,
                seed=seed,
                split="validation",
                params={
                    "epochs": epochs,
                    "protocol_id": protocol.identity,
                    "preprocessing_id": preprocessing_id,
                    "hidden_dim": 10,
                    "trees": 100,
                    "max_samples": 256,
                    "calibration_quantiles": 51,
                    "cpu_threads": 1,
                },
            )
            existing = load_completed_result(output, config, provenance)
            if existing is not None:
                _resume_evidence(output, existing, protocol)
                results[method] = existing
                continue
            started = perf_counter()
            scorer, fitted_id = _fit_scorer(
                method, protocol, preprocessing_id, seed, epochs
            )
            model_id = sha256(
                f"{fitted_id}:{preprocessing_id}:{protocol.reference.identity}".encode()
            ).hexdigest()
            calibration = score_pool(protocol.validation, scorer)
            candidates = np.unique(
                np.append(
                    np.quantile(calibration.values, np.linspace(0, 1, 51)),
                    np.nextafter(calibration.values.max(), np.inf),
                )
            )
            relative = Path("evidence") / uuid4().hex
            evidence = output / relative
            freeze_threshold(
                evidence / "freeze.json",
                protocol,
                calibration,
                candidates,
                model_id=model_id,
            )
            development = score_pool(protocol.test, scorer)
            metrics = evaluate_frozen(
                evidence / "freeze.json", protocol, development, model_id=model_id
            )
            receipt = save_scores(
                evidence / "development.npz", protocol.test.labels, development.values
            )
            envelope = ResultEnvelope(
                config=config.canonical_dict(),
                provenance=provenance,
                metrics=asdict(metrics),
                metadata={
                    "evaluation_scope": "development_holdout",
                    "threshold_selected_on": "calibration",
                    "official_test_loaded": False,
                    "model_id": model_id,
                    "evidence_dir": relative.as_posix(),
                    "development_scores": receipt,
                    "elapsed_seconds": perf_counter() - started,
                },
            )
            write_result_atomic(output, envelope)
            results[method] = envelope
    finally:
        torch.set_num_threads(old_threads)
    return results


def summarize(records, *, expected_seeds):
    """Seed variability conditional on fixed rows, not generalization uncertainty."""
    expected = {(seed, method) for seed in expected_seeds for method in METHODS}
    actual = {(r.config["seed"], r.config["method"]) for r in records}
    if not expected or actual != expected or len(records) != len(expected):
        raise ValueError("complete unique paired seed/method grid required")
    if len({r.provenance.identity_hash for r in records}) != 1:
        raise ValueError("mixed provenance")
    if any(
        r.metadata.get("evaluation_scope") != "development_holdout" for r in records
    ):
        raise ValueError("development scope required")
    comparable = [
        {k: v for k, v in r.config.items() if k not in {"seed", "method"}}
        for r in records
    ]
    if any(config != comparable[0] for config in comparable):
        raise ValueError("incompatible configurations")
    metrics = (
        "average_precision",
        "auroc",
        "precision",
        "recall",
        "f1",
        "false_positive_rate",
    )

    def statistics(values):
        values = np.asarray(values, dtype=float)
        return {
            "n": len(values),
            "mean": float(values.mean()),
            "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
            "ci95": list(bootstrap_mean_ci(values)),
        }

    ordered = {
        method: sorted(
            (r for r in records if r.config["method"] == method),
            key=lambda r: r.config["seed"],
        )
        for method in METHODS
    }
    return {
        "scope": "development_holdout",
        "uncertainty": "model-seed variability conditional on one fixed split",
        "methods": {
            method: {
                metric: statistics([r.metrics[metric] for r in rows])
                for metric in metrics
            }
            for method, rows in ordered.items()
        },
        "paired_vigil_minus_isolation_forest": {
            metric: statistics(
                [
                    left.metrics[metric] - right.metrics[metric]
                    for left, right in zip(
                        ordered["vigil_kde"], ordered["isolation_forest"]
                    )
                ]
            )
            for metric in metrics
        },
    }


def run_pilot(
    train_path,
    output,
    *,
    seeds=tuple(range(10)),
    epochs=20,
    n_reference=2000,
    novel_classes=NOVEL_CLASSES,
):
    """Fit paired development models without accepting an official test path."""
    from data.nsl_kdd_loader import COLUMN_NAMES

    if len(seeds) < MIN_REFERENCE or len(set(seeds)) != len(seeds):
        raise ValueError("at least two unique model seeds required")
    train_path, output = Path(train_path), Path(output)
    dataset = prepare_frames(
        pd.read_csv(train_path, header=None, names=COLUMN_NAMES), None, seed=42
    )
    protocol = development_protocol(
        dataset, n_reference=n_reference, novel_classes=novel_classes
    )
    preprocessing_id = dataset.audit["preprocessing_sha256"]
    provenance = capture_provenance([train_path])
    provenance = replace(
        provenance,
        dataset_checksums={
            **provenance.dataset_checksums,
            "development_protocol": protocol.identity,
            "preprocessing": preprocessing_id,
        },
    )
    records = []
    for seed in seeds:
        print(
            f"Development seed {seed}: fitting/checking all three methods", flush=True
        )
        records.extend(
            run_seed(
                protocol,
                preprocessing_id=preprocessing_id,
                seed=seed,
                epochs=epochs,
                output=output,
                provenance=provenance,
            ).values()
        )
    summary = summarize(records, expected_seeds=seeds)
    config = ExperimentConfig(
        dataset="nsl_kdd_novelty_development",
        method="summary",
        seed=42,
        split="validation",
        params={
            "seeds": list(seeds),
            "epochs": epochs,
            "protocol_id": protocol.identity,
        },
    )
    summary_root = output / "summary"
    existing = load_completed_result(summary_root, config, provenance)
    if existing is not None:
        if existing.metrics != summary:
            raise ValueError("summary does not match completed seed evidence")
        return (
            summary_root / config.config_hash / provenance.identity_hash / "result.json"
        )
    population = {
        name: {
            "n": len(pool.X),
            "class_counts": dict(Counter(pool.original_labels)),
            "row_ids": list(pool.row_ids),
            "identity": pool.identity,
        }
        for name, pool in (
            ("reference", protocol.reference),
            ("calibration", protocol.validation),
            ("development", protocol.test),
        )
    }
    return write_result_atomic(
        summary_root,
        ResultEnvelope(
            config=config.canonical_dict(),
            provenance=provenance,
            metrics=summary,
            metadata={
                "official_test_loaded": False,
                "source_audit": dataset.audit,
                "population": population,
                "feature_names": list(dataset.feature_names),
                "evaluation_scope": "development_holdout",
            },
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(run_pilot(args.train, args.output), flush=True)
