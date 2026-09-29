from __future__ import annotations

from time import perf_counter_ns

import numpy as np
from scipy import stats
from scipy.spatial.distance import jensenshannon

from experiments.attribution.base import AttributionScores, validate_inputs


class _StatisticalAttributor:
    name = "statistical"
    supported_type = "numerical"

    def _score(self, reference: np.ndarray, current: np.ndarray) -> float:
        raise NotImplementedError

    def rank(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        feature_types: tuple[str, ...],
    ) -> AttributionScores:
        left, right = validate_inputs(reference, current, feature_types)
        started = perf_counter_ns()
        scores = np.full(left.shape[1], np.nan, dtype=float)
        for index, feature_type in enumerate(feature_types):
            if feature_type == self.supported_type:
                scores[index] = self._score(left[:, index], right[:, index])
        elapsed_ms = (perf_counter_ns() - started) / 1_000_000
        return AttributionScores(self.name, scores, elapsed_ms, {})


class MeanDifferenceAttributor(_StatisticalAttributor):
    name = "absolute_mean_difference"

    def _score(self, reference: np.ndarray, current: np.ndarray) -> float:
        return float(abs(current.mean() - reference.mean()))


class StandardizedMeanDifferenceAttributor(_StatisticalAttributor):
    name = "standardized_mean_difference"

    def _score(self, reference: np.ndarray, current: np.ndarray) -> float:
        pooled = np.sqrt((reference.var(ddof=1) + current.var(ddof=1)) / 2)
        difference = abs(current.mean() - reference.mean())
        if pooled == 0:
            return float(difference)
        return float(difference / pooled)


class KSAttributor(_StatisticalAttributor):
    name = "kolmogorov_smirnov"

    def _score(self, reference: np.ndarray, current: np.ndarray) -> float:
        return float(stats.ks_2samp(reference, current).statistic)


class WassersteinAttributor(_StatisticalAttributor):
    name = "wasserstein"

    def _score(self, reference: np.ndarray, current: np.ndarray) -> float:
        return float(stats.wasserstein_distance(reference, current))


class JensenShannonAttributor(_StatisticalAttributor):
    name = "jensen_shannon"
    supported_type = "categorical"

    def _score(self, reference: np.ndarray, current: np.ndarray) -> float:
        categories = np.union1d(reference, current)
        left = np.asarray([(reference == value).sum() for value in categories]) + 1
        right = np.asarray([(current == value).sum() for value in categories]) + 1
        left = left / left.sum()
        right = right / right.sum()
        return float(jensenshannon(left, right, base=2.0))
