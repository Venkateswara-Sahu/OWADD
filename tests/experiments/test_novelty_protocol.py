# ruff: noqa: PLR2004
# Hand-computed expected counts and thresholds are deliberate test literals.
import json
from dataclasses import replace

import numpy as np
import pytest

from experiments.datasets.base import DatasetSplit


def split(labels, offset):
    return DatasetSplit(
        np.arange(offset, offset + len(labels), dtype=float)[:, None],
        np.array(labels),
        tuple(f"row-{i}" for i in range(offset, offset + len(labels))),
    )


def protocol():
    from experiments.novelty_protocol import make_protocol

    return make_protocol(
        split(["known"] * 4, 0),
        split(["known", "novel", "known", "novel"], 10),
        split(["known", "novel", "known", "novel"], 20),
        known_classes={"known"},
        novel_classes={"novel"},
    )


def test_declared_classes_and_disjoint_identity_are_required():
    from experiments.novelty_protocol import make_protocol

    p = protocol()
    assert p.reference.labels.tolist() == [0, 0, 0, 0]
    assert p.validation.labels.tolist() == [0, 1, 0, 1]
    with pytest.raises(ValueError, match="reference"):
        make_protocol(
            split(["novel"], 0),
            split(["known", "novel"], 10),
            split(["known", "novel"], 20),
            known_classes={"known"},
            novel_classes={"novel"},
        )
    with pytest.raises(ValueError, match="overlap"):
        make_protocol(
            split(["known"], 0),
            split(["known", "novel"], 0),
            split(["known", "novel"], 20),
            known_classes={"known"},
            novel_classes={"novel"},
        )
    with pytest.raises(ValueError, match="undeclared"):
        make_protocol(
            split(["known"], 0),
            split(["other", "novel"], 10),
            split(["known", "novel"], 20),
            known_classes={"known"},
            novel_classes={"novel"},
        )


def test_known_class_must_actually_occur_in_reference():
    from experiments.novelty_protocol import make_protocol

    with pytest.raises(ValueError, match="known classes"):
        make_protocol(
            split(["known"], 0),
            split(["untrained", "novel"], 10),
            split(["untrained", "novel"], 20),
            known_classes={"known", "untrained"},
            novel_classes={"novel"},
        )


def test_changed_protocol_or_validation_sidecar_is_rejected(tmp_path):
    from experiments.novelty_protocol import (
        evaluate_frozen,
        freeze_threshold,
        score_pool,
    )

    p = protocol()
    val = score_pool(p.validation, lambda X: [0.1, 0.8, 0.2, 0.9])
    test = score_pool(p.test, lambda X: [0.1, 0.8, 0.2, 0.9])
    path = tmp_path / "frozen.json"
    freeze_threshold(path, p, val, [0.5], model_id="model")
    changed = replace(p, test=replace(p.test, row_ids=("changed", *p.test.row_ids[1:])))
    with pytest.raises(ValueError, match="protocol"):
        evaluate_frozen(path, changed, test, model_id="model")
    evidence = path.parent / json.loads(path.read_text())["validation_scores"]["file"]
    with evidence.open("ab") as file:
        file.write(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        evaluate_frozen(path, p, test, model_id="model")


def test_freeze_uses_only_bound_validation_evidence_and_reuses_threshold(tmp_path):
    from experiments.novelty_protocol import (
        evaluate_frozen,
        freeze_threshold,
        score_pool,
    )

    p = protocol()
    val = score_pool(p.validation, lambda X: np.array([0.1, 0.8, 0.4, 0.9]))
    test = score_pool(p.test, lambda X: np.array([0.9, 0.1, 0.8, 0.2]))
    path = tmp_path / "frozen.json"
    with pytest.raises(ValueError, match="validation"):
        freeze_threshold(path, p, test, [0.3, 0.5, 0.7], model_id="model-a")
    freeze_threshold(path, p, val, [0.3, 0.5, 0.7], model_id="model-a")
    frozen = json.loads(path.read_text())
    assert frozen["threshold"] == 0.7  # Tied F1/FPR: higher threshold wins.
    result = evaluate_frozen(path, p, test, model_id="model-a")
    assert result.f1 == 0  # Cannot tune on the reversed test scores.
    with pytest.raises(ValueError, match="model"):
        evaluate_frozen(path, p, test, model_id="different-model")
    with pytest.raises(FileExistsError):
        freeze_threshold(path, p, val, [0.1], model_id="model-a")
    frozen["threshold"] = 0.1
    path.write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match="integrity"):
        evaluate_frozen(path, p, test, model_id="model-a")


def test_prevalence_sampling_is_exact_unique_and_deterministic():
    from experiments.novelty_protocol import prevalence_indices

    labels = np.array([0] * 100 + [1] * 100)
    for prevalence, count in [(0.01, 1), (0.05, 5), (0.1, 10), (0.25, 25), (0.5, 50)]:
        indices = prevalence_indices(labels, prevalence, 100, seed=42)
        assert len(set(indices)) == 100
        assert labels[indices].sum() == count
        np.testing.assert_array_equal(
            indices, prevalence_indices(labels, prevalence, 100, seed=42)
        )
    with pytest.raises(ValueError, match="insufficient"):
        prevalence_indices([0, 1], 0.5, 100, seed=42)
    with pytest.raises(ValueError, match="integer"):
        prevalence_indices(labels, 0.01, 10, seed=42)


def test_runner_persists_prevalence_results_and_checks_sidecar_on_resume(tmp_path):
    from experiments.config import ExperimentConfig
    from experiments.novelty_protocol import freeze_threshold, make_protocol, score_pool
    from experiments.runner import run_novelty_evaluation

    p = make_protocol(
        split(["known"] * 20, 0),
        split(["known"] * 100 + ["novel"] * 100, 100),
        split(["known"] * 100 + ["novel"] * 100, 500),
        known_classes={"known"},
        novel_classes={"novel"},
    )
    val = score_pool(p.validation, lambda X: np.r_[np.zeros(100), np.ones(100)])
    test = score_pool(p.test, lambda X: np.r_[np.zeros(100), np.ones(100)])
    frozen = tmp_path / "frozen.json"
    freeze_threshold(frozen, p, val, [0.3, 0.7], model_id="fixture-model")
    config = ExperimentConfig(
        dataset="novelty_fixture",
        method="fixed_fixture_scores",
        seed=42,
        split="test",
        params={"n_prevalence_samples": 100},
    )
    output = tmp_path / "results"
    first = run_novelty_evaluation(config, p, test, frozen, "fixture-model", output)
    assert first.metadata["resumed"] is False
    assert first.metrics["natural"]["n_samples"] == 200
    assert [row["n_novel"] for row in first.metrics["prevalence_grid"]] == [
        1,
        5,
        10,
        25,
        50,
    ]
    assert all(row["metrics"]["f1"] == 1 for row in first.metrics["prevalence_grid"])
    second = run_novelty_evaluation(config, p, test, frozen, "fixture-model", output)
    assert second.metadata["resumed"] is True
    sidecar = next(output.rglob("novelty_scores-*.npz"))
    with sidecar.open("ab") as file:
        file.write(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        run_novelty_evaluation(config, p, test, frozen, "fixture-model", output)


def test_interrupted_freeze_can_retry_without_overwriting_evidence(
    tmp_path, monkeypatch
):
    import experiments.novelty_protocol as module

    p = protocol()
    scores = module.score_pool(p.validation, lambda X: [0.1, 0.8, 0.2, 0.9])
    path = tmp_path / "freeze.json"
    original = module.json.dump

    def fail(*args, **kwargs):
        raise RuntimeError("simulated publication failure")

    monkeypatch.setattr(module.json, "dump", fail)
    with pytest.raises(RuntimeError, match="publication"):
        module.freeze_threshold(path, p, scores, [0.5], model_id="model")
    assert not path.exists()
    monkeypatch.setattr(module.json, "dump", original)
    module.freeze_threshold(path, p, scores, [0.5], model_id="model")
    assert path.exists()


def test_runner_retry_after_interruption_accepts_string_paths(tmp_path, monkeypatch):
    from experiments import runner
    from experiments.config import ExperimentConfig
    from experiments.novelty_protocol import freeze_threshold, make_protocol, score_pool

    p = make_protocol(
        split(["known"] * 20, 0),
        split(["known"] * 100 + ["novel"] * 100, 100),
        split(["known"] * 100 + ["novel"] * 100, 500),
        known_classes={"known"},
        novel_classes={"novel"},
    )
    val = score_pool(p.validation, lambda X: np.r_[np.zeros(100), np.ones(100)])
    test = score_pool(p.test, lambda X: np.r_[np.zeros(100), np.ones(100)])
    path, output = tmp_path / "frozen.json", tmp_path / "results"
    freeze_threshold(path, p, val, [0.5], model_id="model")
    config = ExperimentConfig(
        dataset="fixture",
        method="fixture",
        seed=42,
        split="test",
        params={"n_prevalence_samples": 100},
    )
    original = runner.write_result_atomic

    def fail(*args, **kwargs):
        raise RuntimeError("simulated publication failure")

    monkeypatch.setattr(runner, "write_result_atomic", fail)
    with pytest.raises(RuntimeError, match="publication"):
        runner.run_novelty_evaluation(config, p, test, path, "model", output)
    monkeypatch.setattr(runner, "write_result_atomic", original)
    result = runner.run_novelty_evaluation(
        config, p, test, str(path), "model", str(output)
    )
    assert result.metrics["natural"]["f1"] == 1
