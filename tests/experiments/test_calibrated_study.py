"""Tests for the calibrated attribution study module."""

import json

import numpy as np
import pytest

from experiments.calibrated_study import (
    METHODS,
    build_bundle,
    method_outputs,
    run_study,
)

SMALL_TRIALS = 3
SMALL_SEEDS = (101, 102)
SMALL_PERMUTATIONS = 49
FLAG_PERMUTATIONS = 199


def _bundle(seed=0, d=8, n=160, n_permutations=SMALL_PERMUTATIONS):
    rng = np.random.default_rng(seed)
    ref = rng.normal(size=(n, d))
    cur = rng.normal(size=(n, d))
    cur[:, 1] += 1.0
    return build_bundle(
        ref, cur, n_permutations=n_permutations, seed=seed, include_rank_transform=False
    )


def test_build_bundle_produces_every_statistic_once():
    bundle = _bundle()
    assert bundle.cal.marginal_evidence.shape == (8,)
    assert bundle.cal.edge_pvalues.shape == (8, 8)
    assert bundle.decomposed[0].shape == (8,)
    assert bundle.ks_pearson[0].shape == (8,)


def test_rank_transform_can_be_disabled():
    rng = np.random.default_rng(1)
    ref = rng.normal(size=(120, 6))
    bundle = build_bundle(
        ref,
        rng.normal(size=(120, 6)),
        n_permutations=SMALL_PERMUTATIONS,
        seed=0,
        include_rank_transform=False,
    )
    assert bundle.cal_rank is None
    assert "peeling_rank_transform" not in method_outputs(bundle)


def test_method_outputs_match_the_registry_and_score_every_feature():
    rng = np.random.default_rng(0)
    ref = rng.normal(size=(160, 8))
    bundle = build_bundle(ref, rng.normal(size=(160, 8)), n_permutations=49, seed=0)
    outputs = method_outputs(bundle)
    # The registry is the canonical reporting order; the dict is insertion-ordered.
    assert tuple(outputs) == METHODS
    for scores, reject in outputs.values():
        assert scores.shape == (8,)
        assert isinstance(reject, bool)


def test_method_outputs_flags_the_shifted_feature():
    outputs = method_outputs(_bundle(n_permutations=FLAG_PERMUTATIONS))
    for name in ("decomposed_asymptotic", "peeling_joint", "ks_asymptotic"):
        scores, reject = outputs[name]
        assert reject, name
        assert int(np.argmax(scores)) == 1, name


def test_study_writes_a_self_describing_summary(tmp_path):
    result = run_study(
        tmp_path / "run",
        null_trials=SMALL_TRIALS,
        seeds=SMALL_SEEDS,
        n_permutations=SMALL_PERMUTATIONS,
        include_real=False,
    )
    payload = json.loads(result.read_text())
    metrics = payload["metrics"]
    assert set(metrics["null"]["populations"]) == {
        "gaussian",
        "zero_inflated_tied",
        "multivariate_t3",
    }
    summary = json.loads((tmp_path / "run" / "summary.json").read_text())
    assert summary["null_trials"] == SMALL_TRIALS
    assert summary["seeds"] == list(SMALL_SEEDS)
    assert "wall_seconds" in summary
    markdown = (tmp_path / "run" / "summary.md").read_text()
    assert "| null population |" in markdown
    assert "chance" in markdown


def test_study_records_incomplete_protocol_for_small_runs(tmp_path):
    result = run_study(
        tmp_path / "run",
        null_trials=SMALL_TRIALS,
        seeds=SMALL_SEEDS,
        n_permutations=SMALL_PERMUTATIONS,
        include_real=False,
        skip_null=True,
    )
    payload = json.loads(result.read_text())
    assert payload["metadata"]["protocol_complete"] is False


def test_study_is_deterministic_across_repeat_runs(tmp_path):
    first = run_study(
        tmp_path / "a",
        null_trials=SMALL_TRIALS,
        seeds=SMALL_SEEDS,
        n_permutations=SMALL_PERMUTATIONS,
        include_real=False,
        skip_null=True,
    )
    second = run_study(
        tmp_path / "b",
        null_trials=SMALL_TRIALS,
        seeds=SMALL_SEEDS,
        n_permutations=SMALL_PERMUTATIONS,
        include_real=False,
        skip_null=True,
    )
    left = json.loads(first.read_text())["metrics"]
    right = json.loads(second.read_text())["metrics"]
    for payload in (left, right):
        payload.pop("wall_seconds", None)
        payload.pop("markdown", None)  # embeds nothing random, but keep it cheap
        payload["localization"].pop("timings", None)
    assert left == right


def test_study_resumes_into_the_same_output_dir(tmp_path):
    """A second run reuses the cached summary instead of raising a mismatch."""

    kwargs = {
        "null_trials": 1,
        "seeds": (101,),
        "n_permutations": SMALL_PERMUTATIONS,
        "include_real": False,
        "trials": 1,
    }
    first = run_study(tmp_path / "run", **kwargs)
    second = run_study(tmp_path / "run", **kwargs)

    left = json.loads(first.read_text())["metrics"]
    right = json.loads(second.read_text())["metrics"]
    for payload in (left, right):
        payload.pop("wall_seconds", None)
        payload.pop("markdown", None)
        payload["localization"].pop("timings", None)
    assert left == right


def test_study_rejects_duplicate_seeds(tmp_path):
    with pytest.raises(ValueError):
        run_study(
            tmp_path / "run",
            null_trials=1,
            seeds=(1, 1),
            n_permutations=9,
            include_real=False,
            skip_null=True,
        )


def test_study_reruns_when_the_protocol_changes(tmp_path):
    """A different permutation count is a different cache key, not a mismatch."""

    base = {
        "null_trials": 1,
        "seeds": (101,),
        "include_real": False,
        "trials": 1,
    }
    run_study(tmp_path / "run", n_permutations=SMALL_PERMUTATIONS, **base)
    run_study(tmp_path / "run", n_permutations=199, **base)

    summary = json.loads((tmp_path / "run" / "summary.json").read_text())
    assert summary["n_permutations"] == 199


def test_study_rejects_non_positive_trial_counts(tmp_path):
    with pytest.raises(ValueError):
        run_study(
            tmp_path / "run",
            null_trials=0,
            seeds=SMALL_SEEDS,
            n_permutations=9,
            include_real=False,
        )
