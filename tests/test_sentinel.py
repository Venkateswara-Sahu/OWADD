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
        sentinel.detect(stable[i:i+50])

    # Feed heavily drifted data
    result = sentinel.detect(drifted)
    if result.drift_detected:
        assert result.attribution is not None
        assert len(result.attribution.top_features) <= 3
