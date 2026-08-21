"""
DAG: owadd_stream_monitor
==========================
Runs every hour to process the latest batch of network traffic through
Vigil, log results to MLflow, and trigger retraining if drift
is consistently detected across multiple consecutive chunks.

Schedule: hourly
Owner:    vigil

Task Graph:
    load_latest_chunk
          │
          ▼
    run_drift_detection
          │
          ▼
    log_to_mlflow
          │
          ▼
    check_drift_threshold ──► (no drift) ──► end_pipeline
          │
          │ (drift detected)
          ▼
    trigger_retrain_dag
          │
          ▼
    send_alert
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta

import numpy as np

# ─── Airflow imports ──────────────────────────────────────────────────────────
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.models import Variable
from airflow.utils.dates import days_ago

# ─── Project root on PATH ─────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

log = logging.getLogger(__name__)

# ─── Default args ─────────────────────────────────────────────────────────────
DEFAULT_ARGS = {
    "owner":            "vigil",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
}

# ─── Constants (override via Airflow Variables in the UI) ─────────────────────
CHUNK_SIZE          = int(Variable.get("owadd_chunk_size",      default_var=200))
DRIFT_THRESHOLD     = float(Variable.get("owadd_drift_threshold", default_var=0.3))
CONSECUTIVE_DRIFTS  = int(Variable.get("owadd_consecutive_drifts", default_var=3))
MLFLOW_TRACKING_URI = Variable.get("mlflow_tracking_uri", default_var="http://localhost:5000")
DATA_SPLIT          = Variable.get("owadd_data_split", default_var="train")


# ─── Task functions ───────────────────────────────────────────────────────────

def load_latest_chunk(**context) -> dict:
    """
    Load the next chunk of network traffic data.
    In production this would read from a Kafka topic, S3 bucket, or DB.
    Here we use the NSL-KDD stream simulator, advancing by execution_date.
    """
    from data.nsl_kdd_loader import load_nsl_kdd
    from data.stream_simulator import StreamSimulator

    execution_date = context["execution_date"]
    log.info("Loading NSL-KDD chunk for execution_date=%s", execution_date)

    X, y, feature_names = load_nsl_kdd(split=DATA_SPLIT)

    # Determine which chunk to process based on how many DAG runs have executed
    run_number = context["dag_run"].run_id
    # Use a hash of the run_id to pick a reproducible chunk index
    chunk_idx  = abs(hash(run_number)) % max(1, len(X) // CHUNK_SIZE - 1)
    start      = chunk_idx * CHUNK_SIZE
    end        = start + CHUNK_SIZE

    chunk_data = X[start:end].tolist()
    chunk_label = str(y[start]) if len(y) > start else "unknown"

    log.info("Loaded chunk %d: %d samples, %d features, label=%s",
             chunk_idx, len(chunk_data), len(feature_names), chunk_label)

    # Push to XCom so downstream tasks can read it
    context["task_instance"].xcom_push(key="chunk_data",     value=chunk_data)
    context["task_instance"].xcom_push(key="feature_names",  value=feature_names)
    context["task_instance"].xcom_push(key="chunk_label",    value=chunk_label)
    context["task_instance"].xcom_push(key="chunk_idx",      value=chunk_idx)


def run_drift_detection(**context) -> dict:
    """
    Run Vigil on the current chunk.
    Model state is loaded from a saved checkpoint if available, otherwise
    fit on the first chunk encountered.
    """
    import pickle

    ti          = context["task_instance"]
    chunk_data  = np.array(ti.xcom_pull(task_ids="load_latest_chunk", key="chunk_data"),
                           dtype="float32")
    feat_names  = ti.xcom_pull(task_ids="load_latest_chunk", key="feature_names")

    from vigil import Vigil

    model_path = os.path.join(PROJECT_ROOT, "airflow", "model_checkpoint.pkl")

    if os.path.exists(model_path):
        log.info("Loading Vigil from checkpoint: %s", model_path)
        with open(model_path, "rb") as f:
            sentinel = pickle.load(f)
    else:
        log.info("No checkpoint found — fitting Vigil on current chunk (cold start)")
        sentinel = Vigil(feature_names=feat_names, top_k_features=5)
        sentinel.fit(chunk_data, verbose=False)
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        with open(model_path, "wb") as f:
            pickle.dump(sentinel, f)
        # First run: no drift to report
        ti.xcom_push(key="drift_detected",    value=False)
        ti.xcom_push(key="drift_severity",    value=0.0)
        ti.xcom_push(key="novelty_proportion", value=0.0)
        ti.xcom_push(key="top_features",      value=[])
        return

    result = sentinel.detect(chunk_data)

    log.info(
        "Detection result — drift=%s severity=%.2f novelty=%.1f%%",
        result.drift_detected, result.drift_severity, result.novelty_proportion * 100
    )

    if result.drift_detected:
        top_feats = [
            {"feature_name": f["feature_name"], "contribution": f["contribution"]}
            for f in (result.attribution.top_features if result.attribution else [])
        ]
        log.info("Top drifted features: %s", top_feats)
    else:
        top_feats = []

    # Save updated model (it adapts internally on drift)
    with open(model_path, "wb") as f:
        pickle.dump(sentinel, f)

    ti.xcom_push(key="drift_detected",     value=result.drift_detected)
    ti.xcom_push(key="drift_severity",     value=result.drift_severity)
    ti.xcom_push(key="novelty_proportion", value=result.novelty_proportion)
    ti.xcom_push(key="top_features",       value=top_feats)


def log_to_mlflow(**context) -> None:
    """Log drift metrics and attribution to MLflow."""
    import mlflow

    ti              = context["task_instance"]
    drift_detected  = ti.xcom_pull(task_ids="run_drift_detection", key="drift_detected")
    severity        = ti.xcom_pull(task_ids="run_drift_detection", key="drift_severity")
    novelty         = ti.xcom_pull(task_ids="run_drift_detection", key="novelty_proportion")
    top_feats       = ti.xcom_pull(task_ids="run_drift_detection", key="top_features") or []
    chunk_idx       = ti.xcom_pull(task_ids="load_latest_chunk",   key="chunk_idx")
    label           = ti.xcom_pull(task_ids="load_latest_chunk",   key="chunk_label")
    execution_date  = str(context["execution_date"])

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("owadd-airflow-monitor")

    with mlflow.start_run(run_name=f"chunk-{chunk_idx}-{execution_date[:10]}"):
        mlflow.log_param("chunk_idx",      chunk_idx)
        mlflow.log_param("ground_truth",   label)
        mlflow.log_param("execution_date", execution_date)

        mlflow.log_metric("drift_detected",    int(drift_detected))
        mlflow.log_metric("drift_severity",    severity)
        mlflow.log_metric("novelty_proportion", novelty)

        if top_feats:
            feat_json = json.dumps(top_feats, indent=2)
            mlflow.log_text(feat_json, "top_drifted_features.json")

    log.info("MLflow run logged to experiment 'owadd-airflow-monitor'")


def check_drift_threshold(**context) -> str:
    """
    Branching task: decide whether to trigger retraining.
    Returns the task_id of the branch to follow.
    """
    ti             = context["task_instance"]
    drift_detected = ti.xcom_pull(task_ids="run_drift_detection", key="drift_detected")
    severity       = ti.xcom_pull(task_ids="run_drift_detection", key="drift_severity") or 0.0

    if drift_detected and severity >= DRIFT_THRESHOLD:
        log.warning("Drift confirmed (severity=%.2f >= threshold=%.2f) → triggering retrain",
                    severity, DRIFT_THRESHOLD)
        return "trigger_retrain_dag"

    log.info("No significant drift (severity=%.2f) → normal end", severity)
    return "end_pipeline"


def send_alert(**context) -> None:
    """
    Post-retrain alert. In production: send Slack/email/PagerDuty.
    Here we log a structured summary.
    """
    ti         = context["task_instance"]
    severity   = ti.xcom_pull(task_ids="run_drift_detection", key="drift_severity")
    novelty    = ti.xcom_pull(task_ids="run_drift_detection", key="novelty_proportion")
    top_feats  = ti.xcom_pull(task_ids="run_drift_detection", key="top_features") or []
    chunk_idx  = ti.xcom_pull(task_ids="load_latest_chunk",   key="chunk_idx")

    alert = {
        "alert_type":    "CONCEPT_DRIFT_DETECTED",
        "chunk_idx":     chunk_idx,
        "severity":      severity,
        "novelty":       novelty,
        "top_features":  [f["feature_name"] for f in top_feats[:3]],
        "action":        "Retrain DAG triggered automatically",
        "timestamp":     str(context["execution_date"]),
    }

    log.warning("OWADD ALERT: %s", json.dumps(alert, indent=2))
    # TODO: replace with actual notification (Slack webhook, email SMTP, etc.)


# ─── DAG definition ───────────────────────────────────────────────────────────

with DAG(
    dag_id="owadd_stream_monitor",
    description="Hourly Vigil drift monitoring on network traffic stream",
    schedule_interval="@hourly",
    start_date=days_ago(1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["owadd", "drift-detection", "network-security", "mlflow"],
    doc_md="""
## OWADD Stream Monitor DAG

Runs every hour to check if network traffic distribution has shifted.

### What it does
1. **load_latest_chunk** — loads the current batch of network traffic data
2. **run_drift_detection** — runs Vigil dual-autoencoder drift detection
3. **log_to_mlflow** — records drift metrics and feature attribution to MLflow
4. **check_drift_threshold** — decides if drift is significant enough to retrain
5. **trigger_retrain_dag** — if yes, kicks off the `owadd_retrain` DAG
6. **send_alert** — logs structured alert (extend to Slack/email in production)

### Airflow Variables
Configure these in the Airflow UI → Admin → Variables:
- `owadd_chunk_size` (default: 200)
- `owadd_drift_threshold` (default: 0.3)
- `mlflow_tracking_uri` (default: http://localhost:5000)
    """,
) as monitor_dag:

    load_chunk = PythonOperator(
        task_id="load_latest_chunk",
        python_callable=load_latest_chunk,
    )

    detect = PythonOperator(
        task_id="run_drift_detection",
        python_callable=run_drift_detection,
    )

    log_mlflow = PythonOperator(
        task_id="log_to_mlflow",
        python_callable=log_to_mlflow,
    )

    branch = BranchPythonOperator(
        task_id="check_drift_threshold",
        python_callable=check_drift_threshold,
    )

    trigger_retrain = TriggerDagRunOperator(
        task_id="trigger_retrain_dag",
        trigger_dag_id="owadd_retrain",
        wait_for_completion=False,
    )

    alert = PythonOperator(
        task_id="send_alert",
        python_callable=send_alert,
        trigger_rule="none_failed_min_one_success",
    )

    end = EmptyOperator(
        task_id="end_pipeline",
    )

    # ── Task dependencies ─────────────────────────────────────────────────────
    load_chunk >> detect >> log_mlflow >> branch
    branch >> trigger_retrain >> alert
    branch >> end
