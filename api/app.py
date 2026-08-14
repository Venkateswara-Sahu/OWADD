"""
OWADD Sentinel — FastAPI REST Service
======================================
Exposes the OWADDSentinel as a production-ready HTTP microservice.

Endpoints:
  GET  /health          — liveness probe (for Docker/K8s health checks)
  GET  /status          — model status (fitted?, n_drifts, etc.)
  POST /fit             — train sentinel on initial data batch
  POST /detect          — process incoming batch, return drift + novelty report
  GET  /docs            — auto-generated Swagger UI (built into FastAPI)

Usage:
  uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

Then open:
  http://localhost:8000/docs  — interactive API docs
  http://localhost:8000/health
"""

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from owadd_sentinel import OWADDSentinel
from api.schemas import (
    DetectRequest,
    DetectResponse,
    FitRequest,
    StatusResponse,
    TopFeature,
)

# ─────────────────────────────────────────────
# App lifespan: initialise sentinel on startup
# ─────────────────────────────────────────────

sentinel: OWADDSentinel | None = None
chunks_processed: int = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global sentinel
    sentinel = OWADDSentinel()
    print("[OWADD Sentinel API] Ready. POST /fit to train, POST /detect to analyse.")
    yield
    print("[OWADD Sentinel API] Shutting down.")


# ─────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────

app = FastAPI(
    title="OWADD Sentinel API",
    description=(
        "Production-ready unsupervised ML data drift detection with feature attribution. "
        "Based on arXiv:2605.29834. "
        "Detects concept drift and novel class emergence in tabular data streams — "
        "no labels required."
    ),
    version="0.1.0",
    contact={"name": "Venkateswara Sahu", "url": "https://github.com/Venkateswara-Sahu/OWADD"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# Allow Streamlit dashboard to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """
    Liveness probe.
    Returns 200 OK if the service is running.
    Used by Docker HEALTHCHECK and Kubernetes liveness probes.
    """
    return {"status": "ok", "service": "owadd-sentinel"}


@app.get("/status", response_model=StatusResponse, tags=["System"])
def status():
    """Return current model status: fitted state, drift count, chunks processed."""
    return StatusResponse(
        is_fitted=sentinel.is_fitted if sentinel else False,
        n_features=sentinel.n_features if sentinel and sentinel.is_fitted else None,
        n_drifts_detected=sentinel.n_drifts_detected if sentinel else 0,
        chunks_processed=chunks_processed,
    )


@app.post("/fit", tags=["Model"])
def fit(request: FitRequest):
    """
    Train the OWADD Sentinel on the initial data batch (offline phase).

    Must be called once before /detect. Provide at least 200 samples.
    The model trains two autoencoders and fits the KDE novelty baseline.
    """
    global sentinel

    data = np.array(request.data, dtype=np.float32)

    if data.ndim != 2:
        raise HTTPException(status_code=422, detail="data must be a 2D array (n_samples, n_features)")
    if len(data) < 50:
        raise HTTPException(status_code=422, detail="Need at least 50 samples to train. Provide more data.")

    sentinel = OWADDSentinel(
        feature_names=request.feature_names,
        top_k_features=5,
    )
    sentinel.fit(data, verbose=False)

    return {
        "message": "Sentinel fitted successfully.",
        "n_samples": len(data),
        "n_features": data.shape[1],
    }


@app.post("/detect", response_model=DetectResponse, tags=["Detection"])
def detect(request: DetectRequest):
    """
    Process an incoming data batch and detect concept drift + novel classes.

    Returns:
    - drift_detected: bool
    - drift_severity: float [0.0–1.0] — proportion of T-tests significant
    - novelty_proportion: float — fraction of unknown-class samples
    - top_drifted_features: list — ranked features causing the drift (if drift detected)

    Call this endpoint repeatedly as new data batches arrive in your stream.
    """
    global chunks_processed

    if not sentinel or not sentinel.is_fitted:
        raise HTTPException(
            status_code=400,
            detail="Sentinel not fitted. Call POST /fit with initial training data first."
        )

    data = np.array(request.data, dtype=np.float32)

    if data.ndim != 2:
        raise HTTPException(status_code=422, detail="data must be 2D array (n_samples, n_features)")

    if data.shape[1] != sentinel.n_features:
        raise HTTPException(
            status_code=422,
            detail=f"Feature count mismatch. Model expects {sentinel.n_features} features, got {data.shape[1]}."
        )

    # Run drift + novelty detection
    if request.feature_names:
        sentinel.feature_names = request.feature_names
        sentinel._attributor.feature_names = request.feature_names

    result = sentinel.detect(data)
    chunks_processed += 1

    # Build attribution response
    top_features = None
    if result.drift_detected and result.attribution:
        top_features = [
            TopFeature(
                feature_index=f["feature_index"],
                feature_name=f["feature_name"],
                contribution=round(f["contribution"], 4),
                error_delta=round(f["error_delta"], 6),
            )
            for f in result.attribution.top_features
        ]

    msg = (
        f"⚠️ Concept drift detected (severity={result.drift_severity:.2f})"
        if result.drift_detected
        else "✅ No drift detected. Stream is stable."
    )

    return DetectResponse(
        chunk_id=result.chunk_id,
        drift_detected=result.drift_detected,
        drift_severity=round(result.drift_severity, 4),
        novelty_proportion=round(result.novelty_proportion, 4),
        n_novel=result.n_novel,
        batch_error_mean=round(result.drift_result.batch_error_mean, 6),
        reference_error_mean=round(result.drift_result.reference_error_mean, 6),
        top_drifted_features=top_features,
        message=msg,
    )
