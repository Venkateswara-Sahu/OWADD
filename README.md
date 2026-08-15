<div align="center">

<img src="https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/PyTorch-2.x-EE4C2C?style=flat-square&logo=pytorch&logoColor=white"/>
<img src="https://img.shields.io/github/actions/workflow/status/Venkateswara-Sahu/OWADD/ci.yml?branch=main&style=flat-square&label=CI&logo=github"/>
<img src="https://img.shields.io/badge/License-MIT-green?style=flat-square"/>
<img src="https://img.shields.io/badge/arXiv-2605.29834-b31b1b?style=flat-square&logo=arxiv"/>

<br/><br/>

# 🛡️ OWADD Sentinel

### Production-ready unsupervised concept drift detection for tabular data streams

**No labels. No manual thresholds. Knows when your data changes — and tells you exactly which features changed.**

[Quick Start](#-quick-start) · [Dashboard](#-live-dashboard) · [API Docs](#-rest-api) · [Architecture](#-architecture) · [Paper](#-research-basis)

</div>

---

## The Problem

In production ML systems, the data your model was trained on eventually stops looking like the data it receives — a phenomenon called **concept drift**. For network security, this means attacks evolve. For fraud detection, patterns shift. For predictive maintenance, machinery ages.

Most drift detectors either require labels (which you never have in real-time) or only tell you *that* drift happened, not *what* drifted.

**OWADD Sentinel solves both.**

---

## What It Does

| Capability | How |
|---|---|
| 🔍 **Detect concept drift** | Replicated T-Test on autoencoder reconstruction errors — no labels needed |
| 🆕 **Identify novel classes** | KDE density estimation on a frozen mirror autoencoder (A_KC) |
| 📊 **Explain the drift** | Feature-level attribution: ranks which input features caused the drift |
| ⚡ **Serve at scale** | FastAPI REST service with `/detect` endpoint |
| 📈 **Track experiments** | MLflow logs every chunk's drift severity, novelty rate, and attribution report |
| 🖥️ **Visualize live** | SOC-style Streamlit dashboard with real-time charts |

---

## Architecture

```
                    ┌─────────────────────────────────────────────────┐
                    │              OWADD Sentinel System               │
                    │                                                  │
  Data Stream       │  ┌──────────┐    ┌─────────────────────────┐   │
 ─────────────►     │  │  Chunk   │───►│    Autoencoder A         │   │
  (CSV / API /      │  │ (200 rows│    │   (adapts on drift)      │   │     ┌──────────┐
   Kafka topic)     │  └──────────┘    └──────────┬──────────────┘   │────►│  MLflow  │
                    │        │                    │ errors_A          │     │ Tracking │
                    │        │         ┌──────────▼──────────────┐   │     └──────────┘
                    │        │         │  Replicated T-Test       │   │
                    │        │         │  (15 tests, α=0.05)      │   │     ┌──────────┐
                    │        │         │  Buffer size: 1000       │   │────►│FastAPI   │
                    │        │         └──────────┬──────────────┘   │     │ /detect  │
                    │        │                    │ DRIFT?            │     └──────────┘
                    │        │         ┌──────────▼──────────────┐   │
                    │        │         │  DriftAttributor         │   │     ┌──────────┐
                    │        │         │  (novel contribution)    │   │────►│Streamlit │
                    │        │         │  Which features drifted? │   │     │Dashboard │
                    │        │         └─────────────────────────┘   │     └──────────┘
                    │        │                                        │
                    │        │         ┌─────────────────────────┐   │
                    │        └────────►│  Autoencoder A_KC        │   │
                    │                 │  (frozen mirror)         │   │
                    │                 └──────────┬──────────────┘   │
                    │                            │ errors_AKC        │
                    │                 ┌──────────▼──────────────┐   │
                    │                 │  KDE Novelty Detector    │   │
                    │                 │  Novel class proportion  │   │
                    │                 └─────────────────────────┘   │
                    └─────────────────────────────────────────────────┘
```

**Key design decisions (from arXiv:2605.29834):**
- Uses 1-D reconstruction error proxy instead of full feature vectors → memory complexity O(buffer_size) not O(n × d)
- Dual autoencoders: **A** adapts on drift; **A_KC** stays frozen to distinguish drift from novelty
- Replicated T-tests (r=15) reduce variance vs. a single test

**Novel contribution (OWADD Sentinel, not in the paper):**
- `DriftAttributor` computes per-feature reconstruction error delta → ranks features by drift contribution → makes alerts *actionable*

---

## 📦 Quick Start

### Install

```bash
git clone https://github.com/Venkateswara-Sahu/OWADD.git
cd OWADD
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -e ".[dev]"
```

### Run as a Python library

```python
import pandas as pd
from owadd_sentinel import OWADDSentinel

# Load your data
df = pd.read_csv("your_data.csv")
feature_cols = [c for c in df.columns if c != "label"]
X = df[feature_cols].values.astype("float32")

# Initialise
sentinel = OWADDSentinel(
    feature_names=feature_cols,
    top_k_features=5,
)

# Phase 1: train on first batch (offline)
sentinel.fit(X[:200])

# Phase 2: process stream chunk by chunk
chunk_size = 200
for i in range(200, len(X), chunk_size):
    result = sentinel.detect(X[i:i+chunk_size])

    print(result)
    # SentinelResult(chunk=3, status=⚠️  DRIFT, severity=0.93, novelty=0.0%)

    if result.drift_detected:
        for feat in result.attribution.top_features:
            print(f"  {feat['feature_name']}: {feat['contribution']:.1%} contribution")
```

---

## 🖥️ Live Dashboard

SOC-style real-time monitoring of the NSL-KDD network traffic stream:

```bash
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

Open **http://localhost:8501**, press **▶ Start** and watch:
- Reconstruction error timeline update chunk by chunk
- Red ⚠ drift markers appear when the traffic distribution shifts
- Feature attribution chart reveals which network features drifted
- Novelty gauge tracks unknown attack class emergence

---

## 🌐 REST API

FastAPI microservice for production deployment:

```bash
pip install -e ".[api]"
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000/docs** for interactive Swagger UI.

```bash
# Train on initial data
curl -X POST http://localhost:8000/fit \
  -H "Content-Type: application/json" \
  -d '{"data": [[0.1, 0.5, ...], ...]}'

# Detect drift in incoming batch
curl -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{"data": [[0.3, 0.9, ...], ...]}'
```

**Response:**
```json
{
  "drift_detected": true,
  "drift_severity": 0.93,
  "novelty_proportion": 0.0,
  "top_drifted_features": [
    {"feature_name": "diff_srv_rate", "contribution": 0.23, "error_delta": 0.041},
    {"feature_name": "service_other", "contribution": 0.07, "error_delta": 0.012}
  ],
  "message": "⚠️ Concept drift detected (severity=0.93)"
}
```

---

## 📊 MLflow Experiment Tracking

```bash
pip install -e ".[mlflow]"

# Run stream with experiment logging
python -c "
from data.nsl_kdd_loader import load_nsl_kdd
from data.stream_simulator import StreamSimulator
from owadd_sentinel import OWADDSentinel
from owadd_sentinel.logging.mlflow_logger import MLflowLogger

X, y, feat = load_nsl_kdd()
sim = StreamSimulator(X, y)
sentinel = OWADDSentinel(feature_names=feat)
logger = MLflowLogger(experiment_name='nsl-kdd-stream')

first = next(sim.stream(n_chunks=1))
sentinel.fit(first.X, verbose=False)

logger.start_run(params={'buffer_size': 1000, 'drift_threshold': 0.3})
for chunk in sim.stream(n_chunks=25):
    result = sentinel.detect(chunk.X)
    logger.log_chunk(result, ground_truth_label=chunk.dominant_class)
logger.end_run()
"

# View results
mlflow ui   # → http://localhost:5000
```

---

## 🧪 Tests

```bash
pytest tests/ -v --cov=owadd_sentinel
```

```
tests/test_autoencoder.py::test_autoencoder_forward_shape          PASSED
tests/test_autoencoder.py::test_reconstruction_errors_non_negative PASSED
tests/test_autoencoder.py::test_mirrored_pair_identical_weights    PASSED
tests/test_autoencoder.py::test_training_reduces_loss              PASSED
tests/test_drift_detector.py::test_no_drift_during_warmup          PASSED
tests/test_drift_detector.py::test_no_false_drift_on_stable_stream PASSED
tests/test_drift_detector.py::test_drift_detected_on_shifted_dist  PASSED
tests/test_sentinel.py::test_sentinel_fit_and_detect               PASSED
tests/test_sentinel.py::test_sentinel_attribution_on_drift         PASSED
... 14 passed in 15s, 81% coverage
```

---

## 🗂️ Project Structure

```
OWADD/
├── owadd_sentinel/              # Core pip package
│   ├── core/
│   │   ├── autoencoder.py       # Dual mirrored autoencoders (A and A_KC)
│   │   ├── drift_detector.py    # Replicated T-Test drift detection
│   │   └── novelty_detector.py  # KDE-based novel class recognition
│   ├── logging/
│   │   └── mlflow_logger.py     # MLflow experiment tracking
│   ├── attribution.py           # Feature-level drift attribution (novel)
│   └── sentinel.py              # Main OWADDSentinel public API
│
├── api/
│   ├── app.py                   # FastAPI REST service
│   └── schemas.py               # Pydantic request/response models
│
├── data/
│   ├── nsl_kdd_loader.py        # NSL-KDD download + preprocessing
│   └── stream_simulator.py      # 3-phase non-stationary stream
│
├── dashboard/
│   └── app.py                   # SOC-style Streamlit dashboard
│
├── tests/                       # 14 unit + integration tests
├── .github/workflows/ci.yml     # GitHub Actions CI
└── pyproject.toml               # pip install owadd-sentinel
```

---

## 🔬 Research Basis

This project implements and extends:

> **"Open World Autoencoding Drift Detection with Novel Class Recognition in Tabular Non-stationary Data Streams"**  
> arXiv:2605.29834

**Extensions in OWADD Sentinel (not in the paper):**
- `DriftAttributor`: per-feature reconstruction error delta analysis — makes drift detection *actionable* by identifying which features drifted and by how much
- FastAPI REST service for production deployment
- MLflow integration for experiment tracking and model versioning
- SOC-style real-time monitoring dashboard

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Core algorithm | Python, PyTorch, SciPy, scikit-learn |
| REST API | FastAPI, Pydantic, Uvicorn |
| Experiment tracking | MLflow |
| Dashboard | Streamlit, Plotly |
| Dataset | NSL-KDD (Canadian Institute for Cybersecurity) |
| Testing | pytest, pytest-cov |
| Linting | Ruff |
| CI/CD | GitHub Actions |

---

## 📄 License

MIT © Venkateswara Sahu

---

<div align="center">

**Built with the belief that ML systems should know when they're wrong.**

[⭐ Star this repo](https://github.com/Venkateswara-Sahu/OWADD) if you find it useful

</div>
