"""
Novelty Detector Module
========================
Implements KDE-based novel class recognition using the A_KC mirror autoencoder,
as described in arXiv:2605.29834 (Algorithm 2).

Key Insight from the paper:
  Instead of running KDE on the full high-dimensional feature vector (which
  suffers from the curse of dimensionality), OWADD runs KDE on the 1-D
  reconstruction error proxy. This makes density estimation robust and
  memory-efficient.

Algorithm 2 (from paper):
  1. Use A_KC (frozen mirror autoencoder) to compute reconstruction errors E.
  2. Fit a KDE model K on the initial known-class error distribution.
  3. For each sample, get its density score from K.
  4. Samples with density score ABOVE threshold delta → known class (1).
  5. Samples with density score BELOW threshold delta → novel/unknown (0).
  6. If novelty is confirmed externally, update A_KC weights to the new
     known-class distribution.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.neighbors import KernelDensity


@dataclass
class NoveltyResult:
    """
    Result of novelty detection for a single data batch.

    Attributes
    ----------
    labels : np.ndarray of int, shape (n_samples,)
        1 = known class sample, 0 = novel/unknown class sample.
    density_scores : np.ndarray of float, shape (n_samples,)
        Raw KDE density scores. Higher = more familiar to the model.
    novelty_proportion : float
        Fraction of samples classified as novel in this batch.
    n_novel : int
        Absolute count of novel samples in this batch.
    n_known : int
        Absolute count of known samples in this batch.
    """
    labels: np.ndarray
    density_scores: np.ndarray
    novelty_proportion: float
    n_novel: int
    n_known: int


class NoveltyDetector:
    """
    KDE-based novel class detector operating on reconstruction error proxy.

    Uses the A_KC mirror autoencoder (kept frozen from initial training)
    to compute reconstruction errors, then applies KDE density estimation
    to distinguish known-class samples from novel/unknown ones.

    Parameters
    ----------
    novelty_threshold : float
        Density score threshold below which a sample is flagged as novel.
        Paper uses 0.02. Default: 0.02.
    kde_bandwidth : str or float
        Bandwidth for the KDE model. 'scott' uses Scott's rule (automatic).
        Default: 'scott'.
    kde_kernel : str
        Kernel type for KDE. Default: 'gaussian'.
    """

    def __init__(
        self,
        novelty_threshold: float = 0.02,
        kde_bandwidth: str = "scott",
        kde_kernel: str = "gaussian",
    ):
        self.novelty_threshold = novelty_threshold
        self.kde_bandwidth = kde_bandwidth
        self.kde_kernel = kde_kernel

        self._kde: KernelDensity | None = None
        self._is_fitted: bool = False

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    def fit(self, reference_errors: np.ndarray) -> None:
        """
        Fit the KDE model on initial known-class reconstruction errors.

        Called once during the offline phase after A_KC is trained on
        the first data chunk.

        Parameters
        ----------
        reference_errors : np.ndarray, shape (n_samples,)
            Reconstruction errors from A_KC on the initial known-class data.
        """
        # KDE expects 2D input: reshape (n_samples,) → (n_samples, 1)
        errors_2d = reference_errors.reshape(-1, 1)

        self._kde = KernelDensity(
            bandwidth=self.kde_bandwidth,
            kernel=self.kde_kernel,
        )
        self._kde.fit(errors_2d)
        self._is_fitted = True

    def detect(self, errors: np.ndarray) -> NoveltyResult:
        """
        Classify each sample in the current batch as known or novel.

        Parameters
        ----------
        errors : np.ndarray, shape (n_samples,)
            Reconstruction errors from A_KC for the current data batch.

        Returns
        -------
        NoveltyResult

        Raises
        ------
        RuntimeError
            If the detector has not been fitted yet (call .fit() first).
        """
        if not self._is_fitted:
            raise RuntimeError(
                "NoveltyDetector must be fitted before calling detect(). "
                "Call .fit(reference_errors) first."
            )

        errors_2d = errors.reshape(-1, 1)

        # log_density → density (exponentiate to get actual probability density)
        log_density_scores = self._kde.score_samples(errors_2d)
        density_scores = np.exp(log_density_scores)

        # Classify: above threshold = known (1), below = novel (0)
        labels = (density_scores >= self.novelty_threshold).astype(int)

        n_novel = int(np.sum(labels == 0))
        n_known = int(np.sum(labels == 1))
        n_total = len(labels)

        return NoveltyResult(
            labels=labels,
            density_scores=density_scores,
            novelty_proportion=n_novel / n_total if n_total > 0 else 0.0,
            n_novel=n_novel,
            n_known=n_known,
        )

    def update(self, new_reference_errors: np.ndarray) -> None:
        """
        Re-fit the KDE model when a confirmed novel class becomes known.

        Called when novelty is externally confirmed and the novel class
        should be absorbed into the known-class distribution. This mirrors
        the A_KC weight update described in the paper.

        Parameters
        ----------
        new_reference_errors : np.ndarray, shape (n_samples,)
            Reconstruction errors from A_KC on the updated known-class data.
        """
        self.fit(new_reference_errors)
