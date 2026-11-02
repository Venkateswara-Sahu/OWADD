"""Pydantic schemas for the Vigil REST API.

Defines request and response payloads for `/fit`, `/detect`, and `/status`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

import vigil

AttributionModeLiteral = Literal[
    "decomposed",
    "calibrated",
    "positive_delta",
    "absolute_delta",
    "standardized_delta",
]
AdaptationModeLiteral = Literal["auto", "verified_only", "frozen"]


class DetectRequest(BaseModel):
    """Request body for `POST /detect`."""

    data: list[list[float]] = Field(
        ...,
        description=(
            "2D numeric batch of shape (n_samples, n_features). "
            "Each inner list is one observation."
        ),
        examples=[[[0.1, 0.5, 0.0], [0.2, 0.4, 0.1]]],
    )
    feature_names: list[str] | None = Field(
        default=None,
        description="Optional column names used in the attribution report.",
    )


class TopFeature(BaseModel):
    """A single feature's contribution to the detected drift."""

    feature_index: int
    feature_name: str
    contribution: float = Field(
        ..., description="Normalized drift-evidence share in [0.0, 1.0]."
    )
    error_delta: float = Field(
        ..., description="Raw pathway evidence or reconstruction-error delta."
    )
    drift_type: str | None = Field(
        default=None,
        description="Dominant pathway ('marginal', 'relational', or 'reconstruction').",
    )


class DetectResponse(BaseModel):
    """Response body from `POST /detect`."""

    chunk_id: int
    drift_detected: bool
    drift_severity: float = Field(
        ...,
        description="Proportion of replicated Welch tests rejecting H0 [0.0-1.0].",
    )
    novelty_proportion: float = Field(
        ...,
        description="Fraction of samples flagged outside the KDE reference support.",
    )
    n_novel: int = Field(..., description="Count of novel samples in this batch.")
    batch_error_mean: float = Field(
        ..., description="Mean reconstruction error of the current batch."
    )
    reference_error_mean: float = Field(
        ..., description="Mean reconstruction error of the reference buffer."
    )
    dominant_drift_regime: str | None = Field(
        default=None,
        description=(
            "Aggregate shift regime ('marginal', 'relational', 'mixed', 'none') "
            "when decomposed or calibrated attribution is active."
        ),
    )
    significant_features: list[int] | None = Field(
        default=None,
        description=(
            "Feature indices surviving Westfall-Young family-wise calibration "
            "(populated when attribution_mode='calibrated')."
        ),
    )
    top_drifted_features: list[TopFeature] | None = Field(
        default=None,
        description="Ranked features contributing most to the detected shift.",
    )
    message: str


class StatusResponse(BaseModel):
    """Response from `GET /status`."""

    is_fitted: bool
    n_features: int | None
    n_drifts_detected: int
    chunks_processed: int
    attribution_mode: str | None = None
    adaptation_mode: str | None = None
    model_version: str = vigil.__version__


class FitRequest(BaseModel):
    """Request body for `POST /fit` — fit Vigil on an initial reference window."""

    data: list[list[float]] = Field(
        ...,
        description="Initial reference batch of shape (n_samples, n_features).",
    )
    feature_names: list[str] | None = None
    attribution_mode: AttributionModeLiteral = Field(
        default="decomposed",
        description=(
            "Attribution mode: 'decomposed' (fast Copula-KS), 'calibrated' "
            "(Westfall-Young permutation + greedy edge peeling), 'positive_delta', "
            "'absolute_delta', or 'standardized_delta'."
        ),
    )
    adaptation_mode: AdaptationModeLiteral = Field(
        default="auto",
        description="Retraining policy on drift: 'auto', 'verified_only', or 'frozen'.",
    )
    n_permutations: int = Field(
        default=199,
        ge=19,
        le=5000,
        description="Monte-Carlo permutations B when attribution_mode='calibrated'.",
    )
    block_size: int = Field(
        default=1,
        ge=1,
        description="Contiguous block length for block-permutation calibration.",
    )
    alpha: float = Field(
        default=0.05,
        gt=0.0,
        lt=1.0,
        description="Family-wise significance level for calibrated attribution.",
    )
    seed: int | None = Field(
        default=42,
        description="Optional RNG seed for reproducible training and permutations.",
    )
