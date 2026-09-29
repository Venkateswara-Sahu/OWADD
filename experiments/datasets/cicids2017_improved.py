"""Disk-backed, retrospective chronological preparation of the CNS2022 variant."""

from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from zipfile import ZipFile

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from experiments.provenance import sha256_file, capture_provenance

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")
DROP = {
    "id",
    "Flow ID",
    "Src IP",
    "Dst IP",
    "Src Port",
    "Timestamp",
    "Label",
    "Attempted Category",
}
REQUIRED = {
    "id",
    "Flow ID",
    "Src IP",
    "Dst IP",
    "Timestamp",
    "Label",
    "Attempted Category",
}


def prepare_archive(archive: Path, output: Path, *, read_chunk_rows=25000):
    """Create immutable day caches; completion manifest is written only on success.

    Attempted attacks map to BENIGN, with original metadata preserved. Feature
    duplicates retain the earliest timestamp (day order wins across partitions).
    Scaling fits only retained Monday rows. No random rebalancing or clipping.
    """
    archive, output = Path(archive), Path(output)
    if read_chunk_rows < 1:
        raise ValueError("positive read_chunk_rows required")
    output.mkdir(parents=True, exist_ok=False)
    digest = sha256_file(archive)
    report = {
        "dataset": "cicids2017_improved_cns2022",
        "archive_sha256": digest,
        "complete": False,
        "read_chunk_rows": read_chunk_rows,
        "max_read_chunk_rows": 0,
        "drop_columns": sorted(DROP),
        "attempted_policy": "benign",
        "ordering": "retrospective flow-start timestamp; not live feature availability",
        "timezone": "naive source clock; UTC interpretation not independently verified",
        "identity": "SHA256 of canonical float64 feature vector, excluding label and identifiers",
        "duplicate_policy": "earliest day then earliest timestamp then source row; no future removal of past rows",
        "numeric_policy": "exclude nonfinite rows; Monday-only minmax; no clipping or imputation",
        "days": {},
    }
    report["split_days"] = {
        "reference": ["monday"],
        "validation": ["tuesday"],
        "test": ["wednesday", "thursday", "friday"],
    }
    report["provenance"] = capture_provenance([]).canonical_dict()
    database = sqlite3.connect(output / "identities.sqlite")
    database.execute("PRAGMA cache_size=-32768")
    database.execute("PRAGMA temp_store=FILE")
    database.execute(
        "CREATE TABLE rows (identity BLOB PRIMARY KEY, day INTEGER, timestamp INTEGER, sequence INTEGER, features BLOB, label TEXT, original TEXT, category INTEGER) WITHOUT ROWID"
    )
    schema = features = None
    try:
        with ZipFile(archive) as zipped:
            names = zipped.namelist()
            if sorted(names) != sorted(day + ".csv" for day in DAYS):
                raise ValueError("archive must contain exactly five named weekday CSVs")
            for day_index, day in enumerate(DAYS):
                counts = {
                    "raw_rows": 0,
                    "nonfinite_removed": 0,
                    "label_conflicts_observed": 0,
                }
                report["days"][day] = counts
                with zipped.open(day + ".csv") as source:
                    for chunk in pd.read_csv(
                        source,
                        chunksize=read_chunk_rows,
                        dtype=str,
                        keep_default_na=False,
                    ):
                        chunk.columns = chunk.columns.str.strip()
                        if chunk.columns.duplicated().any() or not REQUIRED.issubset(
                            chunk.columns
                        ):
                            raise ValueError(
                                "missing required or duplicate normalized columns"
                            )
                        if schema is None:
                            schema = list(chunk.columns)
                            features = [name for name in schema if name not in DROP]
                            if not features:
                                raise ValueError("no model features")
                        if list(chunk.columns) != schema:
                            raise ValueError("weekday schema mismatch")
                        report["max_read_chunk_rows"] = max(
                            report["max_read_chunk_rows"], len(chunk)
                        )
                        sequence_start = counts["raw_rows"]
                        counts["raw_rows"] += len(chunk)
                        raw = chunk["Timestamp"].str.strip()
                        if not raw.str.fullmatch(
                            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,9})?"
                        ).all():
                            raise ValueError("non-ISO timestamp")
                        times = pd.to_datetime(raw, format="ISO8601", errors="coerce")
                        if (
                            times.isna().any()
                            or not times.dt.strftime("%Y-%m-%d")
                            .eq(f"2017-07-{day_index+3:02d}")
                            .all()
                        ):
                            raise ValueError("invalid timestamp or wrong capture day")
                        labels = chunk["Label"].str.strip()
                        categories = pd.to_numeric(
                            chunk["Attempted Category"], errors="coerce"
                        )
                        if (
                            labels.eq("").any()
                            or not categories.isin(range(-1, 7)).all()
                        ):
                            raise ValueError("invalid label or attempted category")
                        if (
                            labels.str.contains("Attempted", case=False)
                            != categories.ne(-1)
                        ).any():
                            raise ValueError("attempted category contradicts label")
                        if day_index == 0 and not labels.eq("BENIGN").all():
                            raise ValueError("Monday must be benign")
                        values = (
                            chunk[features]
                            .apply(pd.to_numeric, errors="coerce")
                            # Own writable storage for signed-zero normalization.
                            .to_numpy(dtype="<f8", copy=True)
                        )
                        finite = np.isfinite(values).all(axis=1)
                        counts["nonfinite_removed"] += int((~finite).sum())
                        values[values == 0] = (
                            0  # Canonicalize signed zero for identity.
                        )
                        for i in np.flatnonzero(finite):
                            blob = values[i].tobytes()
                            identity = sha256(blob).digest()
                            timestamp = int(times.iloc[i].value)
                            original, category = labels.iloc[i], int(categories.iloc[i])
                            label = "BENIGN" if category != -1 else original
                            record = (
                                identity,
                                day_index,
                                timestamp,
                                sequence_start + int(i),
                                blob,
                                label,
                                original,
                                category,
                            )
                            cursor = database.execute(
                                "INSERT OR IGNORE INTO rows VALUES (?,?,?,?,?,?,?,?)",
                                record,
                            )
                            if cursor.rowcount == 0:
                                old = database.execute(
                                    "SELECT day,timestamp,original FROM rows WHERE identity=?",
                                    (identity,),
                                ).fetchone()
                                counts["label_conflicts_observed"] += int(
                                    old[2] != original
                                )
                                if old[0] == day_index and timestamp < old[1]:
                                    database.execute(
                                        "UPDATE rows SET timestamp=?,sequence=?,features=?,label=?,original=?,category=? WHERE identity=?",
                                        record[2:] + (identity,),
                                    )
                        database.commit()
                counts["retained_rows"] = database.execute(
                    "SELECT COUNT(*) FROM rows WHERE day=?", (day_index,)
                ).fetchone()[0]
                counts["duplicates_removed"] = (
                    counts["raw_rows"]
                    - counts["nonfinite_removed"]
                    - counts["retained_rows"]
                )
                if not counts["retained_rows"]:
                    raise ValueError(f"empty retained partition: {day}")
                print(f"{day}: {counts}", flush=True)
        if sha256_file(archive) != digest:
            raise ValueError("source changed during preparation")
        database.execute("CREATE INDEX chronological ON rows(day,timestamp,sequence)")
        database.commit()

        def batches(day):
            cursor = database.execute(
                "SELECT identity,timestamp,features,label,original,category FROM rows WHERE day=? ORDER BY timestamp,sequence",
                (day,),
            )
            while rows := cursor.fetchmany(read_chunk_rows):
                yield rows, np.vstack(
                    [np.frombuffer(row[2], dtype="<f8") for row in rows]
                )

        scaler = MinMaxScaler()
        for _, matrix in batches(0):
            scaler.partial_fit(matrix)
        report["feature_names"] = features
        report["scaler"] = {
            "fit_day": "monday",
            "data_min": scaler.data_min_.tolist(),
            "data_max": scaler.data_max_.tolist(),
            "scale": scaler.scale_.tolist(),
            "offset": scaler.min_.tolist(),
        }
        report["artifacts"] = {}
        for index, day in enumerate(DAYS):
            size = report["days"][day]["retained_rows"]
            matrix_path = output / f"{day}.X.npy"
            matrix = np.lib.format.open_memmap(
                matrix_path, mode="w+", dtype=np.float32, shape=(size, len(features))
            )
            metadata_path = output / f"{day}.metadata.csv"
            offset, last = 0, None
            with metadata_path.open("x", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(
                    [
                        "row_id",
                        "timestamp_ns",
                        "label",
                        "original_label",
                        "attempted_category",
                    ]
                )
                for rows, values in batches(index):
                    transformed = scaler.transform(values).astype(np.float32)
                    if not np.isfinite(transformed).all():
                        raise ValueError("nonfinite transformed features")
                    for row in rows:
                        if last is not None and row[1] < last:
                            raise ValueError("nonmonotonic output")
                        last = row[1]
                        writer.writerow([row[0].hex(), row[1], row[3], row[4], row[5]])
                    matrix[offset : offset + len(rows)] = transformed
                    offset += len(rows)
            matrix.flush()
            del matrix
            report["artifacts"][matrix_path.name] = sha256_file(matrix_path)
            report["artifacts"][metadata_path.name] = sha256_file(metadata_path)
        report["complete"] = True
        temporary = output / "manifest.json.tmp"
        temporary.write_text(
            json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
        )
        temporary.rename(output / "manifest.json")
        return report
    finally:
        database.close()


def iter_prepared_day(output: Path, day: str, *, chunk_rows=200):
    """Yield bounded (feature matrix, evaluation metadata) pairs after integrity checks."""
    if day not in DAYS or type(chunk_rows) is not int or chunk_rows < 1:
        raise ValueError("valid day and positive integer chunk_rows required")
    output = Path(output)
    report = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    if (
        report.get("complete") is not True
        or report.get("dataset") != "cicids2017_improved_cns2022"
    ):
        raise ValueError("incomplete or incompatible prepared dataset")
    paths = [output / f"{day}.X.npy", output / f"{day}.metadata.csv"]
    for path in paths:
        if sha256_file(path) != report["artifacts"].get(path.name):
            raise ValueError(f"cache checksum mismatch: {path.name}")
    matrix = np.load(paths[0], mmap_mode="r", allow_pickle=False)
    expected = report["days"][day]["retained_rows"]
    if matrix.shape != (expected, len(report["feature_names"])):
        raise ValueError("cache shape mismatch")
    offset = 0
    for metadata in pd.read_csv(paths[1], chunksize=chunk_rows, dtype={"row_id": str}):
        end = offset + len(metadata)
        if end > expected:
            raise ValueError("cache metadata length mismatch")
        yield matrix[offset:end], metadata
        offset = end
    if offset != expected:
        raise ValueError("cache metadata length mismatch")
