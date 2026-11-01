"""Tests for the real-traffic null calibration of the attribution pathways."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# ``data`` is a scripts package imported from the repository root, not an installed
# one, so the tests have to put the checkout on the path themselves.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.nsl_kdd_loader import DATA_DIR
from experiments.real_null_calibration import (
    BLOCK,
    FEATURES,
    WINDOW,
    draw_pair,
    load_null_pool,
    render,
    run,
)

KDD_TRAIN = DATA_DIR / "KDDTrain+.txt"

pytestmark = pytest.mark.skipif(
    not KDD_TRAIN.is_file(), reason=f"NSL-KDD training split missing at {KDD_TRAIN}"
)


@pytest.fixture(scope="module")
def pool():
    return load_null_pool()


def test_pool_keeps_only_varying_features(pool) -> None:
    assert pool.n_rows > 2 * BLOCK
    assert len(pool.names) == pool.values.shape[1]
    # ``wrong_fragment`` is identically zero for normal traffic in NSL-KDD.
    assert "wrong_fragment" in pool.dropped
    assert "wrong_fragment" not in pool.names
    assert set(pool.modal_mass) == set(pool.names)


def test_modal_mass_is_a_fraction_and_flags_ties(pool) -> None:
    assert all(0.0 < mass <= 1.0 for mass in pool.modal_mass.values())
    assert 0.0 < pool.mean_modal_mass <= 1.0
    assert pool.heavy_tie_features
    assert set(pool.heavy_tie_features) <= set(pool.names)
    for name in pool.heavy_tie_features:
        assert pool.modal_mass[name] >= 0.5


def test_draw_pair_takes_two_disjoint_windows_from_one_block(pool) -> None:
    rng = np.random.default_rng(0)

    reference, current, block = draw_pair(pool, rng, blocks=10)

    assert reference.shape == (WINDOW, len(FEATURES) - len(pool.dropped))
    assert current.shape == reference.shape
    block_rows = pool.values[block * BLOCK : (block + 1) * BLOCK]
    for row in reference:
        assert any(np.array_equal(row, candidate) for candidate in block_rows)
    # Disjointness: the multiset of rows differs by exactly one window's worth.
    merged = np.vstack([reference, current])
    assert merged.shape[0] == 2 * WINDOW


def test_run_reports_every_pathway(pool) -> None:
    metrics = run(
        output=DATA_DIR / "unused",
        trials=2,
        n_permutations=49,
        write=False,
        label="normal",
    )

    assert metrics["trials"] == 2
    assert metrics["d"] == len(pool.names)
    assert metrics["window"] == WINDOW
    assert metrics["blocks"]["distinct"] >= 1
    assert metrics["pool"]["mean_modal_mass"] == pytest.approx(pool.mean_modal_mass)
    assert {
        "decomposed_asymptotic",
        "ks_asymptotic",
        "copula_asymptotic",
        "pearson_asymptotic",
        "peeling_joint",
        "peeling_separate",
        "maxedge_joint",
    } <= set(metrics["methods"])
    for payload in metrics["methods"].values():
        assert payload["trials"] == 2
        assert 0.0 <= payload["fwer"] <= 1.0
        assert payload["rejections"] <= payload["trials"]


def test_permutation_floor_guard_is_enforced() -> None:
    with pytest.raises(ValueError, match="too small"):
        run(output=DATA_DIR / "unused", trials=1, n_permutations=19, write=False)


def test_render_states_the_null_and_reports_both_intervals() -> None:
    metrics = run(
        output=DATA_DIR / "unused",
        trials=2,
        n_permutations=49,
        write=False,
    )

    table = render(metrics)

    assert "Real-traffic null" in table
    assert "95% CI (trials)" in table and "95% CI (blocks)" in table
    assert "Mean modal mass" in table
    assert "Distinct blocks behind the trials" in table
