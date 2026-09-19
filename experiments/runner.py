from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import random
import traceback

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


def run_experiment(
    config: ExperimentConfig, output_root: Path
) -> ResultEnvelope:
    """Run one validated configuration or resume an exact completed result."""

    _seed_everything(config.seed)
    provenance = capture_provenance([])
    completed = load_completed_result(output_root, config, provenance)
    if completed is not None:
        return replace(completed, metadata={**completed.metadata, "resumed": True})
    try:
        if config.dataset != "synthetic":
            raise ValueError(f"unsupported dataset: {config.dataset}")
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
                "attribution": attribution_metrics,
                "events": event_metrics,
                "manifest": {
                    "hash": result_id,
                    "events": [asdict(event) for event in manifest.events],
                },
            },
            result_id=result_id,
            metadata={"resumed": False, "uses_labels": False},
        )
        write_result_atomic(output_root, envelope)
        return envelope
    except Exception as error:
        _write_failure(output_root, config, provenance, error)
        raise
