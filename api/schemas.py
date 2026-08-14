"""
Pydantic schemas for the OWADD Sentinel REST API.
Defines the shape of requests and responses for the /detect endpoint.
"""

from pydantic import BaseModel, Field
from typing import Optional


class DetectRequest(BaseModel):
    """
    Request body for POST /detect.

    Send a batch of tabular data rows for drift and novelty analysis.

    Example JSON:
    {
        "data": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
        "feature_names": ["duration", "src_bytes", ...]
    }
    """
    data: list[list[float]] = Field(
        ...,
        description="2D array of shape (n_samples, n_features). Each inner list is one data row.",
        example=[[0.1, 0.5, 0.0], [0.2, 0.4, 0.1]],
    )
    feature_names: Optional[list[str]] = Field(
        None,
        description="Optional column names for the features (used in attribution report).",
    )


class TopFeature(BaseModel):
    """A single feature's contribution to the detected drift."""
    feature_index: int
    feature_name: str
    contribution: float = Field(..., description="Proportion of total drift [0.0-1.0]")
    error_delta: float = Field(..., description="Change in reconstruction error for this feature")


class DetectResponse(BaseModel):
    """
    Response body from POST /detect.

    Returns drift status, severity score, novelty proportion,
    and (if drift detected) a ranked list of features that drifted most.
    """
    chunk_id: int
    drift_detected: bool
    drift_severity: float = Field(..., description="Proportion of T-tests significant [0.0-1.0]. Threshold: 0.3")
    novelty_proportion: float = Field(..., description="Fraction of samples classified as novel/unknown")
    n_novel: int = Field(..., description="Absolute count of novel samples in this batch")
    batch_error_mean: float = Field(..., description="Mean reconstruction error of current batch")
    reference_error_mean: float = Field(..., description="Mean reconstruction error of reference buffer")
    top_drifted_features: Optional[list[TopFeature]] = Field(
        None,
        description="Ranked list of features that contributed most to the drift. Only present when drift_detected=True."
    )
    message: str


class StatusResponse(BaseModel):
    """Response from GET /status."""
    is_fitted: bool
    n_features: Optional[int]
    n_drifts_detected: int
    chunks_processed: int
    model_version: str = "0.1.0"


class FitRequest(BaseModel):
    """Request body for POST /fit — train sentinel on initial data."""
    data: list[list[float]] = Field(
        ...,
        description="Initial training data, shape (n_samples, n_features)."
    )
    feature_names: Optional[list[str]] = None
