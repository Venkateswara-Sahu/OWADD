from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ExperimentConfig:
    """Validated, canonical configuration for one experiment run."""

    dataset: str
    method: str
    seed: int
    split: str = "test"
    chunk_size: int = 200
    tolerance_chunks: int = 2
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.seed < 0:
            raise ValueError("seed must be non-negative")
        if self.chunk_size < 2:
            raise ValueError("chunk_size must be at least 2")
        if self.tolerance_chunks < 0:
            raise ValueError("tolerance_chunks must be non-negative")

    @classmethod
    def from_yaml(cls, path: Path) -> ExperimentConfig:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError("configuration root must be a mapping")
        allowed = {item.name for item in fields(cls)}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"unknown configuration keys: {unknown}")
        return cls(**payload)

    def canonical_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def config_hash(self) -> str:
        encoded = json.dumps(
            self.canonical_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return sha256(encoded).hexdigest()[:16]
