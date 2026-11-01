"""Tests for the paired-comparison and chance-line helpers."""

import math

import numpy as np
import pytest

from experiments.stats import (
    bootstrap_mean_ci,
    chance_line,
    holm_bonferroni,
    paired_comparison,
)


def test_paired_comparison_detects_consistent_improvement():
    rng = np.random.default_rng(0)
    baseline = rng.normal(0.5, 0.1, size=20)
    candidate = baseline + 0.2
    result = paired_comparison(candidate, baseline)
    assert result.n == 20
    assert result.wins == 20
    assert result.losses == 0
    assert result.delta == pytest.approx(0.2)
    assert result.p_value < 0.01


def test_paired_comparison_identical_vectors_is_not_evidence():
    values = np.linspace(0.1, 0.9, 20)
    result = paired_comparison(values, values.copy())
    assert result.p_value == 1.0
    assert result.ties == 20
    assert result.delta == 0.0


def test_paired_comparison_falls_back_to_sign_test_for_small_samples():
    candidate = np.array([1.0, 1.0, 1.0, 0.0, 1.0])
    baseline = np.zeros(5)
    result = paired_comparison(candidate, baseline)
    assert result.wins == 4
    assert 0.0 < result.p_value <= 1.0


def test_paired_comparison_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        paired_comparison(np.zeros(3), np.zeros(4))


def test_holm_bonferroni_is_monotone_and_bounded():
    adjusted = holm_bonferroni({"a": 0.001, "b": 0.02, "c": 0.04})
    assert adjusted["a"] == pytest.approx(0.003)
    assert adjusted["b"] >= 0.003
    assert adjusted["c"] >= adjusted["b"] - 1e-12
    assert max(adjusted.values()) <= 1.0


def test_holm_bonferroni_single_comparison_is_unchanged():
    assert holm_bonferroni({"only": 0.03})["only"] == pytest.approx(0.03)


def test_chance_line_matches_hypergeometric_means():
    d, truth = 20, 2
    line = chance_line(d, truth, (1, 3, 5))
    assert line["recall@1"] == pytest.approx(1 / d)
    assert line["recall@3"] == pytest.approx(3 / d)
    assert line["precision@3"] == pytest.approx(truth / d)
    assert line["precision@1"] == pytest.approx(truth / d)


def test_chance_line_mrr_matches_monte_carlo():
    d, truth = 12, 2
    rng = np.random.default_rng(3)
    draws = np.empty(4000)
    for i in range(len(draws)):
        order = rng.permutation(d)
        draws[i] = 1.0 / (1 + min(np.flatnonzero(np.isin(order, (0, 1)))))
    analytic = chance_line(d, truth, (1,))["mrr"]
    assert analytic == pytest.approx(draws.mean(), abs=0.02)


def test_chance_line_ndcg_is_one_when_everything_is_truth():
    line = chance_line(4, 4, (4,))
    assert line["ndcg@4"] == pytest.approx(1.0)
    assert line["recall@4"] == pytest.approx(1.0)


def test_chance_line_validates_inputs():
    with pytest.raises(ValueError):
        chance_line(0, 1, (1,))
    with pytest.raises(ValueError):
        chance_line(5, 6, (1,))


def test_bootstrap_mean_ci_brackets_the_mean():
    values = np.linspace(-1.0, 1.0, 40)
    low, high = bootstrap_mean_ci(values, n_resamples=500, seed=1)
    assert low <= values.mean() <= high
    assert high - low < 1.0


def test_bootstrap_mean_ci_is_deterministic_for_a_seed():
    values = np.random.default_rng(5).normal(size=30)
    first = bootstrap_mean_ci(values, n_resamples=300, seed=7)
    second = bootstrap_mean_ci(values, n_resamples=300, seed=7)
    assert first == second


def test_chance_line_ndcg_uses_log_discount():
    line = chance_line(10, 1, (3,))
    # A single relevant feature found at a random position.
    expected = sum((1 / 10) * (1 / math.log2(i + 2)) for i in range(3)) / (
        1 / math.log2(2)
    )
    assert line["ndcg@3"] == pytest.approx(expected)
