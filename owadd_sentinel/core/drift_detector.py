"""
Drift Detector Module
=====================
Implements the replicated T-Test based concept drift detection algorithm
from arXiv:2605.29834.

Algorithm (from paper):
1. Maintain a reference buffer B of size 1000 storing reconstruction errors
   from previously validated stable data.
2. For each new incoming batch, compute reconstruction errors L_n using
   autoencoder A.
3. If buffer is not full yet, fill it and skip detection.
4. Once buffer is full, run r=15 replicated one-sided T-tests, each comparing
   a random sample of size N=30 from B against a random sample from L_n.
5. Count how many tests show significant difference (p < alpha=0.05).
6. If that proportion exceeds threshold theta=0.3 → DRIFT DETECTED.
7. On drift: reset buffer B and incrementally retrain autoencoder A.
"""

import numpy as np
from scipy import stats
from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class DriftResult:
    """
    Result returned by the drift detector for each processed batch.

    Attributes
    ----------
    drift_detected : bool
        True if concept drift was detected in this batch.
    drift_severity : float
        Proportion of T-tests that were significant. Range [0.0, 1.0].
        A higher value means more evidence of drift. Threshold is 0.3.
    p_values : list of float
        Raw p-values from all r replicated T-tests.
    buffer_size : int
        Current number of errors stored in the reference buffer.
    batch_error_mean : float
        Mean reconstruction error of the current batch.
    reference_error_mean : float
        Mean reconstruction error of the reference buffer.
    """
    drift_detected: bool
    drift_severity: float
    p_values: list
    buffer_size: int
    batch_error_mean: float
    reference_error_mean: float


class DriftDetector:
    """
    Replicated T-Test drift detector based on autoencoder reconstruction errors.

    This is the core detection mechanism of OWADD (arXiv:2605.29834).

    Instead of comparing raw high-dimensional feature vectors (expensive),
    it compares 1-dimensional reconstruction error scalars. This reduces
    memory complexity from O(n_samples × n_features) to O(buffer_size).

    Parameters
    ----------
    buffer_size : int
        Maximum number of reconstruction errors to store as reference.
        Paper uses 1000. Default: 1000.
    n_replications : int
        Number of T-test replications per batch. Paper uses 15. Default: 15.
    sample_size : int
        Number of samples drawn per T-test replication. Paper uses 30.
        Default: 30.
    drift_threshold : float
        Proportion of significant tests needed to declare drift.
        Paper uses 0.3 (i.e., 30% of tests must be significant). Default: 0.3.
    alpha : float
        Significance level for each individual T-test. Default: 0.05.
    """

    def __init__(
        self,
        buffer_size: int = 1000,
        n_replications: int = 15,
        sample_size: int = 30,
        drift_threshold: float = 0.3,
        alpha: float = 0.05,
    ):
        self.buffer_size = buffer_size
        self.n_replications = n_replications
        self.sample_size = sample_size
        self.drift_threshold = drift_threshold
        self.alpha = alpha

        # Reference buffer: stores reconstruction errors of stable data
        # deque with maxlen automatically evicts oldest entries when full
        self._buffer: deque = deque(maxlen=buffer_size)

        # Tracking
        self.n_drifts_detected: int = 0
        self.chunks_processed: int = 0

    @property
    def buffer_array(self) -> np.ndarray:
        """Return the current buffer as a numpy array."""
        return np.array(self._buffer)

    @property
    def is_buffer_full(self) -> bool:
        """True when buffer has reached its maximum capacity."""
        return len(self._buffer) >= self.buffer_size

    def update_buffer(self, errors: np.ndarray) -> None:
        """
        Add reconstruction errors from a new batch to the reference buffer.

        Called after a drift is detected (buffer is reset) or during
        the warm-up phase before the buffer is full.

        Parameters
        ----------
        errors : np.ndarray, shape (n_samples,)
            Per-sample reconstruction errors from the current batch.
        """
        for error in errors:
            self._buffer.append(float(error))

    def reset_buffer(self) -> None:
        """
        Clear the reference buffer.

        Called after drift is detected so the new post-drift distribution
        becomes the new reference baseline.
        """
        self._buffer.clear()

    def _run_replicated_ttest(
        self, batch_errors: np.ndarray
    ) -> tuple[float, list]:
        """
        Run r replicated one-sided T-tests comparing buffer vs batch errors.

        Each replication:
          1. Draw N random samples from the reference buffer B.
          2. Draw N random samples from the current batch errors L_n.
          3. Run a two-sample T-test.
          4. Record whether p-value < alpha (significant difference).

        Parameters
        ----------
        batch_errors : np.ndarray

        Returns
        -------
        significant_proportion : float
            Proportion of replications that showed significant difference.
            This is the drift severity score.
        p_values : list of float
        """
        buffer_arr = self.buffer_array
        p_values = []

        for _ in range(self.n_replications):
            # Randomly sample from buffer and from current batch
            ref_sample = np.random.choice(
                buffer_arr, size=self.sample_size, replace=True
            )
            batch_sample = np.random.choice(
                batch_errors, size=min(self.sample_size, len(batch_errors)),
                replace=True
            )

            # Two-sample T-test (two-sided: detects any distribution change)
            _, p_val = stats.ttest_ind(ref_sample, batch_sample)
            p_values.append(float(p_val))

        # Proportion of tests where null hypothesis (same distribution) rejected
        n_significant = sum(p < self.alpha for p in p_values)
        significant_proportion = n_significant / self.n_replications

        return significant_proportion, p_values

    def detect(self, batch_errors: np.ndarray) -> DriftResult:
        """
        Process a new batch of reconstruction errors and detect drift.

        Parameters
        ----------
        batch_errors : np.ndarray, shape (n_samples,)
            Per-sample reconstruction errors for the current data chunk.

        Returns
        -------
        DriftResult
            Contains drift_detected flag, drift_severity, and diagnostics.
        """
        self.chunks_processed += 1

        batch_error_mean = float(np.mean(batch_errors))
        reference_mean = float(np.mean(self._buffer)) if self._buffer else 0.0

        # Warm-up phase: fill buffer before running any tests
        if not self.is_buffer_full:
            self.update_buffer(batch_errors)
            return DriftResult(
                drift_detected=False,
                drift_severity=0.0,
                p_values=[],
                buffer_size=len(self._buffer),
                batch_error_mean=batch_error_mean,
                reference_error_mean=reference_mean,
            )

        # Run replicated T-tests
        severity, p_values = self._run_replicated_ttest(batch_errors)

        # Declare drift if severity exceeds threshold
        drift_detected = severity >= self.drift_threshold

        if drift_detected:
            self.n_drifts_detected += 1
            # Reset buffer — new distribution becomes the reference
            self.reset_buffer()
            self.update_buffer(batch_errors)

        return DriftResult(
            drift_detected=drift_detected,
            drift_severity=float(severity),
            p_values=p_values,
            buffer_size=len(self._buffer),
            batch_error_mean=batch_error_mean,
            reference_error_mean=reference_mean,
        )
