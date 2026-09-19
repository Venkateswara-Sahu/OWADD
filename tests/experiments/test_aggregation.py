from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from experiments.aggregate import AggregationIntegrityError, aggregate_results


def write_record(
    root: Path,
    *,
    method: str,
    seed: int,
    value: float,
    manifest_hash: str = "stream-a",
    checksum: str = "data-a",
    uses_labels: bool = False,
    undefined_reason: str | None = None,
) -> Path:
    path = root / f"{method}-{seed}.json"
    payload = {
        "config": {
            "dataset": "synthetic",
            "method": method,
            "seed": seed,
            "params": {"shift_family": "mean", "magnitude": 1.0},
        },
        "provenance": {"dataset_checksums": {"data": checksum}},
        "metrics": {
            "primary": value,
            "manifest": {"hash": manifest_hash},
        },
        "metadata": {
            "uses_labels": uses_labels,
            "undefined_reasons": (
                {"primary": undefined_reason} if undefined_reason else {}
            ),
        },
    }
    path.write_text(json.dumps(payload, allow_nan=True), encoding="utf-8")
    return path


def test_aggregation_rejects_missing_seed(tmp_path: Path) -> None:
    write_record(tmp_path, method="vigil", seed=0, value=0.5)

    with pytest.raises(AggregationIntegrityError, match="missing combinations"):
        aggregate_results(tmp_path, expected_methods={"vigil"}, expected_seeds={0, 1})


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("manifest", "stream manifest"),
        ("checksum", "dataset checksums"),
        ("labels", "label-usage"),
    ],
)
def test_aggregation_rejects_incompatible_comparisons(
    tmp_path: Path, field: str, message: str
) -> None:
    write_record(tmp_path, method="vigil", seed=0, value=0.5)
    kwargs = {}
    if field == "manifest":
        kwargs["manifest_hash"] = "stream-b"
    elif field == "checksum":
        kwargs["checksum"] = "data-b"
    else:
        kwargs["uses_labels"] = True
    write_record(tmp_path, method="ks", seed=0, value=0.4, **kwargs)

    with pytest.raises(AggregationIntegrityError, match=message):
        aggregate_results(
            tmp_path, expected_methods={"vigil", "ks"}, expected_seeds={0}
        )


def test_nan_requires_an_undefined_reason(tmp_path: Path) -> None:
    write_record(tmp_path, method="vigil", seed=0, value=np.nan)

    with pytest.raises(AggregationIntegrityError, match="non-finite"):
        aggregate_results(tmp_path, {"vigil"}, {0})


def test_complete_results_produce_summary_with_confidence_interval(
    tmp_path: Path,
) -> None:
    for seed, value in enumerate((0.4, 0.6, 0.8)):
        write_record(tmp_path, method="vigil", seed=seed, value=value)

    summary = aggregate_results(tmp_path, {"vigil"}, {0, 1, 2})

    assert summary.loc[0, "count"] == 3
    assert summary.loc[0, "mean"] == pytest.approx(0.6)
    assert summary.loc[0, "ci_low"] <= summary.loc[0, "mean"]
    assert summary.loc[0, "ci_high"] >= summary.loc[0, "mean"]
