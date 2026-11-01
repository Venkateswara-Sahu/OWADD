"""Tests for the detection-floor study (`experiments/calibrated_power.py`).

The study backs a figure and a claim in the manuscript ("the pathway has a
detection floor at roughly half the window for a moderate mean shift"), so the pieces
that make the claim -- the evidence scale, the row-shift construction, the
aggregation -- are pinned here. The expensive full grid is not run; one small cell is
enough to check direction.
"""

from __future__ import annotations

import numpy as np
import pytest

from experiments.calibrated_power import (
    Cell,
    evidence_threshold,
    make_case,
    marginal_evidence,
    run_cell,
    summarize,
)


def test_threshold_matches_the_published_scale() -> None:
    """`-log10(0.05) = 1.301` and `-log10(0.5) = 0.301`, as the paper quotes."""
    assert evidence_threshold(0.05) == pytest.approx(1.30103, abs=1e-5)
    assert evidence_threshold(0.5) == pytest.approx(0.30103, abs=1e-5)


def test_marginal_evidence_is_larger_for_a_larger_shift() -> None:
    rng = np.random.default_rng(0)
    ref = rng.standard_normal((200, 4))

    small = ref.copy()
    small[:100, 1] += 0.2
    large = ref.copy()
    large[:100, 1] += 1.0

    assert marginal_evidence(ref, large)[1] > marginal_evidence(ref, small)[1]


def test_make_case_shifts_exactly_the_requested_rows() -> None:
    cell = Cell(fraction_rows=0.25, delta=1.0, n_shifted_features=2)
    ref, cur, truth = make_case(cell, seed=0, window=100, d=6)

    assert truth.shape == (2,)
    assert cur.shape == ref.shape
    moved = np.flatnonzero(np.any(cur != ref, axis=1))
    assert moved.size == 25
    untouched = np.setdiff1d(np.arange(6), truth)
    assert np.array_equal(cur[:, untouched], ref[:, untouched])
    assert np.allclose(cur[np.ix_(moved, truth)] - ref[np.ix_(moved, truth)], 1.0)


def test_run_cell_reports_both_thresholds_and_a_rank() -> None:
    cell = Cell(fraction_rows=1.0, delta=0.5, n_shifted_features=2)
    result = run_cell(cell, trials=4, seed=1, window=200, d=6, n_permutations=49)

    assert set(result["detection"]) == {"declared", "loose"}
    assert 0.0 <= result["detection"]["declared"] <= 1.0
    assert result["detection"]["loose"] >= result["detection"]["declared"]
    assert result["rows_moved"] == 200
    assert 0.0 <= result["calibrated_joint"] <= 1.0
    assert result["median_best_rank"] >= 1.0


def test_summarize_orders_each_fraction_by_delta() -> None:
    small = {
        "fraction_rows": 0.05,
        "delta": 0.2,
        "detection": {"declared": 0.0, "loose": 0.0},
        "mean_max_evidence": 0.1,
    }
    large = {
        "fraction_rows": 0.05,
        "delta": 0.5,
        "detection": {"declared": 0.25, "loose": 0.5},
        "mean_max_evidence": 0.9,
    }
    summary = summarize({"a": small, "b": large})

    row = summary["rows_by_fraction"]["0.05"]
    assert row["delta_0.2"]["declared"] == 0.0
    assert row["delta_0.5"]["declared"] == 0.25
    assert row["delta_0.5"]["loose"] == 0.5
    assert summary["thresholds"]["declared_0.05"] == 1.301
