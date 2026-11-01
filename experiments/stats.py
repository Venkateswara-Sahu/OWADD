"""Paired nonparametric comparisons and chance references for attribution studies.

The attribution studies compare detectors on the *same* simulated instances, so
every comparison here is paired by seed. Unpaired tests would ignore that
pairing and understate the effect of a method change.

Nothing in this module touches attribution scores; it only turns per-seed
metric vectors into the numbers a paper table needs (effect size, p-value,
multiplicity-adjusted decision) plus the analytic chance line that a random
ranking would achieve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats

MIN_SIGNED_RANK_PAIRS = 10
SURVIVAL_EPS = 1e-12

__all__ = [
    "PairedComparison",
    "block_bootstrap_ci",
    "block_sizes",
    "bootstrap_mean_ci",
    "chance_line",
    "holm_bonferroni",
    "null_rejection_metrics",
    "paired_comparison",
    "wilson_interval",
]


@dataclass(frozen=True)
class PairedComparison:
    """Result of a paired test of ``candidate`` against ``baseline``."""

    candidates: str
    baseline: str
    n: int
    mean_candidate: float
    mean_baseline: float
    delta: float
    wins: int
    losses: int
    ties: int
    p_value: float
    holm_p_value: float = float("nan")
    rejected: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate": self.candidates,
            "baseline": self.baseline,
            "n": self.n,
            "mean_candidate": self.mean_candidate,
            "mean_baseline": self.mean_baseline,
            "delta": self.delta,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "p_value": self.p_value,
            "holm_p_value": self.holm_p_value,
            "rejected": self.rejected,
        }


def paired_comparison(
    candidate: np.ndarray,
    baseline: np.ndarray,
    *,
    candidates: str = "candidate",
    baseline_name: str = "baseline",
) -> PairedComparison:
    """Two-sided Wilcoxon signed-rank test on paired per-seed metrics.

    All-zero differences (identical methods on identical instances) return
    ``p_value = 1.0`` rather than raising; that is the honest reading of
    "no evidence of a difference".
    """
    a = np.asarray(candidate, dtype=float)
    b = np.asarray(baseline, dtype=float)
    if a.shape != b.shape:
        raise ValueError("paired comparison needs equal-length vectors")
    if a.ndim != 1:
        raise ValueError("paired comparison needs 1-D vectors")
    n = len(a)
    if n == 0:
        raise ValueError("paired comparison needs at least one pair")
    delta = a - b
    if not np.any(delta != 0.0):
        p_value = 1.0
    elif n < MIN_SIGNED_RANK_PAIRS:
        # Too few pairs for a useful signed-rank test; report the exact sign test.
        non_zero = int(np.count_nonzero(delta))
        wins = int(np.count_nonzero(delta > 0))
        p_value = float(stats.binomtest(wins, non_zero, 0.5).pvalue)
    else:
        p_value = float(
            stats.wilcoxon(delta, zero_method="wilcox", alternative="two-sided").pvalue
        )
    return PairedComparison(
        candidates=candidates,
        baseline=baseline_name,
        n=n,
        mean_candidate=float(a.mean()),
        mean_baseline=float(b.mean()),
        delta=float(a.mean() - b.mean()),
        wins=int(np.count_nonzero(delta > 0)),
        losses=int(np.count_nonzero(delta < 0)),
        ties=int(np.count_nonzero(delta == 0)),
        p_value=p_value,
    )


def holm_bonferroni(p_values: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values for one family of comparisons.

    Holm controls the family-wise error rate under arbitrary dependence, which
    is what a table of methods sharing the same simulated instances needs.
    Reject whenever ``adjusted[name] <= alpha``.
    """
    if not p_values:
        return {}
    items = sorted(p_values.items(), key=lambda item: item[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return adjusted


def bootstrap_mean_ci(
    values: np.ndarray,
    *,
    n_resamples: int = 2000,
    level: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean of ``values``."""
    data = np.asarray(values, dtype=float)
    if data.size == 0:
        raise ValueError("bootstrap needs at least one value")
    rng = np.random.default_rng(seed)
    draws = rng.choice(data, size=(n_resamples, data.size), replace=True).mean(axis=1)
    tail = (1.0 - level) / 2.0
    low, high = np.quantile(draws, [tail, 1.0 - tail])
    return float(low), float(high)


def chance_line(d: int, n_truth: int, ks: tuple[int, ...]) -> dict[str, float]:
    """Expected metrics for a uniformly random ranking of ``d`` features.

    ``recall@k`` is ``k / d`` (hypergeometric mean). ``mrr`` is the exact
    expectation of ``1 / rank`` of the first relevant feature, and ``ndcg@k``
    uses binary gains normalised by the ideal ordering. ``precision@1`` equals
    ``n_truth / d``.
    """
    if d < 1:
        raise ValueError("d must be positive")
    if not 0 <= n_truth <= d:
        raise ValueError("n_truth must be within [0, d]")
    out: dict[str, float] = {"precision@1": n_truth / d}
    for k in ks:
        out[f"recall@{k}"] = min(1.0, k / d)
        out[f"precision@{k}"] = n_truth / d
        discount = sum(1.0 / math.log2(i + 2) for i in range(min(k, d)))
        expected_gain = (n_truth / d) * discount
        ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, n_truth)))
        out[f"ndcg@{k}"] = expected_gain / ideal if ideal > 0 else 0.0
    # E[1/R] where R is the position of the first relevant feature.
    mrr = 0.0
    if n_truth > 0:
        survival = 1.0
        for position in range(1, d + 1):
            if d - position + 1 <= 0:
                break
            hit = n_truth / (d - position + 1)
            mrr += (1.0 / position) * survival * min(1.0, hit)
            survival *= max(0.0, 1.0 - min(1.0, hit))
            if survival <= SURVIVAL_EPS:
                break
    out["mrr"] = mrr
    return out


def wilson_interval(
    successes: int, trials: int, z: float = 1.959963984540054
) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Preferred over the Wald interval at the rates these studies measure: a 0% or
    5% false-alarm rate with a few hundred trials leaves the Wald interval
    degenerate.
    """
    if trials <= 0:
        return (float("nan"), float("nan"))
    p = successes / trials
    denom = 1.0 + z * z / trials
    centre = (p + z * z / (2.0 * trials)) / denom
    half = z * np.sqrt(p * (1 - p) / trials + z * z / (4.0 * trials * trials)) / denom
    return (float(max(0.0, centre - half)), float(min(1.0, centre + half)))


def block_sizes(blocks: list[int]) -> dict[str, int]:
    """How many draws each block supplied, keyed by block id."""
    return {
        str(block): blocks.count(block) for block in sorted(set(blocks))
    }


def block_bootstrap_ci(
    flags: list[int],
    blocks: list[int],
    *,
    reps: int = 2000,
    seed: int = 20_241_024,
    min_clusters: int = 2,
) -> tuple[float | None, float | None]:
    """Cluster bootstrap interval that resamples whole blocks, not draws.

    Trials that reuse a block are not independent replicates of the data
    generating process, so a binomial interval over trials understates the
    uncertainty. Resampling blocks keeps within-block correlation intact.
    """
    grouped: dict[int, list[int]] = {}
    for flag, block in zip(flags, blocks, strict=True):
        grouped.setdefault(block, []).append(flag)
    keys = sorted(grouped)
    if len(keys) < min_clusters:
        # Artifacts are written with allow_nan=False, so "undefined" is null.
        return (None, None)
    rates = []
    rng = np.random.default_rng(seed)
    for _ in range(reps):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        pooled = [value for index in pick for value in grouped[keys[index]]]
        rates.append(float(np.mean(pooled)))
    return (float(np.quantile(rates, 0.025)), float(np.quantile(rates, 0.975)))


def null_rejection_metrics(
    flags: list[int], blocks: list[int], alpha: float
) -> dict[str, object]:
    """Rejection count and both intervals for one method under the null."""
    rejections = int(sum(flags))
    trials = len(flags)
    if trials == 0:
        raise ValueError("no trials to aggregate")
    return {
        "rejections": rejections,
        "fwer": rejections / trials,
        "ci95": list(wilson_interval(rejections, trials)),
        "ci95_block": list(block_bootstrap_ci(flags, blocks)),
        "alpha": alpha,
        "trials": trials,
    }
