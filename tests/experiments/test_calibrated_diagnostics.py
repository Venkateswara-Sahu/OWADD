"""Tests for the tie-driven effective-sample-size diagnostic."""

from __future__ import annotations

import json

import numpy as np
import pytest

from experiments.calibrated_diagnostics import (
    _json_safe,
    _pct,
    analyse,
    analytic_edge_pvalues,
    main,
)


def _tied_pair(rng: np.random.Generator, n: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """Two independent features with three distinct values each (heavy ties)."""

    ref = np.column_stack(
        [
            rng.integers(0, 3, size=n).astype(float),
            rng.integers(0, 3, size=n).astype(float),
        ]
    )
    cur = np.column_stack(
        [
            rng.integers(0, 3, size=n).astype(float),
            rng.integers(0, 3, size=n).astype(float),
        ]
    )
    return ref, cur


def test_analytic_edge_pvalues_are_family_wise_scaled() -> None:
    rng = np.random.default_rng(0)
    ref = rng.normal(size=(200, 4))
    cur = rng.normal(size=(200, 4))

    independent = analytic_edge_pvalues(ref, cur, n_pairs=1)
    bonferroni = analytic_edge_pvalues(ref, cur, n_pairs=6)

    assert independent.shape == (4, 4)
    assert np.allclose(np.diag(independent), 1.0)
    assert np.all(independent >= 0.0) and np.all(independent <= 1.0)
    assert np.all(bonferroni >= independent - 1e-12)


def test_analyse_reports_both_nulls_for_the_same_edges() -> None:
    ref, cur = _tied_pair(np.random.default_rng(7))

    metrics = analyse(ref, cur, n_permutations=199, alpha=0.05, seed=0)

    assert metrics["n_edges"] == 1
    top = metrics["top_analytic"][0]
    assert 0.0 <= top["analytic_p"] <= 1.0
    # Permutation p-values are add-one corrected over B permutations, so they
    # can never fall below 1 / (B + 1).
    assert 1.0 / 200 <= top["permutation_p"] <= 1.0
    assert top["min_unique"] == pytest.approx(3 / 200)  # three levels, n = 200


def test_continuous_gaussian_agrees_with_the_permutation_null() -> None:
    """With no ties and no dependence, both nulls stay quiet (sanity check)."""

    ref, cur = _tied_pair(np.random.default_rng(3))
    ref = np.random.default_rng(4).normal(size=ref.shape)
    cur = np.random.default_rng(5).normal(size=cur.shape)

    metrics = analyse(ref, cur, n_permutations=99, alpha=0.05, seed=0)

    assert metrics["analytic_family_reject"] is False
    assert metrics["permutation_family_reject"] is False


def test_bin_counts_partition_the_edges() -> None:
    ref, cur = _tied_pair(np.random.default_rng(1))
    metrics = analyse(ref, cur, n_permutations=49, alpha=0.05, seed=0)

    binned = sum(block["n_edges"] for block in metrics["bins"].values())
    assert binned == metrics["n_edges"] == 1


def test_json_safe_replaces_non_finite_floats() -> None:
    payload = {"a": float("nan"), "b": [float("inf"), 1.0], "c": {"d": None}}

    cleaned = _json_safe(payload)

    assert cleaned["a"] is None
    assert cleaned["b"][0] is None
    assert json.dumps(cleaned)  # serialisable


@pytest.mark.parametrize(
    ("value", "expected"), [(None, "-"), (float("nan"), "-"), (0.05, "5.0%")]
)
def test_pct_formats(value: float | None, expected: str) -> None:
    assert _pct(value) == expected


def test_main_writes_summary_for_synthetic_population(tmp_path) -> None:
    summary_path = main(
        [
            "--output",
            str(tmp_path / "diag"),
            "--seeds",
            "1",
            "--datasets",
            "gaussian",
            "--n-permutations",
            "49",
        ]
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["diagnostic_version"] == 2
    assert set(summary["datasets"]) == {"gaussian"}
    assert summary["datasets"]["gaussian"]["seeds"] == 1
    assert (tmp_path / "diag" / "summary.md").exists()
