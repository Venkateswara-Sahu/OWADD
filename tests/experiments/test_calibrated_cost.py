"""Contract test for the latency benchmark behind the paper's cost numbers."""

from __future__ import annotations

import json

from experiments.calibrated_cost import benchmark, main


def test_benchmark_reports_both_pathways_for_every_population():
    payload = benchmark(d=4, n=40, n_permutations=40, calls=1, seed=0)

    assert payload["d"] == 4
    assert payload["n"] == 40
    assert payload["n_permutations"] == 40
    assert set(payload["results"]) == {
        "gaussian",
        "zero_inflated_tied",
        "multivariate_t3",
    }
    for stats in payload["results"].values():
        assert stats["calls"] == 1
        assert stats["min"] <= stats["median_seconds"] <= stats["max"]
        assert stats["median_seconds"] > 0.0
    assert payload["asymptotic_decomposed_ms"] > 0.0
    assert payload["asymptotic_calls"] == 1


def test_main_writes_json_with_provenance(tmp_path):
    output = main(
        [
            "--output",
            str(tmp_path / "cost.json"),
            "--d",
            "4",
            "--n",
            "40",
            "--n-permutations",
            "40",
            "--calls",
            "1",
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["d"] == 4
    assert payload["provenance"]["source_tree_hash"]
