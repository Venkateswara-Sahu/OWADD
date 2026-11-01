"""
Feature Reconstruction-Error Attribution
===================================================
This module extends arXiv:2605.29834 with feature-level drift attribution.

The original OWADD paper only answers: "Did drift happen?" (yes/no).
This module answers: "WHICH features show increased reconstruction error?"

Approach: Differences in mean per-feature squared reconstruction error.
  For each feature, we compute how much it contributed to the increase in
  reconstruction error between the reference distribution and the current batch.

  Method:
    1. Compute per-feature reconstruction error: (x_i - x̂_i)² for each feature.
    2. Compare per-feature error means between reference buffer and current batch.
    3. Normalize contributions to get a proportion (sums to 1.0).
    4. Rank features by their drift contribution.

These scores are heuristic rankings, not causal explanations or attack labels.
Evaluation did not establish consistent superiority over simple baselines;
see docs/research-status.md.
"""

import warnings
from dataclasses import dataclass, field

import numpy as np
import torch
from scipy import stats

REFERENCE_SD_FLOOR = 1e-12
ARRAY_2D_NDIM = 2
MIN_KS_SAMPLES = 2
MIN_COPULA_SAMPLES = 4
MIN_COPULA_FEATURES = 2


@dataclass
class AttributionResult:
    """
    Feature-level drift attribution result.

    Attributes
    ----------
    feature_contributions : np.ndarray, shape (n_features,)
        Normalized drift contribution per feature. Sums to 1.0 (or 0.0 when empty).
    feature_error_delta : np.ndarray, shape (n_features,)
        Signed change in per-feature reconstruction error
        (current batch mean - reference buffer mean).
    top_features : list of dict
        Top drifting features ranked by contribution, each dict has:
        - 'feature_index': int
        - 'feature_name': str (if column names provided, else 'feature_N')
        - 'contribution': float (0.0 to 1.0)
        - 'error_delta': float
        - 'drift_type': str ('marginal', 'relational', 'none', or 'reconstruction')
    feature_names : list of str
    metadata : dict
        Diagnostic evidence including marginal and relational scores when
        decomposed or calibrated attribution is enabled.
    """

    feature_contributions: np.ndarray
    feature_error_delta: np.ndarray
    top_features: list
    feature_names: list
    metadata: dict[str, object] = field(default_factory=dict)


def compute_decomposed_scores(
    reference_data: np.ndarray,
    current_batch: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute Marginal (KS) and Relational (Gaussian-Copula / van der Waerden
    rank correlation) attribution scores under asymptotic Bonferroni scaling.

    Why this works where autoencoder MSE deltas fail:
      1. Marginal pathway: exact two-sample Kolmogorov-Smirnov test per feature,
         converted to family-wise Bonferroni log-evidence ``-log10(d * p_KS)``.
         Captures univariate mean, variance, and tail shifts without autoencoder
         bottleneck pass-through or cross-feature error smearing.
      2. Relational pathway: transforms each feature within each window to
         empirical normal scores ``Phi^{-1}(rank / (N + 1))`` (Gaussian copula)
         before computing Fisher-z correlation changes across all ``d*(d-1)/2``
         feature pairs, scaled by the bivariate-normal variance approximation
         ``1/(n_ref - 3) + 1/(n_cur - 3)``. While rank-normal scores strip out
         monotonic marginal changes and outlier magnitude, non-Gaussian joint
         tail dependence and heavy ties inflate asymptotic Fisher-z false-alarm
         rates; use ``compute_calibrated_scores`` (``mode="calibrated"``) for
         permutation-calibrated family-wise error control on exchangeable rows.

    Parameters
    ----------
    reference_data : np.ndarray, shape (n_ref, d)
    current_batch : np.ndarray, shape (n_cur, d)

    Returns
    -------
    marginal_evidence : np.ndarray, shape (d,)
        ``-log10(d * p_KS)`` per feature (non-negative).
    relational_evidence : np.ndarray, shape (d,)
        ``-log10(n_pairs * p_Copula)`` per feature (non-negative).
    combined_scores : np.ndarray, shape (d,)
        ``np.maximum(marginal_evidence, relational_evidence)``.
    """
    ref = np.asarray(reference_data, dtype=float)
    cur = np.asarray(current_batch, dtype=float)
    if (
        ref.ndim != ARRAY_2D_NDIM
        or cur.ndim != ARRAY_2D_NDIM
        or ref.shape[1] != cur.shape[1]
    ):
        raise ValueError("reference_data and current_batch must be aligned 2D arrays")
    n_ref, d = ref.shape
    n_cur = cur.shape[0]
    if n_ref < MIN_KS_SAMPLES or n_cur < MIN_KS_SAMPLES or d < 1:
        return np.zeros(d), np.zeros(d), np.zeros(d)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        ks_results = [stats.ks_2samp(ref[:, j], cur[:, j]) for j in range(d)]
    ks_pvals = np.array([result.pvalue for result in ks_results], dtype=float)
    ks_stats = np.array([result.statistic for result in ks_results], dtype=float)
    # p-values are clipped at 1e-300, so every very strong shift would tie at
    # evidence 300 and rank arbitrarily. Add a tiny monotone KS-statistic
    # tie-break: it cannot reorder anything except saturated features.
    marginal_evidence = np.maximum(
        -np.log10(np.clip(ks_pvals * max(d, 1), 1e-300, 1.0)),
        0.0,
    ) + 1e-3 * ks_stats

    relational_evidence = np.zeros(d, dtype=float)
    if (
        d >= MIN_COPULA_FEATURES
        and n_ref >= MIN_COPULA_SAMPLES
        and n_cur >= MIN_COPULA_SAMPLES
    ):
        ranks_ref = stats.rankdata(ref, axis=0)
        ranks_cur = stats.rankdata(cur, axis=0)
        ref_std = ranks_ref.std(axis=0)
        cur_std = ranks_cur.std(axis=0)
        valid = (ref_std > REFERENCE_SD_FLOOR) & (cur_std > REFERENCE_SD_FLOOR)
        if np.sum(valid) >= MIN_COPULA_FEATURES:
            v_idx = np.flatnonzero(valid)
            g_ref = stats.norm.ppf(ranks_ref[:, v_idx] / (n_ref + 1.0))
            g_cur = stats.norm.ppf(ranks_cur[:, v_idx] / (n_cur + 1.0))
            c_ref = np.corrcoef(g_ref, rowvar=False)
            c_cur = np.corrcoef(g_cur, rowvar=False)
            np.fill_diagonal(c_ref, 0.0)
            np.fill_diagonal(c_cur, 0.0)

            z_ref = np.arctanh(np.clip(c_ref, -0.999999, 0.999999))
            z_cur = np.arctanh(np.clip(c_cur, -0.999999, 0.999999))
            se = np.sqrt(1.0 / (n_ref - 3.0) + 1.0 / (n_cur - 3.0))
            z_diff = np.abs(z_cur - z_ref) / se
            np.fill_diagonal(z_diff, 0.0)

            max_z = z_diff.max(axis=1)
            rms_z = np.sqrt(np.mean(z_diff**2, axis=1))
            n_pairs = max(d * (d - 1) / 2.0, 1.0)
            p_rel = np.clip(2.0 * stats.norm.sf(max_z) * n_pairs, 1e-300, 1.0)
            rel_valid = np.maximum(-np.log10(p_rel), 0.0) + 1e-3 * rms_z
            relational_evidence[v_idx] = rel_valid

    combined_scores = np.maximum(marginal_evidence, relational_evidence)
    return marginal_evidence, relational_evidence, combined_scores


class DriftAttributor:
    """
    Computes feature-level attribution for detected concept drift.

    Supports reconstruction-error rankings (``mode='positive_delta'``,
    ``'absolute_delta'``, ``'standardized_delta'``), fast asymptotic
    Decomposed Copula-KS attribution (``mode='decomposed'``), and
    permutation-calibrated edge-peeling attribution (``mode='calibrated'``).

    Parameters
    ----------
    top_k : int
        Number of top contributing features to return. Default: 5.
    feature_names : list of str, optional
        Column names of the input features. If not provided, features
        will be named 'feature_0', 'feature_1', etc.
    mode : str
        Attribution scoring rule:
        - ``'positive_delta'`` (default for backward compatibility): positive
          increase in per-feature autoencoder reconstruction MSE.
        - ``'absolute_delta'``: two-sided absolute change in per-feature MSE.
        - ``'standardized_delta'``: absolute MSE change standardized by
          reference per-feature squared-error standard deviation.
        - ``'decomposed'``: fast asymptotic Marginal (KS) + Relational
          (Gaussian-Copula Fisher-z) attribution.
        - ``'calibrated'``: pooled-window Westfall-Young max-statistic
          permutation calibration with alpha/2 family split and greedy edge
          peeling.
    feature_groups : dict[str, tuple[int, ...]] or None
        Optional mapping from logical parent feature names (e.g. ``'service'``)
        to one-hot column indices for grouped reporting in
        ``metadata['grouped_top_features']``.
    n_permutations : int
        Permutation budget when ``mode='calibrated'``. Default: 200.
    alpha : float
        Joint family-wise significance level when ``mode='calibrated'``.
        Default: 0.05.
    block_size : int
        Contiguous row block size for block-permutation calibration when
        ``mode='calibrated'``. Default: 1 (i.i.d. row permutation).
    seed : int or None
        RNG seed for permutation calibration. Default: 0.
    """

    VALID_MODES = (
        "positive_delta",
        "absolute_delta",
        "standardized_delta",
        "decomposed",
        "calibrated",
    )
    MODEL_FREE_MODES = ("decomposed", "calibrated")

    def __init__(
        self,
        top_k: int = 5,
        feature_names: list | None = None,
        mode: str = "positive_delta",
        feature_groups: dict[str, tuple[int, ...]] | None = None,
        n_permutations: int = 200,
        alpha: float = 0.05,
        block_size: int = 1,
        seed: int | None = 0,
    ):
        if mode not in self.VALID_MODES:
            raise ValueError(f"mode must be one of {self.VALID_MODES}")
        self.top_k = top_k
        self.feature_names = feature_names
        self.mode = mode
        self.feature_groups = feature_groups
        self.n_permutations = n_permutations
        self.alpha = alpha
        self.block_size = block_size
        self.seed = seed

    def _get_per_feature_errors(
        self, model, data: np.ndarray
    ) -> np.ndarray:
        """
        Compute mean per-feature reconstruction error across all samples.
        """
        model.eval()
        X = torch.tensor(data, dtype=torch.float32)
        with torch.no_grad():
            reconstructed = model(X)
            per_feature_errors = torch.mean(
                (X - reconstructed) ** 2, dim=0
            ).cpu().numpy()
        return per_feature_errors

    def _get_per_sample_feature_errors(
        self, model, data: np.ndarray
    ) -> np.ndarray:
        """Compute per-sample, per-feature squared errors (n_samples, n_features)."""
        model.eval()
        X = torch.as_tensor(data, dtype=torch.float32)
        with torch.no_grad():
            reconstructed = model(X)
            return ((X - reconstructed) ** 2).cpu().numpy()

    def _group_contributions(
        self,
        contributions: np.ndarray,
        error_delta: np.ndarray,
        n_features: int,
    ) -> list[dict[str, object]]:
        if not self.feature_groups:
            return []
        grouped = []
        for group_name, indices in self.feature_groups.items():
            valid_idx = [i for i in indices if 0 <= i < n_features]
            if not valid_idx:
                continue
            grouped.append(
                {
                    "group_name": group_name,
                    "contribution": float(contributions[valid_idx].sum()),
                    "error_delta": float(error_delta[valid_idx].sum()),
                    "n_columns": len(valid_idx),
                }
            )
        grouped.sort(key=lambda item: item["contribution"], reverse=True)
        return grouped[: self.top_k]

    def attribute(
        self,
        model=None,
        reference_data: np.ndarray | None = None,
        current_batch: np.ndarray | None = None,
        feature_names: list | None = None,
        mode: str | None = None,
    ) -> AttributionResult:
        """
        Compute drift attribution comparing reference_data and current_batch.
        """
        if reference_data is None or current_batch is None:
            raise ValueError("reference_data and current_batch are required")

        active_mode = mode or self.mode
        if active_mode not in self.VALID_MODES:
            raise ValueError(f"mode must be one of {self.VALID_MODES}")
        model_free = active_mode in self.MODEL_FREE_MODES
        if model is None and not model_free:
            raise ValueError(f"model is required when mode='{active_mode}'")

        n_features = current_batch.shape[1]
        names = feature_names or self.feature_names or [
            f"feature_{i}" for i in range(n_features)
        ]

        if model is not None and not model_free:
            ref_sample_errors = self._get_per_sample_feature_errors(
                model, reference_data
            )
            cur_sample_errors = self._get_per_sample_feature_errors(
                model, current_batch
            )
            error_delta = cur_sample_errors.mean(axis=0) - ref_sample_errors.mean(
                axis=0
            )
        else:
            ref_sample_errors = np.zeros_like(reference_data, dtype=float)
            error_delta = np.zeros(n_features, dtype=float)

        positive_delta = np.maximum(error_delta, 0.0)
        pos_total = float(positive_delta.sum())

        metadata: dict[str, object] = {
            "no_positive_delta": bool(pos_total <= 0),
            "mode": active_mode,
        }

        drift_types = ["reconstruction"] * n_features
        if active_mode == "positive_delta":
            raw_scores = positive_delta
        elif active_mode == "absolute_delta":
            raw_scores = np.abs(error_delta)
        elif active_mode == "standardized_delta":
            ref_sd = (
                ref_sample_errors.astype(float).std(axis=0, ddof=1)
                if len(reference_data) > 1
                else np.ones(n_features)
            )
            raw_scores = np.abs(error_delta) / np.maximum(ref_sd, REFERENCE_SD_FLOOR)
        elif active_mode == "calibrated":
            raw_scores, drift_types, cal_metadata = self._calibrated_attribution(
                reference_data, current_batch, n_features
            )
            metadata.update(cal_metadata)

        else:
            marg_ev, rel_ev, raw_scores = compute_decomposed_scores(
                reference_data, current_batch
            )
            drift_types = [
                "relational" if rel_ev[j] > marg_ev[j] else "marginal"
                for j in range(n_features)
            ]
            metadata["marginal_evidence"] = marg_ev.tolist()
            metadata["relational_evidence"] = rel_ev.tolist()
            metadata["raw_decomposed_scores"] = raw_scores.tolist()
            is_rel = float(rel_ev.max()) > float(marg_ev.max())
            metadata["dominant_drift_regime"] = "relational" if is_rel else "marginal"

        total = float(raw_scores.sum())
        contributions = (
            raw_scores / total if total > 0 else np.zeros(n_features, dtype=float)
        )

        top_indices = np.argsort(contributions)[::-1][: self.top_k]
        score_key = "evidence" if model_free else "error_delta"
        top_features = [
            {
                "feature_index": int(idx),
                "feature_name": names[idx] if idx < len(names) else f"feature_{idx}",
                "contribution": float(contributions[idx]),
                "error_delta": float(error_delta[idx]),
                score_key: float(raw_scores[idx]),
                "drift_type": drift_types[idx],
            }
            for idx in top_indices
        ]

        if self.feature_groups:
            metadata["grouped_top_features"] = self._group_contributions(
                contributions, error_delta, n_features
            )

        return AttributionResult(
            feature_contributions=contributions,
            feature_error_delta=error_delta,
            top_features=top_features,
            feature_names=names,
            metadata=metadata,
        )

    def _calibrated_attribution(
        self,
        reference_data: np.ndarray,
        current_batch: np.ndarray,
        n_features: int,
    ) -> tuple[np.ndarray, list[str], dict[str, object]]:
        """Permutation-calibrated scores plus the metadata they imply.

        Kept out of ``attribute`` so the model-free entry point stays under the
        local statement budget; the branch is self-contained by design.
        """
        from vigil.calibration import compute_calibrated_scores

        cal = compute_calibrated_scores(
            reference_data,
            current_batch,
            n_permutations=self.n_permutations,
            alpha=self.alpha,
            block_size=self.block_size,
            seed=self.seed,
        )
        marg_ev, rel_ev = cal.marginal_evidence, cal.relational_evidence
        sig = set(cal.significant_features())
        drift_types = [
            ("relational" if rel_ev[j] > marg_ev[j] else "marginal")
            if j in sig
            else "none"
            for j in range(n_features)
        ]
        alpha_marginal = float(cal.metadata.get("alpha_marginal", 0.05))
        marginal_hits = cal.marginal_pvalues <= alpha_marginal
        metadata: dict[str, object] = {
            "marginal_evidence": marg_ev.tolist(),
            "relational_evidence": rel_ev.tolist(),
            # One family per pathway: the "family" p-value *is* the adjusted
            # p-value, so publishing both keys showed the same array twice.
            "marginal_adjusted_pvalues": cal.marginal_pvalues.tolist(),
            "calibration_method": cal.metadata.get("calibration_method"),
            "alpha": cal.metadata.get("alpha"),
            "alpha_marginal": alpha_marginal,
            "block_size": cal.metadata.get("block_size", self.block_size),
            "timings": cal.timings(),
            "max_abs_ref_corr": cal.metadata.get("max_abs_ref_corr"),
            "relational_selected_features": cal.selected_features,
            "significant_features": sorted(sig),
            "n_permutations": cal.n_permutations,
            # ``importance_scores`` carries a tier offset of log10(B + 1) + 1
            # for significant features, so it ranks but is not evidence and is
            # not comparable across permutation budgets. Use
            # ``marginal_evidence`` / ``relational_evidence`` for magnitudes.
            "score_kind": "rank_only_tiered",
            "dominant_drift_regime": (
                "relational"
                if (cal.selected_features and not marginal_hits.any())
                else "marginal"
                if marginal_hits.any()
                else "none"
            ),
        }
        return cal.combined_scores, drift_types, metadata
