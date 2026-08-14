"""
OWADDSentinel — Main Public API
================================
The top-level class that ties together all components:
  - Dual mirrored autoencoders (A and A_KC)
  - Replicated T-Test drift detector
  - KDE-based novelty detector
  - Feature attribution (original contribution)

This is the only class users need to import for basic usage:

    from owadd_sentinel import OWADDSentinel

    sentinel = OWADDSentinel(n_features=50)
    sentinel.fit(initial_data)

    result = sentinel.detect(new_batch)
    print(result)
"""

from dataclasses import dataclass

import numpy as np
import torch

from owadd_sentinel.attribution import AttributionResult, DriftAttributor
from owadd_sentinel.core.autoencoder import (
    Autoencoder,
    create_autoencoder_pair,
    train_autoencoder,
)
from owadd_sentinel.core.drift_detector import DriftDetector, DriftResult
from owadd_sentinel.core.novelty_detector import NoveltyDetector, NoveltyResult


@dataclass
class SentinelResult:
    """
    Complete result from OWADDSentinel.detect() for a single data batch.

    Attributes
    ----------
    chunk_id : int
        Sequential batch/chunk number.
    drift_detected : bool
        True if concept drift was detected.
    drift_severity : float
        Proportion of T-tests showing significant difference [0.0, 1.0].
    novelty_proportion : float
        Fraction of samples classified as novel/unknown in this batch.
    n_novel : int
        Number of novel samples detected.
    attribution : AttributionResult or None
        Feature-level drift attribution. Only computed when drift_detected=True.
    drift_result : DriftResult
        Full drift detection diagnostics.
    novelty_result : NoveltyResult
        Full novelty detection results.
    """
    chunk_id: int
    drift_detected: bool
    drift_severity: float
    novelty_proportion: float
    n_novel: int
    attribution: AttributionResult | None
    drift_result: DriftResult
    novelty_result: NoveltyResult

    def __repr__(self):
        status = "⚠️  DRIFT" if self.drift_detected else "✅ STABLE"
        return (
            f"SentinelResult(chunk={self.chunk_id}, "
            f"status={status}, "
            f"severity={self.drift_severity:.2f}, "
            f"novelty={self.novelty_proportion:.1%})"
        )

    def to_dict(self) -> dict:
        """Serialize result to a flat dictionary (for MLflow logging, APIs)."""
        d = {
            "chunk_id": self.chunk_id,
            "drift_detected": self.drift_detected,
            "drift_severity": self.drift_severity,
            "novelty_proportion": self.novelty_proportion,
            "n_novel": self.n_novel,
            "batch_error_mean": self.drift_result.batch_error_mean,
            "reference_error_mean": self.drift_result.reference_error_mean,
        }
        if self.attribution:
            for i, feat in enumerate(self.attribution.top_features):
                d[f"top_feature_{i+1}"] = feat["feature_name"]
                d[f"top_feature_{i+1}_contribution"] = feat["contribution"]
        return d


class OWADDSentinel:
    """
    Open World Autoencoding Drift Detector — Production API.

    Detects concept drift and novel class emergence in tabular data streams
    without requiring any labels. Extends arXiv:2605.29834 with feature-level
    drift attribution.

    Parameters
    ----------
    n_features : int, optional
        Number of input features. Auto-detected from data if not provided.
    hidden_dim : int
        Neurons per hidden layer in the autoencoders. Default: 10.
    buffer_size : int
        Reference buffer size for drift detection. Default: 1000.
    n_replications : int
        T-test replications per batch. Default: 15.
    sample_size : int
        Samples per T-test replication. Default: 30.
    drift_threshold : float
        Drift severity threshold [0, 1]. Default: 0.3.
    novelty_threshold : float
        KDE density threshold for novel class classification. Default: 0.02.
    top_k_features : int
        Number of top drifting features to report in attribution. Default: 5.
    feature_names : list of str, optional
        Column names of input features for readable attribution reports.
    initial_epochs : int
        Training epochs for initial offline phase. Default: 400.
    update_epochs : int
        Training epochs for incremental update after drift. Default: 50.

    Example
    -------
        import pandas as pd
        from owadd_sentinel import OWADDSentinel

        df = pd.read_csv("nsl_kdd_stream.csv")
        feature_cols = [c for c in df.columns if c != "label"]

        sentinel = OWADDSentinel(
            feature_names=feature_cols,
            top_k_features=5,
        )

        # Phase 1: offline training on first chunk
        sentinel.fit(df[feature_cols].iloc[:200].values)

        # Phase 2: process stream chunk by chunk
        chunk_size = 200
        for start in range(200, len(df), chunk_size):
            chunk = df[feature_cols].iloc[start:start+chunk_size].values
            result = sentinel.detect(chunk)
            print(result)
            if result.drift_detected:
                print("Top drifted features:", result.attribution.top_features)
    """

    def __init__(
        self,
        n_features: int | None = None,
        hidden_dim: int = 10,
        buffer_size: int = 1000,
        n_replications: int = 15,
        sample_size: int = 30,
        drift_threshold: float = 0.3,
        novelty_threshold: float = 0.02,
        top_k_features: int = 5,
        feature_names: list | None = None,
        initial_epochs: int = 400,
        update_epochs: int = 50,
    ):
        self.n_features = n_features
        self.hidden_dim = hidden_dim
        self.initial_epochs = initial_epochs
        self.update_epochs = update_epochs
        self.feature_names = feature_names

        # Will be initialized in .fit()
        self._autoencoder_A: Autoencoder | None = None
        self._autoencoder_AKC: Autoencoder | None = None
        self._reference_data: np.ndarray | None = None

        # Sub-components
        self._drift_detector = DriftDetector(
            buffer_size=buffer_size,
            n_replications=n_replications,
            sample_size=sample_size,
            drift_threshold=drift_threshold,
        )
        self._novelty_detector = NoveltyDetector(
            novelty_threshold=novelty_threshold,
        )
        self._attributor = DriftAttributor(
            top_k=top_k_features,
            feature_names=feature_names,
        )

        self._is_fitted: bool = False
        self._chunk_counter: int = 0

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def n_drifts_detected(self) -> int:
        return self._drift_detector.n_drifts_detected

    def fit(self, initial_data: np.ndarray, verbose: bool = True) -> "OWADDSentinel":
        """
        Offline training phase on the first data chunk.

        Trains both autoencoders (A and A_KC) on the initial data,
        then fits the KDE novelty detector on A_KC's reconstruction errors.

        Parameters
        ----------
        initial_data : np.ndarray, shape (n_samples, n_features)
            First chunk of the data stream. Paper uses chunks of 200 samples.
        verbose : bool
            Print training progress. Default: True.

        Returns
        -------
        self : OWADDSentinel (for method chaining)
        """
        if self.n_features is None:
            self.n_features = initial_data.shape[1]

        if verbose:
            print(f"[OWADD Sentinel] Fitting on {len(initial_data)} samples, "
                  f"{self.n_features} features...")

        # Create dual mirrored autoencoders
        self._autoencoder_A, self._autoencoder_AKC = create_autoencoder_pair(
            n_features=self.n_features,
            hidden_dim=self.hidden_dim,
        )

        # Train both on initial data (they start identical)
        if verbose:
            print(f"[OWADD Sentinel] Training autoencoders ({self.initial_epochs} epochs)...")
        train_autoencoder(
            self._autoencoder_A, initial_data,
            epochs=self.initial_epochs, verbose=verbose
        )
        # Mirror A_KC: copy weights from A after training
        self._autoencoder_AKC.load_state_dict(self._autoencoder_A.state_dict())

        # Fill drift detector buffer with initial reconstruction errors
        X = torch.tensor(initial_data, dtype=torch.float32)
        init_errors_A = self._autoencoder_A.reconstruction_errors(X)
        self._drift_detector.update_buffer(init_errors_A)

        # Fit KDE novelty detector on A_KC's initial errors
        init_errors_AKC = self._autoencoder_AKC.reconstruction_errors(X)
        self._novelty_detector.fit(init_errors_AKC)

        # Store reference data for attribution comparison
        self._reference_data = initial_data.copy()

        self._is_fitted = True
        self._chunk_counter = 1

        if verbose:
            print("[OWADD Sentinel] ✅ Fitted and ready for stream processing.")

        return self

    def detect(self, batch: np.ndarray) -> SentinelResult:
        """
        Process a new data batch and return drift + novelty + attribution results.

        Parameters
        ----------
        batch : np.ndarray, shape (n_samples, n_features)
            Incoming data chunk from the stream.

        Returns
        -------
        SentinelResult

        Raises
        ------
        RuntimeError
            If .fit() has not been called yet.
        """
        if not self._is_fitted:
            raise RuntimeError(
                "OWADDSentinel must be fitted before calling detect(). "
                "Call .fit(initial_data) first."
            )

        self._chunk_counter += 1
        X = torch.tensor(batch, dtype=torch.float32)

        # Step 1: Compute reconstruction errors using A (drift detection model)
        errors_A = self._autoencoder_A.reconstruction_errors(X)

        # Step 2: Detect drift via replicated T-test on errors_A
        drift_result = self._drift_detector.detect(errors_A)

        # Step 3: Compute reconstruction errors using A_KC (novelty model, frozen)
        errors_AKC = self._autoencoder_AKC.reconstruction_errors(X)

        # Step 4: Detect novel classes via KDE on errors_AKC
        novelty_result = self._novelty_detector.detect(errors_AKC)

        # Step 5: If drift detected → incrementally update A + compute attribution
        attribution = None
        if drift_result.drift_detected:
            # Compute feature attribution BEFORE updating the model
            if self._reference_data is not None:
                attribution = self._attributor.attribute(
                    model=self._autoencoder_A,
                    reference_data=self._reference_data,
                    current_batch=batch,
                    feature_names=self.feature_names,
                )

            # Incrementally update A to adapt to new distribution
            train_autoencoder(
                self._autoencoder_A, batch,
                epochs=self.update_epochs, verbose=False
            )

            # Update reference data for next attribution comparison
            self._reference_data = batch.copy()

        return SentinelResult(
            chunk_id=self._chunk_counter,
            drift_detected=drift_result.drift_detected,
            drift_severity=drift_result.drift_severity,
            novelty_proportion=novelty_result.novelty_proportion,
            n_novel=novelty_result.n_novel,
            attribution=attribution,
            drift_result=drift_result,
            novelty_result=novelty_result,
        )
