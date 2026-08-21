<div align="center">

[![PyPI](https://img.shields.io/pypi/v/vigil-drift?style=flat-square&logo=pypi&logoColor=white&label=vigil-drift&color=0d6efd)](https://pypi.org/project/vigil-drift/)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![CI](https://img.shields.io/github/actions/workflow/status/Venkateswara-Sahu/OWADD/ci.yml?branch=main&style=flat-square&label=CI&logo=github)
![Coverage](https://img.shields.io/badge/coverage-81%25-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
[![arXiv](https://img.shields.io/badge/arXiv-2605.29834-b31b1b?style=flat-square&logo=arxiv)](https://arxiv.org/abs/2605.29834)

# 🛡️ Vigil

### Production-ready unsupervised concept drift detection for network traffic streams

**No labels. No manual thresholds. Knows when your data changes — and tells you exactly which features changed.**

</div>

---

## Install

```bash
pip install vigil-drift
```

---

## The Problem

In production ML systems, the data your model was trained on eventually stops looking like the data it receives — **concept drift**. For network security, attacks evolve. Most drift detectors require labels (unavailable in real-time) or only tell you *that* drift happened, not *what* drifted.

**Vigil solves both.**

---

## What It Does

| Capability | How |
|---|---|
| 🔍 **Detect concept drift** | Replicated T-Test (r=15) on autoencoder reconstruction errors — no labels needed |
| 🆕 **Identify novel classes** | KDE density estimation on a frozen mirror autoencoder (A_KC) |
| 📊 **Explain the drift** | `DriftAttributor` ranks input features by reconstruction error delta |
| ⚡ **Serve at scale** | FastAPI REST service with `/fit` and `/detect` endpoints |
| 📡 **Stream-native** | Kafka producer/consumer pipeline for live network traffic |
| 📈 **Track experiments** | MLflow logs every chunk's drift severity, novelty, and attribution |
| ✈️ **Auto-retrain** | Airflow DAGs trigger retraining with quality gate when drift accumulates |
| 🖥️ **Visualize live** | SOC-style Streamlit dashboard with real-time charts |

---

## Architecture

```
                                    ┌─────────────────────────────────────────────┐
                                    │                   Vigil                     │
                                    │                                             │
 Data Stream                        │  ┌─────────────┐   ┌─────────────────────┐ │
 CSV · Kafka · REST ──► Chunk  ─────┼─►│ Autoencoder │──►│ Reconstruction      │ │
                       200 rows     │  │  A (adapts) │   │ Errors A            │ │   ┌──────────┐
                           │        │  └─────────────┘   └──────────┬──────────┘ │──►│  MLflow  │
                           │        │                               │             │   └──────────┘
                           │        │                    ┌──────────▼──────────┐  │
                           │        │                    │  Replicated T-Test  │  │   ┌──────────┐
                           │        │                    │  r=15   α=0.05      ├──┼──►│ FastAPI  │
                           │        │                    └──────────┬──────────┘  │   └──────────┘
                           │        │                               │ Drift?      │
                           │        │                    ┌──────────▼──────────┐  │   ┌──────────┐
                           │        │                    │  DriftAttributor    ├──┼──►│Streamlit │
                           │        │                    │  ★ novel contrib    │  │   └──────────┘
                           │        │                    │  ranks Δerror/feat  │  │
                           │        │                    └─────────────────────┘  │   ┌──────────┐
                           │        │                                             │──►│ Airflow  │
                           │        │  ┌─────────────┐   ┌─────────────────────┐ │   │ DAG      │
                           └────────┼─►│ Autoencoder │──►│ Reconstruction      │ │   └──────────┘
                                    │  │ A_KC(frozen)│   │ Errors A_KC         │ │
                                    │  └─────────────┘   └──────────┬──────────┘ │
                                    │                    ┌──────────▼──────────┐  │
                                    │                    │  KDE Novelty        │  │
                                    │                    │  Detector           │  │
                                    │                    └─────────────────────┘  │
                                    └─────────────────────────────────────────────┘
```

**Key design decisions (arXiv:2605.29834):**
- 1-D reconstruction error proxy → memory O(buffer_size) not O(n × d)
- Dual autoencoders: **A** adapts on drift; **A_KC** stays frozen → separates *drift* from *novelty*
- Replicated T-tests (r=15) reduce variance vs a single test

**Novel contribution (not in the paper):**
- `DriftAttributor` — per-feature Δerror → ranks features by drift contribution → makes alerts *actionable*

---

## Quick Start

```python
from vigil import Vigil

v = Vigil(feature_names=feature_cols, top_k_features=5)

# Phase 1: train on baseline traffic (offline)
v.fit(baseline_data)

# Phase 2: detect on every incoming chunk
for chunk in stream:
    result = v.detect(chunk)

    if result.drift_detected:
        print(f"⚠  severity={result.drift_severity:.2f}")
        for feat in result.attribution.top_features:
            print(f"   {feat['feature_name']}: {feat['contribution']:.1%}")

# ⚠  severity=1.00
# → service_eco_i               15.3%   (port scan signature)
# → dst_host_same_src_port_rate  12.3%  (scanning pattern)
# → srv_diff_host_rate           11.1%  (lateral movement)
```

---

## Live Dashboard

```bash
pip install "vigil-drift[dashboard]"
streamlit run dashboard/app.py
```

---

## REST API

```bash
pip install "vigil-drift[api]"
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
# Swagger UI → http://localhost:8000/docs
```

---

## Kafka Streaming

```bash
docker compose up kafka zookeeper -d
python kafka_pipeline/producer.py   # publish NSL-KDD chunks
python kafka_pipeline/consumer.py   # detect drift in real-time
```

```
[Consumer] Chunk 11 [ipsweep] ⚠ DRIFT  | severity=1.00
             → service_eco_i(15.3%), dst_host_same_src_port_rate(12.3%)
[Consumer] Chunk 24 [normal] ⚠ DRIFT   | severity=0.33
             → root_shell(27.7%), service_telnet(21.5%)
```

---

## Tests

```bash
pytest tests/ -v --cov=vigil
# 14 passed, 81% coverage
```

---

## Research Basis

Implements and extends:

> **"Open World Autoencoding Drift Detection with Novel Class Recognition in Tabular Non-stationary Data Streams"**
> arXiv:2605.29834

---

## Links

- **GitHub**: https://github.com/Venkateswara-Sahu/OWADD
- **Website**: https://venkateswara-sahu.github.io/OWADD/
- **PyPI**: https://pypi.org/project/vigil-drift/

---

MIT © Venkateswara Sahu
