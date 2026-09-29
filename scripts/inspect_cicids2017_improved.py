"""Read-only candidate profiling, not a benchmark approval gate."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd


def inspect(archive):
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    report = {
        "archive_sha256": digest,
        "archive_bytes": archive.stat().st_size,
        "scope": "candidate profile, not benchmark approval",
        "chunk_rows": 25000,
        "unchecked": [
            "duplicates",
            "cross-split leakage",
            "timezone verification",
            "label correctness",
        ],
        "files": [],
    }
    excluded = {
        "id",
        "Flow ID",
        "Src IP",
        "Dst IP",
        "Timestamp",
        "Label",
        "Attempted Category",
    }
    schema = None
    with ZipFile(archive) as zipped:
        for entry in sorted(zipped.infolist(), key=lambda item: item.filename):
            if not entry.filename.endswith(".csv"):
                raise ValueError(f"Unexpected member: {entry.filename}")
            labels, categories, dates, joint = (
                Counter(),
                Counter(),
                Counter(),
                Counter(),
            )
            record = {
                "file": entry.filename,
                "bytes": entry.file_size,
                "rows": 0,
                "invalid_timestamps": 0,
                "non_iso_timestamps": 0,
                "backward_steps": 0,
                "nonfinite_numeric_rows": 0,
                "missing_labels": 0,
                "invalid_attempted_categories": 0,
                "attempted_label_category_disagreements": 0,
            }
            minimum = maximum = previous = None
            # Reading to EOF verifies each ZIP member's CRC.
            with zipped.open(entry) as source:
                for chunk in pd.read_csv(
                    source, chunksize=25000, dtype=str, keep_default_na=False
                ):
                    columns = list(chunk.columns)
                    if schema is None:
                        schema = columns
                    if columns != schema:
                        raise ValueError("Cross-file schema mismatch")
                    record["rows"] += len(chunk)
                    raw = chunk["Timestamp"]
                    record["non_iso_timestamps"] += int(
                        (
                            ~raw.str.fullmatch(
                                r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,9})?"
                            )
                        ).sum()
                    )
                    times = pd.to_datetime(raw, format="ISO8601", errors="coerce")
                    record["invalid_timestamps"] += int(times.isna().sum())
                    valid = times.dropna()
                    if len(valid):
                        record["backward_steps"] += int(
                            (valid.diff().dt.total_seconds() < 0).sum()
                        )
                        if previous is not None and valid.iloc[0] < previous:
                            record["backward_steps"] += 1
                        previous = valid.iloc[-1]
                        minimum = (
                            valid.min()
                            if minimum is None
                            else min(minimum, valid.min())
                        )
                        maximum = (
                            valid.max()
                            if maximum is None
                            else max(maximum, valid.max())
                        )
                        dates.update(valid.dt.strftime("%Y-%m-%d"))
                    label, category = (
                        chunk["Label"].str.strip(),
                        chunk["Attempted Category"].str.strip(),
                    )
                    labels.update(label)
                    categories.update(category)
                    joint.update(zip(label, category))
                    record["missing_labels"] += int(label.eq("").sum())
                    numeric_category = pd.to_numeric(category, errors="coerce")
                    record["invalid_attempted_categories"] += int(
                        (~numeric_category.isin(range(-1, 7))).sum()
                    )
                    record["attempted_label_category_disagreements"] += int(
                        (
                            label.str.contains("Attempted", case=False)
                            != numeric_category.ne(-1)
                        ).sum()
                    )
                    features = chunk[
                        [name for name in columns if name not in excluded]
                    ].apply(pd.to_numeric, errors="coerce")
                    record["nonfinite_numeric_rows"] += int(
                        (~np.isfinite(features.to_numpy(dtype=float)).all(axis=1)).sum()
                    )
            record.update(
                timestamp_min=str(minimum),
                timestamp_max=str(maximum),
                label_counts=dict(labels),
                attempted_category_counts=dict(categories),
                dates=dict(dates),
                label_category_counts=[
                    {"label": k[0], "category": k[1], "rows": v}
                    for k, v in sorted(joint.items())
                ],
            )
            report["files"].append(record)
            print(json.dumps(record), flush=True)
    report["columns"] = schema
    report["excluded_from_numeric_profile"] = sorted(excluded)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = inspect(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        json.dump(result, destination, indent=2, allow_nan=False)
