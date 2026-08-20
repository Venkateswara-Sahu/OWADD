"""
DAG: owadd_retrain
===================
Triggered by owadd_stream_monitor when drift severity crosses threshold.
Retrains OWADD Sentinel on accumulated recent data, evaluates the new model,
and promotes it to production if it passes quality checks.

Schedule: triggered only (not scheduled)
Owner:    owadd-sentinel

Task Graph:
    load_recent_data
          │
          ▼
    retrain_sentinel
          │
          ▼
    evaluate_model
          │
          ▼
    quality_gate ──► (fail) ──► rollback_model
          │                          │
          │ (pass)                   │
          ▼                          ▼
    promote_model              alert_retrain_failed
          │
          ▼
    log_retrain_to_mlflow
"""

from __future__ import annotations

import logging
import os
import sys
import pickle
import shutil
from datetime import timedelta

import numpy as np

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.models import Variable
from airflow.utils.dates import days_ago

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner":            "owadd-sentinel",
    "depends_on_past":  False,
    "email_on_failure": False,
    "retries":          0,
}

MLFLOW_TRACKING_URI  = Variable.get("mlflow_tracking_uri",  default_var="http://localhost:5000")
DATA_SPLIT           = Variable.get("owadd_data_split",     default_var="train")
MIN_QUALITY_SCORE    = float(Variable.get("owadd_min_quality_score", default_var=0.7))

MODEL_CHECKPOINT = os.path.join(PROJECT_ROOT, "airflow", "model_checkpoint.pkl")
MODEL_BACKUP     = os.path.join(PROJECT_ROOT, "airflow", "model_backup.pkl")
MODEL_CANDIDATE  = os.path.join(PROJECT_ROOT, "airflow", "model_candidate.pkl")


# ─── Task functions ───────────────────────────────────────────────────────────

def load_recent_data(**context) -> None:
    """Load recent traffic data for retraining."""
    from data.nsl_kdd_loader import load_nsl_kdd

    log.info("Loading recent NSL-KDD data for retraining...")
    X, y, feature_names = load_nsl_kdd(split=DATA_SPLIT)

    # Use last 20% of data as "recent" — in production this would be a rolling window
    cutoff = int(len(X) * 0.8)
    recent_X = X[cutoff:]
    recent_y = y[cutoff:]

    log.info("Loaded %d recent samples (%d features)", len(recent_X), recent_X.shape[1])

    ti = context["task_instance"]
    ti.xcom_push(key="recent_X",        value=recent_X.tolist())
    ti.xcom_push(key="recent_y",        value=recent_y.tolist())
    ti.xcom_push(key="feature_names",   value=feature_names)
    ti.xcom_push(key="n_samples",       value=len(recent_X))


def retrain_sentinel(**context) -> None:
    """Retrain OWADD Sentinel on recent data."""
    from owadd_sentinel import OWADDSentinel

    ti          = context["task_instance"]
    recent_X    = np.array(ti.xcom_pull(task_ids="load_recent_data", key="recent_X"),
                           dtype="float32")
    feat_names  = ti.xcom_pull(task_ids="load_recent_data", key="feature_names")

    log.info("Retraining OWADD Sentinel on %d samples...", len(recent_X))

    # Back up current production model before overwriting
    if os.path.exists(MODEL_CHECKPOINT):
        shutil.copy(MODEL_CHECKPOINT, MODEL_BACKUP)
        log.info("Production model backed up to %s", MODEL_BACKUP)

    # Fit new candidate model
    candidate = OWADDSentinel(
        feature_names=feat_names,
        top_k_features=5,
        buffer_size=1000,
        initial_epochs=400,
    )

    # Use first 70% for training, rest for internal eval
    split = int(len(recent_X) * 0.7)
    candidate.fit(recent_X[:split], verbose=False)

    os.makedirs(os.path.dirname(MODEL_CANDIDATE), exist_ok=True)
    with open(MODEL_CANDIDATE, "wb") as f:
        pickle.dump(candidate, f)

    # Stash eval data for quality gate
    ti.xcom_push(key="eval_X", value=recent_X[split:].tolist())
    log.info("Candidate model saved to %s", MODEL_CANDIDATE)


def evaluate_model(**context) -> None:
    """
    Evaluate the candidate model.
    Quality metric: what fraction of stable chunks does the model correctly
    classify as non-drifted (false-positive rate on stable data).
    """
    ti     = context["task_instance"]
    eval_X = np.array(ti.xcom_pull(task_ids="retrain_sentinel", key="eval_X"),
                      dtype="float32")

    with open(MODEL_CANDIDATE, "rb") as f:
        candidate = pickle.load(f)

    chunk_size = 100
    stable_count  = 0
    correct_count = 0

    for i in range(0, len(eval_X) - chunk_size, chunk_size):
        chunk = eval_X[i:i + chunk_size]
        result = candidate.detect(chunk)
        stable_count  += 1
        if not result.drift_detected:
            correct_count += 1

    quality_score = correct_count / max(stable_count, 1)
    log.info("Model quality score (true-negative rate): %.3f (threshold=%.2f)",
             quality_score, MIN_QUALITY_SCORE)

    context["task_instance"].xcom_push(key="quality_score", value=quality_score)


def quality_gate(**context) -> str:
    """Branch: promote if quality passes, rollback if not."""
    ti            = context["task_instance"]
    quality_score = ti.xcom_pull(task_ids="evaluate_model", key="quality_score") or 0.0

    if quality_score >= MIN_QUALITY_SCORE:
        log.info("Quality gate PASSED (%.3f >= %.2f)", quality_score, MIN_QUALITY_SCORE)
        return "promote_model"
    else:
        log.warning("Quality gate FAILED (%.3f < %.2f) — rolling back", quality_score, MIN_QUALITY_SCORE)
        return "rollback_model"


def promote_model(**context) -> None:
    """Replace production model with the validated candidate."""
    shutil.copy(MODEL_CANDIDATE, MODEL_CHECKPOINT)
    os.remove(MODEL_CANDIDATE)
    log.info("Candidate model promoted to production: %s", MODEL_CHECKPOINT)


def rollback_model(**context) -> None:
    """Restore backup model if candidate fails quality gate."""
    if os.path.exists(MODEL_BACKUP):
        shutil.copy(MODEL_BACKUP, MODEL_CHECKPOINT)
        log.warning("Rolled back to backup model: %s", MODEL_BACKUP)
    else:
        log.error("No backup model found — keeping existing checkpoint")


def log_retrain_to_mlflow(**context) -> None:
    """Log retraining run to MLflow."""
    import mlflow

    ti            = context["task_instance"]
    quality_score = ti.xcom_pull(task_ids="evaluate_model", key="quality_score") or 0.0
    n_samples     = ti.xcom_pull(task_ids="load_recent_data", key="n_samples") or 0

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("owadd-retrain-runs")

    with mlflow.start_run(run_name=f"retrain-{context['execution_date'].date()}"):
        mlflow.log_param("trigger",      "drift_detected")
        mlflow.log_param("data_split",   DATA_SPLIT)
        mlflow.log_param("n_samples",    n_samples)
        mlflow.log_metric("quality_score", quality_score)
        mlflow.log_metric("promoted",    1.0 if quality_score >= MIN_QUALITY_SCORE else 0.0)

        if os.path.exists(MODEL_CHECKPOINT):
            mlflow.log_artifact(MODEL_CHECKPOINT, artifact_path="model")

    log.info("Retrain run logged to MLflow experiment 'owadd-retrain-runs'")


def alert_retrain_failed(**context) -> None:
    """Alert when retraining fails quality gate."""
    ti            = context["task_instance"]
    quality_score = ti.xcom_pull(task_ids="evaluate_model", key="quality_score") or 0.0
    log.error(
        "OWADD RETRAIN FAILED: quality_score=%.3f below threshold=%.2f. "
        "Production model unchanged. Manual review required.",
        quality_score, MIN_QUALITY_SCORE
    )
    # TODO: Slack/email/PagerDuty alert here


# ─── DAG definition ───────────────────────────────────────────────────────────

with DAG(
    dag_id="owadd_retrain",
    description="Triggered retraining of OWADD Sentinel when drift is detected",
    schedule_interval=None,     # triggered only — never runs on a schedule
    start_date=days_ago(1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["owadd", "retraining", "mlops", "mlflow"],
    doc_md="""
## OWADD Retrain DAG

Triggered automatically by `owadd_stream_monitor` when drift severity exceeds threshold.

### Pipeline
1. Load recent 20% of NSL-KDD data (simulates rolling window in production)
2. Retrain OWADD Sentinel from scratch on this data
3. Evaluate on held-out stable data (measures false-positive rate)
4. **Quality gate**: promote if score ≥ threshold, rollback otherwise
5. Log everything to MLflow

### To trigger manually
```bash
airflow dags trigger owadd_retrain
```
    """,
) as retrain_dag:

    load_data = PythonOperator(
        task_id="load_recent_data",
        python_callable=load_recent_data,
    )

    retrain = PythonOperator(
        task_id="retrain_sentinel",
        python_callable=retrain_sentinel,
    )

    evaluate = PythonOperator(
        task_id="evaluate_model",
        python_callable=evaluate_model,
    )

    gate = BranchPythonOperator(
        task_id="quality_gate",
        python_callable=quality_gate,
    )

    promote = PythonOperator(
        task_id="promote_model",
        python_callable=promote_model,
    )

    rollback = PythonOperator(
        task_id="rollback_model",
        python_callable=rollback_model,
    )

    mlflow_log = PythonOperator(
        task_id="log_retrain_to_mlflow",
        python_callable=log_retrain_to_mlflow,
        trigger_rule="none_failed_min_one_success",
    )

    alert_failed = PythonOperator(
        task_id="alert_retrain_failed",
        python_callable=alert_retrain_failed,
    )

    # ── Task dependencies ─────────────────────────────────────────────────────
    load_data >> retrain >> evaluate >> gate
    gate >> promote >> mlflow_log
    gate >> rollback >> alert_failed
