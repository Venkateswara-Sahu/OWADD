# ruff: noqa: PLR2004
import numpy as np
import pytest


def test_dependency_generator_covariance_truth_and_independent_pools():
    from experiments.dependency_data import make_dependency_cases, pair_root

    for rho in (0.0, 0.2, 0.3, 0.5, 0.6, 0.9):
        root = pair_root(rho)
        np.testing.assert_allclose(root @ root.T, [[1, rho], [rho, 1]], atol=1e-14)
    cases = make_dependency_cases(1001)
    assert len(cases) == 12
    repeated = make_dependency_cases(1001)
    for case, again in zip(cases, repeated, strict=True):
        np.testing.assert_array_equal(case["current"], again["current"])
        n = case["window_size"]
        assert case["train"].shape == (2000, 20)
        assert case["reference"].shape == case["current"].shape == (n, 20)
        rows = np.vstack([case["train"], case["reference"], case["current"]])
        assert len(np.unique(rows, axis=0)) == 2000 + 2 * n
        assert sorted(case["tie_order"]) == list(range(20))
        stable = next(
            c
            for c in cases
            if c["background"] == case["background"]
            and c["window_size"] == n
            and c["strength"] == 0
        )
        if case["strength"] == 0:
            assert case["truth"] == ()
        else:
            assert len(case["truth"]) == 2
            untouched = sorted(set(range(20)) - set(case["truth"]))
            np.testing.assert_array_equal(
                case["current"][:, untouched], stable["current"][:, untouched]
            )


def test_summary_requires_exact_grid_and_pairs_by_seed():
    from experiments.dependency_screen import EXPECTED_KEYS, aggregate_runs

    runs = {}
    for seed in (1001, 1002):
        records = []
        for case, method in sorted(EXPECTED_KEYS):
            value = 0.5 if method == "vigil_positive_delta" else 0.25
            records.append(
                {
                    "case": case,
                    "method": method,
                    "elapsed_ms": 1.0,
                    "metrics": {
                        "recall@3": None if case.endswith("delta_0") else value
                    },
                }
            )
        runs[seed] = records
    summary = aggregate_runs(runs)
    assert len(summary["groups"]) == 132
    assert len(summary["paired_differences"]) == 72
    for row in summary["paired_differences"]:
        if row["case"].endswith("delta_0"):
            assert row["metrics"]["recall@3"]["mean"] is None
        elif row["candidate"] == "vigil_positive_delta":
            assert row["metrics"]["recall@3"] == {"mean": 0.25, "ci95": [0.25, 0.25]}
    with pytest.raises(ValueError, match="grid"):
        aggregate_runs({1001: runs[1001][1:], 1002: runs[1002]})
    with pytest.raises(ValueError, match="grid"):
        aggregate_runs({1001: runs[1001] + [runs[1001][0]], 1002: runs[1002]})


def test_dependency_screen_smoke_resume_and_state_preservation(tmp_path):
    import json

    import torch

    from experiments.dependency_screen import run_screen

    before = torch.get_rng_state().clone()
    threads = torch.get_num_threads()
    path = run_screen(tmp_path, seeds=(1001, 1002), epochs=1)
    assert torch.equal(before, torch.get_rng_state())
    assert torch.get_num_threads() == threads
    payload = json.loads(path.read_text())
    assert payload["metadata"]["protocol_complete"] is False
    assert len(payload["metrics"]["groups"]) == 132
    assert len(payload["metrics"]["paired_differences"]) == 72
    runs = list(tmp_path.glob("*/*/result.json"))
    assert len(runs) == 2
    for run in runs:
        result = json.loads(run.read_text())
        assert len(result["metrics"]["records"]) == 132
        assert len(result["metadata"]["models"]) == 2
        for row in result["metrics"]["records"]:
            assert len(row["scores"]) == 20
            assert row["elapsed_ms"] >= 0
            if row["method"] == "nonlinear_permutation":
                assert "held_out_balanced_accuracy" in row["details"]
    assert run_screen(tmp_path, seeds=(1001, 1002), epochs=1) == path
