"""NSL-KDD validation trials with frozen autoencoder weights."""

from dataclasses import asdict, replace
from hashlib import sha256
import json

import numpy as np

from experiments.datasets.nsl_kdd import build_network_stream, prepare_nsl_kdd
from experiments.freeze import freeze_validation_results, load_frozen_config
from experiments.io import ResultEnvelope, load_completed_result, write_result_atomic
from experiments.metrics.events import match_events
from experiments.provenance import capture_provenance, sha256_file
from experiments.runner import _seed_everything
from vigil import Vigil


def run_network_trial(config, dataset, provenance, output, *, smoke=False):
    if config.dataset != "nsl_kdd" or config.method != "vigil":
        raise ValueError("network workflow supports nsl_kdd/vigil only")
    if config.split not in {"validation", "test"}:
        raise ValueError("network split must be validation or test")
    params = config.params
    allowed = {
        "n_reference",
        "initial_epochs",
        "interval_chunks",
        "attack_classes",
        "drift_threshold",
        "buffer_size",
        "smoke",
    }
    if set(params) - allowed:
        raise ValueError("unsupported network parameters")
    n_reference = int(params.get("n_reference", 2000))
    epochs = int(params.get("initial_epochs", 20))
    interval = int(params.get("interval_chunks", 5))
    if not 30 <= n_reference <= len(dataset.reference.X) or epochs < 1:
        raise ValueError("insufficient reference rows or invalid epochs")
    if config.tolerance_chunks >= interval:
        raise ValueError("event tolerance must be shorter than interval")
    threshold = float(params.get("drift_threshold", 0.3))
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("invalid drift threshold")
    completed = load_completed_result(output, config, provenance)
    if completed is not None:
        return replace(completed, metadata={**completed.metadata, "resumed": True})
    _seed_everything(config.seed)
    indices = np.random.default_rng(config.seed).choice(
        len(dataset.reference.X), n_reference, replace=False
    )
    reference = dataset.reference.X[indices]
    chunks, manifest, row_ids = build_network_stream(
        getattr(dataset, config.split),
        attack_classes=tuple(params.get("attack_classes", ["neptune", "satan"])),
        chunk_size=config.chunk_size,
        interval_chunks=interval,
        seed=config.seed,
    )
    if set(row_ids) & set(dataset.reference.row_ids):
        raise ValueError("reference/stream overlap")
    model = Vigil(
        n_features=reference.shape[1],
        feature_names=list(dataset.feature_names),
        initial_epochs=epochs,
        update_epochs=0,
        buffer_size=int(params.get("buffer_size", 1000)),
        drift_threshold=threshold,
    )
    model.fit(reference, verbose=False)
    alerts, severities = [], []
    for chunk in chunks:
        result = model.detect(chunk.X)
        severities.append(float(result.drift_severity))
        if result.drift_detected:
            alerts.append(chunk.chunk_id)
    events = asdict(
        match_events(
            manifest.events, alerts, config.tolerance_chunks, total_samples=len(row_ids)
        )
    )
    events["average_stable_run_length"] = None
    manifest_payload = {
        "definition": asdict(manifest),
        "row_ids": row_ids,
        "reference_ids": [dataset.reference.row_ids[i] for i in indices],
    }
    manifest_hash = sha256(
        json.dumps(manifest_payload, sort_keys=True).encode()
    ).hexdigest()
    result = ResultEnvelope(
        config.canonical_dict(),
        provenance,
        {
            "primary": events["event_f1"],
            "events": events,
            "manifest": {"hash": manifest_hash, **manifest_payload},
            "alerts": alerts,
            "severities": severities,
            "stream_rows": len(row_ids),
            "unique_stream_rows": len(set(row_ids)),
            "audit": dataset.audit,
        },
        result_id=f"{config.config_hash}-{provenance.identity_hash}",
        metadata={
            "stage": "smoke_only" if smoke else config.split,
            "primary_metric": "event_f1",
            "uses_labels": False,
            "evaluation_uses_labels": True,
            "selection_uses_labels": config.split == "validation",
            "adaptation": "frozen autoencoder; stable-chunk error buffer updates",
            "undefined_reasons": {
                "average_stable_run_length": "stable-only exposure not implemented"
            },
            "resumed": False,
        },
    )
    write_result_atomic(output, result)
    return result


def run_nsl_kdd_mode(
    config,
    output,
    *,
    train_path,
    test_path,
    mode,
    frozen_path,
    thresholds=(0.05, 0.1, 0.2, 0.3, 0.5),
):
    if mode not in {"smoke", "tune", "test"}:
        raise ValueError("network mode must be smoke, tune or test")
    if mode == "test" and not frozen_path.is_file():
        raise FileNotFoundError(f"frozen manifest required: {frozen_path}")
    if mode == "tune" and frozen_path.exists():
        raise FileExistsError(f"frozen manifest already exists: {frozen_path}")
    checksums = {"train": sha256_file(train_path), "test": sha256_file(test_path)}
    if mode == "test":
        frozen = load_frozen_config(frozen_path, checksums)
        requested = replace(
            config,
            split="test",
            params={
                **config.params,
                "drift_threshold": frozen.params["drift_threshold"],
            },
        )
        if requested.canonical_dict() != frozen.canonical_dict():
            raise ValueError("requested protocol differs from frozen configuration")
        config = frozen
    else:
        config = replace(config, split="validation")
    if mode == "smoke":
        config = replace(
            config,
            chunk_size=40,
            tolerance_chunks=1,
            params={
                **config.params,
                "initial_epochs": 2,
                "n_reference": 200,
                "interval_chunks": 3,
                "smoke": True,
            },
        )
    dataset = prepare_nsl_kdd(
        train_path, test_path, seed=config.seed, include_test=mode == "test"
    )
    provenance = replace(
        capture_provenance([train_path, test_path]), dataset_checksums=checksums
    )
    if mode != "tune":
        return [
            run_network_trial(
                config, dataset, provenance, output, smoke=mode == "smoke"
            )
        ]
    trials = [
        run_network_trial(
            replace(config, params={**config.params, "drift_threshold": float(value)}),
            dataset,
            provenance,
            output,
        )
        for value in thresholds
    ]
    freeze_validation_results(frozen_path, trials)
    return trials
