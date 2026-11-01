"""Tests for the drift injections that the calibrated study relies on."""

import numpy as np
import pytest

from experiments.calibrated_data import (
    LOCALIZATION_CONDITIONS,
    NULL_POPULATIONS,
    Injection,
    apply_injection,
    injectable_columns,
    real_window,
    synthetic_pool,
)


def _ref_cur(n=300, d=6, seed=0):
    rng = np.random.default_rng(seed)
    ref = rng.normal(size=(n, d))
    cur = rng.normal(size=(n, d))
    return ref, cur, rng


def test_null_injection_returns_an_untouched_copy():
    ref, cur, rng = _ref_cur()
    observed, truth = apply_injection(ref, cur, Injection("none"), rng)
    assert truth == ()
    assert np.array_equal(observed, cur)
    assert observed is not cur


def test_mean_injection_shifts_only_the_truth_columns():
    ref, cur, rng = _ref_cur()
    observed, truth = apply_injection(ref, cur, Injection("mean", 0.75, 2), rng)
    assert len(truth) == 2
    delta = observed - cur
    shifted = np.abs(delta).sum(axis=0)
    assert np.allclose(shifted[list(truth)], 0.75 * len(cur))
    untouched = [j for j in range(cur.shape[1]) if j not in truth]
    assert np.allclose(shifted[untouched], 0.0)


def test_sparse_mean_injection_touches_only_a_fraction_of_rows():
    ref, cur, rng = _ref_cur(n=400)
    observed, _ = apply_injection(ref, cur, Injection("mean", 1.0, 2, 0.1), rng)
    changed_rows = np.any(observed != cur, axis=1)
    assert 20 <= changed_rows.sum() <= 60
    assert np.allclose(observed[~changed_rows], cur[~changed_rows])


def test_scale_injection_multiplies_dispersion_about_the_reference_mean():
    ref, cur, rng = _ref_cur(n=400, d=4)
    observed, truth = apply_injection(ref, cur, Injection("scale", 0.5, 2), rng)
    for column in truth:
        assert observed[:, column].std() == pytest.approx(
            0.5 * cur[:, column].std(), rel=1e-6
        )
        assert observed[:, column].mean() == pytest.approx(
            0.5 * cur[:, column].mean() + 0.5 * ref[:, column].mean(), rel=1e-6
        )


def test_permutation_injection_preserves_the_marginal_exactly():
    ref, cur, rng = _ref_cur()
    observed, truth = apply_injection(ref, cur, Injection("permute", 0, 2), rng)
    for column in truth:
        assert np.array_equal(np.sort(observed[:, column]), np.sort(cur[:, column]))
    # A permutation must break the cross-feature covariance that was there.
    before = np.corrcoef(cur[:, truth[0]], cur[:, truth[1]])[0, 1]
    after = np.corrcoef(observed[:, truth[0]], observed[:, truth[1]])[0, 1]
    assert abs(after) < 0.5 or abs(before) < 0.5


def test_permutation_injection_is_sorted_value_preserving_under_sparsity():
    ref, cur, rng = _ref_cur(n=400)
    observed, truth = apply_injection(ref, cur, Injection("permute", 0, 2, 0.25), rng)
    changed_rows = np.any(observed != cur, axis=1)
    assert changed_rows.sum() < len(cur)
    for column in truth:
        assert np.array_equal(
            np.sort(observed[changed_rows, column]), np.sort(cur[changed_rows, column])
        )


def test_paircorr_injection_reaches_the_target_rank_correlation():
    ref, cur, rng = _ref_cur(n=500, d=4)
    observed, truth = apply_injection(ref, cur, Injection("paircorr", 0.8, 2), rng)
    a, b = truth
    from scipy import stats

    achieved = stats.spearmanr(observed[:, a], observed[:, b]).statistic
    assert achieved == pytest.approx(0.8, abs=0.05)
    for column in truth:
        assert np.array_equal(np.sort(observed[:, column]), np.sort(cur[:, column]))


def test_paircorr_requires_exactly_two_features():
    ref, cur, rng = _ref_cur()
    with pytest.raises(ValueError):
        apply_injection(ref, cur, Injection("paircorr", 0.5, 3), rng)


def test_injection_labels_are_unique_and_descriptive():
    labels = [condition.label for condition in LOCALIZATION_CONDITIONS]
    assert len(labels) == len(set(labels))
    assert "null" in labels
    assert any("sparse20" in label for label in labels)
    assert any(label.startswith("permute") for label in labels)


def test_unknown_injection_kind_is_rejected():
    ref, cur, rng = _ref_cur()
    with pytest.raises(ValueError):
        apply_injection(ref, cur, Injection("teleport"), rng)


def test_injections_are_deterministic_for_a_given_seed():
    ref, cur, _ = _ref_cur()
    first, truth_first = apply_injection(
        ref, cur, Injection("permute", 0, 2), np.random.default_rng([7, 1])
    )
    second, truth_second = apply_injection(
        ref, cur, Injection("permute", 0, 2), np.random.default_rng([7, 1])
    )
    assert truth_first == truth_second
    assert np.array_equal(first, second)


def test_synthetic_pools_have_the_advertised_shape_and_finite_values():
    for name in NULL_POPULATIONS:
        rng = np.random.default_rng(0)
        pool = synthetic_pool(name, rng, 200, 7)
        assert pool.shape == (200, 7)
        assert np.isfinite(pool).all()


def test_zero_inflated_population_actually_has_ties_and_zeros():
    pool = synthetic_pool("zero_inflated_tied", np.random.default_rng(1), 400, 5)
    zero_fraction = float(np.mean(pool == 0.0))
    assert zero_fraction > 0.4
    distinct = len(np.unique(pool[:, 0]))
    assert distinct < len(pool) // 2


def test_multivariate_t_population_is_heavier_tailed_than_gaussian():
    t_pool = synthetic_pool("multivariate_t3", np.random.default_rng(2), 2000, 4)
    g_pool = synthetic_pool("gaussian", np.random.default_rng(2), 2000, 4)
    kurtosis_t = float(np.mean(((t_pool - t_pool.mean(0)) / t_pool.std(0)) ** 4))
    kurtosis_g = float(np.mean(((g_pool - g_pool.mean(0)) / g_pool.std(0)) ** 4))
    assert kurtosis_t > kurtosis_g


def test_unknown_population_is_rejected():
    with pytest.raises(ValueError):
        synthetic_pool("cauchy_party", np.random.default_rng(0), 10, 3)


def test_real_window_is_row_disjoint_and_seed_dependent():
    pools = {"validation": np.random.default_rng(4).normal(size=(4000, 3))}
    ref_a, cur_a = real_window(pools, seed=0, window=100, block_size=200, n_blocks=10)
    ref_b, _ = real_window(pools, seed=1, window=100, block_size=200, n_blocks=10)
    assert ref_a.shape == cur_a.shape == (100, 3)
    assert not np.array_equal(ref_a, ref_b)
    assert not np.array_equal(ref_a, cur_a)
    assert not np.any(np.isin(ref_a[:, 0], cur_a[:, 0]))


def test_real_window_rejects_impossible_block_requests():
    pools = {"validation": np.zeros((100, 2))}
    with pytest.raises(ValueError):
        real_window(pools, seed=0, window=100, block_size=150, n_blocks=5)


def test_injectable_columns_skips_constant_features():
    pool = np.random.default_rng(0).normal(size=(50, 4))
    pool[:, 2] = 1.0
    assert injectable_columns(pool) == [0, 1, 3]
