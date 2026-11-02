"""Vigil — FastAPI REST Service.

Exposes Vigil (`vigil-drift`) as an HTTP microservice.

Endpoints:
  GET  /health  — liveness probe
  GET  /status  — model status (fitted state, drift count, active modes)
  POST /fit     — fit sentinel on an initial reference batch
  POST /detect  — evaluate an incoming batch for drift, novelty, and attribution
"""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import vigil
from api.schemas import (
    DetectRequest,
    DetectResponse,
    FitRequest,
    StatusResponse,
    TopFeature,
)
from vigil import Vigil

EXPECTED_NDIM = 2
MIN_FIT_SAMPLES = 50
DEFAULT_TOP_K = 5

sentinel: Vigil | None = None
chunks_processed: int = 0
_state_lock = threading.Lock()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialise an unfitted Vigil instance on startup."""
    global sentinel
    sentinel = Vigil()
    yield


app = FastAPI(
    title="Vigil API",
    description=(
        "Unsupervised tabular drift monitoring, KDE novelty scoring, and "
        "Decomposed / Permutation-Calibrated Copula-KS feature attribution."
    ),
    version=vigil.__version__,
    contact={
        "name": "Venkateswara Sahu",
        "url": "https://github.com/Venkateswara-Sahu/OWADD",
    },
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    """Liveness probe for container orchestrators."""
    return {"status": "ok", "service": "vigil", "version": vigil.__version__}


@app.get("/status", response_model=StatusResponse, tags=["System"])
def status() -> StatusResponse:
    """Return current sentinel state, drift count, and active configuration."""
    with _state_lock:
        is_fitted = bool(sentinel and sentinel.is_fitted)
        return StatusResponse(
            is_fitted=is_fitted,
            n_features=sentinel.n_features if sentinel and is_fitted else None,
            n_drifts_detected=sentinel.n_drifts_detected if sentinel else 0,
            chunks_processed=chunks_processed,
            attribution_mode=sentinel.attribution_mode if sentinel else None,
            adaptation_mode=sentinel.adaptation_mode if sentinel else None,
        )


@app.post("/fit", tags=["Model"])
def fit(request: FitRequest) -> dict[str, object]:
    """Fit Vigil on an initial reference window (minimum 50 rows)."""
    global sentinel, chunks_processed

    data = np.asarray(request.data, dtype=np.float32)
    if data.ndim != EXPECTED_NDIM:
        raise HTTPException(
            status_code=422,
            detail="data must be a 2D array of shape (n_samples, n_features).",
        )
    if len(data) < MIN_FIT_SAMPLES:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least {MIN_FIT_SAMPLES} samples to fit a baseline.",
        )

    with _state_lock:
        sentinel = Vigil(
            feature_names=request.feature_names,
            top_k_features=DEFAULT_TOP_K,
            attribution_mode=request.attribution_mode,
            adaptation_mode=request.adaptation_mode,
            n_permutations=request.n_permutations,
            block_size=request.block_size,
            seed=request.seed,
        )
        sentinel._attributor.alpha = request.alpha
        sentinel.fit(data, verbose=False)
        chunks_processed = 0

    return {
        "message": "Sentinel fitted.",
        "n_samples": len(data),
        "n_features": int(data.shape[1]),
        "attribution_mode": request.attribution_mode,
        "adaptation_mode": request.adaptation_mode,
        "n_permutations": request.n_permutations,
        "block_size": request.block_size,
    }


@app.post("/detect", response_model=DetectResponse, tags=["Detection"])
def detect(request: DetectRequest) -> DetectResponse:
    """Evaluate an incoming batch for distribution shift and novel classes."""
    global chunks_processed

    with _state_lock:
        if not sentinel or not sentinel.is_fitted:
            raise HTTPException(
                status_code=400,
                detail="Sentinel not fitted. Call POST /fit with baseline data first.",
            )

        data = np.asarray(request.data, dtype=np.float32)
        if data.ndim != EXPECTED_NDIM:
            raise HTTPException(
                status_code=422,
                detail="data must be a 2D array of shape (n_samples, n_features).",
            )
        if data.shape[1] != sentinel.n_features:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Feature count mismatch: expected {sentinel.n_features}, "
                    f"got {data.shape[1]}."
                ),
            )

        if request.feature_names is not None:
            sentinel.feature_names = request.feature_names
            sentinel._attributor.feature_names = request.feature_names

        result = sentinel.detect(data)
        chunks_processed += 1

    top_features: list[TopFeature] | None = None
    dominant_regime: str | None = None
    sig_features: list[int] | None = None

    if result.drift_detected and result.attribution is not None:
        meta = result.attribution.metadata
        dominant_regime = meta.get("dominant_drift_regime")
        raw_sig = meta.get("significant_features")
        if isinstance(raw_sig, list):
            sig_features = [int(idx) for idx in raw_sig]
        top_features = [
            TopFeature(
                feature_index=int(f["feature_index"]),
                feature_name=str(f["feature_name"]),
                contribution=round(float(f["contribution"]), 4),
                error_delta=round(float(f["error_delta"]), 6),
                drift_type=f.get("drift_type"),
            )
            for f in result.attribution.top_features
        ]

    msg = (
        f"Drift detected (severity={result.drift_severity:.2f})"
        if result.drift_detected
        else "No drift detected. Stream within reference baseline."
    )

    return DetectResponse(
        chunk_id=result.chunk_id,
        drift_detected=result.drift_detected,
        drift_severity=round(float(result.drift_severity), 4),
        novelty_proportion=round(float(result.novelty_proportion), 4),
        n_novel=int(result.n_novel),
        batch_error_mean=round(float(result.drift_result.batch_error_mean), 6),
        reference_error_mean=round(float(result.drift_result.reference_error_mean), 6),
        dominant_drift_regime=dominant_regime,
        significant_features=sig_features,
        top_drifted_features=top_features,
        message=msg,
    )
