# ruff: noqa: PLR2004
import numpy as np
import pytest


def test_correlation_change_scores_known_pair_and_rejects_constants():
    from experiments.attribution.dependency import CorrelationChangeAttributor

    reference = np.array(
        [[-1.0, -1.0, 1.0], [-1.0, 1.0, -1.0], [1.0, -1.0, -1.0], [1.0, 1.0, 1.0]]
    )
    current = reference.copy()
    current[:, 1] = current[:, 0]
    method = CorrelationChangeAttributor()
    result = method.rank(reference, current, ("numerical",) * 3)
    np.testing.assert_allclose(result.scores, [1.0, 1.0, 0.0])
    assert result.elapsed_ms >= 0
    with pytest.raises(ValueError, match="constant"):
        method.rank(np.ones((4, 3)), current, ("numerical",) * 3)


def test_nonlinear_importance_retains_heldout_diagnostics_and_is_repeatable():
    from threadpoolctl import threadpool_limits

    from experiments.attribution.dependency import NonlinearPermutationAttributor

    rng = np.random.default_rng(1001)
    reference = rng.normal(size=(80, 3))
    current = rng.normal(size=(80, 3))
    current[:, 1] = current[:, 0] + current[:, 1] * 0.1
    with threadpool_limits(limits=1):
        method = NonlinearPermutationAttributor(seed=7)
        first = method.rank(reference, current, ("numerical",) * 3)
        second = method.rank(reference, current, ("numerical",) * 3)
    np.testing.assert_array_equal(first.scores, second.scores)
    assert first.metadata == second.metadata
    assert first.metadata["train_rows"] == 112
    assert first.metadata["held_out_rows"] == 48
    assert 0 <= first.metadata["held_out_balanced_accuracy"] <= 1
    np.testing.assert_array_equal(
        first.scores, np.maximum(first.metadata["signed_importance"], 0)
    )
    assert first.elapsed_ms >= 0
