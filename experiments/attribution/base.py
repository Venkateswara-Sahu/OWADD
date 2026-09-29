from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


VALID_FEATURE_TYPES = {"numerical", "categorical"}


@dataclass(frozen=True)
class AttributionScores:
    method: str
    scores: np.ndarray
    elapsed_ms: float
    metadata: dict[str, object]


class AttributionMethod(Protocol):
    name: str

    def rank(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        feature_types: tuple[str, ...],
    ) -> AttributionScores: ...


def validate_inputs(
    reference: np.ndarray,
    current: np.ndarray,
    feature_types: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray]:
    left = np.asarray(reference)
    right = np.asarray(current)
    if left.ndim != 2 or right.ndim != 2:
        raise ValueError("reference and current arrays must be two-dimensional")
    if left.shape[1] != right.shape[1]:
        raise ValueError("reference and current arrays must share a feature schema")
    if len(feature_types) != left.shape[1]:
        raise ValueError("feature_types length must equal the feature count")
    unknown = sorted(set(feature_types) - VALID_FEATURE_TYPES)
    if unknown:
        raise ValueError(f"unknown feature type: {unknown}")
    return left, right
