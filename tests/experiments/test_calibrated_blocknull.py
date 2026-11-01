"""Tests for the block-permutation null study harness.

The harness itself is cheap to exercise at tiny trial counts: what matters is
that the payload records the block sizes that ran, that a machine without the
held-out prepared days still produces a run, and that the real-pool split
mapping matches the study it mirrors.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from experiments import calibrated_blocknull as blocknull


def test_pool_split_mapping() -> None:
    assert blocknull._pool_split("real_tuesday") == "validation"
    assert blocknull._pool_split("real_heldout") == "test"


def test_temporal_window_keeps_row_order() -> None:
    base = np.arange(1000, dtype=float)
    rows = np.column_stack([base, base])
    ref, cur = blocknull._temporal_window(rows, seed=0, window=400, block_rows=800)
    assert ref.shape == (400, 2)
    assert cur.shape == (400, 2)
    # Adjacent unshuffled slices: the point of the exercise is that order survives.
    np.testing.assert_array_equal(ref[:, 0], np.arange(0, 400))
    np.testing.assert_array_equal(cur[:, 0], np.arange(400, 800))


def test_temporal_window_rejects_short_blocks() -> None:
    rows = np.zeros((100, 2))
    with pytest.raises(ValueError):
        blocknull._temporal_window(rows, seed=0, window=400, block_rows=800)


def test_run_synthetic_only_records_block_sizes(tmp_path) -> None:
    payload = blocknull.run(
        tmp_path,
        trials=2,
        n_permutations=99,
        alpha=0.05,
        prepared=None,
        block_sizes=(1, 25),
        conditions=("null",),
    )
    assert payload["real_pools_available"] == []
    assert payload["real_pools_missing"] == list(blocknull.REAL_POOLS)
    assert set(payload["pools"]) == set(blocknull.SYNTHETIC_POOLS)
    for name in blocknull.SYNTHETIC_POOLS:
        cell = payload["pools"][name]["null"]
        assert set(cell) == {"1", "25"}
        assert cell["1"]["trials"] == 2
        assert 0.0 <= cell["1"]["rate"] <= 1.0
    written = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert written["block_sizes"] == [1, 25]
    assert (tmp_path / "summary.md").read_text(encoding="utf-8").strip()


def test_run_skips_unavailable_real_pool(tmp_path) -> None:
    """A prepared dir with only the validation days must still run."""
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    (prepared / "manifest.json").write_text(
        json.dumps(
            {
                "complete": True,
                "dataset": "cicids2017_improved_cns2022",
                "split_days": {"reference": ["monday"], "validation": ["tuesday"]},
            }
        ),
        encoding="utf-8",
    )

    def fake_load(root):
        return {"validation": np.random.default_rng(0).standard_normal((1600, 20))}

    from experiments import mechanism_data

    original = mechanism_data.load_real_pools
    mechanism_data.load_real_pools = fake_load  # type: ignore[assignment]
    try:
        payload = blocknull.run(
            tmp_path / "out",
            trials=1,
            n_permutations=99,
            alpha=0.05,
            prepared=prepared,
            block_sizes=(1,),
            conditions=("null",),
        )
    finally:
        mechanism_data.load_real_pools = original  # type: ignore[assignment]

    assert payload["real_pools_available"] == ["real_tuesday"]
    assert payload["real_pools_missing"] == ["real_heldout"]
    assert "real_tuesday" in payload["pools"]
    assert "real_heldout" not in payload["pools"]
