"""Bounded-memory source audit. Does not silently repair ambiguous timestamps."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

import numpy as np
import pandas as pd

from experiments.provenance import sha256_file

DROP_COLUMNS = {"Flow ID", "Source IP", "Destination IP", "Timestamp", "Label"}
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


def audit_files(paths, *, read_chunk_rows=25000, work_dir: Path):
    if read_chunk_rows < 1 or not paths:
        raise ValueError("nonempty paths and positive read_chunk_rows required")
    work_dir.mkdir(parents=True, exist_ok=True)
    database_path = work_dir / f"dedup-{uuid4().hex}.sqlite"
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA cache_size=-16384")
    connection.execute(
        "CREATE TABLE identities (digest BLOB PRIMARY KEY) WITHOUT ROWID"
    )
    files, features, blockers = [], None, []
    try:
        for path in paths:
            path = Path(path)
            digest_before = sha256_file(path)
            labels = Counter()
            record = {
                "file": path.name,
                "sha256": digest_before,
                "raw_rows": 0,
                "empty_padding_rows": 0,
                "duplicate_rows": 0,
                "nonfinite_rows": 0,
                "missing_numeric_values": 0,
                "infinite_numeric_values": 0,
                "timestamp_parse_failures": 0,
                "ambiguous_early_hour_rows": 0,
                "backward_timestamp_steps": 0,
                "retained_rows": 0,
                "max_chunk_rows": 0,
                "missing_labels": 0,
            }
            previous = None
            minimum, maximum = None, None
            for chunk in pd.read_csv(
                path,
                chunksize=read_chunk_rows,
                dtype=str,
                keep_default_na=False,
                encoding="latin-1",
            ):
                chunk.columns = chunk.columns.str.strip()
                if chunk.columns.duplicated().any():
                    raise ValueError(f"duplicate normalized columns: {path.name}")
                if not {"Timestamp", "Label"}.issubset(chunk.columns):
                    raise ValueError(f"Timestamp and Label required: {path.name}")
                names = [name for name in chunk.columns if name not in DROP_COLUMNS]
                if features is None:
                    features = names
                record["schema_matches_reference"] = names == features
                record["columns"] = list(chunk.columns)
                record["raw_rows"] += len(chunk)
                record["max_chunk_rows"] = max(record["max_chunk_rows"], len(chunk))
                chunk = chunk.apply(lambda column: column.str.strip())
                empty = chunk.eq("").all(axis=1)
                record["empty_padding_rows"] += int(empty.sum())
                chunk = chunk.loc[~empty]
                if chunk.empty:
                    continue
                labels.update(chunk["Label"].tolist())
                missing_label = chunk["Label"].eq("").to_numpy()
                record["missing_labels"] += int(missing_label.sum())
                numerical = (
                    chunk[names]
                    .apply(pd.to_numeric, errors="coerce")
                    .to_numpy(dtype=float)
                )
                finite = np.isfinite(numerical).all(axis=1)
                record["nonfinite_rows"] += int((~finite).sum())
                record["missing_numeric_values"] += int(np.isnan(numerical).sum())
                record["infinite_numeric_values"] += int(np.isinf(numerical).sum())
                timestamps = pd.to_datetime(
                    chunk["Timestamp"], format="mixed", dayfirst=True, errors="coerce"
                )
                valid_time = timestamps.notna().to_numpy()
                record["timestamp_parse_failures"] += int((~valid_time).sum())
                # CIC capture is daytime; 01:00 without AM/PM is not safely sortable.
                ambiguous = timestamps.dt.hour.between(1, 7) & ~chunk[
                    "Timestamp"
                ].str.contains(r"\b[AP]M\b", case=False, regex=True)
                record["ambiguous_early_hour_rows"] += int(ambiguous.sum())
                valid = timestamps.dropna()
                if len(valid):
                    record["backward_timestamp_steps"] += int(
                        (valid.diff().dt.total_seconds() < 0).sum()
                    )
                    if previous is not None and valid.iloc[0] < previous:
                        record["backward_timestamp_steps"] += 1
                    previous = valid.iloc[-1]
                    minimum = (
                        min(minimum, valid.min())
                        if minimum is not None
                        else valid.min()
                    )
                    maximum = (
                        max(maximum, valid.max())
                        if maximum is not None
                        else valid.max()
                    )
                for index, row in enumerate(chunk.itertuples(index=False, name=None)):
                    identity = sha256(
                        json.dumps(
                            row, ensure_ascii=False, separators=(",", ":")
                        ).encode()
                    ).digest()
                    cursor = connection.execute(
                        "INSERT OR IGNORE INTO identities VALUES (?)", (identity,)
                    )
                    if cursor.rowcount == 0:
                        record["duplicate_rows"] += 1
                    elif (
                        finite[index] and valid_time[index] and not missing_label[index]
                    ):
                        record["retained_rows"] += 1
                connection.commit()
            if sha256_file(path) != digest_before:
                raise ValueError(f"source changed during audit: {path}")
            record["label_counts"] = dict(sorted(labels.items()))
            record["timestamp_min_as_parsed"] = (
                str(minimum) if minimum is not None else None
            )
            record["timestamp_max_as_parsed"] = (
                str(maximum) if maximum is not None else None
            )
            for key in (
                "timestamp_parse_failures",
                "ambiguous_early_hour_rows",
                "backward_timestamp_steps",
                "missing_labels",
            ):
                if record[key]:
                    blockers.append(f"{path.name}: {key}={record[key]}")
            if (
                not record.get("schema_matches_reference", False)
                or not record["raw_rows"]
            ):
                blockers.append(f"{path.name}: empty file or schema mismatch")
            files.append(record)
    finally:
        connection.close()
    return {
        "schema_version": 1,
        "scope": "source audit only; no transformed partitions or model evaluation",
        "read_chunk_rows": read_chunk_rows,
        "encoding": "latin-1 (byte-preserving decode)",
        "feature_columns": features,
        "drop_columns": sorted(DROP_COLUMNS),
        "files": files,
        "identity_policy": "SHA-256 of whitespace-normalized full raw row, including label; global disk-backed dedup",
        "numeric_policy": "exclude nonfinite rows from retained count; no imputation",
        "empty_record_policy": "count entirely empty CSV records separately; exclude before flow validity and duplicate checks",
        "timestamp_policy": "day-first parse; no AM/PM repair or reordering",
        "chronology_blockers": blockers,
        "ready_for_chronological_benchmark": not blockers,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--read-chunk-rows", type=int, default=25000)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(args.output)
    paths = sorted(
        args.data_root.glob("*.csv"),
        key=lambda path: (
            next(
                (index for index, day in enumerate(DAYS) if path.name.startswith(day)),
                5,
            ),
            path.name,
        ),
    )
    report = audit_files(
        paths,
        read_chunk_rows=args.read_chunk_rows,
        work_dir=args.output.parent / "audit_cache",
    )
    temporary = args.output.with_name(f".{args.output.name}.{uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8"
    )
    temporary.replace(args.output)
    print(
        json.dumps(
            {
                "audit": str(args.output),
                "files": len(report["files"]),
                "chronology_blockers": report["chronology_blockers"],
            },
            indent=2,
        )
    )
    return 0 if report["ready_for_chronological_benchmark"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
