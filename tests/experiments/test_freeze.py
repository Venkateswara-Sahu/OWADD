from dataclasses import replace
import json

import pytest

from experiments.config import ExperimentConfig
from experiments.io import ResultEnvelope
from experiments.provenance import Provenance


def trial(threshold, f1, *, split="validation", manifest="validation-stream"):
    config = ExperimentConfig(
        dataset="nsl_kdd",
        method="vigil",
        seed=42,
        split=split,
        params={"drift_threshold": threshold, "initial_epochs": 5},
    )
    provenance = Provenance(
        "abc",
        False,
        "3.11",
        "windows",
        "cpu",
        16,
        {"numpy": "1"},
        {"train": "a", "test": "b"},
        "now",
    )
    return ResultEnvelope(
        config.canonical_dict(),
        provenance,
        {
            "events": {"event_f1": f1, "true_events": 2, "false_alarms": 1},
            "manifest": {"hash": manifest},
        },
        metadata={"stage": "validation"},
    )


def test_freeze_selects_validation_winner_and_binds_test_checksums(tmp_path):
    from experiments.freeze import freeze_validation_results, load_frozen_config

    path = tmp_path / "frozen.json"
    freeze_validation_results(path, [trial(0.1, 0.5), trial(0.3, 0.8)])
    chosen = load_frozen_config(path, {"train": "a", "test": "b"})
    assert chosen.split == "test"
    assert chosen.params["drift_threshold"] == 0.3
    with pytest.raises(ValueError, match="checksum"):
        load_frozen_config(path, {"train": "a", "test": "changed"})
    with pytest.raises(FileExistsError):
        freeze_validation_results(path, [trial(0.1, 0.9)])


@pytest.mark.parametrize(
    "bad", [trial(0.2, 0.9, split="test"), trial(0.2, 0.9, manifest="other-stream")]
)
def test_freeze_rejects_test_or_unpaired_evidence(tmp_path, bad):
    from experiments.freeze import freeze_validation_results

    with pytest.raises(ValueError):
        freeze_validation_results(tmp_path / "frozen.json", [trial(0.1, 0.5), bad])


def test_frozen_configuration_tampering_is_rejected(tmp_path):
    from experiments.freeze import freeze_validation_results, load_frozen_config

    path = tmp_path / "frozen.json"
    freeze_validation_results(path, [trial(0.1, 0.5)])
    payload = json.loads(path.read_text())
    payload["selected_config"]["params"]["drift_threshold"] = 0.99
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="integrity"):
        load_frozen_config(path, {"train": "a", "test": "b"})


def test_freeze_rejects_empty_and_smoke_evidence(tmp_path):
    from experiments.freeze import freeze_validation_results

    for trials in ([], [replace(trial(0.1, 0.5), metadata={"stage": "smoke_only"})]):
        with pytest.raises(ValueError):
            freeze_validation_results(tmp_path / "frozen.json", trials)
