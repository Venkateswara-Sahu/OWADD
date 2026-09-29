import pandas as pd
import pytest


def test_empty_csv_padding_is_not_a_flow_or_clock_failure(tmp_path):
    from experiments.datasets.cicids2017 import audit_files

    path = tmp_path / "Thursday.csv"
    pd.DataFrame(
        {
            "Timestamp": ["6/7/2017 09:00", "", ""],
            "Duration": ["1", "", ""],
            "Label": ["BENIGN", "", ""],
        }
    ).to_csv(path, index=False)
    record = audit_files([path], read_chunk_rows=1, work_dir=tmp_path / "audit")[
        "files"
    ][0]
    assert record["raw_rows"] == 3
    assert record["empty_padding_rows"] == 2
    assert record["retained_rows"] == 1
    assert record["duplicate_rows"] == 0
    assert record["timestamp_parse_failures"] == record["missing_labels"] == 0


def test_incremental_audit_counts_invalid_duplicates_and_normalizes_headers(tmp_path):
    from experiments.datasets.cicids2017 import audit_files

    path = tmp_path / "Monday.csv"
    pd.DataFrame(
        {
            " Timestamp": ["03/07/2017 09:00:00"] * 5,
            " Flow Duration": [1, 1, "Infinity", "NaN", 2],
            " Label": [" BENIGN "] * 4 + ["Unseen label"],
        }
    ).to_csv(path, index=False)
    result = audit_files([path], read_chunk_rows=2, work_dir=tmp_path / "audit")
    record = result["files"][0]
    assert record["raw_rows"] == 5
    assert record["duplicate_rows"] == 1
    assert record["nonfinite_rows"] == 2
    assert record["retained_rows"] == 2
    assert record["label_counts"] == {"BENIGN": 4, "Unseen label": 1}
    assert record["max_chunk_rows"] == 2
    assert result["feature_columns"] == ["Flow Duration"]


def test_audit_flags_clock_ambiguity_and_disorder_without_repairing(tmp_path):
    from experiments.datasets.cicids2017 import audit_files

    path = tmp_path / "Tuesday.csv"
    pd.DataFrame(
        {
            "Timestamp": ["4/7/2017 11:59", "4/7/2017 1:00"],
            "Flow Duration": [1, 2],
            "Label": ["BENIGN", "Attack"],
        }
    ).to_csv(path, index=False)
    result = audit_files([path], read_chunk_rows=1, work_dir=tmp_path / "audit")
    record = result["files"][0]
    assert record["backward_timestamp_steps"] == 1
    assert record["ambiguous_early_hour_rows"] == 1
    assert result["ready_for_chronological_benchmark"] is False


def test_audit_rejects_missing_timestamp(tmp_path):
    from experiments.datasets.cicids2017 import audit_files

    path = tmp_path / "missing.csv"
    pd.DataFrame({"Flow Duration": [1], "Label": ["BENIGN"]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Timestamp"):
        audit_files([path], read_chunk_rows=2, work_dir=tmp_path / "audit")


def test_audit_flags_bad_timestamp_and_schema_mismatch(tmp_path):
    from experiments.datasets.cicids2017 import audit_files

    paths = []
    for name, feature in (("Monday", "Duration"), ("Tuesday", "Other")):
        path = tmp_path / f"{name}.csv"
        pd.DataFrame(
            {"Timestamp": ["invalid"], feature: [1], "Label": ["BENIGN"]}
        ).to_csv(path, index=False)
        paths.append(path)
    result = audit_files(paths, read_chunk_rows=2, work_dir=tmp_path / "audit")
    assert result["files"][0]["timestamp_parse_failures"] == 1
    assert result["files"][1]["schema_matches_reference"] is False
    assert not result["ready_for_chronological_benchmark"]
