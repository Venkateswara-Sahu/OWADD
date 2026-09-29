from __future__ import annotations

import json
from hashlib import sha256
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
    path.with_suffix(".complete").write_text(
        sha256(path.read_bytes()).hexdigest(), encoding="ascii"
    )
    return path


def test_aggregation_rejects_missing_seed(tmp_path: Path) -> None:
    write_record(tmp_path, method="vigil", seed=0, value=0.5)

    with pytest.raises(AggregationIntegrityError, match="missing combinations"):
        aggregate_results(tmp_path, expected_methods={"vigil"}, expected_seeds={0, 1})


def test_aggregation_ignores_unfinished_result(tmp_path):
    path = write_record(tmp_path, method="vigil", seed=0, value=0.5)
    path.with_suffix(".complete").unlink()
    with pytest.raises(AggregationIntegrityError, match="no result"):
        aggregate_results(tmp_path, {"vigil"}, {0})


def test_aggregation_rejects_changed_result(tmp_path):
    path = write_record(tmp_path, method="vigil", seed=0, value=0.5)
    path.write_text(path.read_text().replace("0.5", "0.9"), encoding="utf-8")
    with pytest.raises(AggregationIntegrityError, match="checksum"):
        aggregate_results(tmp_path, {"vigil"}, {0})


def test_each_scenario_requires_every_seed(tmp_path):
    for directory, seed in (("a", 0), ("b", 1)):
        folder = tmp_path / directory
        folder.mkdir()
        path = write_record(folder, method="vigil", seed=seed, value=0.5)
        payload = json.loads(path.read_text())
        payload["config"]["params"]["magnitude"] = seed + 1
        path.write_text(json.dumps(payload), encoding="utf-8")
        path.with_suffix(".complete").write_text(sha256(path.read_bytes()).hexdigest())
    with pytest.raises(AggregationIntegrityError, match="missing combinations"):
        aggregate_results(tmp_path, {"vigil"}, {0, 1})


def test_effect_sizes_do_not_pool_different_scenarios(tmp_path):
    for magnitude, values in ((1, (0.6, 0.8)), (2, (0.4, 0.2))):
        folder = tmp_path / str(magnitude)
        folder.mkdir()
        for seed in (0, 1):
            for method, value in (("vigil", 0.5), ("ks", values[seed])):
                path = write_record(folder, method=method, seed=seed, value=value)
                payload = json.loads(path.read_text())
                payload["config"]["params"]["magnitude"] = magnitude
                path.write_text(json.dumps(payload), encoding="utf-8")
                path.with_suffix(".complete").write_text(
                    sha256(path.read_bytes()).hexdigest()
                )
    summary = aggregate_results(tmp_path, {"vigil", "ks"}, {0, 1})
    candidate = summary[summary.method == "ks"].set_index("magnitude")
    assert candidate.loc[1, "paired_effect_vs_reference"] == pytest.approx(2**0.5)
    assert candidate.loc[2, "paired_effect_vs_reference"] == pytest.approx(-(2**0.5))


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
