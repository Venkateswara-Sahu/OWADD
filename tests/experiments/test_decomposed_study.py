"""Tests for Decomposed Copula-KS attribution study."""

import json

import numpy as np

from experiments.attribution.vigil_adapter import DecomposedDriftAttributor
from experiments.decomposed_study import run_decomposed_study, score_decomposed_variants

EXPECTED_FEATURE_INDEX = 2
EXPECTED_FEATURE_COUNT = 6


def test_score_decomposed_variants_disentangles_marginal_and_relational():
    rng = np.random.default_rng(101)
    ref = rng.standard_normal((250, 8))
    cur_marginal = ref.copy()
    cur_marginal[:, 2] += 1.5
    scores_m, details_m = score_decomposed_variants(ref, cur_marginal)
    assert int(np.argmax(scores_m["decomposed_copula_ks"])) == EXPECTED_FEATURE_INDEX
    assert details_m["drift_types"][2] == "marginal"

    # Pure relational shift with identical N(0,1) marginals
    cur_rel = ref.copy()
    z = rng.standard_normal(250)
    rho = 0.85
    cur_rel[:, 4] = rho * z + np.sqrt(1 - rho**2) * rng.standard_normal(250)
    cur_rel[:, 5] = rho * z + np.sqrt(1 - rho**2) * rng.standard_normal(250)
    scores_r, details_r = score_decomposed_variants(ref, cur_rel)
    top2 = set(np.argsort(scores_r["decomposed_copula_ks"])[-2:])
    assert top2 == {4, 5}
    assert details_r["drift_types"][4] == "relational"
    assert details_r["drift_types"][5] == "relational"


def test_decomposed_attributor_adapter_contract():
    rng = np.random.default_rng(7)
    ref = rng.standard_normal((120, EXPECTED_FEATURE_COUNT))
    cur = ref.copy()
    cur[:, 1] += 2.0
    attributor = DecomposedDriftAttributor()
    ranking = attributor.rank(ref, cur, ("numerical",) * EXPECTED_FEATURE_COUNT)
    assert int(np.argmax(ranking.scores)) == 1
    assert ranking.scores.shape == (EXPECTED_FEATURE_COUNT,)


def test_run_decomposed_study_writes_summary(tmp_path):
    summary_path = run_decomposed_study(tmp_path, seeds=(50, 51), epochs=2)
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["stage"] == "decomposed_attribution_validation"
    # 18 synthetic cases * 12 methods = 216 groups
    assert len(payload["metrics"]["groups"]) == 18 * 12
    assert len(payload["metrics"]["paired_differences"]) == 18 * 5


