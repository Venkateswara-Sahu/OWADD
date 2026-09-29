from __future__ import annotations

import numpy as np
import pytest
import torch

from experiments.attribution.discriminative import DiscriminativeAttributor
from experiments.attribution.statistical import (
    JensenShannonAttributor,
    KSAttributor,
    MeanDifferenceAttributor,
    StandardizedMeanDifferenceAttributor,
    WassersteinAttributor,
)
from vigil.attribution import DriftAttributor


NUMERIC_TYPES = ("numerical", "numerical", "categorical")


def make_reference(seed: int = 4) -> np.ndarray:
    rng = np.random.default_rng(seed)
    values = np.column_stack(
        [
            rng.normal(0, 1, 800),
            rng.normal(0, 1, 800),
            rng.choice([0.0, 1.0], 800, p=[0.8, 0.2]),
        ]
    )
    return values.astype(np.float64)


def test_mean_methods_rank_mean_shift_first() -> None:
    reference = make_reference()
    current = reference.copy()
    current[:, 0] += 3.0

    for method in (
        MeanDifferenceAttributor(),
        StandardizedMeanDifferenceAttributor(),
    ):
        result = method.rank(reference, current, NUMERIC_TYPES)
        assert np.nanargmax(result.scores) == 0
        assert np.isnan(result.scores[2])


def test_standardized_mean_difference_is_finite_for_constant_shift() -> None:
    reference = np.zeros((20, 1))
    current = np.ones((20, 1))

    result = StandardizedMeanDifferenceAttributor().rank(
        reference, current, ("numerical",)
    )

    assert np.isfinite(result.scores[0])
    assert result.scores[0] == pytest.approx(1.0)


def test_distribution_methods_rank_variance_shift_first() -> None:
    reference = make_reference()
    current = reference.copy()
    current[:, 1] *= 4.0

    for method in (KSAttributor(), WassersteinAttributor()):
        result = method.rank(reference, current, NUMERIC_TYPES)
        assert np.nanargmax(result.scores) == 1
        assert np.isnan(result.scores[2])


def test_jensen_shannon_ranks_categorical_frequency_shift_first() -> None:
    reference = make_reference()
    current = reference.copy()
    current[:, 2] = np.tile([1.0, 1.0, 1.0, 0.0], 200)

    result = JensenShannonAttributor().rank(reference, current, NUMERIC_TYPES)

    assert np.nanargmax(result.scores) == 2
    assert np.isnan(result.scores[0])


def test_discriminative_attributor_finds_separable_feature() -> None:
    reference = make_reference()
    current = reference.copy()
    current[:, 0] += 4.0

    result = DiscriminativeAttributor(seed=12).rank(
        reference, current, NUMERIC_TYPES
    )

    assert np.argmax(result.scores) == 0
    assert result.metadata["held_out_balanced_accuracy"] > 0.9


def test_unknown_feature_type_is_rejected() -> None:
    reference = make_reference()

    with pytest.raises(ValueError, match="unknown feature type"):
        MeanDifferenceAttributor().rank(
            reference, reference.copy(), ("numerical", "mystery", "categorical")
        )


class IdentityModel(torch.nn.Module):
    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return values


def test_drift_attributor_reports_no_evidence_when_all_deltas_are_zero() -> None:
    values = np.ones((20, 3), dtype=np.float32)

    result = DriftAttributor(top_k=2).attribute(
        IdentityModel(), values, values.copy()
    )

    np.testing.assert_array_equal(result.feature_contributions, np.zeros(3))
    assert result.metadata["no_positive_delta"] is True
