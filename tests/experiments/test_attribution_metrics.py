import numpy as np
import pytest

from experiments.metrics.attribution import evaluate_ranking, top_k_jaccard


def test_ranking_metrics_match_known_order() -> None:
    scores = np.array([0.1, 0.9, 0.8, 0.2])

    metrics = evaluate_ranking(scores, shifted_features={1, 2}, ks=(1, 2, 5))

    assert metrics["precision@1"] == 1.0
    assert metrics["recall@1"] == 0.5
    assert metrics["precision@2"] == 1.0
    assert metrics["recall@2"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["precision@5"] == pytest.approx(0.5)
    assert metrics["average_shifted_rank"] == pytest.approx(1.5)
    assert metrics["top1_accuracy"] == 1.0


def test_empty_ground_truth_has_explicit_undefined_recall() -> None:
    metrics = evaluate_ranking(
        np.array([0.2, 0.1]), shifted_features=set(), ks=(1,)
    )

    assert metrics["recall@1"] is None
    assert metrics["mrr"] is None
    assert metrics["ndcg@1"] is None


def test_ties_are_broken_by_feature_index() -> None:
    metrics = evaluate_ranking(
        np.array([0.5, 0.5, 0.1]), shifted_features={0}, ks=(1,)
    )

    assert metrics["top1_accuracy"] == 1.0


def test_invalid_scores_and_ground_truth_are_rejected() -> None:
    with pytest.raises(ValueError, match="one-dimensional"):
        evaluate_ranking(np.zeros((2, 2)), {0}, (1,))
    with pytest.raises(ValueError, match="non-finite"):
        evaluate_ranking(np.array([0.2, np.nan]), {0}, (1,))
    with pytest.raises(ValueError, match="shifted feature"):
        evaluate_ranking(np.array([0.2, 0.1]), {2}, (1,))


def test_top_k_jaccard_uses_clamped_k() -> None:
    assert top_k_jaccard(np.array([3.0, 2.0]), np.array([2.0, 3.0]), 5) == 1.0
