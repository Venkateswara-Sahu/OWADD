from pathlib import Path
import pytest

from experiments.config import ExperimentConfig
from experiments.runner import run_experiment


def test_smoke_run_is_resumable(tmp_path: Path) -> None:
    config = ExperimentConfig.from_yaml(Path("experiments/configs/smoke.yaml"))

    first = run_experiment(config, tmp_path)
    second = run_experiment(config, tmp_path)

    assert first.result_id == second.result_id
    assert first.metadata["resumed"] is False
    assert second.metadata["resumed"] is True
    assert "attribution" in first.metrics
    assert "events" in first.metrics


def test_failed_run_has_no_completion_marker(tmp_path: Path) -> None:
    config = ExperimentConfig(dataset="unsupported", method="vigil", seed=1, params={})

    try:
        run_experiment(config, tmp_path)
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported dataset should fail")

    assert not list(tmp_path.rglob("*.complete"))
    assert list(tmp_path.rglob("failure.json"))


def test_runner_output_can_be_aggregated(tmp_path: Path) -> None:
    from experiments.aggregate import aggregate_results

    config = ExperimentConfig.from_yaml(Path("experiments/configs/smoke.yaml"))
    run_experiment(config, tmp_path)
    summary = aggregate_results(tmp_path, {"vigil"}, {42})
    assert len(summary) == 1
    assert summary.iloc[0]["count"] == 1


def test_runner_does_not_silently_label_vigil_as_another_method(tmp_path):
    config = ExperimentConfig(dataset="synthetic", method="ks", seed=42)
    with pytest.raises(ValueError, match="unsupported method"):
        run_experiment(config, tmp_path)
    assert not list(tmp_path.rglob("*.complete"))
