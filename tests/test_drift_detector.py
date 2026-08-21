"""Tests for the DriftDetector module."""
import numpy as np
import pytest
from vigil.core.drift_detector import DriftDetector


def test_no_drift_during_warmup():
    """Drift should not be reported while buffer is filling."""
    detector = DriftDetector(buffer_size=100)
    errors = np.random.randn(50).astype(np.float32) * 0.1 + 0.5
    result = detector.detect(errors)
    assert result.drift_detected is False
    assert result.drift_severity == 0.0


def test_buffer_fills_correctly():
    """Buffer should fill up over multiple batches."""
    detector = DriftDetector(buffer_size=100)
    errors = np.random.randn(60).astype(np.float32)
    detector.detect(errors)
    assert len(detector._buffer) == 60


def test_no_false_drift_on_stable_stream():
    """Stable stream (same distribution) should NOT trigger drift."""
    np.random.seed(42)
    detector = DriftDetector(buffer_size=200, drift_threshold=0.3)

    # Fill buffer
    ref_errors = np.random.normal(0.5, 0.05, 200).astype(np.float32)
    for i in range(0, 200, 50):
        detector.detect(ref_errors[i:i+50])

    # Feed same distribution — should be stable
    for _ in range(5):
        same_dist = np.random.normal(0.5, 0.05, 50).astype(np.float32)
        result = detector.detect(same_dist)
        assert result.drift_detected is False, "Stable stream should not trigger drift"


def test_drift_detected_on_shifted_distribution():
    """A strongly shifted distribution should trigger drift."""
    np.random.seed(42)
    detector = DriftDetector(buffer_size=300, drift_threshold=0.3)

    # Fill buffer with low-error stable data
    stable = np.random.normal(0.1, 0.01, 300).astype(np.float32)
    for i in range(0, 300, 100):
        detector.detect(stable[i:i+100])

    # Inject heavily drifted data (much higher reconstruction error)
    drifted = np.random.normal(5.0, 0.5, 100).astype(np.float32)
    result = detector.detect(drifted)
    assert result.drift_detected is True, "Strongly shifted distribution should trigger drift"


def test_buffer_resets_after_drift():
    """After drift detection, buffer should be reset."""
    np.random.seed(0)
    detector = DriftDetector(buffer_size=200, drift_threshold=0.3)

    stable = np.random.normal(0.1, 0.01, 200).astype(np.float32)
    for i in range(0, 200, 100):
        detector.detect(stable[i:i+100])

    drifted = np.random.normal(10.0, 1.0, 100).astype(np.float32)
    result = detector.detect(drifted)

    if result.drift_detected:
        assert len(detector._buffer) == 100, "Buffer should contain only current batch after reset"
