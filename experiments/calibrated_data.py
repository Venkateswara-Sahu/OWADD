"""Data generation and drift injection for the calibrated-attribution study.

The study needs three things the existing loaders do not provide:

1. **Null populations with awkward structure.** The permutation null is only
   calibrated if the reference and current windows are exchangeable, so the
   null table has to include populations where the *asymptotic* KS/copula
   p-values are known to be unreliable: heavy tails (multivariate t), exact
   ties and point mass at zero (zero-inflated flow features), and strong
   cross-feature dependence. A Gaussian null alone cannot show a calibration
   failure.

2. **Injections that separate the marginal and relational pathways.** Full
   column shifts are easy for both pathways; sparse sub-population shifts and
   pure permutations are where they differ. Column permutation destroys every
   dependency of a feature while preserving its marginal exactly, which is the
   cleanest relational-only signal available.

3. **Exact-marginal relational injections.** Rotating a pair to a target rank
   correlation and then re-ranking to the original sorted values keeps the
   marginal distribution identical, so a detector that responds to it can only
   have used the dependency structure.

``apply_injection`` mutates a copy of the current window and returns the truth
set, so every method sees byte-identical inputs and the comparison is paired.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
from scipy import stats

__all__ = [
    "LOCALIZATION_CONDITIONS",
    "NULL_POPULATIONS",
    "Injection",
    "apply_injection",
    "real_window",
    "synthetic_pool",
]

MIN_SD = 1e-8
NDIM = 2
ZERO_FRACTION = 0.7
ROUND_DECIMALS = 1
MIX_INDEPENDENT = 0.6


def _random_correlation(
    rng: np.random.Generator, d: int, strength: float
) -> np.ndarray:
    """Random correlation matrix mixing a low-rank factor with white noise."""
    factors = max(1, d // 5)
    loadings = rng.normal(size=(d, factors))
    loadings /= np.sqrt(factors)
    corr = strength * (loadings @ loadings.T) + (1.0 - strength) * np.eye(d)
    return corr


def _gaussian(rng: np.random.Generator, n: int, d: int) -> np.ndarray:
    corr = _random_correlation(rng, d, strength=0.5)
    chol = np.linalg.cholesky(corr)
    return rng.normal(size=(n, d)) @ chol.T


def _zero_inflated_tied(rng: np.random.Generator, n: int, d: int) -> np.ndarray:
    """~70% exact zeros, the rest rounded absolute t(2) draws.

    Both pathologies that break asymptotic two-sample tests are present:
    a point mass at zero (which produces huge tie blocks and a discrete
    spectrum) and heavy tails among the non-zero entries.
    """
    # Round to one decimal so the tie blocks are real, not floating-point luck.
    heavy = np.round(np.abs(rng.standard_t(2, size=(n, d))), ROUND_DECIMALS)
    zeros = rng.random((n, d)) < ZERO_FRACTION
    values = np.where(zeros, 0.0, heavy)
    # Induce cross-feature dependence among the non-zero entries.
    permuted = values[:, rng.permutation(d)]
    mixed = (1.0 - MIX_INDEPENDENT) * values + MIX_INDEPENDENT * permuted
    # Re-mask so the point mass at zero survives the mixture: without this the
    # zeros are smeared into the mixture and the population has no ties at all.
    return np.where(zeros, 0.0, mixed)


def _multivariate_t(
    rng: np.random.Generator, n: int, d: int, df: int = 3
) -> np.ndarray:
    """Multivariate t with a strong equicorrelation structure.

    Heavy *joint* tails: a shared chi-square scale means tail events happen in
    all features at once, so both the KS null and the Fisher-z null are wrong.
    """
    corr = _random_correlation(rng, d, strength=0.6)
    chol = np.linalg.cholesky(corr)
    normal = rng.normal(size=(n, d)) @ chol.T
    scale = np.sqrt(rng.chisquare(df, size=(n, 1)) / df)
    return normal / scale


NULL_POPULATIONS: dict[str, object] = {
    "gaussian": _gaussian,
    "zero_inflated_tied": _zero_inflated_tied,
    "multivariate_t3": _multivariate_t,
}


def synthetic_pool(
    population: str,
    rng: np.random.Generator,
    n: int,
    d: int,
) -> np.ndarray:
    """Draw ``n`` rows from one of the study populations."""
    if population not in NULL_POPULATIONS:
        raise ValueError(f"unknown population: {population}")
    return np.asarray(NULL_POPULATIONS[population](rng, n, d), dtype=float)


@dataclass(frozen=True)
class Injection:
    """One drift scenario.

    Attributes
    ----------
    kind : {"none", "mean", "scale", "paircorr", "permute"}
    magnitude : float
        Mean shift in reference standard deviations, scale multiplier, or target
        correlation depending on ``kind``.
    n_features : int
        Number of features touched. ``paircorr`` always touches exactly two.
    sparse : float
        Fraction of current-window rows that receive the injection. ``1.0``
        applies it to the whole column (the standard benchmark); smaller values
        model a sub-population shift.
    """

    kind: str
    magnitude: float = 0.0
    n_features: int = 2
    sparse: float = 1.0

    @property
    def label(self) -> str:
        if self.kind == "none":
            return "null"
        base = (
            f"{self.kind}_{self.magnitude:g}" if self.kind != "permute" else "permute"
        )
        if self.kind == "paircorr":
            base = f"paircorr_{self.magnitude:g}"
        parts = [base, f"k{self.n_features}"]
        if self.sparse < 1.0:
            parts.append(f"sparse{round(100 * self.sparse)}")
        return "_".join(parts)


LOCALIZATION_CONDITIONS: tuple[Injection, ...] = (
    Injection("none"),
    Injection("mean", 0.5, 2),
    Injection("mean", 0.2, 2),
    Injection("mean", 0.5, 2, 0.05),
    Injection("mean", 0.5, 2, 0.20),
    Injection("scale", 0.5, 2),
    Injection("scale", 2.0, 2),
    Injection("scale", 0.5, 2, 0.20),
    Injection("paircorr", 0.8, 2),
    Injection("paircorr", 0.3, 2),
    Injection("permute", 0.0, 1),
    Injection("permute", 0.0, 2),
    Injection("permute", 0.0, 5),
    Injection("permute", 0.0, 2, 0.20),
)


def _affected_rows(rng: np.random.Generator, n: int, sparse: float) -> np.ndarray:
    """Row subset receiving a sparse injection (all rows when ``sparse == 1``)."""
    if not 0.0 < sparse <= 1.0:
        raise ValueError("sparse must be in (0, 1]")
    count = max(1, round(sparse * n))
    if count >= n:
        return np.arange(n)
    return np.sort(rng.choice(n, size=count, replace=False))


def _pick_features(
    rng: np.random.Generator, d: int, n_features: int
) -> tuple[int, ...]:
    if not 1 <= n_features <= d:
        raise ValueError("n_features must be in [1, d]")
    return tuple(int(i) for i in rng.choice(d, size=n_features, replace=False))


def _inject_paircorr(
    cur: np.ndarray,
    columns: tuple[int, int],
    target: float,
    rows: np.ndarray,
    rng: np.random.Generator,
) -> None:
    """Raise the rank correlation of two columns while keeping both marginals.

    A fresh independent copy drives the second column to the target correlation,
    then the values are re-assigned in the new order so the sorted marginal is
    unchanged. The achieved rank correlation therefore matches ``target`` up to
    the granularity of the row subset.
    """
    a, b = columns
    anchor = cur[rows, a]
    independent = rng.normal(size=len(rows))
    mix = target * stats.rankdata(anchor) + np.sqrt(
        max(0.0, 1.0 - target**2)
    ) * stats.rankdata(independent)
    original_sorted = np.sort(cur[rows, b])
    order = np.argsort(mix, kind="stable")
    new_values = np.empty(len(rows))
    new_values[order] = original_sorted
    cur[rows, b] = new_values


def apply_injection(
    ref: np.ndarray,
    cur: np.ndarray,
    injection: Injection,
    rng: np.random.Generator,
) -> tuple[np.ndarray, tuple[int, ...]]:
    """Return ``(modified current window, truth features)`` without mutating input."""
    ref = np.asarray(ref, dtype=float)
    current = np.array(cur, dtype=float, copy=True)
    d = current.shape[1]
    if injection.kind == "none":
        return current, ()
    if injection.kind == "paircorr":
        if injection.n_features != NDIM:
            raise ValueError("paircorr injections use exactly two features")
        columns = _pick_features(rng, d, NDIM)
        rows = _affected_rows(rng, len(current), injection.sparse)
        _inject_paircorr(
            current, (columns[0], columns[1]), injection.magnitude, rows, rng
        )
        return current, tuple(sorted(columns))

    columns = np.asarray(_pick_features(rng, d, injection.n_features))
    if injection.kind == "mean":
        rows = _affected_rows(rng, len(current), injection.sparse)
        current[np.ix_(rows, columns)] += injection.magnitude
    elif injection.kind == "scale":
        rows = _affected_rows(rng, len(current), injection.sparse)
        center = ref[:, columns].mean(axis=0)
        current[np.ix_(rows, columns)] = center + injection.magnitude * (
            current[np.ix_(rows, columns)] - center
        )
    elif injection.kind == "permute":
        rows = _affected_rows(rng, len(current), injection.sparse)
        for column in columns:
            values = current[rows, column]
            current[rows, column] = rng.permutation(values)
    else:
        raise ValueError(f"unknown injection kind: {injection.kind}")
    return current, tuple(sorted(int(c) for c in columns))


def real_window(
    pools: dict,
    *,
    seed: int,
    window: int,
    block_size: int,
    n_blocks: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Two adjacent, row-disjoint windows drawn from one disjoint block.

    Block selection is ``seed % n_blocks`` so every seed sees a different slice
    of the real data and no two seeds share rows. Rows are permuted within the
    block so the split is not a contiguous time segment (contiguous traffic
    blocks carry autocorrelation, which would violate exchangeability).
    """
    rows_all = np.asarray(pools["validation"], dtype=float)
    if 2 * window > block_size:
        raise ValueError("window must fit inside a block twice")
    if n_blocks * block_size > len(rows_all):
        raise ValueError("requested blocks exceed available real rows")
    block = int(seed) % n_blocks
    start = block * block_size
    rows = np.random.default_rng([int(seed), 7]).permutation(block_size) + start
    ordered = rows_all[rows]
    return ordered[:window], ordered[window : 2 * window]


def feature_sd(pool: np.ndarray) -> np.ndarray:
    """Per-feature standard deviation with a floor to avoid division by zero."""
    return np.maximum(pool.std(axis=0, ddof=1), MIN_SD)


def injectable_columns(pool: np.ndarray, *, min_sd: float = MIN_SD) -> Iterable[int]:
    """Columns with enough variation to carry a shift injection."""
    return [i for i, sd in enumerate(pool.std(axis=0, ddof=1)) if sd > min_sd]
