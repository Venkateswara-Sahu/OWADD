import numpy as np
import pandas as pd
import pytest

from experiments.config import ExperimentConfig
from experiments.datasets.nsl_kdd import prepare_frames
from experiments.provenance import capture_provenance


def test_cli_test_mode_refuses_missing_frozen_manifest(tmp_path, capsys):
    from experiments.cli import main

    config = tmp_path / "config.yaml"
    config.write_text("dataset: nsl_kdd\nmethod: vigil\nseed: 42\n")
    status = main(
        [
            "run",
            "--config",
            str(config),
            "--output",
            str(tmp_path / "results"),
            "--mode",
            "test",
            "--train",
            str(tmp_path / "train"),
            "--test",
            str(tmp_path / "test"),
            "--frozen",
            str(tmp_path / "frozen.json"),
        ]
    )
    assert status == 1
    assert "frozen manifest required" in capsys.readouterr().err
    assert not (tmp_path / "results").exists()


def test_validation_trial_runs_without_a_test_pool(tmp_path):
    from experiments.network import run_network_trial

    rng = np.random.default_rng(42)
    train = pd.DataFrame(
        {
            "duration": rng.uniform(size=1000),
            "bytes": rng.uniform(size=1000),
            "label": ["normal"] * 800 + ["attack"] * 200,
        }
    )
    prepared = prepare_frames(train, None)
    config = ExperimentConfig(
        dataset="nsl_kdd",
        method="vigil",
        seed=42,
        split="validation",
        chunk_size=10,
        tolerance_chunks=1,
        params={
            "n_reference": 40,
            "initial_epochs": 1,
            "interval_chunks": 3,
            "attack_classes": ["attack"],
            "drift_threshold": 0.3,
        },
    )
    result = run_network_trial(config, prepared, capture_provenance([]), tmp_path)
    assert result.metadata["stage"] == "validation"
    assert result.metrics["events"]["true_events"] == 2
    assert result.metrics["stream_rows"] == result.metrics["unique_stream_rows"] == 90
    assert result.metrics["audit"]["test_loaded"] is False
    assert 0 <= result.metrics["primary"] <= 1


def test_test_mode_requires_freeze_before_loading_datasets(tmp_path):
    from experiments.network import run_nsl_kdd_mode

    config = ExperimentConfig(dataset="nsl_kdd", method="vigil", seed=42)
    with pytest.raises(FileNotFoundError, match="frozen"):
        run_nsl_kdd_mode(
            config,
            tmp_path,
            train_path=tmp_path / "missing-train",
            test_path=tmp_path / "missing-test",
            mode="test",
            frozen_path=tmp_path / "frozen.json",
        )


def test_tune_freeze_test_roundtrip_and_changed_data_rejection(tmp_path):
    from data.nsl_kdd_loader import COLUMN_NAMES
    from experiments.network import run_nsl_kdd_mode

    paths = []
    for name, size, offset in (("train", 1000, 0), ("test", 120, 10000)):
        frame = pd.DataFrame(0, index=range(size), columns=COLUMN_NAMES)
        frame["protocol_type"] = "tcp"
        frame["service"] = "http"
        frame["flag"] = "SF"
        frame["duration"] = np.arange(size) + offset
        frame["src_bytes"] = np.random.default_rng(offset).uniform(size=size)
        frame["label"] = ["normal"] * (size * 4 // 5) + ["neptune"] * (size // 5)
        path = tmp_path / name
        frame.to_csv(path, header=False, index=False)
        paths.append(path)
    config = ExperimentConfig(
        dataset="nsl_kdd",
        method="vigil",
        seed=42,
        chunk_size=10,
        tolerance_chunks=1,
        params={
            "n_reference": 40,
            "initial_epochs": 1,
            "interval_chunks": 3,
            "attack_classes": ["neptune"],
            "drift_threshold": 0.3,
        },
    )
    kwargs = dict(
        train_path=paths[0], test_path=paths[1], frozen_path=tmp_path / "frozen.json"
    )
    trials = run_nsl_kdd_mode(
        config, tmp_path / "results", mode="tune", thresholds=(0.1, 0.3), **kwargs
    )
    assert all(not result.metrics["audit"]["test_loaded"] for result in trials)
    test = run_nsl_kdd_mode(config, tmp_path / "results", mode="test", **kwargs)[0]
    assert test.metadata["stage"] == "test"
    assert test.metrics["audit"]["test_loaded"] is True
    assert test.metrics["manifest"]["hash"] != trials[0].metrics["manifest"]["hash"]
    paths[1].write_text(paths[1].read_text() + "\n")
    with pytest.raises(ValueError, match="checksum"):
        run_nsl_kdd_mode(config, tmp_path / "results", mode="test", **kwargs)
