from __future__ import annotations

import json
import random
import traceback
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import numpy as np
import torch

from experiments.attribution.vigil_adapter import VigilAttributionAdapter
from experiments.config import ExperimentConfig
from experiments.io import (
    ResultEnvelope,
    load_completed_result,
    write_result_atomic,
)
from experiments.metrics.attribution import evaluate_ranking
from experiments.metrics.events import match_events
from experiments.provenance import capture_provenance
from experiments.streams.controlled import ControlledStreamBuilder, ShiftSpec
from vigil import Vigil


def run_novelty_evaluation(
    config, protocol, test_scores, frozen_path, model_id, output_root
):
    """Persist evaluation of externally fitted, frozen scores; does not fit a model.

    The caller owns a truthful model identity and training-only preprocessing.
    Natural prevalence and controlled-prevalence results are reported separately.
    """
    from experiments.novelty_protocol import evaluate_frozen
    from experiments.novelty_scores import load_scores, save_scores
    from experiments.provenance import sha256_file

    frozen_path, output_root = Path(frozen_path), Path(output_root)
    if config.split != "test" or set(config.params) != {"n_prevalence_samples"}:
        raise ValueError("test split and explicit n_prevalence_samples required")
    natural = evaluate_frozen(frozen_path, protocol, test_scores, model_id=model_id)
    provenance = replace(
        capture_provenance([]),
        dataset_checksums={
            "novelty_protocol": protocol.identity,
            "novelty_freeze": sha256_file(frozen_path),
        },
    )
    directory = Path(output_root) / config.config_hash / provenance.identity_hash
    completed = load_completed_result(output_root, config, provenance)
    if completed is not None:
        receipt = completed.metadata["novelty_scores"]
        name = receipt["file"]
        if Path(name).name != name or not name.endswith(".npz"):
            raise ValueError("invalid score evidence filename")
        labels, scores = load_scores(directory / name, receipt)
        if not np.array_equal(labels, protocol.test.labels) or not np.array_equal(
            scores, test_scores.values
        ):
            raise ValueError(
                "resumed score evidence differs from supplied frozen-model scores"
            )
        return replace(completed, metadata={**completed.metadata, "resumed": True})
    grid = []
    for prevalence in (0.01, 0.05, 0.1, 0.25, 0.5):
        result = evaluate_frozen(
            frozen_path,
            protocol,
            test_scores,
            model_id=model_id,
            prevalence=prevalence,
            n_samples=config.params["n_prevalence_samples"],
            seed=config.seed,
        )
        grid.append(
            {
                "prevalence": prevalence,
                "n_novel": result.true_positives + result.false_negatives,
                "metrics": asdict(result),
            }
        )
    score_path = directory / f"novelty_scores-{uuid4().hex}.npz"
    receipt = save_scores(score_path, protocol.test.labels, test_scores.values)
    receipt["file"] = score_path.name
    result = ResultEnvelope(
        config.canonical_dict(),
        provenance,
        {
            "primary": natural.average_precision,
            "natural": asdict(natural),
            "prevalence_grid": grid,
            "manifest": {"hash": protocol.identity},
        },
        result_id=f"{config.config_hash}-{provenance.identity_hash}",
        metadata={
            "stage": "test",
            "primary_metric": "sample_average_precision",
            "resumed": False,
            "model_id": model_id,
            "novelty_scores": receipt,
            "threshold_selected_on": "validation",
            "evaluation_uses_labels": True,
        },
    )
    write_result_atomic(output_root, result)
    return result


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _write_failure(
    output_root: Path,
    config: ExperimentConfig,
    provenance: object,
    error: Exception,
) -> None:
    directory = output_root / config.config_hash
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / ".failure.json.tmp"
    failure = directory / "failure.json"
    payload = {
        "config": config.canonical_dict(),
        "provenance": asdict(provenance),
        "exception": type(error).__name__,
        "message": str(error),
        "traceback": traceback.format_exc(),
    }
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(failure)


def run_experiment(config: ExperimentConfig, output_root: Path) -> ResultEnvelope:
    """Run one validated configuration or resume an exact completed result."""

    _seed_everything(config.seed)
    provenance = capture_provenance([])
    completed = load_completed_result(output_root, config, provenance)
    if completed is not None:
        return replace(completed, metadata={**completed.metadata, "resumed": True})
    try:
        if config.dataset != "synthetic":
            raise ValueError(f"unsupported dataset: {config.dataset}")
        if config.method != "vigil":
            raise ValueError(
                f"unsupported method: {config.method}; "
                "this runner currently supports Vigil smoke tests only"
            )
        params = config.params
        n_reference = int(params.get("n_reference", 200))
        n_chunks = int(params.get("n_chunks", 6))
        n_features = int(params.get("n_features", 8))
        rng = np.random.default_rng(config.seed)
        reference = rng.normal(size=(n_reference, n_features)).astype(np.float32)
        shift = ShiftSpec(
            kind="mean",
            features=(0,),
            magnitude=2.0,
            event_chunk=max(2, n_chunks // 2),
            n_chunks=n_chunks,
            chunk_size=config.chunk_size,
            seed=config.seed,
        )
        chunks, manifest = ControlledStreamBuilder().build(reference, shift)
        vigil = Vigil(
            n_features=n_features,
            feature_names=[f"feature_{index}" for index in range(n_features)],
            buffer_size=n_reference,
            drift_threshold=0.3,
            initial_epochs=5,
            update_epochs=2,
        )
        vigil.fit(reference, verbose=False)
        adapter = VigilAttributionAdapter(vigil._autoencoder_A)
        shifted_chunk = chunks[shift.event_chunk - 1].X
        attribution = adapter.rank(
            reference,
            shifted_chunk,
            tuple("numerical" for _ in range(n_features)),
        )
        attribution_metrics = evaluate_ranking(
            attribution.scores,
            shifted_features=set(shift.features),
            ks=(1, 3, 5),
        )
        alerts: list[int] = []
        for chunk in chunks:
            result = vigil.detect(chunk.X)
            if result.drift_detected:
                alerts.append(chunk.chunk_id)
        event_metrics = asdict(
            match_events(
                manifest.events,
                alerts,
                config.tolerance_chunks,
                total_samples=n_chunks * config.chunk_size,
            )
        )
        result_id = f"{config.config_hash}-{provenance.identity_hash}"
        envelope = ResultEnvelope(
            config=config.canonical_dict(),
            provenance=provenance,
            metrics={
                "primary": attribution_metrics["ndcg@5"],
                "attribution": attribution_metrics,
                "events": event_metrics,
                "manifest": {
                    "hash": sha256(
                        reference.tobytes()
                        + b"".join(chunk.X.tobytes() for chunk in chunks)
                        + json.dumps(asdict(manifest), sort_keys=True).encode()
                    ).hexdigest(),
                    "events": [asdict(event) for event in manifest.events],
                },
            },
            result_id=result_id,
            metadata={
                "resumed": False,
                "uses_labels": False,
                "primary_metric": "ndcg@5",
                "stage": "smoke_only",
            },
        )
        write_result_atomic(output_root, envelope)
        return envelope
    except Exception as error:
        _write_failure(output_root, config, provenance, error)
        raise
