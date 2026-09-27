# ruff: noqa: PLR2004
import numpy as np


def test_independent_pools_and_exact_shift_ground_truth():
    from experiments.attribution_screen import make_cases

    train, reference, cases, order = make_cases(0)
    assert train.shape == (2000, 20)
    assert reference.shape == (200, 20)
    assert len(np.unique(np.vstack([train, reference, cases[0][2]]), axis=0)) == 2400
    assert cases[0][1] == ()
    base = cases[0][2]
    for name, truth, current in cases[1:]:
        assert len(truth) == 2
        untouched = sorted(set(range(20)) - set(truth))
        np.testing.assert_array_equal(current[:, untouched], base[:, untouched])
        if name == "mean_2":
            np.testing.assert_allclose(current[:, truth] - base[:, truth], 2)
        if name == "std_0.5":
            np.testing.assert_allclose(current[:, truth], base[:, truth] * 0.5)
    repeated = make_cases(0)
    np.testing.assert_array_equal(train, repeated[0])
    assert sorted(order) == list(range(20))
    assert cases[1][1] != make_cases(1)[2][1][1]


def test_screen_runs_complete_paired_methods_and_retains_null_metrics(tmp_path):
    import json

    import torch

    from experiments.attribution_screen import run_screen

    before = torch.get_rng_state().clone()
    threads = torch.get_num_threads()
    path = run_screen(tmp_path, seeds=(0, 1), epochs=1)
    assert torch.equal(before, torch.get_rng_state())
    assert torch.get_num_threads() == threads
    payload = json.loads(path.read_text())
    assert payload["metadata"]["protocol_complete"] is False
    assert len(payload["metrics"]["groups"]) == 42
    for group in payload["metrics"]["groups"]:
        assert group["n_seeds"] == 2
        if group["case"] == "stable":
            assert group["metrics"]["top1_accuracy"]["mean"] is None
    assert run_screen(tmp_path, seeds=(0, 1), epochs=1) == path
    runs = list(tmp_path.glob("*/*/result.json"))
    assert len(runs) == 2
    for run in runs:
        result = json.loads(run.read_text())
        assert len(result["metrics"]["records"]) == 42
        assert all(len(r["scores"]) == 20 for r in result["metrics"]["records"])


def test_ablation_retains_direction_and_paired_uncertainty(tmp_path):
    import json

    from experiments.attribution_screen import run_screen

    path = run_screen(tmp_path, seeds=(10, 11), epochs=1, ablation=True)
    result = json.loads(path.read_text())
    assert result["metadata"]["protocol_complete"] is False
    assert result["config"]["params"]["protocol_version"] == 2
    assert len(result["metrics"]["groups"]) == 54
    comparisons = result["metrics"]["paired_differences"]
    assert len(comparisons) == 90
    runs = [json.loads(p.read_text()) for p in tmp_path.glob("*/*/result.json")]
    assert len(runs) == 2
    for run in runs:
        assert len(run["metrics"]["records"]) == 54
        candidates = [
            r
            for r in run["metrics"]["records"]
            if r["method"] == "vigil_absolute_delta"
        ]
        assert len(candidates) == 6
        for row in candidates:
            np.testing.assert_allclose(row["scores"], np.abs(row["signed_delta"]))
    for comparison in comparisons:
        differences = []
        for run in runs:
            rows = {
                r["method"]: r["metrics"]["recall@3"]
                for r in run["metrics"]["records"]
                if r["case"] == comparison["case"]
            }
            if comparison["case"] != "stable":
                differences.append(
                    rows[comparison["candidate"]] - rows[comparison["baseline"]]
                )
        metric = comparison["metrics"]["recall@3"]
        if differences:
            assert metric["mean"] == np.mean(differences)
            assert metric["ci95"][0] <= metric["mean"] <= metric["ci95"][1]
        else:
            assert metric == {"mean": None, "ci95": None}
    assert run_screen(tmp_path, seeds=(10, 11), epochs=1, ablation=True) == path
