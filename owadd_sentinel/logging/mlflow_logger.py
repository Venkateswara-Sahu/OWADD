"""
MLflow Logger
=============
Logs every OWADD Sentinel detection result to MLflow for experiment tracking.

What gets logged per chunk:
  Metrics:
    - drift_detected (0 or 1)
    - drift_severity (float, 0.0–1.0)
    - novelty_proportion (float)
    - n_novel (int)
    - batch_error_mean (float)
    - reference_error_mean (float)
    - error_delta (batch_mean - reference_mean)

  Tags:
    - chunk_id
    - dominant_class (if provided)

  Artifacts (on drift):
    - attribution report as JSON

Usage:
    from owadd_sentinel.logging.mlflow_logger import MLflowLogger

    logger = MLflowLogger(experiment_name="nsl_kdd_stream")
    logger.start_run()

    for chunk in stream:
        result = sentinel.detect(chunk.X)
        logger.log_chunk(result, ground_truth_label=chunk.dominant_class)

    logger.end_run()
"""

import json
from pathlib import Path

import mlflow
import mlflow.pytorch

from owadd_sentinel.sentinel import SentinelResult


class MLflowLogger:
    """
    Logs OWADD Sentinel stream processing results to MLflow.

    Parameters
    ----------
    experiment_name : str
        MLflow experiment name. Creates it if it doesn't exist.
    tracking_uri : str
        MLflow tracking server URI.
        Default: 'mlruns' (local directory).
    run_name : str
        Name for this specific run.
    """

    def __init__(
        self,
        experiment_name: str = "owadd-sentinel",
        tracking_uri: str = "mlruns",
        run_name: str = "stream-run",
    ):
        self.experiment_name = experiment_name
        self.run_name = run_name

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

        self._run = None
        self._drift_count = 0

    def start_run(self, params: dict | None = None) -> "MLflowLogger":
        """
        Start a new MLflow run and log initial parameters.

        Parameters
        ----------
        params : dict, optional
            Hyperparameters to log (e.g. drift_threshold, buffer_size).
        """
        self._run = mlflow.start_run(run_name=self.run_name)
        print(f"[MLflow] Run started: {self._run.info.run_id}")
        print(f"[MLflow] Experiment: {self.experiment_name}")
        print("[MLflow] View at: mlflow ui  (then open http://localhost:5000)")

        if params:
            mlflow.log_params(params)

        return self

    def log_chunk(
        self,
        result: SentinelResult,
        ground_truth_label: str | None = None,
    ) -> None:
        """
        Log metrics for a single processed stream chunk.

        Parameters
        ----------
        result : SentinelResult
            Output from OWADDSentinel.detect().
        ground_truth_label : str, optional
            True dominant class label for this chunk (used as a tag).
        """
        step = result.chunk_id

        # Core metrics
        mlflow.log_metrics(
            {
                "drift_detected": int(result.drift_detected),
                "drift_severity": result.drift_severity,
                "novelty_proportion": result.novelty_proportion,
                "n_novel": float(result.n_novel),
                "batch_error_mean": result.drift_result.batch_error_mean,
                "reference_error_mean": result.drift_result.reference_error_mean,
                "error_delta": (
                    result.drift_result.batch_error_mean
                    - result.drift_result.reference_error_mean
                ),
            },
            step=step,
        )

        # Log drift event details as artifact
        if result.drift_detected:
            self._drift_count += 1
            mlflow.set_tag(f"drift_chunk_{step}", "True")

            if result.attribution:
                report = {
                    "chunk_id": step,
                    "drift_severity": result.drift_severity,
                    "top_drifted_features": result.attribution.top_features,
                }
                report_path = Path(f"drift_report_chunk_{step}.json")
                report_path.write_text(json.dumps(report, indent=2))
                mlflow.log_artifact(str(report_path))
                report_path.unlink()  # clean up local file

        if ground_truth_label:
            mlflow.set_tag(f"chunk_{step}_class", ground_truth_label)

    def log_model(self, sentinel, artifact_path: str = "autoencoder") -> None:
        """
        Save the trained autoencoder A to MLflow as a PyTorch artifact.

        Parameters
        ----------
        sentinel : OWADDSentinel
        artifact_path : str
        """
        if sentinel._autoencoder_A is not None:
            mlflow.pytorch.log_model(
                sentinel._autoencoder_A,
                artifact_path=artifact_path,
            )
            print(f"[MLflow] Autoencoder logged to artifact path: {artifact_path}")

    def end_run(self) -> None:
        """End the current MLflow run and log summary stats."""
        mlflow.log_metric("total_drifts_detected", self._drift_count)
        mlflow.end_run()
        print(f"[MLflow] Run ended. Total drifts detected: {self._drift_count}")
        print("[MLflow] Run UI: mlflow ui  → http://localhost:5000")
