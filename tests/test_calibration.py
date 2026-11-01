import numpy as np
import pytest

from vigil.attribution import DriftAttributor
from vigil.calibration import compute_calibrated_scores

B = 99


def _block_cov(rng, d=12):
    a = rng.normal(size=(d, 3))
    cov = a @ a.T + np.diag(rng.uniform(0.3, 1.0, d))
    sd = np.sqrt(np.diag(cov))
    return cov / np.outer(sd, sd)


def test_deterministic_for_fixed_seed():
    rng = np.random.default_rng(0)
    ref, cur = rng.normal(size=(120, 6)), rng.normal(size=(120, 6))
    a = compute_calibrated_scores(ref, cur, n_permutations=B, seed=5)
    b = compute_calibrated_scores(ref, cur, n_permutations=B, seed=5)
    np.testing.assert_array_equal(a.combined_scores, b.combined_scores)


def test_pvalues_are_valid_and_bounded_below():
    rng = np.random.default_rng(1)
    ref = rng.normal(size=(150, 5))
    cur = rng.normal(size=(150, 5))
    cur[:, 0] += 3.0
    out = compute_calibrated_scores(ref, cur, n_permutations=B, seed=0)
    assert np.all(out.marginal_pvalues >= 1.0 / (B + 1))
    assert np.all(out.marginal_pvalues <= 1.0)
    assert out.marginal_pvalues[0] == pytest.approx(1.0 / (B + 1))
    assert out.combined_scores.argmax() == 0


def test_null_has_few_family_wise_rejections():
    rng = np.random.default_rng(2)
    rejections = 0
    trials = 30
    for t in range(trials):
        pool = rng.standard_t(df=3, size=(240, 8))  # heavy-tailed null
        out = compute_calibrated_scores(
            pool[:120], pool[120:], n_permutations=B, seed=t
        )
        rejections += bool(out.significant_features())
    # Nominal 5%: allow generous Monte-Carlo slack, far below the 50%+ the
    # asymptotic Fisher-z calibration shows on t-copula data.
    assert rejections / trials <= 0.2


def test_peeling_recovers_both_permuted_features():
    rng = np.random.default_rng(3)
    hits = 0
    trials = 12
    for t in range(trials):
        x = rng.multivariate_normal(np.zeros(12), _block_cov(rng), size=600)
        ref, cur = x[:300], x[300:].copy()
        truth = rng.choice(12, 2, replace=False)
        for c in truth:
            cur[:, c] = rng.permutation(cur[:, c])
        out = compute_calibrated_scores(ref, cur, n_permutations=B, seed=t)
        top3 = set(np.argsort(-out.combined_scores)[:3])
        hits += len(top3 & set(truth)) / 2
    assert hits / trials >= 0.9


def test_pair_correlation_shift_ranks_both_endpoints_top3():
    rng = np.random.default_rng(4)
    a, b = (np.sqrt(1.8) + np.sqrt(0.2)) / 2, (np.sqrt(1.8) - np.sqrt(0.2)) / 2
    ref, base = rng.normal(size=(400, 10)), rng.normal(size=(400, 10))
    cur = base.copy()
    cur[:, [2, 7]] = base[:, [2, 7]] @ np.array([[a, b], [b, a]])
    out = compute_calibrated_scores(ref, cur, n_permutations=B, seed=0)
    assert {2, 7} <= set(np.argsort(-out.combined_scores)[:3])
    assert {2, 7} & set(out.selected_features)


def test_constant_and_tiny_inputs_do_not_crash():
    ref = np.zeros((50, 3))
    cur = np.random.default_rng(0).normal(size=(50, 3))
    out = compute_calibrated_scores(ref, cur, n_permutations=19, seed=0)
    assert out.combined_scores.shape == (3,) and np.isfinite(out.combined_scores).all()
    tiny = compute_calibrated_scores(np.zeros((2, 3)), np.zeros((2, 3)))
    assert not tiny.combined_scores.any()


def test_input_validation():
    with pytest.raises(ValueError):
        compute_calibrated_scores(np.zeros((10, 3)), np.zeros((10, 4)))
    with pytest.raises(ValueError):
        compute_calibrated_scores(
            np.zeros((10, 3)), np.zeros((10, 3)), n_permutations=0
        )


def test_drift_attributor_calibrated_mode_without_model():
    rng = np.random.default_rng(5)
    ref = rng.normal(size=(200, 6))
    cur = rng.normal(size=(200, 6))
    cur[:, 3] += 1.0
    res = DriftAttributor(top_k=2, mode="calibrated", n_permutations=B).attribute(
        reference_data=ref, current_batch=cur
    )
    assert res.top_features[0]["feature_index"] == 3
    assert res.top_features[0]["drift_type"] == "marginal"
    significant = res.metadata["significant_features"]
    assert isinstance(significant, list)
    assert 3 in significant
    assert res.metadata["dominant_drift_regime"] == "marginal"


def test_constant_column_is_masked_not_significant():
    """A column that never varies must never be reported as drift."""
    rng = np.random.default_rng(11)
    ref = rng.normal(size=(120, 4))
    cur = rng.normal(size=(120, 4))
    ref[:, 2] = 0.0
    cur[:, 2] = 0.0
    out = compute_calibrated_scores(ref, cur, n_permutations=B, seed=0)
    assert out.marginal_pvalues[2] == 1.0
    assert out.marginal_evidence[2] == 0.0
    assert 2 not in out.selected_features
    assert out.metadata["constant_columns_masked"] == [2]


def test_sparse_column_constant_in_one_window_still_detected():
    """Masking is by *pooled* variance: a feature that fires only after the
    shift is the strongest possible marginal signal and must survive."""
    rng = np.random.default_rng(12)
    ref = rng.normal(size=(150, 5))
    cur = rng.normal(size=(150, 5))
    ref[:, 1] = 0.0
    cur[:30, 1] = rng.normal(loc=2.0, scale=0.1, size=30)
    out = compute_calibrated_scores(ref, cur, n_permutations=B, seed=0)
    assert out.marginal_pvalues[1] == pytest.approx(1.0 / (B + 1))
    assert out.significant_features() == [1]
    # The relational pathway cannot see it: a column constant in the reference
    # window has no baseline correlation to shift, so it is not a copula column.
    assert 1 not in out.metadata["copula_columns"]


def test_insufficient_permutations_raise():
    rng = np.random.default_rng(13)
    ref, cur = rng.normal(size=(60, 4)), rng.normal(size=(60, 4))
    with pytest.raises(ValueError, match="cannot resolve alpha"):
        compute_calibrated_scores(ref, cur, n_permutations=10, alpha=0.05)
    # Two-family split halves the level, so B must clear 2 / alpha.
    with pytest.raises(ValueError, match="cannot resolve alpha"):
        compute_calibrated_scores(ref, cur, n_permutations=30, alpha=0.05)


def test_family_alias_is_a_copy_not_an_alias():
    rng = np.random.default_rng(14)
    ref, cur = rng.normal(size=(80, 4)), rng.normal(size=(80, 4))
    out = compute_calibrated_scores(ref, cur, n_permutations=B, seed=0)
    marginal = out.marginal_family_pvalues
    edge = out.edge_family_pvalues
    assert marginal is not None and edge is not None
    np.testing.assert_array_equal(marginal, out.marginal_pvalues)
    marginal[0] = -1.0
    assert out.marginal_pvalues[0] != -1.0
    np.testing.assert_array_equal(edge, out.edge_pvalues)


def test_masked_edges_get_unit_pvalue():
    """Undefined correlations (constant column after the shift) cannot be
    evidence: their edge p-value must be 1.0, never the resolution floor."""
    rng = np.random.default_rng(15)
    ref = rng.normal(size=(120, 4))
    cur = rng.normal(size=(120, 4))
    cur[:, 3] = 0.0  # constant in the current window -> corr undefined
    out = compute_calibrated_scores(ref, cur, n_permutations=B, seed=0)
    assert out.edge_pvalues[3, 0] == 1.0
    assert out.edge_pvalues[0, 3] == 1.0
    assert 3 not in out.metadata["copula_columns"]


def test_resolution_floor_equals_saturation():
    """1 / (B + 1) is exactly the smallest attainable p-value."""
    rng = np.random.default_rng(16)
    ref = rng.normal(size=(150, 4))
    cur = rng.normal(size=(150, 4))
    cur[:, 0] += 6.0
    out = compute_calibrated_scores(ref, cur, n_permutations=79, alpha=0.05, seed=0)
    assert out.marginal_pvalues[0] == pytest.approx(1.0 / 80.0)
    # -log10(p) plus the <= 1e-3 monotone statistic tie-break.
    assert out.marginal_evidence[0] == pytest.approx(np.log10(80.0), abs=2e-3)


def test_pvalues_are_equivariant_under_column_permutation():
    """Relabelling the features permutes the p-values and leaves them unchanged.

    A reviewer's first question about a permutation statistic is whether the
    answer depends on column order. The adjusted p-values and the evidence must
    not; the peel *order* may, because exact strength ties are broken by index
    (documented on `_peel`), which only reorders indistinguishable features.
    """
    rng = np.random.default_rng(17)
    ref = rng.normal(size=(200, 5))
    cur = rng.normal(size=(200, 5))
    cur[:, 1] = cur[:, 1] * 2.5
    perm = rng.permutation(5)

    plain = compute_calibrated_scores(ref, cur, n_permutations=B, seed=0)
    relabelled = compute_calibrated_scores(
        ref[:, perm], cur[:, perm], n_permutations=B, seed=0
    )

    assert np.allclose(plain.marginal_pvalues[perm], relabelled.marginal_pvalues)
    assert np.allclose(plain.edge_pvalues[np.ix_(perm, perm)], relabelled.edge_pvalues)
    assert np.isclose(plain.combined_scores[perm], relabelled.combined_scores).all()


def test_block_size_must_divide_both_windows():
    """A block-permutation null cannot straddle the split boundary."""
    rng = np.random.default_rng(18)
    ref, cur = rng.normal(size=(120, 4)), rng.normal(size=(120, 4))
    with pytest.raises(ValueError, match="block_size must divide"):
        compute_calibrated_scores(ref, cur, n_permutations=B, seed=0, block_size=7)
    with pytest.raises(ValueError, match="block_size must be >= 1"):
        compute_calibrated_scores(ref, cur, n_permutations=B, seed=0, block_size=0)


def test_block_permutation_is_reproducible_and_recorded():
    rng = np.random.default_rng(19)
    ref, cur = rng.normal(size=(120, 4)), rng.normal(size=(120, 4))
    first = compute_calibrated_scores(ref, cur, n_permutations=B, seed=3, block_size=20)
    again = compute_calibrated_scores(ref, cur, n_permutations=B, seed=3, block_size=20)
    assert first.metadata["permutation_block_size"] == 20
    np.testing.assert_array_equal(first.combined_scores, again.combined_scores)


def test_block_permutation_keeps_runs_that_iid_permutation_breaks():
    """Runs of identical adjacent rows inflate the KS statistic.

    Under block permutation those runs stay on one side of the split, so the
    null of the statistic is wider than the i.i.d. null on the same data. If
    the block path ever degenerated to a row permutation this inequality would
    flip, which is what this test guards.
    """
    from vigil.calibration import _null_maxima, _pooled_order

    n_blocks, block_rows, d = 12, 20, 3
    rng = np.random.default_rng(20)
    level = rng.normal(size=(n_blocks, d))
    data = np.repeat(level, block_rows, axis=0)  # adjacent rows are identical
    n_ref = len(data) // 2
    order, tie_mask = _pooled_order(data)

    iid_ks, _ = _null_maxima(
        data,
        order,
        tie_mask,
        n_ref,
        199,
        None,
        np.random.default_rng(0),
        "normal_scores",
        1,
    )
    block_ks, _ = _null_maxima(
        data,
        order,
        tie_mask,
        n_ref,
        199,
        None,
        np.random.default_rng(0),
        "normal_scores",
        block_rows,
    )
    assert np.quantile(block_ks, 0.95) > np.quantile(iid_ks, 0.95)
