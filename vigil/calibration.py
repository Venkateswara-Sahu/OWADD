"""
Permutation-calibrated drift attribution with edge-peeling localization.
=======================================================================
Replaces the asymptotic Bonferroni calibration in
:func:`vigil.attribution.compute_decomposed_scores` with a
Westfall-Young max-statistic *permutation* calibration, and replaces the
max-edge relational aggregation with greedy edge peeling.

Why:
  * The asymptotic Fisher-z null variance ``1/(n_ref-3) + 1/(n_cur-3)`` only
    holds for bivariate-normal data. Rank-normal marginals do not make the
    joint distribution Gaussian (e.g. t-copulas) and tied/zero-inflated flow
    features do not map to exact N(0, 1) scores, so the Bonferroni
    family-wise error rate is uncontrolled (measured 8%-53% vs 5% nominal).
  * Pooling both windows and re-splitting them at random gives the exact null
    distribution of *any* statistic under the exchangeability hypothesis
    ``H0: P_ref == P_cur``. The maximum of the statistic over the whole family
    then yields family-wise adjusted p-values that are exact up to
    Monte-Carlo error, regardless of ties, tails, or dependence.
  * A single decision ("is feature j implicated?") is the union of a marginal
    KS rejection and a relational edge rejection. Calibrating those two
    families *separately* at alpha bounds the union by 2*alpha, not alpha.
    The two statistics live on different scales (KS D in [0, 1], Fisher-z in
    [0, inf)), so a single max over both is not a valid maxT statistic; the
    correction here splits alpha across the pathways instead ("Holm-style
    union control"): each pathway keeps its own exact maxT null and receives
    ``alpha / 2``. The union is then bounded by ``alpha`` without any scale
    assumption.
  * Scoring each feature by its single strongest changed correlation edge
    ranks a permuted feature's strongest *partner* second, hiding the second
    permuted feature. Greedy peeling instead selects the feature explaining
    the most significant changed edges, removes those edges, and repeats
    (a greedy vertex cover of the significant-edge graph).

All adjusted p-values use the add-one estimator ``(1 + #{null >= obs})/(B + 1)``
so they are never zero and are valid (conservative) under H0.

Naming note: the add-one estimator is *exact* for the permutation family in the
sense of yielding a valid (super-uniform) p-value under exchangeability, up to
Monte-Carlo resolution ``1/(B+1)``. It is not an asymptotic closed form.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
from scipy import stats

MIN_SAMPLES = 4
NDIM = 2
SD_FLOOR = 1e-12
TIE_BREAK = 1e-3
EDGE_Z_SCALE = 10.0
TOL = 1e-12


@dataclass
class CalibratedScores:
    """Calibrated attribution evidence for one reference/current window pair.

    Attributes
    ----------
    marginal_evidence, relational_evidence : np.ndarray, shape (d,)
        ``-log10`` of the pathway's family-wise adjusted p-value plus a
        monotone statistic tie-break (so saturated features stay ordered).
    combined_scores : np.ndarray, shape (d,)
        Ranking score. Significant features are lifted into a higher tier, so
        ordering is "significance first, evidence second".
    marginal_pvalues : np.ndarray, shape (d,)
        Within-family max-statistic adjusted p-values for the KS pathway. The
        joint guarantee comes from splitting ``alpha`` across pathways (see
        ``metadata['alpha_marginal']``), not from a union null, so these are
        the p-values to threshold at ``alpha_marginal``.
    edge_pvalues : np.ndarray, shape (d, d)
        Within-family max-statistic adjusted p-values for copula correlation
        edges; 1.0 where the edge is masked (a column is constant in one of
        the windows, so its correlation is undefined) or on the diagonal.
    selected_features : list[int]
        Features selected by greedy peeling, in selection order.
    n_permutations : int
        Number of pooled-label permutations actually drawn (0 for degenerate
        inputs).
    marginal_family_pvalues, edge_family_pvalues :
        The pathway-only adjusted p-values again, by construction equal to
        ``marginal_pvalues`` / ``edge_pvalues`` (one max-statistic family per
        pathway). They exist as named accessors because the *family* is what
        the calibration controls. **Do not** threshold both at ``alpha`` and
        union the results; that is the double-dipping error the ``alpha``
        split exists to avoid.
    peel_order : list[int]
        Same as ``selected_features``; kept as a separate name because the
        order is the ranking signal.
    metadata : dict
        Diagnostics (alpha, timing, copula columns, identifiability helper).
    """

    marginal_evidence: np.ndarray
    relational_evidence: np.ndarray
    combined_scores: np.ndarray
    marginal_pvalues: np.ndarray
    edge_pvalues: np.ndarray
    selected_features: list[int] = field(default_factory=list)
    n_permutations: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    marginal_family_pvalues: np.ndarray | None = None
    edge_family_pvalues: np.ndarray | None = None
    peel_order: list[int] = field(default_factory=list)
    maxedge_scores: np.ndarray | None = None
    separate_scores: np.ndarray | None = None
    selected_features_separate: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Materialise the family aliases without sharing one object.

        ``marginal_family_pvalues`` is ``marginal_pvalues`` renamed, so a
        caller mutating one must not silently mutate the other.
        """
        if self.marginal_family_pvalues is None:
            self.marginal_family_pvalues = np.array(self.marginal_pvalues, copy=True)
        if self.edge_family_pvalues is None:
            self.edge_family_pvalues = np.array(self.edge_pvalues, copy=True)

    def significant_features(self, alpha: float | None = None) -> list[int]:
        """Features implicated by a marginal rejection or by the peeled cover.

        Both events are subsets of the family that the permutation null
        calibrates. With ``joint=True`` each pathway was tested at
        ``alpha / 2``, so this set is family-wise controlled at ``alpha``.

        ``alpha`` defaults to the level used when the scores were computed.
        Passing a different level re-thresholds the marginal p-values only;
        the peeled cover is fixed at call time.
        """
        stored = float(self.metadata.get("alpha", 0.05))
        if alpha is None or alpha == stored:
            alpha_marg = float(self.metadata.get("alpha_marginal", stored))
        else:
            alpha_marg = (
                alpha / 2.0
                if self.metadata.get("alpha_relational", stored) != stored
                else alpha
            )
        marg = set(np.flatnonzero(self.marginal_pvalues <= alpha_marg).tolist())
        return sorted(marg | set(self.selected_features))

    @property
    def marginal_significant(self) -> np.ndarray:
        """Boolean mask of marginal-pathway rejections at the stored level."""
        return self.marginal_pvalues <= float(
            self.metadata.get("alpha_marginal", self.metadata.get("alpha", 0.05))
        )

    def timings(self) -> dict[str, float]:
        """Wall-clock timings captured during the call (seconds)."""
        return dict(self.metadata.get("timings", {}))


def _pooled_order(pooled: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Stable sort order per column plus a within-column last-tie mask."""
    order = np.argsort(pooled, axis=0, kind="stable")
    sorted_vals = np.take_along_axis(pooled, order, axis=0)
    tie_mask = np.ones_like(sorted_vals, dtype=bool)
    tie_mask[:-1] = sorted_vals[:-1] != sorted_vals[1:]
    return order, tie_mask


def _window_labels(n_ref: int, n_total: int) -> np.ndarray:
    """Boolean labels: True marks rows of the current window."""
    labels = np.zeros(n_total, dtype=bool)
    labels[n_ref:] = True
    return labels


def _null_maxima(
    pooled: np.ndarray,
    order: np.ndarray,
    tie_mask: np.ndarray,
    n_ref: int,
    n_permutations: int,
    columns: np.ndarray | None,
    rng: np.random.Generator,
    copula_transform: str,
    block_size: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Family maxima of both statistics under pooled-label permutations.

    Each permutation re-splits the pooled rows once and reuses that split for
    both statistics, so the two pathways share a permutation budget.

    Columns that are constant in the pooled data carry no KS information: their
    statistic is identically zero (or a pure tie artefact), so including them
    would only inflate the family maximum. They are dropped from the family by
    the caller and by this function. Permutations in which an edge correlation
    is undefined (a resampled window degenerates to a constant column) are
    recorded as ``-inf`` so they can never win the maximum; ``_adjusted_pvalues``
    ignores them.

    ``block_size > 1`` replaces the i.i.d. row permutation with a permutation of
    contiguous blocks of that many consecutive pooled rows, which keeps runs of
    adjacent (autocorrelated) rows together on the same side of the split. The
    split is still balanced because the caller guarantees that both window
    lengths are multiples of ``block_size``.
    """
    n_total = len(pooled)
    ks_columns = np.flatnonzero(pooled.std(axis=0) > SD_FLOOR)
    null_ks_max = np.full(n_permutations, -np.inf)
    null_z_max = np.full(n_permutations, -np.inf)
    n_blocks = n_total // block_size
    block_offsets = np.arange(block_size, dtype=np.intp)[None, :]
    for b in range(n_permutations):
        if block_size == 1:
            perm = rng.permutation(n_total)
        else:
            starts = rng.permutation(n_blocks)[:, None] * block_size
            perm = (starts + block_offsets).ravel()
        labels = np.zeros(n_total, dtype=bool)
        labels[perm[n_ref:]] = True
        if ks_columns.size:
            ks_b = _ks_statistics(labels[order], tie_mask, n_ref, n_total - n_ref)[
                ks_columns
            ]
            null_ks_max[b] = ks_b.max()
        if columns is not None:
            z_b, valid = _copula_z(
                pooled[perm[:n_ref]],
                pooled[perm[n_ref:]],
                columns,
                copula_transform,
                return_valid=True,
            )
            if valid.any():
                null_z_max[b] = z_b[valid].max()
    return null_ks_max, null_z_max


def _relational_pathway(
    ref: np.ndarray,
    cur: np.ndarray,
    d: int,
    columns: np.ndarray | None,
    obs_z: np.ndarray,
    null_z_max: np.ndarray,
    alpha: float,
    alpha_rel: float,
    peel: bool,
) -> dict[str, Any]:
    """Edge-level calibration, peeling, and honest per-feature evidence."""
    relational_ev = np.zeros(d)
    edge_p_full = np.ones((d, d))
    selected: list[int] = []
    separate_selected: list[int] = []
    max_ref_corr = np.zeros(d)
    if columns is not None:
        p_edge = _adjusted_pvalues(obs_z, null_z_max)
        np.fill_diagonal(p_edge, 1.0)
        # Honest relational evidence: strongest changed edge of each feature.
        # Masked edges are -inf, so they never become a feature's best edge;
        # a feature with no usable edge gets zero evidence.
        z_max = np.nan_to_num(obs_z.max(axis=1), neginf=0.0)
        vertex_p = p_edge.min(axis=1)
        relational_ev[columns] = -np.log10(vertex_p) + TIE_BREAK * z_max / (
            z_max + EDGE_Z_SCALE
        )
        edge_p_full[np.ix_(columns, columns)] = p_edge
        if peel:
            selected = [int(columns[i]) for i in _peel(obs_z, p_edge, alpha_rel)]
            # Ablation only: the separately-calibrated (double-dipping) cover.
            separate_selected = [int(columns[i]) for i in _peel(obs_z, p_edge, alpha)]
        max_ref_corr[columns] = _reference_copula_corr(ref, columns)
    return {
        "ev": relational_ev,
        "edge_p": edge_p_full,
        "selected": selected,
        "separate_selected": separate_selected,
        "max_ref_corr": max_ref_corr,
    }


def _combine_rankings(
    marginal_ev: np.ndarray,
    marginal_p: np.ndarray,
    rel: dict[str, Any],
    alpha_marg: float,
    alpha: float,
    n_permutations: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Combine the pathways into ranking scores (plus the two ablations).

    Tier 1 holds significant features (marginal rejection, or the peeled
    relational cover); partners whose changed edges a peeled feature explains
    sit in tier 2; everything else in tier 3. Evidence orders features inside
    a tier and peeling order breaks ties among the selected ones.
    """
    tier = np.log10(n_permutations + 1.0) + 1.0

    def _lift(selected_order: list[int]) -> np.ndarray:
        ranked = rel["ev"].copy()
        if selected_order:
            n_sel = float(len(selected_order))
            for position, feature in enumerate(selected_order):
                ranked[feature] += tier + TIE_BREAK * (n_sel - position) / n_sel
        return ranked

    rank_marg = marginal_ev + tier * (marginal_p <= alpha_marg)
    rank_marg_separate = marginal_ev + tier * (marginal_p <= alpha)
    combined = np.maximum(rank_marg, _lift(rel["selected"]))
    # Ablations that reuse the same permutation budget: max-edge aggregation
    # (peeling off) and the separately-calibrated cover (double dipping).
    maxedge_scores = np.maximum(rank_marg, rel["ev"])
    separate_scores = np.maximum(rank_marg_separate, _lift(rel["separate_selected"]))
    return combined, maxedge_scores, separate_scores


def _ks_statistics(ordered_labels: np.ndarray, tie_mask: np.ndarray, n_ref, n_cur):
    """Two-sample KS D per column; labels are in pooled-sorted order (N, d)."""
    step = np.where(ordered_labels, 1.0 / n_cur, -1.0 / n_ref)
    cdf_gap = np.cumsum(step, axis=0)
    return np.where(tie_mask, np.abs(cdf_gap), 0.0).max(axis=0)


def _rank_scores(x: np.ndarray, n: int, kind: str) -> np.ndarray:
    """Within-window rank transform used by the relational pathway."""
    ranks = stats.rankdata(x, axis=0)
    if kind == "normal_scores":
        return stats.norm.ppf(ranks / (n + 1.0))
    if kind == "ranks":
        return ranks
    raise ValueError(f"unknown copula transform: {kind}")


def _safe_corr(g: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Correlation matrix plus a mask of edges whose value is defined.

    ``np.corrcoef`` returns ``nan`` for any pair involving a constant column.
    Those edges are masked rather than mapped to zero: ``nan -> 0`` would
    pretend the windows agree perfectly and the difference statistic would be
    spuriously small.
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(g, rowvar=False)
    valid = np.isfinite(corr)
    return np.where(valid, corr, 0.0), valid


def _copula_z(
    ref: np.ndarray,
    cur: np.ndarray,
    columns: np.ndarray,
    transform: str = "normal_scores",
    *,
    return_valid: bool = False,
) -> np.ndarray | tuple[np.ndarray, np.ndarray]:
    """|Fisher-z difference| between within-window rank correlations.

    Masked edges (undefined correlation in either window) are set to ``-inf``,
    which loses every comparison in ``_adjusted_pvalues`` and therefore gets
    an adjusted p-value of exactly 1.0.
    """
    n_ref, n_cur = len(ref), len(cur)
    g_ref = _rank_scores(ref[:, columns], n_ref, transform)
    g_cur = _rank_scores(cur[:, columns], n_cur, transform)
    c_ref, ok_ref = _safe_corr(g_ref)
    c_cur, ok_cur = _safe_corr(g_cur)
    valid = ok_ref & ok_cur
    np.fill_diagonal(valid, False)
    se = np.sqrt(1.0 / (n_ref - 3.0) + 1.0 / (n_cur - 3.0))
    z = np.abs(
        np.arctanh(np.clip(c_cur, -0.999999, 0.999999))
        - np.arctanh(np.clip(c_ref, -0.999999, 0.999999))
    )
    z = np.where(valid, z / se, -np.inf)
    np.fill_diagonal(z, 0.0)
    if return_valid:
        return z, valid
    return z


def _reference_copula_corr(ref: np.ndarray, columns: np.ndarray) -> np.ndarray:
    """Max |rank-normal correlation| of each column in the reference window.

    Identifiability diagnostic: a feature with no dependence on any other
    feature cannot be localized by a *relational* pathway even in principle.
    """
    n = len(ref)
    g = stats.norm.ppf(stats.rankdata(ref[:, columns], axis=0) / (n + 1.0))
    with np.errstate(invalid="ignore", divide="ignore"):
        c = np.nan_to_num(np.corrcoef(g, rowvar=False))
    np.fill_diagonal(c, 0.0)
    return np.abs(c).max(axis=1)


def _adjusted_pvalues(observed: np.ndarray, null_max: np.ndarray) -> np.ndarray:
    """Westfall-Young max-statistic adjusted p-values with add-one correction.

    Two degenerate cases are handled conservatively rather than optimistically:
    permutations whose family maximum is undefined are dropped, and a family
    whose null maximum is identically zero yields p-values of 1.0 because the
    Monte-Carlo evidence cannot discriminate anything there (a saturated
    statistic in a column that never varies is a data artefact, not a
    discovery).
    """
    usable = null_max[np.isfinite(null_max)]
    shape = np.shape(observed)
    if usable.size == 0 or np.all(usable <= TOL):
        return np.ones(shape)
    usable.sort()
    ge = usable.size - np.searchsorted(usable, observed - TOL, side="left")
    return (1.0 + ge) / (usable.size + 1.0)


def _peel(z: np.ndarray, p_edge: np.ndarray, alpha: float) -> list[int]:
    """Greedy edge peeling: return selected vertices in selection order.

    Repeatedly select the vertex with the largest sum of squared significant
    edge statistics, then delete all of its edges. Stops when no significant
    edge remains. Selected vertices form a greedy cover of the significant-edge
    graph: features that *explain* the changed dependencies, as opposed to
    partners whose only changed edge is to an already-selected feature.

    Ties in ``strength`` are broken by column index (``np.argmax`` returns the
    first maximum). Two features with identical significant-edge strength --
    the exact situation the permutation condition creates, where both endpoints
    of a swapped pair carry the same edge -- are therefore ordered by their
    column position, not by evidence. The selection is not equivariant under a
    relabelling of columns in that case, while the adjusted ``p``-values and
    the evidence are (see
    ``tests/test_calibration.py::test_pvalues_are_equivariant_under_column_permutation``).
    This only reorders features the statistic cannot distinguish, so it changes
    the order but not the selected set.
    """
    work = np.where(p_edge <= alpha, z, 0.0)
    np.fill_diagonal(work, 0.0)
    selected: list[int] = []
    while True:
        strength = (work**2).sum(axis=1)
        v = int(np.argmax(strength))
        if strength[v] <= 0.0:
            break
        selected.append(v)
        work[v, :] = 0.0
        work[:, v] = 0.0
    return selected


def compute_calibrated_scores(
    reference_data: np.ndarray,
    current_batch: np.ndarray,
    *,
    n_permutations: int = 200,
    alpha: float = 0.05,
    seed: int | None = 0,
    peel: bool = True,
    joint: bool = True,
    copula_transform: str = "normal_scores",
    block_size: int = 1,
) -> CalibratedScores:
    """Permutation-calibrated marginal (KS) and relational (copula) attribution.

    Parameters
    ----------
    reference_data, current_batch : np.ndarray, shapes (n_ref, d), (n_cur, d)
    n_permutations : int
        Number of pooled-label permutations B. The smallest attainable adjusted
        p-value is ``1 / (B + 1)``; evidence saturates at ``log10(B + 1)``.
    alpha : float
        Family-wise level for the combined decision and for edge peeling. With
        ``joint=True`` each pathway is tested at ``alpha / 2``.
    seed : int or None
        Seed for the permutation stream (deterministic output when set).
    peel : bool
        If False, score each feature by its single strongest edge (max-edge
        aggregation, the uncalibrated-localization baseline).
    joint : bool
        If True (default), ``alpha`` is split evenly across the two pathways so
        that the union of their rejections is family-wise controlled at
        ``alpha``. If False, each pathway gets the full ``alpha``, which only
        bounds the union by ``2 * alpha``; kept for the ablation table.
    copula_transform : {"normal_scores", "ranks"}
        Rank transform for the relational pathway. ``normal_scores`` is the
        Gaussian-copula transform; ``ranks`` gives Spearman and exists as the
        transform ablation.
    block_size : int
        Length of the contiguous run that is permuted as one unit. ``1``
        (default) permutes individual rows and is only valid when rows are
        exchangeable within a window. For temporally correlated streams set
        this to the autocorrelation length (e.g. tens of consecutive flows) so
        that the null keeps short-range dependence intact; both window lengths
        must be multiples of it.

    Returns
    -------
    CalibratedScores
        ``marginal_evidence`` / ``relational_evidence`` are ``-log10`` of the
        joint family-wise adjusted p-values plus a tiny monotone
        statistic-based tie-break so saturated features remain ordered.

    Notes
    -----
    The same ``B`` permutations drive both pathways. Each pathway's p-values
    are max-statistic adjusted within its own family (``KS_j`` over features,
    ``Z_jk`` over edges), and ``alpha`` is split evenly between the families,
    so the union of a marginal rejection and a relational rejection is
    family-wise controlled at ``alpha`` by the union bound. ``joint=False``
    gives each family the full ``alpha``, which only bounds the union by
    ``2 * alpha`` and reproduces the double-dipping baseline.

    ``n_permutations`` must be large enough to resolve the level it is asked
    for: with the default split, ``B >= 2 / alpha`` is required and a smaller
    ``B`` raises ``ValueError`` rather than returning evidence that can never
    reach significance.
    """
    started = time.perf_counter()
    ref = np.asarray(reference_data, dtype=float)
    cur = np.asarray(current_batch, dtype=float)
    if ref.ndim != NDIM or cur.ndim != NDIM or ref.shape[1] != cur.shape[1]:
        raise ValueError("reference_data and current_batch must be aligned 2D arrays")
    if n_permutations < 1:
        raise ValueError("n_permutations must be >= 1")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    n_ref, d = ref.shape
    n_cur = cur.shape[0]
    zeros = np.zeros(d)
    if n_ref < MIN_SAMPLES or n_cur < MIN_SAMPLES or d < 1:
        return CalibratedScores(
            zeros,
            zeros.copy(),
            zeros.copy(),
            np.ones(d),
            np.ones((d, d)),
            [],
            0,
            {"alpha": alpha, "peel": peel, "degenerate": True},
        )

    if block_size < 1:
        raise ValueError("block_size must be >= 1")
    if n_ref % block_size or n_cur % block_size:
        raise ValueError(
            "block_size must divide both window lengths "
            f"(n_ref={n_ref}, n_cur={n_cur}, block_size={block_size}); "
            "the block-permutation null keeps the reference/current split "
            "balanced, so it cannot straddle a block"
        )

    pooled = np.vstack([ref, cur])
    n_total = n_ref + n_cur

    # --- Marginal KS machinery (ordering of pooled data is label-independent) ---
    order, tie_mask = _pooled_order(pooled)
    obs_ks_full = _ks_statistics(
        _window_labels(n_ref, n_total)[order], tie_mask, n_ref, n_cur
    )
    # A column that never varies in the pooled data cannot carry KS evidence.
    # Leaving it in the family would let tie artefacts set the family maximum.
    ks_columns = np.flatnonzero(pooled.std(axis=0) > SD_FLOOR)
    obs_ks = obs_ks_full[ks_columns]

    # --- Relational machinery on columns varying in both windows ---
    valid = (ref.std(axis=0) > SD_FLOOR) & (cur.std(axis=0) > SD_FLOOR)
    columns = np.flatnonzero(valid)
    use_copula = d >= NDIM and len(columns) >= NDIM
    if use_copula:
        obs_z = cast(np.ndarray, _copula_z(ref, cur, columns, copula_transform))
    else:
        obs_z = np.zeros((0, 0))
    null_ks_max, null_z_max = _null_maxima(
        pooled,
        order,
        tie_mask,
        n_ref,
        n_permutations,
        columns if use_copula else None,
        np.random.default_rng(seed),
        copula_transform,
        block_size,
    )

    # One shared permutation budget, two separately-calibrated families. The
    # statistics are not on a common scale, so alpha is split between the
    # pathways rather than taking max(KS, z): union FWER <= alpha_marg +
    # alpha_rel == alpha. ``joint=False`` reproduces the double-dipping
    # baseline (each pathway at the full alpha), which only bounds the union
    # by 2 * alpha.
    alpha_marg = alpha / 2.0 if (joint and use_copula) else alpha
    alpha_rel = alpha / 2.0 if (joint and use_copula) else alpha

    # Monte-Carlo resolution: the smallest attainable adjusted p-value is
    # 1 / (B + 1), so a level below that can never be reached and the whole
    # call would be vacuously non-significant. Refuse instead of lying.
    min_p = 1.0 / (n_permutations + 1.0)
    if min_p > alpha_marg + TOL:
        raise ValueError(
            f"n_permutations={n_permutations} cannot resolve alpha={alpha_marg:.4g}: "
            f"the smallest attainable adjusted p-value is {min_p:.4g}. "
            f"Use n_permutations >= {int(np.ceil(1.0 / alpha_marg))}."
        )

    marginal_p = np.ones(d)
    marginal_ev = np.zeros(d)
    if ks_columns.size:
        marginal_ks_p = _adjusted_pvalues(obs_ks, null_ks_max)
        marginal_p[ks_columns] = marginal_ks_p
        marginal_ev[ks_columns] = -np.log10(marginal_ks_p) + TIE_BREAK * obs_ks

    rel = _relational_pathway(
        ref,
        cur,
        d,
        columns if use_copula else None,
        obs_z,
        null_z_max,
        alpha,
        alpha_rel,
        peel,
    )
    combined, maxedge_scores, separate_scores = _combine_rankings(
        marginal_ev, marginal_p, rel, alpha_marg, alpha, n_permutations
    )

    elapsed = time.perf_counter() - started
    return CalibratedScores(
        marginal_evidence=marginal_ev,
        relational_evidence=rel["ev"],
        combined_scores=combined,
        marginal_pvalues=marginal_p,
        edge_pvalues=rel["edge_p"],
        selected_features=rel["selected"],
        n_permutations=n_permutations,
        metadata={
            "alpha": alpha,
            "alpha_marginal": alpha_marg,
            "alpha_relational": alpha_rel,
            "peel": peel,
            "joint": joint,
            "copula_transform": copula_transform,
            "permutation_block_size": int(block_size),
            "calibration_method": "permutation_maxT_split_alpha"
            if joint
            else "permutation_maxT_unsplit_alpha",
            "separate_selected_features": rel["separate_selected"],
            "marginal_pvalues": marginal_p.tolist(),
            "constant_columns_masked": [
                int(i) for i in range(d) if i not in set(ks_columns.tolist())
            ],
            "copula_columns": columns.tolist(),
            "max_abs_ref_corr": rel["max_ref_corr"].tolist(),
            "n_ref": int(n_ref),
            "n_cur": int(n_cur),
            "n_features": int(d),
            "timings": {
                "total_s": elapsed,
                "per_permutation_ms": 1000.0 * elapsed / n_permutations,
            },
        },
        marginal_family_pvalues=np.array(marginal_p, copy=True),
        edge_family_pvalues=np.array(rel["edge_p"], copy=True),
        peel_order=rel["selected"],
        maxedge_scores=maxedge_scores,
        separate_scores=separate_scores,
        selected_features_separate=rel["separate_selected"],
    )
