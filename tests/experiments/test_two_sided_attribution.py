import numpy as np
import pytest
import torch


def test_two_sided_scores_retain_decreases_and_reference_scale():
    from experiments.attribution.two_sided import two_sided_scores

    model = torch.nn.Linear(2, 2, bias=False)
    with torch.no_grad():
        model.weight.zero_()
    reference = np.array([[0.0, 0.0], [2.0, 4.0]])
    current = np.array([[1.0, 2.0], [1.0, 2.0]])
    scores, details = two_sided_scores(model, reference, current)
    np.testing.assert_allclose(details["signed_delta"], [-1.0, -4.0])
    np.testing.assert_allclose(scores["vigil_absolute_delta"], [1.0, 4.0])
    np.testing.assert_allclose(
        scores["vigil_standardized_absolute_delta"], [1 / np.sqrt(8), 1 / np.sqrt(8)]
    )
    assert model.training
    assert model.weight.grad is None


def test_zero_variance_is_finite_and_original_rule_is_unchanged():
    from experiments.attribution.two_sided import two_sided_scores
    from vigil.attribution import DriftAttributor

    model = torch.nn.Linear(2, 2, bias=False)
    with torch.no_grad():
        model.weight.zero_()
    reference, current = np.ones((3, 2)), np.zeros((3, 2))
    before = DriftAttributor().attribute(model, reference, current)
    scores, details = two_sided_scores(model, reference, current)
    after = DriftAttributor().attribute(model, reference, current)
    np.testing.assert_array_equal(before.feature_contributions, [0.0, 0.0])
    np.testing.assert_array_equal(
        after.feature_contributions, before.feature_contributions
    )
    np.testing.assert_array_equal(
        scores["vigil_standardized_absolute_delta"], [1e12, 1e12]
    )
    np.testing.assert_array_equal(details["signed_delta"], [-1.0, -1.0])
    repeated = two_sided_scores(model, reference, current)
    np.testing.assert_array_equal(
        repeated[0]["vigil_absolute_delta"], scores["vigil_absolute_delta"]
    )


@pytest.mark.parametrize(
    "reference,current",
    [
        (np.ones((1, 2)), np.zeros((3, 2))),
        (np.ones((3, 2)), np.zeros((3, 1))),
        (np.ones((3, 2)), np.full((3, 2), np.nan)),
        (np.ones((3, 2)), np.empty((0, 2))),
    ],
)
def test_invalid_windows_rejected(reference, current):
    from experiments.attribution.two_sided import two_sided_scores

    with pytest.raises(ValueError):
        two_sided_scores(torch.nn.Identity(), reference, current)
