# Vigil

Unsupervised drift-monitoring prototype and reproducible attribution evaluation.

[PyPI](https://pypi.org/project/vigil-drift/) · [Project site](https://venkateswara-sahu.github.io/OWADD/) · [Research evidence](https://github.com/Venkateswara-Sahu/OWADD/blob/main/docs/research-status.md)

## Status

Vigil combines autoencoder reconstruction errors, statistical drift tests, KDE novelty scores and feature-error rankings with example monitoring integrations. It is an engineering/research prototype, not a validated intrusion-detection system or a production-readiness claim.

The September 2026 investigation did **not** establish a generally superior new attribution method. Trained reconstruction rankings helped in some dependency-shift conditions but underperformed simple KS/correlation baselines in other conditions. The original default remains unchanged; research variants are experimental.

There is no Vigil publication claimed here. The old manuscript in `paper/` is an unpublished, superseded draft. Historical NSL-KDD demo numbers are not current evidence of attack-detection performance.

## Quick start

Install the published package:

```bash
pip install vigil-drift
```

The published package may lag this repository's research tooling. For current source and tests:

```bash
git clone https://github.com/Venkateswara-Sahu/OWADD.git
cd OWADD
pip install -e ".[dev,research]"
python -m pytest tests/ -v --cov=vigil
```

Supply preprocessed finite numeric arrays with consistent feature order; fit preprocessing on training data only.

```python
from vigil import Vigil

v = Vigil(feature_names=feature_names)
v.fit(baseline_data)

for batch in stream:
    result = v.detect(batch)
    if result.attribution is not None:
        for feature in result.attribution.top_features:
            print(feature["feature_name"], feature["contribution"])
```

Contributions are normalized reconstruction-error scores, not percentages of input change, attack probabilities or causal explanations. Detection has configurable thresholds; label-free inference does not remove the need for calibration and labeled evaluation.

## Implemented components

| Component | Scope |
| --- | --- |
| Dual autoencoders, replicated tests, KDE | Experimental drift/novelty monitoring |
| `DriftAttributor` | Per-feature reconstruction-error ranking |
| FastAPI, Kafka, MLflow | Example serving, ingestion and experiment tracking |
| Airflow DAGs | Example monitoring/retraining orchestration |
| Streamlit and Docker Compose | Local demonstration stack |
| `experiments/` | Versioned protocols, data audits, baselines and reproducible comparisons |

These integrations do not establish security hardening, throughput guarantees or reliable autonomous adaptation.

## Research evidence

Read the [research status](https://github.com/Venkateswara-Sahu/OWADD/blob/main/docs/research-status.md) and [final decision report](https://github.com/Venkateswara-Sahu/OWADD/blob/main/docs/superpowers/final-mechanism-decision-2026-09-28.md).

The final bounded study covered 20 seeds, nine ranking methods, 18 synthetic conditions and six controlled real-data conditions. Real-data tests injected shifts into reserved CICIDS2017 development flow features; they were not held-out attack detection or live chronological deployment tests. Results and limitations are reported together rather than collapsed into a winning headline.

Raw datasets, prepared caches and per-run outputs are not distributed. Protocols, source, tests and compact reports are retained. Reproduction requires obtaining the specified data separately.

## Example integrations

Run from a source checkout after installing the appropriate extras:

```bash
pip install -e ".[api,dashboard,mlflow,kafka]"
uvicorn api.app:app --host 127.0.0.1 --port 8000
# In a separate terminal:
streamlit run dashboard/app.py
```

Other examples live in `kafka_pipeline/`, `airflow/dags/` and the Compose configuration. Review their configuration before running; do not expose demo services directly to an untrusted network.

## Attribution and historical material

The original project cites *Open World Autoencoding Drift Detection with Novel Class Recognition in Tabular Non-stationary Data Streams*, arXiv:2605.29834, as its algorithmic basis. That reference is not a Vigil publication or evidence that Vigil's additions are novel. Research novelty remains unestablished.

Historical plans record decisions at their time of writing; the final decision supersedes earlier optimistic hypotheses. Legacy demo scripts and manuscript figures are not the current evaluation protocol.

## License

MIT. See LICENSE.
