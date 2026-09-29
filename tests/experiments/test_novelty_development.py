# ruff: noqa: PLR2004
import numpy as np
import pandas as pd
import pytest

from experiments.datasets.nsl_kdd import prepare_frames


def prepared():
    return prepare_frames(
        pd.DataFrame(
            {"duration": range(200), "label": ["normal"] * 140 + ["attack"] * 60}
        ),
        None,
        seed=42,
    )


def test_development_pools_are_fixed_disjoint_and_exclude_official_test():
    from experiments.novelty_development import development_protocol

    data = prepared()
    p = development_protocol(data, n_reference=20, novel_classes=("attack",))
    repeat = development_protocol(data, n_reference=20, novel_classes=("attack",))
    assert p.identity == repeat.identity
    assert len(p.reference.X) == 20
    assert set(p.reference.original_labels) == {"normal"}
    assert sum(p.validation.labels) == 30
    assert sum(p.test.labels) == 30
    assert set(p.validation.row_ids) | set(p.test.row_ids) == set(
        data.validation.row_ids
    )
    assert not set(p.reference.row_ids) & (
        set(p.validation.row_ids) | set(p.test.row_ids)
    )
    with pytest.raises(ValueError, match="reference"):
        development_protocol(data, n_reference=1000, novel_classes=("attack",))
    with pytest.raises(ValueError, match="declared"):
        development_protocol(data, n_reference=20, novel_classes=("other",))


def test_seed_runs_real_families_freezes_threshold_and_checks_resume(tmp_path):
    import torch

    from experiments.novelty_development import development_protocol, run_seed
    from experiments.provenance import capture_provenance

    data = prepared()
    p = development_protocol(data, n_reference=20, novel_classes=("attack",))
    provenance = capture_provenance([])
    options = dict(
        preprocessing_id=data.audit["preprocessing_sha256"],
        seed=0,
        epochs=1,
        output=tmp_path,
        provenance=provenance,
    )
    rng_before = torch.get_rng_state().clone()
    threads_before = torch.get_num_threads()
    results = run_seed(p, **options)
    assert torch.equal(torch.get_rng_state(), rng_before)
    assert torch.get_num_threads() == threads_before
    assert set(results) == {"vigil_kde", "isolation_forest", "constant"}
    for result in results.values():
        assert result.config["split"] == "validation"
        assert result.metadata["evaluation_scope"] == "development_holdout"
        assert result.metrics["n_samples"] == len(p.test.X)
        assert result.metadata["threshold_selected_on"] == "calibration"
    assert results["constant"].metrics["auroc"] == 0.5
    assert results["constant"].metrics["average_precision"] == np.mean(p.test.labels)
    assert run_seed(p, **options) == results
    evidence = tmp_path / results["vigil_kde"].metadata["evidence_dir"]
    (evidence / "development.npz").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        run_seed(p, **options)


def test_summary_requires_all_paired_seeds_and_matches_known_means():
    from dataclasses import replace

    from experiments.io import ResultEnvelope
    from experiments.novelty_development import summarize
    from experiments.provenance import capture_provenance

    provenance = capture_provenance([])
    records = []
    for seed in (0, 1):
        for method, score in (
            ("vigil_kde", 0.8),
            ("isolation_forest", 0.6),
            ("constant", 0.5),
        ):
            records.append(
                ResultEnvelope(
                    config={"method": method, "seed": seed, "split": "validation"},
                    provenance=provenance,
                    metrics={
                        name: score
                        for name in (
                            "average_precision",
                            "auroc",
                            "precision",
                            "recall",
                            "f1",
                            "false_positive_rate",
                        )
                    },
                    metadata={"evaluation_scope": "development_holdout"},
                )
            )
    summary = summarize(records, expected_seeds=(0, 1))
    assert summary["methods"]["vigil_kde"]["f1"]["mean"] == 0.8
    assert summary["methods"]["vigil_kde"]["f1"]["ci95"] == [0.8, 0.8]
    assert summary["paired_vigil_minus_isolation_forest"]["average_precision"][
        "mean"
    ] == pytest.approx(0.2)
    with pytest.raises(ValueError, match="complete"):
        summarize(records[:-1], expected_seeds=(0, 1))
    with pytest.raises(ValueError, match="complete"):
        summarize(records + records[:1], expected_seeds=(0, 1))
    records[0] = replace(records[0], provenance=replace(provenance, git_commit="other"))
    with pytest.raises(ValueError, match="provenance"):
        summarize(records, expected_seeds=(0, 1))


def test_training_file_only_pilot_records_population_and_summary(tmp_path):
    import json

    from data.nsl_kdd_loader import COLUMN_NAMES
    from experiments.novelty_development import run_pilot

    frame = pd.DataFrame(np.zeros((120, len(COLUMN_NAMES))), columns=COLUMN_NAMES)
    frame["duration"] = np.arange(120)
    frame["protocol_type"] = "tcp"
    frame["service"] = "http"
    frame["flag"] = "SF"
    frame["label"] = ["normal"] * 80 + ["attack"] * 40
    train = tmp_path / "train.txt"
    frame.to_csv(train, index=False, header=False)
    path = run_pilot(
        train,
        tmp_path / "results",
        seeds=(0, 1),
        epochs=1,
        n_reference=20,
        novel_classes=("attack",),
    )
    payload = json.loads(path.read_text())
    assert payload["metrics"]["methods"]["constant"]["auroc"]["mean"] == 0.5
    assert payload["metadata"]["official_test_loaded"] is False
    assert payload["metadata"]["source_audit"]["test_loaded"] is False
    assert payload["metadata"]["source_audit"]["train_duplicates_removed"] == 0
    assert payload["metadata"]["population"]["reference"]["n"] == 20
    assert payload["metrics"]["methods"]["vigil_kde"]["f1"]["n"] == 2
    assert path.with_suffix(".complete").exists()
    assert (
        run_pilot(
            train,
            tmp_path / "results",
            seeds=(0, 1),
            epochs=1,
            n_reference=20,
            novel_classes=("attack",),
        )
        == path
    )
