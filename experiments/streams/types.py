from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ChangeEvent:
    event_id: str
    start_chunk: int
    end_chunk: int
    kind: str
    shifted_features: tuple[int, ...]
    magnitude: float


@dataclass(frozen=True)
class StreamChunk:
    chunk_id: int
    X: np.ndarray
    sample_labels: np.ndarray | None = None


@dataclass(frozen=True)
class StreamManifest:
    seed: int
    n_features: int
    chunk_size: int
    events: tuple[ChangeEvent, ...]
