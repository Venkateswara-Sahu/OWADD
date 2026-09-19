from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from experiments.config import ExperimentConfig
from experiments.provenance import Provenance


class ResultIntegrityError(RuntimeError):
    """Raised when a completed result cannot be trusted."""


@dataclass(frozen=True)
class ResultEnvelope:
    config: dict[str, Any]
    provenance: Provenance
    metrics: dict[str, Any]
    result_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _config_hash(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()[:16]


def _result_path(
    root: Path, config_hash: str, provenance_hash: str
) -> Path:
    return root / config_hash / provenance_hash / "result.json"


def write_result_atomic(root: Path, envelope: ResultEnvelope) -> Path:
    """Atomically persist a result, then publish its completion marker."""

    result_path = _result_path(
        root,
        _config_hash(envelope.config),
        envelope.provenance.identity_hash,
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    marker = result_path.with_suffix(".complete")
    marker.unlink(missing_ok=True)
    temporary = result_path.with_name(f".{result_path.name}.{uuid4().hex}.tmp")
    try:
        encoded = json.dumps(
            {
                "config": envelope.config,
                "provenance": asdict(envelope.provenance),
                "metrics": envelope.metrics,
                "result_id": envelope.result_id,
                "metadata": envelope.metadata,
            },
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(result_path)
        marker.write_text("complete\n", encoding="ascii")
    finally:
        temporary.unlink(missing_ok=True)
    return result_path


def load_completed_result(
    root: Path,
    config: ExperimentConfig,
    provenance: Provenance,
) -> ResultEnvelope | None:
    """Load an exactly matching completed result, if one exists."""

    result_path = _result_path(root, config.config_hash, provenance.identity_hash)
    marker = result_path.with_suffix(".complete")
    if not marker.exists() or not result_path.exists():
        return None
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        loaded_provenance = Provenance(**payload["provenance"])
        envelope = ResultEnvelope(
            config=payload["config"],
            provenance=loaded_provenance,
            metrics=payload["metrics"],
            result_id=payload.get("result_id", ""),
            metadata=payload.get("metadata", {}),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ResultIntegrityError(
            f"invalid result JSON at {result_path}: {exc}"
        ) from exc
    if envelope.config != config.canonical_dict():
        raise ResultIntegrityError("completed result configuration does not match")
    if envelope.provenance.identity_hash != provenance.identity_hash:
        return None
    return envelope
