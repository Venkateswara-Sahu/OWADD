from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np


def _ranking(scores: np.ndarray) -> np.ndarray:
    values = np.asarray(scores, dtype=float)
    if values.ndim != 1:
        raise ValueError("scores must be one-dimensional")
    if values.size == 0:
        raise ValueError("scores must not be empty")
    if not np.isfinite(values).all():
        raise ValueError("scores contain non-finite values")
    indices = np.arange(values.size)
    return np.lexsort((indices, -values))


def _validate_shifted_features(
    shifted_features: Iterable[int], n_features: int
) -> set[int]:
    shifted = set(shifted_features)
    invalid = sorted(index for index in shifted if index < 0 or index >= n_features)
    if invalid:
        raise ValueError(f"shifted feature indices outside score vector: {invalid}")
    return shifted


def _dcg(relevance: Sequence[int]) -> float:
    return float(
        sum(
            value / np.log2(position + 2)
            for position, value in enumerate(relevance)
        )
    )


def evaluate_ranking(
    scores: np.ndarray,
    shifted_features: Iterable[int],
    ks: Sequence[int] = (1, 3, 5, 10),
) -> dict[str, float | None]:
    """Evaluate a feature ranking against known shifted features."""

    ranking = _ranking(scores)
    shifted = _validate_shifted_features(shifted_features, ranking.size)
    if any(k <= 0 for k in ks):
        raise ValueError("all k values must be positive")

    rank_by_feature = {
        int(feature): position
        for position, feature in enumerate(ranking, start=1)
    }
    metrics: dict[str, float | None] = {}
    for requested_k in ks:
        effective_k = min(requested_k, ranking.size)
        selected = ranking[:effective_k]
        hits = sum(int(feature) in shifted for feature in selected)
        metrics[f"precision@{requested_k}"] = hits / effective_k
        metrics[f"recall@{requested_k}"] = (
            hits / len(shifted) if shifted else None
        )
        if shifted:
            relevance = [int(int(feature) in shifted) for feature in selected]
            ideal = [1] * min(len(shifted), effective_k)
            ideal.extend([0] * (effective_k - len(ideal)))
            denominator = _dcg(ideal)
            metrics[f"ndcg@{requested_k}"] = (
                _dcg(relevance) / denominator if denominator else None
            )
        else:
            metrics[f"ndcg@{requested_k}"] = None

    if shifted:
        shifted_ranks = [rank_by_feature[feature] for feature in shifted]
        metrics["mrr"] = 1.0 / min(shifted_ranks)
        metrics["average_shifted_rank"] = float(np.mean(shifted_ranks))
        metrics["top1_accuracy"] = float(int(ranking[0]) in shifted)
    else:
        metrics["mrr"] = None
        metrics["average_shifted_rank"] = None
        metrics["top1_accuracy"] = None
    return metrics


def top_k_jaccard(first: np.ndarray, second: np.ndarray, k: int) -> float:
    """Return Jaccard agreement between two deterministic top-k rankings."""

    if k <= 0:
        raise ValueError("k must be positive")
    first_rank = _ranking(first)
    second_rank = _ranking(second)
    if first_rank.size != second_rank.size:
        raise ValueError("rankings must contain the same number of features")
    effective_k = min(k, first_rank.size)
    left = set(map(int, first_rank[:effective_k]))
    right = set(map(int, second_rank[:effective_k]))
    return len(left & right) / len(left | right)
