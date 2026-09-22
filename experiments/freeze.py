"""Validation-only threshold selection and a checksummed test configuration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Sequence

from experiments.config import ExperimentConfig
from experiments.io import ResultEnvelope


def _digest(payload: dict) -> str:
    return sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def _protocol(config: dict) -> dict:
    protocol = deepcopy(config)
    protocol["params"].pop("drift_threshold", None)
    return protocol


def freeze_validation_results(path: Path, trials: Sequence[ResultEnvelope]) -> Path:
    """Select maximum validation event F1; ties prefer fewer FAs, then higher threshold.

    Only a single paired seed/protocol is supported here. This is not a multi-seed
    model-selection procedure. The complete trial evidence is retained.
    """
    if not trials:
        raise ValueError("validation trials must not be empty")
    baseline = trials[0]
    ranked = []
    thresholds = set()
    for trial in trials:
        if (
            trial.config["split"] != "validation"
            or trial.metadata.get("stage") != "validation"
        ):
            raise ValueError("only validation evidence can freeze test parameters")
        if _protocol(trial.config) != _protocol(baseline.config):
            raise ValueError("validation protocols differ beyond drift_threshold")
        if trial.provenance.identity_hash != baseline.provenance.identity_hash:
            raise ValueError("validation provenance mismatch")
        if trial.metrics["manifest"]["hash"] != baseline.metrics["manifest"]["hash"]:
            raise ValueError("validation stream mismatch")
        threshold = float(trial.config["params"]["drift_threshold"])
        if (
            not math.isfinite(threshold)
            or not 0 <= threshold <= 1
            or threshold in thresholds
        ):
            raise ValueError("invalid or repeated threshold")
        thresholds.add(threshold)
        events = trial.metrics["events"]
        if events["true_events"] <= 0:
            raise ValueError("validation requires known change events")
        f1 = events["event_f1"]
        if f1 is None:
            raise ValueError("undefined validation F1 cannot select a threshold")
        if not math.isfinite(f1) or not 0 <= f1 <= 1:
            raise ValueError("invalid validation F1")
        ranked.append((f1, -events["false_alarms"], threshold, trial))
    chosen = max(ranked, key=lambda item: item[:3])[3]
    config = deepcopy(chosen.config)
    config["split"] = "test"
    payload = {
        "schema_version": 1,
        "selected_config": config,
        "dataset_checksums": baseline.provenance.dataset_checksums,
        "selection_rule": "maximum event F1; ties: fewer false alarms, higher threshold",
        "validation_trials": [asdict(trial) for trial in trials],
    }
    payload["integrity_sha256"] = _digest(payload)
    encoded = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: repeated tuning cannot silently replace a frozen protocol.
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    return path


def load_frozen_config(
    path: Path, dataset_checksums: dict[str, str]
) -> ExperimentConfig:
    """Fail closed on absent, edited, or dataset-incompatible manifests."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected = payload.pop("integrity_sha256")
        if expected != _digest(payload) or payload["schema_version"] != 1:
            raise ValueError("frozen manifest integrity mismatch")
        if payload["dataset_checksums"] != dataset_checksums:
            raise ValueError("frozen dataset checksum mismatch")
        config = ExperimentConfig(**payload["selected_config"])
        if config.split != "test":
            raise ValueError("frozen configuration is not a test configuration")
        return config
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("invalid frozen manifest integrity") from error
