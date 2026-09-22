import json
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest


def archive_fixture(
    tmp_path,
    *,
    bad_time=False,
    bad_schema=False,
    bad_category=False,
    bad_monday=False,
    empty_day=False,
    nonfinite=False,
    earlier_duplicate=False,
):
    archive = tmp_path / "source.zip"
    with ZipFile(archive, "w") as zipped:
        for day, date, values in [
            ("monday", 3, [10, 0, 10]),
            ("tuesday", 4, [20, 0, 30]),
            ("wednesday", 5, [40, 50]),
            ("thursday", 6, [60]),
            ("friday", 7, [70]),
        ]:
            frame = pd.DataFrame(
                {
                    "id": range(len(values)),
                    "Flow ID": ["x"] * len(values),
                    "Src IP": ["a"] * len(values),
                    "Dst IP": ["b"] * len(values),
                    "Timestamp": [
                        f"2017-07-{date:02d} 14:00:0{i}" for i in range(len(values))
                    ],
                    "Duration": values,
                    "Label": ["BENIGN"] * len(values),
                    "Attempted Category": [-1] * len(values),
                }
            )
            if day == "monday":
                frame["Timestamp"] = [
                    "2017-07-03 14:00:02",
                    "2017-07-03 14:00:01",
                    "2017-07-03 14:00:03",
                ]
            if day == "tuesday":
                frame.loc[0, ["Label", "Attempted Category"]] = [
                    "New attack - Attempted",
                    0,
                ]
                frame.loc[2, "Label"] = "New attack"
            if bad_time and day == "friday":
                frame.loc[0, "Timestamp"] = "7/7/2017 1:00"
            if bad_schema and day == "friday":
                frame = frame.rename(columns={"Duration": "Other"})
            if bad_category and day == "tuesday":
                frame.loc[0, "Attempted Category"] = -1
            if bad_monday and day == "monday":
                frame.loc[0, "Label"] = "Attack"
            if empty_day and day == "friday":
                frame["Duration"] = np.inf
            if nonfinite and day == "monday":
                frame["Duration"] = frame["Duration"].astype(float)
                frame.loc[2, "Duration"] = np.inf
            if earlier_duplicate and day == "monday":
                frame.loc[2, "Timestamp"] = "2017-07-03 14:00:00"
            zipped.writestr(day + ".csv", frame.to_csv(index=False))
    return archive


def test_preparation_is_sorted_train_only_and_disjoint(tmp_path):
    from experiments.datasets.cicids2017_improved import prepare_archive

    source = archive_fixture(tmp_path)
    output = tmp_path / "prepared"
    report = prepare_archive(source, output, read_chunk_rows=1)
    monday = np.load(output / "monday.X.npy")
    tuesday = np.load(output / "tuesday.X.npy")
    np.testing.assert_allclose(monday[:, 0], [0, 1])
    np.testing.assert_allclose(
        tuesday[:, 0], [2, 3]
    )  # Test/validation never fit scale.
    assert report["feature_names"] == ["Duration"]
    assert report["days"]["monday"]["duplicates_removed"] == 1
    assert report["days"]["tuesday"]["duplicates_removed"] == 1
    assert report["max_read_chunk_rows"] == 1
    all_ids = set()
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
        metadata = pd.read_csv(output / f"{day}.metadata.csv")
        assert metadata.timestamp_ns.is_monotonic_increasing
        assert not all_ids.intersection(metadata.row_id)
        all_ids.update(metadata.row_id)
    metadata = pd.read_csv(output / "tuesday.metadata.csv")
    assert metadata.label.tolist() == ["BENIGN", "New attack"]
    assert metadata.original_label.tolist() == ["New attack - Attempted", "New attack"]
    assert json.loads((output / "manifest.json").read_text())["complete"] is True
    with pytest.raises(FileExistsError):
        prepare_archive(source, output)


@pytest.mark.parametrize(
    "option", ["bad_time", "bad_schema", "bad_category", "bad_monday", "empty_day"]
)
def test_invalid_source_never_publishes_complete_manifest(tmp_path, option):
    from experiments.datasets.cicids2017_improved import prepare_archive

    source = archive_fixture(tmp_path, **{option: True})
    output = tmp_path / "prepared"
    with pytest.raises(ValueError):
        prepare_archive(source, output, read_chunk_rows=2)
    assert not (output / "manifest.json").exists()


def test_nonfinite_exclusion_and_chunk_size_do_not_change_training_scale(tmp_path):
    from experiments.datasets.cicids2017_improved import prepare_archive

    source = archive_fixture(tmp_path, nonfinite=True)
    left = prepare_archive(source, tmp_path / "one", read_chunk_rows=1)
    right = prepare_archive(source, tmp_path / "many", read_chunk_rows=100)
    assert left["days"]["monday"]["nonfinite_removed"] == 1
    assert left["scaler"]["data_min"] == [0.0]
    assert left["scaler"]["data_max"] == [10.0]
    assert left["artifacts"] == right["artifacts"]


def test_prepare_cli_records_protocol_and_checksums(tmp_path):
    from experiments.cli import main

    archive = archive_fixture(tmp_path)
    config = tmp_path / "prepare.yaml"
    config.write_text(
        "dataset: cicids2017_improved_cns2022\nread_chunk_rows: 2\nattempted_policy: benign\n"
    )
    output = tmp_path / "prepared"
    assert (
        main(
            [
                "prepare",
                "--config",
                str(config),
                "--archive",
                str(archive),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    report = json.loads((output / "manifest.json").read_text())
    assert report["attempted_policy"] == "benign"
    assert len(report["artifacts"]) == 10
    assert report["split_days"] == {
        "reference": ["monday"],
        "validation": ["tuesday"],
        "test": ["wednesday", "thursday", "friday"],
    }


def test_cache_reader_is_bounded_and_rejects_tampering(tmp_path):
    from experiments.datasets.cicids2017_improved import (
        prepare_archive,
        iter_prepared_day,
    )

    source = archive_fixture(tmp_path)
    output = tmp_path / "prepared"
    prepare_archive(source, output, read_chunk_rows=2)
    chunks = list(iter_prepared_day(output, "tuesday", chunk_rows=1))
    assert [chunk[0].shape for chunk in chunks] == [(1, 1), (1, 1)]
    assert [chunk[1].label.iloc[0] for chunk in chunks] == ["BENIGN", "New attack"]
    with (output / "tuesday.metadata.csv").open("a") as stream:
        stream.write("tampered\n")
    with pytest.raises(ValueError, match="checksum"):
        list(iter_prepared_day(output, "tuesday"))


def test_duplicate_retains_earliest_timestamp_not_first_export_position(tmp_path):
    from experiments.datasets.cicids2017_improved import prepare_archive

    source = archive_fixture(tmp_path, earlier_duplicate=True)
    output = tmp_path / "prepared"
    prepare_archive(source, output, read_chunk_rows=1)
    np.testing.assert_allclose(np.load(output / "monday.X.npy")[:, 0], [1, 0])
