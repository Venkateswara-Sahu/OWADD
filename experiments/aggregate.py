from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from experiments.metrics.stats import bootstrap_mean_ci, paired_effect_size


class AggregationIntegrityError(RuntimeError):
    """Raised when result records cannot form a trustworthy comparison."""


def _load_records(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(root.rglob("*.json")):
        if path.name == "failure.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if {"config", "provenance", "metrics"}.issubset(payload):
            records.append(payload)
    if not records:
        raise AggregationIntegrityError(f"no result records found under {root}")
    return records


def aggregate_results(
    paths: Path,
    expected_methods: Iterable[str],
    expected_seeds: Iterable[int],
    *,
    reference_method: str = "vigil",
) -> pd.DataFrame:
    """Validate paired result records and return grouped primary summaries."""

    records = _load_records(paths)
    methods = set(expected_methods)
    seeds = set(expected_seeds)
    observed = {
        (str(record["config"]["method"]), int(record["config"]["seed"]))
        for record in records
    }
    expected = {(method, seed) for method in methods for seed in seeds}
    missing = sorted(expected - observed)
    if missing:
        raise AggregationIntegrityError(f"missing combinations: {missing}")
    extras = sorted(observed - expected)
    if extras:
        raise AggregationIntegrityError(f"unexpected combinations: {extras}")

    rows: list[dict[str, object]] = []
    for record in records:
        config = record["config"]
        metrics = record["metrics"]
        metadata = record.get("metadata", {})
        value = float(metrics["primary"])
        reason = metadata.get("undefined_reasons", {}).get("primary")
        if not np.isfinite(value) and not reason:
            raise AggregationIntegrityError(
                "non-finite primary metric has no undefined reason"
            )
        params = config.get("params", {})
        rows.append(
            {
                "dataset": config["dataset"],
                "method": config["method"],
                "seed": int(config["seed"]),
                "shift_family": params.get("shift_family", "unspecified"),
                "magnitude": params.get("magnitude", np.nan),
                "value": value,
                "manifest_hash": metrics["manifest"]["hash"],
                "checksum": json.dumps(
                    record["provenance"]["dataset_checksums"], sort_keys=True
                ),
                "uses_labels": bool(metadata.get("uses_labels", False)),
            }
        )
    frame = pd.DataFrame(rows)
    comparison_keys = ["dataset", "seed", "shift_family", "magnitude"]
    for _, paired in frame.groupby(comparison_keys, dropna=False):
        if paired["manifest_hash"].nunique() != 1:
            raise AggregationIntegrityError("stream manifest mismatch")
        if paired["checksum"].nunique() != 1:
            raise AggregationIntegrityError("dataset checksums mismatch")
        if paired["uses_labels"].nunique() != 1:
            raise AggregationIntegrityError("label-usage mismatch")

    output: list[dict[str, object]] = []
    group_keys = ["dataset", "shift_family", "magnitude", "method"]
    for key, group in frame.groupby(group_keys, dropna=False, sort=True):
        finite = group.loc[np.isfinite(group["value"]), "value"].to_numpy()
        if finite.size == 0:
            mean = standard_deviation = ci_low = ci_high = np.nan
        else:
            mean = float(finite.mean())
            standard_deviation = float(finite.std(ddof=1)) if finite.size > 1 else 0.0
            ci_low, ci_high = bootstrap_mean_ci(finite)
        output.append(
            {
                "dataset": key[0],
                "shift_family": key[1],
                "magnitude": key[2],
                "method": key[3],
                "count": int(finite.size),
                "mean": mean,
                "std": standard_deviation,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "paired_effect_vs_reference": np.nan,
            }
        )
    summary = pd.DataFrame(output)
    if reference_method in methods:
        reference = frame[frame["method"] == reference_method].set_index(
            comparison_keys
        )["value"]
        for index, row in summary.iterrows():
            candidate_rows = frame[frame["method"] == row["method"]].set_index(
                comparison_keys
            )["value"]
            shared = reference.index.intersection(candidate_rows.index)
            summary.loc[index, "paired_effect_vs_reference"] = paired_effect_size(
                reference.loc[shared].to_numpy(),
                candidate_rows.loc[shared].to_numpy(),
            )
    return summary
