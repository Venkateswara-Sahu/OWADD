# ruff: noqa: PLR2004
import numpy as np
import torch


def test_training_pair_same_initialization_and_input_control():
    from experiments.mechanism import fit_pair, model_hash, score_windows

    data = np.random.default_rng(1001).normal(size=(40, 3))
    state = torch.get_rng_state().clone()
    original, trained, metadata = fit_pair(data, 1001, 1)
    assert torch.equal(state, torch.get_rng_state())
    assert metadata["initial_sha256"] != metadata["trained_sha256"]
    assert metadata["initial_sha256"] == model_hash(original)
    assert metadata["initial_loss"] >= 0 and metadata["trained_loss"] >= 0
    ref = np.array([[0.0, 0.0, 0.0], [2.0, 4.0, 6.0]])
    cur = np.array([[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]])
    scores, details = score_windows(original, trained, ref, cur)
    assert len(scores) == 9
    np.testing.assert_allclose(scores["squared_input_change"], [1.0, 4.0, 9.0])
    np.testing.assert_allclose(details["input_signed_delta"], [-1.0, -4.0, -9.0])
    assert details["correlation_supported"] is False


def test_real_pool_selection_hashes_disjointness_and_training_only_scaling(tmp_path):
    import json

    import pandas as pd

    from experiments.mechanism_data import load_real_pools, real_cases
    from experiments.provenance import sha256_file

    rng = np.random.default_rng(1001)
    manifest = {
        "complete": True,
        "dataset": "cicids2017_improved_cns2022",
        "feature_names": ["Dst Port", "Protocol"] + [f"f{i}" for i in range(20)],
        "artifacts": {},
        "split_days": {
            "reference": ["monday"],
            "validation": ["tuesday"],
            "test": ["wednesday", "thursday", "friday"],
        },
    }
    for day, n in [("monday", 4000), ("tuesday", 32600)]:
        values = rng.normal(size=(n, 22)).astype(np.float32)
        if day == "tuesday":
            values += 10
        np.save(tmp_path / f"{day}.X.npy", values)
        pd.DataFrame({"row_id": [f"{day}_{i}" for i in range(n)]}).to_csv(
            tmp_path / f"{day}.metadata.csv", index=False
        )
        for suffix in ("X.npy", "metadata.csv"):
            name = f"{day}.{suffix}"
            manifest["artifacts"][name] = sha256_file(tmp_path / name)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    pools = load_real_pools(tmp_path)
    np.testing.assert_allclose(pools["train"].mean(0), 0, atol=1e-12)
    assert pools["validation"].mean() > 9
    assert pools["feature_names"] == [f"f{i}" for i in range(20)]
    cases = real_cases(pools, 50)
    assert len(cases) == 6
    assert set(cases[0]["reference_ids"]).isdisjoint(cases[0]["current_ids"])
    assert set(cases[0]["reference_ids"]).isdisjoint(pools["training_ids"])
    assert "tuesday_599" not in cases[0]["reference_ids"] + cases[0]["current_ids"]
    base, permuted = cases[0]["current"], cases[-1]["current"]
    for col in cases[-1]["truth"]:
        np.testing.assert_array_equal(np.sort(base[:, col]), np.sort(permuted[:, col]))
    from experiments.mechanism_screen import run_screen

    path = run_screen(
        tmp_path / "results", seeds=(1001, 1002), epochs=1, prepared=tmp_path
    )
    result = json.loads(path.read_text())
    assert len(result["metrics"]["groups"]) == 216
    assert len(result["metrics"]["paired_differences"]) == 96
    for group in result["metrics"]["groups"]:
        if group["case"] == "real/no_injection":
            assert all(metric["mean"] is None for metric in group["metrics"].values())
    assert result["metadata"]["protocol_complete"] is False
    assert (
        run_screen(
            tmp_path / "results", seeds=(1001, 1002), epochs=1, prepared=tmp_path
        )
        == path
    )


def test_mechanism_runner_complete_synthetic_grid_and_resume(tmp_path):
    import json

    from experiments.mechanism_screen import run_screen

    before = torch.get_rng_state().clone()
    path = run_screen(tmp_path, seeds=(1001, 1002), epochs=1)
    assert torch.equal(before, torch.get_rng_state())
    result = json.loads(path.read_text())
    assert result["metadata"]["protocol_complete"] is False
    assert len(result["metrics"]["groups"]) == 162
    assert len(result["metrics"]["paired_differences"]) == 72
    assert run_screen(tmp_path, seeds=(1001, 1002), epochs=1) == path
    for file in tmp_path.glob("*/*/result.json"):
        payload = json.loads(file.read_text())
        assert len(payload["metrics"]["records"]) == 162
        assert len(payload["metadata"]["cases"]) == 18
        for model in payload["metadata"]["models"].values():
            assert model["initial_sha256"] != model["trained_sha256"]
