# ruff: noqa: PLR2004
import numpy as np
import pytest


@pytest.mark.parametrize("prevalences", [(0.05, 0.05), (None,), (np.nan,), (0,), (1,)])
def test_rejects_duplicate_or_invalid_prevalences_before_reading_evidence(
    tmp_path, prevalences
):
    from experiments.novelty_sensitivity import analyze

    with pytest.raises(ValueError, match="prevalences"):
        analyze(tmp_path / "missing", tmp_path / "output", prevalences=prevalences)


def test_low_fpr_threshold_uses_known_calibration_scores_and_conservative_ties():
    from experiments.novelty_sensitivity import calibration_threshold

    labels = np.array([0] * 100 + [1, 1])
    scores = np.r_[np.arange(100), -1000, 1000]
    threshold = calibration_threshold(labels, scores, target=0.01)
    assert 98 < threshold < 99
    assert np.sum(scores[:100] >= threshold) == 1
    scores[-2:] = [0, 0]
    assert calibration_threshold(labels, scores, target=0.01) == threshold
    assert calibration_threshold(labels, np.zeros(102), target=0.01) > 0
    with pytest.raises(ValueError):
        calibration_threshold([1], [0], target=0.01)
    with pytest.raises(ValueError):
        calibration_threshold(labels, scores, target=1)


def test_saved_score_sensitivity_preserves_freezes_and_rejects_corruption(tmp_path):
    import json

    import pandas as pd

    from experiments.datasets.nsl_kdd import prepare_frames
    from experiments.novelty_development import development_protocol, run_seed
    from experiments.novelty_sensitivity import analyze
    from experiments.provenance import capture_provenance, sha256_file

    data = prepare_frames(
        pd.DataFrame(
            {
                "duration": range(600),
                "label": ["normal"] * 400 + ["attack"] * 200,
            }
        ),
        None,
    )
    protocol = development_protocol(data, n_reference=20, novel_classes=("attack",))
    source = tmp_path / "source"
    provenance = capture_provenance([])
    for seed in (0, 1):
        run_seed(
            protocol,
            preprocessing_id=data.audit["preprocessing_sha256"],
            seed=seed,
            epochs=1,
            output=source,
            provenance=provenance,
        )
    frozen_before = {
        str(p): sha256_file(p) for p in source.glob("evidence/*/freeze.json")
    }
    path = analyze(
        source,
        tmp_path / "analysis",
        expected_seeds=(0, 1),
        n_samples=20,
        prevalences=(0.05, 0.5),
    )
    payload = json.loads(path.read_text())
    assert len(payload["metadata"]["records"]) == 36
    assert frozen_before == {
        str(p): sha256_file(p) for p in source.glob("evidence/*/freeze.json")
    }
    for row in payload["metadata"]["records"]:
        if row["operating_point"] == "calibration_fpr_1pct":
            assert row["calibration_fpr"] <= 0.01
        if row["method"] == "constant" and row["prevalence"] == 0.05:
            if row["operating_point"] == "original_f1":
                assert row["metrics"]["precision"] == 0.05
                assert row["metrics"]["false_positives"] == 19
            else:
                assert row["metrics"]["precision"] is None
                assert row["metrics"]["false_positives"] == 0
    groups = payload["metrics"]["groups"]
    assert all(g["metrics"]["f1"]["n_defined"] == 2 for g in groups)
    next(source.glob("evidence/*/development.npz")).write_bytes(b"bad")
    with pytest.raises(ValueError, match="checksum"):
        analyze(
            source,
            tmp_path / "bad",
            expected_seeds=(0, 1),
            n_samples=20,
            prevalences=(0.05, 0.5),
        )
