from __future__ import annotations

from time import perf_counter_ns

import numpy as np

from experiments.attribution.base import AttributionScores, validate_inputs
from vigil.attribution import DriftAttributor


class VigilAttributionAdapter:
    name = "vigil_reconstruction_delta"

    def __init__(self, model: object) -> None:
        self.model = model

    def rank(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        feature_types: tuple[str, ...],
    ) -> AttributionScores:
        left, right = validate_inputs(reference, current, feature_types)
        started = perf_counter_ns()
        result = DriftAttributor(top_k=left.shape[1]).attribute(
            self.model, left, right
        )
        elapsed_ms = (perf_counter_ns() - started) / 1_000_000
        return AttributionScores(
            method=self.name,
            scores=result.feature_error_delta.copy(),
            elapsed_ms=elapsed_ms,
            metadata=dict(result.metadata),
        )
