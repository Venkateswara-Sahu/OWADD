"""Tests for the end-to-end Vigil."""

import numpy as np
import pytest

from vigil import Vigil


def make_stable_stream(n_samples=1000, n_features=10, seed=42):
    np.random.seed(seed)
    return np.random.normal(0.0, 1.0, (n_samples, n_features)).astype(np.float32)


def make_drifted_batch(n_samples=200, n_features=10, seed=99):
    np.random.seed(seed)
    return np.random.normal(10.0, 0.5, (n_samples, n_features)).astype(np.float32)


def test_sentinel_fit_and_detect():
    """Sentinel should fit without errors and return SentinelResult."""
    data = make_stable_stream()
    sentinel = Vigil(n_features=10)
    sentinel.fit(data[:200], verbose=False)

    result = sentinel.detect(data[200:400])
    assert hasattr(result, "drift_detected")
    assert hasattr(result, "drift_severity")
    assert hasattr(result, "novelty_proportion")


def test_sentinel_raises_without_fit():
    """detect() before fit() must raise RuntimeError."""
    sentinel = Vigil(n_features=10)
    with pytest.raises(RuntimeError):
        sentinel.detect(np.random.randn(100, 10).astype(np.float32))


def test_sentinel_result_to_dict():
    """to_dict() should return a flat dictionary."""
    data = make_stable_stream()
    sentinel = Vigil(n_features=10)
    sentinel.fit(data[:200], verbose=False)
    result = sentinel.detect(data[200:400])
    d = result.to_dict()
    assert isinstance(d, dict)
    assert "drift_detected" in d
    assert "drift_severity" in d


def test_sentinel_attribution_on_drift():
    """Attribution should be computed when drift is detected."""
    stable = make_stable_stream(n_samples=200, n_features=10)
    drifted = make_drifted_batch(n_samples=200, n_features=10)

    sentinel = Vigil(
        n_features=10,
        buffer_size=200,
        drift_threshold=0.3,
        top_k_features=3,
    )
    sentinel.fit(stable, verbose=False)

    # Force buffer to fill
    for i in range(0, 200, 50):
        sentinel.detect(stable[i : i + 50])

    # Feed heavily drifted data
    result = sentinel.detect(drifted)
    if result.drift_detected:
        assert result.attribution is not None
        assert len(result.attribution.top_features) <= 3
        assert result.attribution.metadata["no_positive_delta"] is False
        assert result.attribution.feature_contributions.sum() == pytest.approx(1.0)


def test_decomposed_attribution_marginal_and_relational():
    """Decomposed attribution localizes small marginal and pure correlation shifts."""
    rng = np.random.default_rng(123)
    ref = rng.normal(0.0, 1.0, (400, 10)).astype(np.float32)

    # 1. Small marginal shift on features (2, 7)
    cur_marg = ref.copy()
    cur_marg[:, [2, 7]] += 0.6

    sentinel = Vigil(
        n_features=10,
        buffer_size=400,
        drift_threshold=0.1,
        top_k_features=2,
        attribution_mode="decomposed",
        adaptation_mode="verified_only",
        feature_groups={"group_a": (0, 1, 2), "group_b": (7, 8, 9)},
        seed=42,
    )
    sentinel.fit(ref, verbose=False)
    res_marg = sentinel._attributor.attribute(
        sentinel._autoencoder_A, ref, cur_marg, mode="decomposed"
    )
    top2_marg = {f["feature_index"] for f in res_marg.top_features[:2]}
    assert top2_marg == {2, 7}
    assert res_marg.metadata["dominant_drift_regime"] == "marginal"
    assert "grouped_top_features" in res_marg.metadata

    # 2. Pure relational shift: permutation / strong correlation on columns
    #    (3, 5) with N(0, 1) marginals.
    cur_rel = rng.normal(0.0, 1.0, (400, 10)).astype(np.float32)
    z = rng.normal(0.0, 1.0, 400).astype(np.float32)
    cur_rel[:, 3] = 0.85 * z + np.sqrt(1 - 0.85**2) * cur_rel[:, 3]
    cur_rel[:, 5] = 0.85 * z + np.sqrt(1 - 0.85**2) * cur_rel[:, 5]

    res_rel = sentinel._attributor.attribute(
        sentinel._autoencoder_A, ref, cur_rel, mode="decomposed"
    )
    top2_rel = {f["feature_index"] for f in res_rel.top_features[:2]}
    assert top2_rel == {3, 5}
    assert res_rel.metadata["dominant_drift_regime"] == "relational"


def test_post_drift_detector_does_not_go_blind():
    """After auto-mode drift, later drifted chunks are not skipped by warmup."""
    stable = make_stable_stream(n_samples=600, n_features=10, seed=42)
    drifted_1 = make_drifted_batch(n_samples=200, n_features=10, seed=99)
    drifted_2 = (
        np.random.default_rng(101).normal(-10.0, 0.5, (200, 10)).astype(np.float32)
    )

    sentinel = Vigil(
        n_features=10,
        buffer_size=600,
        drift_threshold=0.3,
        initial_epochs=20,
        update_epochs=5,
        seed=42,
    )
    sentinel.fit(stable, verbose=False)
    r1 = sentinel.detect(drifted_1)
    assert r1.drift_detected is True
    # Immediately next chunk has a completely different shift (-10 vs +10);
    # previously, buffer_size=600 > 200 caused 2 chunks of warmup blindness!
    r2 = sentinel.detect(drifted_2)
    assert len(r2.drift_result.p_values) == 15
    assert r2.drift_detected is True


def test_verified_only_warmup_does_not_double_insert_buffer():
    """With initial_data < buffer_size, warmup batches are appended once."""
    init = make_stable_stream(n_samples=100, n_features=8, seed=1)
    chunk2 = make_stable_stream(n_samples=100, n_features=8, seed=2)
    sentinel = Vigil(
        n_features=8,
        buffer_size=300,
        initial_epochs=10,
        adaptation_mode="verified_only",
        seed=42,
    )
    sentinel.fit(init, verbose=False)
    assert len(sentinel._drift_detector._buffer) == 100
    sentinel.detect(chunk2)
    # Should be 200 (100 from fit + 100 from chunk2 warmup), NOT 300 from double-append
    assert len(sentinel._drift_detector._buffer) == 200


def test_vigil_fit_is_deterministic_when_seed_provided():
    """Same seed must give identical trained autoencoder weights."""
    data = make_stable_stream(n_samples=120, n_features=6, seed=7)
    v1 = Vigil(n_features=6, initial_epochs=15, seed=123).fit(data, verbose=False)
    v2 = Vigil(n_features=6, initial_epochs=15, seed=123).fit(data, verbose=False)
    weights_a, weights_b = v1._autoencoder_A, v2._autoencoder_A
    assert weights_a is not None and weights_b is not None
    for p1, p2 in zip(weights_a.parameters(), weights_b.parameters(), strict=True):
        assert np.allclose(p1.detach().numpy(), p2.detach().numpy())


def test_decomposed_attributor_works_without_model():
    """Decomposed Copula-KS attribution should work with model=None."""
    from vigil.attribution import DriftAttributor

    rng = np.random.default_rng(99)
    ref = rng.normal(0.0, 1.0, (200, 6))
    cur = ref.copy()
    cur[:, 4] += 1.5
    attr = DriftAttributor(top_k=1, mode="decomposed").attribute(
        model=None, reference_data=ref, current_batch=cur
    )
    assert attr.top_features[0]["feature_index"] == 4
    assert attr.top_features[0]["drift_type"] == "marginal"


def test_detect_rejects_non_finite_batch():
    """A NaN/inf batch must fail loudly at the boundary, not silently propagate."""
    stream = make_stable_stream()
    vigil = Vigil(n_features=10, initial_epochs=3, seed=7)
    vigil.fit(stream[:600], verbose=False)

    bad = make_stable_stream(n_samples=50, n_features=10)
    bad[3, 2] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        vigil.detect(bad)


def test_detect_rejects_wrong_feature_count():
    """Feature-count mismatch is a ValueError naming both counts."""
    stream = make_stable_stream()
    vigil = Vigil(n_features=10, initial_epochs=3, seed=7)
    vigil.fit(stream[:600], verbose=False)

    with pytest.raises(ValueError, match="expected 10"):
        vigil.detect(np.zeros((20, 4), dtype=np.float32))


def test_vigil_forwards_calibrated_params_and_seed_to_attributor():
    """Calibrated attribution parameters and seed must propagate from Vigil."""
    rng = np.random.default_rng(314)
    ref = rng.normal(0.0, 1.0, (200, 6)).astype(np.float32)
    cur = ref.copy()
    cur[:, 2] += 1.5

    v1 = Vigil(
        n_features=6,
        initial_epochs=3,
        attribution_mode="calibrated",
        n_permutations=99,
        block_size=10,
        seed=77,
    ).fit(ref, verbose=False)
    v2 = Vigil(
        n_features=6,
        initial_epochs=3,
        attribution_mode="calibrated",
        n_permutations=99,
        block_size=10,
        seed=77,
    ).fit(ref, verbose=False)

    assert v1._attributor.n_permutations == 99
    assert v1._attributor.block_size == 10
    assert v1._attributor.seed == 77
    r1 = v1._attributor.attribute(None, ref, cur)
    r2 = v2._attributor.attribute(None, ref, cur)
    assert r1.top_features[0]["feature_index"] == 2
    assert r1.metadata["block_size"] == 10
    np.testing.assert_array_equal(
        r1.feature_contributions, r2.feature_contributions
    )
