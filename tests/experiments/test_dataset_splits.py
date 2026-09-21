import pytest

from experiments.datasets.base import DataLeakageError, validate_disjoint_ids


def test_split_validator_rejects_duplicate_row_ids() -> None:
    with pytest.raises(DataLeakageError, match="overlap"):
        validate_disjoint_ids({"train": {"a", "b"}, "test": {"b", "c"}})


def test_split_validator_accepts_disjoint_ids() -> None:
    validate_disjoint_ids({"train": {"a", "b"}, "validation": {"c"}, "test": {"d"}})


def test_audit_report_checks_arrays_and_preserves_source_checksums():
    import numpy as np
    from experiments.datasets.base import DatasetSplit, PreparedDataset
    from experiments.datasets.audit import build_audit_report

    splits = [
        DatasetSplit(
            np.array([[value]], dtype=float), np.array(["normal"]), (str(value),)
        )
        for value in (1, 2, 3)
    ]
    dataset = PreparedDataset(
        *splits,
        ("duration",),
        ("numerical",),
        {"duration": (0,)},
        {"train": "abc", "test": "def"},
        {"test_overlap_removed": 2},
    )
    report = build_audit_report(dataset)
    assert report["checksums"] == {"train": "abc", "test": "def"}
    assert report["splits"]["test"]["rows"] == 1
    assert report["splits"]["test"]["nonfinite_values"] == 0
    assert report["preprocessing_audit"]["test_overlap_removed"] == 2
    splits[2].X[0, 0] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        build_audit_report(dataset)
