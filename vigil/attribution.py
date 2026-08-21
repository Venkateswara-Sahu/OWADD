"""
Feature Attribution Module (Original Contribution)
===================================================
This module extends arXiv:2605.29834 with feature-level drift attribution.

The original OWADD paper only answers: "Did drift happen?" (yes/no).
This module answers: "WHICH features caused the drift and by how much?"

Approach: Gradient-based feature attribution on the autoencoder.
  For each feature, we compute how much it contributed to the increase in
  reconstruction error between the reference distribution and the current batch.

  Method:
    1. Compute per-feature reconstruction error: (x_i - x̂_i)² for each feature.
    2. Compare per-feature error means between reference buffer and current batch.
    3. Normalize contributions to get a proportion (sums to 1.0).
    4. Rank features by their drift contribution.

This is the key NOVEL CONTRIBUTION of OWADD Sentinel over the base paper.
It makes drift detection ACTIONABLE — engineers know exactly where to look.
"""

from dataclasses import dataclass

import numpy as np
import torch


@dataclass
class AttributionResult:
    """
    Feature-level drift attribution result.

    Attributes
    ----------
    feature_contributions : np.ndarray, shape (n_features,)
        Normalized drift contribution per feature. Sums to 1.0.
    feature_error_delta : np.ndarray, shape (n_features,)
        Absolute increase in per-feature reconstruction error
        (current batch mean - reference buffer mean).
    top_features : list of dict
        Top drifting features ranked by contribution, each dict has:
        - 'feature_index': int
        - 'feature_name': str (if column names provided, else 'feature_N')
        - 'contribution': float (0.0 to 1.0)
        - 'error_delta': float
    feature_names : list of str
    """
    feature_contributions: np.ndarray
    feature_error_delta: np.ndarray
    top_features: list
    feature_names: list


class DriftAttributor:
    """
    Computes feature-level attribution for detected concept drift.

    This is the original contribution of OWADD Sentinel beyond arXiv:2605.29834.
    It pinpoints which features are responsible for triggering drift detection,
    making drift alerts actionable for data engineers and ML teams.

    Parameters
    ----------
    top_k : int
        Number of top contributing features to return. Default: 5.
    feature_names : list of str, optional
        Column names of the input features. If not provided, features
        will be named 'feature_0', 'feature_1', etc.

    Example
    -------
        attributor = DriftAttributor(top_k=5, feature_names=df.columns.tolist())
        result = attributor.attribute(model, reference_data, current_batch)
        print(result.top_features)
        # [{'feature_name': 'packet_length', 'contribution': 0.41, ...}, ...]
    """

    def __init__(
        self,
        top_k: int = 5,
        feature_names: list | None = None,
    ):
        self.top_k = top_k
        self.feature_names = feature_names

    def _get_per_feature_errors(
        self, model, data: np.ndarray
    ) -> np.ndarray:
        """
        Compute mean per-feature reconstruction error across all samples.

        Parameters
        ----------
        model : Autoencoder
        data : np.ndarray, shape (n_samples, n_features)

        Returns
        -------
        per_feature_errors : np.ndarray, shape (n_features,)
            Mean squared error per feature, averaged over all samples.
        """
        model.eval()
        X = torch.tensor(data, dtype=torch.float32)
        with torch.no_grad():
            reconstructed = model(X)
            # Per-feature MSE: mean over samples, separate for each feature
            per_feature_errors = torch.mean(
                (X - reconstructed) ** 2, dim=0
            ).cpu().numpy()
        return per_feature_errors

    def attribute(
        self,
        model,
        reference_data: np.ndarray,
        current_batch: np.ndarray,
        feature_names: list | None = None,
    ) -> AttributionResult:
        """
        Compute drift attribution by comparing per-feature errors.

        Compares how each feature's reconstruction error has changed
        between the stable reference data and the current (possibly drifted)
        batch. Features with the largest increase in reconstruction error
        are the primary drivers of the detected drift.

        Parameters
        ----------
        model : Autoencoder
            The primary autoencoder A (used for drift detection).
        reference_data : np.ndarray, shape (n_ref_samples, n_features)
            A sample of data from the stable reference period.
        current_batch : np.ndarray, shape (n_batch_samples, n_features)
            The current incoming data batch where drift was detected.
        feature_names : list of str, optional
            Override instance-level feature names.

        Returns
        -------
        AttributionResult
        """
        names = feature_names or self.feature_names
        n_features = current_batch.shape[1]

        if names is None:
            names = [f"feature_{i}" for i in range(n_features)]

        # Per-feature reconstruction error for reference vs current
        ref_errors = self._get_per_feature_errors(model, reference_data)
        cur_errors = self._get_per_feature_errors(model, current_batch)

        # Delta: how much did each feature's error increase?
        error_delta = cur_errors - ref_errors

        # Only consider features where error INCREASED (positive delta)
        # Negative delta means that feature got easier to reconstruct → not drifted
        positive_delta = np.maximum(error_delta, 0.0)

        # Normalize to get proportional contribution (sums to 1.0)
        total = positive_delta.sum()
        if total > 0:
            contributions = positive_delta / total
        else:
            # All errors decreased or stayed the same — uniform attribution
            contributions = np.ones(n_features) / n_features

        # Build ranked list of top-k features
        top_indices = np.argsort(contributions)[::-1][: self.top_k]
        top_features = [
            {
                "feature_index": int(idx),
                "feature_name": names[idx] if idx < len(names) else f"feature_{idx}",
                "contribution": float(contributions[idx]),
                "error_delta": float(error_delta[idx]),
            }
            for idx in top_indices
        ]

        return AttributionResult(
            feature_contributions=contributions,
            feature_error_delta=error_delta,
            top_features=top_features,
            feature_names=names,
        )
