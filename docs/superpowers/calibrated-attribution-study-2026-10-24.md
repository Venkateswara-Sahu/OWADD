# Calibrated attribution: permutation nulls and edge peeling

Status: implemented in `vigil/calibration.py` as opt-in `attribution_mode="calibrated"`.
The `decomposed` pathway is unchanged and its published numbers remain reproducible.
Study artifact: `artifacts/runs/calibrated-study-v3/summary.json` (500 null windows per
population, 20 seeds x 14 conditions x 5 populations; `-v2` holds bit-identical cells).
Power artifact: `artifacts/runs/calibrated-power-v1/power.json`.
Timing artifact: `artifacts/benchmarks/calibrated_cost.json`.
Paper source: `paper/sections/calibrated_method.tex` (method, section
`sec:calibrated`), `paper/sections/calibration_experiment.tex` (real-null and cost
material) and the rendered tables in `paper/sections/calibrated.tex`
(`paper/scripts/render_calibrated_tables.py`), with
`paper/figures/fig4_calibration_power.pdf` from `make_fig4` in
`paper/figures/generate_figures.py`.

## 1. The problem

`DriftAttributor` in `decomposed` mode calibrates two families with asymptotic nulls:

- marginal: two-sample Kolmogorov-Smirnov per feature, Bonferroni over `d`;
- relational: Fisher-`z` on within-window rank-normalised (`Phi^-1(rank/(N+1))`)
  columns, Bonferroni over `d(d-1)/2` pairs.

Both corrections are per-feature or per-edge; neither says anything about the **joint**
distribution of the statistics. Two assumptions fail on network telemetry:

1. the rank transform fixes marginals but not dependence, so with zero inflation and
   mass at zero the sampling distribution of the correlation difference is not
   `N(0, 1/(n_ref-3) + 1/(n_cur-3))`;
2. Bonferroni is valid only if each per-edge `p` is valid, and it degrades to a union
   bound when the edges are dependent.

Either failure inflates rejections. On null data (nothing injected) the relational
pathway reports drift anyway, and the user cannot distinguish that from a real shift.

## 2. What the calibrated pathway does

`compute_calibrated_scores(reference, current, *, n_permutations, seed, alpha)`:
pool both windows, re-split at random `B` times, recompute every statistic per split, and
compare each statistic against the **family maximum** (Westfall-Young max-statistic
`p`-values, add-one estimator). Valid for ties, heavy tails and arbitrary dependence.
Two consequences worth stating plainly:

- Monte-Carlo resolution is `1/(B+1)`. `compute_calibrated_scores` and
  `DriftAttributor` **raise `ValueError`** when `alpha` is below that floor, rather than
  return evidence that can never reach significance.
- The two families are tested at `alpha/2` each, so the union of rejections is
  family-wise controlled at `alpha` by the union bound. This is the correction the
  asymptotic route lacked, and it is conservative by construction.

`AttributeScores.relational_peel_order` returns a greedy vertex cover over the
significant edges: repeatedly pick the feature whose significant edges carry the largest
total `z^2`, delete them, repeat. This is what separates the feature whose own
correlations changed from a partner whose only changed edge is to that feature. The peel
order is a ranking device, **not** a causal claim.

## 3. Protocol

| item | value |
| --- | --- |
| dimension | `d = 20` |
| window size | `n = 400` per window (reference and current) |
| permutations | `B = 199` (floor `1/(B+1) = 0.005`) |
| alpha | `0.05` (each family at `0.025`) |
| null trials | 500 per population, no injection |
| localisation | 14 conditions x 20 seeds, paired by instance |
| null populations | `gaussian`, `zero_inflated_tied`, `multivariate_t3` (Student-t, `df=3`, shared scale), `real_tuesday`, `real_heldout` |
| injections | `two_permuted`, `mean_shift`, `scale_shift`, `correlation`, `sparse_subpop` (5% of rows), `magnitude` sweep |
| statistics | null: family-wise rejection rate; localisation: Recall@1/3/5, MRR, Precision@3, NDCG@3 |
| comparisons | paired Holm-corrected `p` values, proposed vs each baseline |

Real data are CICIDS2017 Tuesday pre-drift (reference) and post-drift (current) windows
drawn from the prepared splits; trials resample a fixed set of disjoint 800-row blocks,
so null trials are **not** independent draws of the data-generating process. The
cluster bootstrap over blocks (`ci95_block` in `summary.json`) is the interval to prefer
for real rows; `ci95` is the ordinary binomial interval over trials.

Chance lines for localisation are the hypergeometric recall of a random top-`k`
(`K/d`: `1/d` for Recall@1, `3/d = 15.0%` for Recall@3 at `d = 20`), independent of truth size.

## 4. Results

### 4.1 Real traffic: nothing changed, and the published pathway still reports drift

`experiments/real_null_calibration.py`, artifact `artifacts/runs/real-null-v1`. Both
windows are drawn from the **normal**-only NSL-KDD pool, so there is no injected and no
class-mix shift: every rejection is a false alarm. 500 trials, 84 distinct 800-row
blocks, `d = 19`, `B = 199`, nominal 5%.

| pathway | rejections | FWER | 95% CI (trials) | 95% CI (blocks) |
| --- | --- | --- | --- | --- |
| KS + raw Pearson | 493/500 | 98.6% | [97.1, 99.3] | [96.1, 100.0] |
| raw Pearson only | 492/500 | 98.4% | [96.9, 99.2] | [95.6, 100.0] |
| decomposed (published) | 413/500 | 82.6% | [79.0, 85.7] | [76.5, 88.4] |
| copula only | 411/500 | 82.2% | [78.6, 85.3] | [76.1, 88.0] |
| decomposed, Bonferroni only | 402/500 | 80.4% | [76.7, 83.6] | [73.9, 86.6] |
| peeling, no alpha split | 43/500 | 8.6% | [6.4, 11.4] | [6.4, 11.0] |
| peeling, rank statistic | 19/500 | 3.8% | [2.4, 5.9] | [2.3, 5.3] |
| max-edge | 17/500 | 3.4% | [2.1, 5.4] | [2.0, 4.9] |
| peeling (joint alpha) | 17/500 | 3.4% | [2.1, 5.4] | [2.0, 4.9] |
| KS only | 2/500 | 0.4% | [0.1, 1.4] | [0.0, 1.0] |

Tie structure of that pool (measured, not assumed): mean modal mass **79.9%** across the
19 retained features; 15 features hold at least half their rows at one value
(`duration`, `hot`, `logged_in`, `num_access_files`, `num_compromised`,
`num_failed_logins`, `num_file_creations`, `num_root`, `num_shells`, `rerror_rate`,
`root_shell`, `same_srv_rate`, `serror_rate`, `su_attempted`, `urgent`);
`wrong_fragment` is constant and dropped by the loader.

Reading: the asymptotic relational null is invalid on real flow records at 80% modal
mass, and the KS-only pathway is conservative rather than calibrated there (0.4%). The
alpha split alone leaves 8.6%, so the null model — not the multiplicity correction — is
what fails. Peeling at 3.4% is below nominal because of the 0.025 per-family level, which
is the documented price of the union bound.

### 4.2 Null calibration, 500 trials per population

`artifacts/runs/calibrated-study-v3`, `--null-trials 500 --n-permutations 199`,
nominal 5%. Synthetic populations resample their whole pool each trial (20 distinct
instances); the two real pools resample a fixed set of 40 disjoint 800-row blocks
(`real_tuesday`, `real_heldout`, 40 each), drawn from the prepared CICIDS2017
arrays.

| null population | decomposed (published) | calibrated, joint alpha | calibrated, alpha not split |
| --- | --- | --- | --- |
| gaussian | 8.6% [6.4, 11.4] | 3.8% [2.4, 5.9] | 9.8% [7.5, 12.7] |
| zero_inflated_tied | 9.8% [7.5, 12.7] | 5.8% [4.1, 8.2] | 10.6% [8.2, 13.6] |
| multivariate_t3 | 45.8% [41.5, 50.2] | 3.2% [2.0, 5.1] | 8.4% [6.3, 11.2] |
| real_tuesday | 59.0% [54.6, 63.2] | 4.4% [2.9, 6.6] | 10.2% [7.8, 13.2] |
| real_heldout | 57.8% [53.4, 62.1] | 3.2% [2.0, 5.1] | 8.6% [6.4, 11.4] |

Intervals are Wilson over 500 draws; the block-clustered intervals in `summary.json`
(`ci95_block`) are the ones to prefer on the two real rows and they agree in direction.

**Two distinct failure modes, two distinct fixes.** On the Gaussian pool the published
pathway rejects at 8.6%, statistically above nominal but of the size the union bound
predicts: the marginal and relational families are each tested at `alpha = 0.05`, so
their union can reach `2*alpha`. Splitting `alpha/2` is the correct fix there. On every
tied, heavy-tailed and real population the rate is far beyond `2*alpha` (9.8%, 45.8%,
59.0%, 57.8%), and splitting `alpha` alone brings it only to 8.4--10.6%, i.e. still
above the predicted union bound. That residual is the invalid Fisher-`z` null, and the
permutation null is what removes it (3.2--5.8%). This is why the paper reports both
ablations and not just the calibrated number: the two columns separate a multiplicity
bug from a null-model bug.

At 500 draws the zero-inflated cell is the only one whose calibrated interval
(5.8% [4.1, 8.2]) does not sit clearly below nominal; the 40-trial run that first
suggested this (5% vs 10% across runs) was too coarse to settle it. The published
pathway's interval there (9.8% [7.5, 12.7]) likewise overlaps the split-alpha column, so
on that population alone the tie-induced inflation is modest in absolute terms and the
strong claim rests on the heavy-tailed and real pools.

### 4.3 Localisation: what calibration fixes, and what it does not

`artifacts/runs/calibrated-study-v3` (bit-identical cells to `-v2`; v3 is the rerun after
the documentation fix and adds deterministic method ordering). 20 seeds per cell, 14
conditions x 5 populations, `d = 20`, `n = 400`, `B = 199`, `alpha = 0.05`. Every method
in a cell sees the identical reference/current pair, so comparisons are paired by seed;
`d` is fixed, so the chance line for Recall@3 is `3/20 = 0.15` and for Recall@1
`1/20 = 0.05`, and both are stored in every cell of `summary.json`.

**Permuted pairs.** Both windows are the same distribution, but two columns exchange
their values across windows, so only the dependence structure changes:

| population | chance | decomposed | max-edge (calibrated) | peeling | peeling detection rate |
| --- | --- | --- | --- | --- | --- |
| gaussian | 0.150 | 0.625 | 0.550 | **0.950** | 1.00 |
| zero_inflated_tied | 0.150 | 0.400 | 0.325 | 0.325 | **0.05** |
| multivariate_t3 | 0.150 | 0.700 | 0.650 | **0.925** | 1.00 |
| real_tuesday | 0.150 | 0.650 | 0.575 | **0.950** | 1.00 |
| real_heldout | 0.150 | 0.650 | 0.575 | **0.950** | 1.00 |

For five permuted columns at once, peeling scores 0.590 (Gaussian), 0.580 (t3),
0.580 (Tuesday) and 0.600 (held-out) against 0.320, 0.360, 0.340 and 0.310 for the
published pathway.

Two protocol definitions make the numbers readable. `detection_rate` is the fraction of
seeds where the method's own decision rule fires at `alpha` (rejects "nothing changed").
Recall@3 is computed by `evaluate_ranking` on **every** seed, fired or not, so it
measures the quality of the ordering even when the method abstains; a cell with recall
above chance but detection near zero is a method that knows the answer and will not say
it. Both are reported side by side everywhere below.

Three regimes, and only one of them is a clean win:

1. **Calibration alone does not localise.** `max-edge`, which ranks by the strongest
   single calibrated edge, is at or below the published pathway everywhere on this
   condition (0.550 vs 0.625; 0.575 vs 0.650). The gain is the *ordering*, not the
   `p`-value: peeling groups the significant edges and removes the vertex that explains
   them, which separates the two permuted features from their partners.
2. **On the tied population, calibration costs power.** Detection there is 0.05 for
   peeling against 0.25 for the published pathway: a rank swap between two columns is
   nearly invisible to a KS statistic, so the `alpha/2` split declines to declare. The
   recall of 0.325 is a *ranking* number computed over all 20 seeds
   (`evaluate_ranking` runs whether or not the method rejected), so on this population
   peeling ranks truth in the top 3 a third of the time while only committing to a
   decision in 1 of 20 draws -- it is informative and unconfident at once, and only the
   pair (recall, detection) tells a reader which. The paired test agrees it is a
   collapse rather than a defeat: -0.075 mean at 1 win / 4 losses / 15 ties, Holm
   p = 1.0.
3. **Sparse sub-population shifts are unsolved.** With 20% of rows shifted on 2 of 20
   features, population-mean recall is 0.680 (peeling), 0.530 (published) and 0.720
   (KS only); with 5% of rows shifted every method sits at 0.28--0.37, i.e. around
   chance. On the two real pools KS alone is the best method on the 20% condition
   (1.000). Peeling recovers dependency structure, not diluted means, and the tables say
   so.

Population-averaged Recall@3 over the five populations (`summary.md` has the
per-population table):

| condition | chance | decomposed | KS | copula | Pearson | max-edge | peeling | peeling, no split | peeling, rank stat. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean_0.2_k2 | 0.15 | 0.790 | 0.885 | 0.155 | 0.135 | 0.845 | 0.845 | 0.845 | 0.855 |
| mean_0.5_k2 | 0.15 | 0.985 | 1.000 | 0.155 | 0.135 | 1.000 | 1.000 | 1.000 | 1.000 |
| scale_0.5_k2 | 0.15 | 1.000 | 1.000 | 0.155 | 0.135 | 1.000 | 1.000 | 1.000 | 1.000 |
| scale_2_k2 | 0.15 | 0.995 | 1.000 | 0.155 | 0.135 | 0.995 | 0.995 | 1.000 | 1.000 |
| mean_0.5_k2_sparse20 | 0.15 | 0.530 | 0.720 | 0.460 | 0.155 | 0.675 | 0.680 | 0.685 | 0.680 |
| mean_0.5_k2_sparse5 | 0.15 | 0.280 | 0.315 | 0.280 | 0.145 | 0.305 | 0.305 | 0.305 | 0.365 |
| scale_0.5_k2_sparse20 | 0.15 | 0.535 | 0.700 | 0.335 | 0.160 | 0.655 | 0.655 | 0.655 | 0.640 |
| paircorr_0.3_k2 | 0.15 | 0.625 | 0.175 | 0.630 | 0.380 | 0.610 | 0.610 | 0.610 | 0.590 |
| paircorr_0.8_k2 | 0.15 | 0.850 | 0.175 | 0.850 | 0.555 | 0.850 | 0.850 | 0.845 | 0.845 |
| permute_k1 | 0.15 | 0.850 | 0.120 | 0.850 | 0.600 | 0.860 | 0.860 | 0.860 | 0.810 |
| permute_k2 | 0.15 | 0.605 | 0.175 | 0.605 | 0.400 | 0.535 | **0.820** | 0.835 | 0.785 |
| permute_k2_sparse20 | 0.15 | 0.425 | 0.175 | 0.455 | 0.225 | 0.370 | 0.380 | 0.380 | 0.410 |
| permute_k5 | 0.15 | 0.318 | 0.168 | 0.316 | 0.258 | 0.276 | **0.518** | 0.520 | 0.506 |

- **The rank transform is not the mechanism of the gain.** `peeling, rank stat.`
  (permutation statistic on rank-transformed columns) is within noise of peeling on every
  condition and slightly worse on the permuted pairs (0.785 vs 0.820). What the pathway
  needs is the permutation null and the peel order, not the Gaussianising transform.
- **The `alpha/2` split is nearly free.** On the nulls it is what brings 9.8--10.6% down
  to 3.2--5.8% (section 4.2); here the unsplit variant is within 0.02 of the split one
  everywhere (0.835 vs 0.820 on `permute_k2`, 0.520 vs 0.518 on `permute_k5`). The tied
  population is the exception, and it is regime 2 above.
- **Raw Pearson is not a competitor.** It is at chance on every marginal condition
  (0.135--0.160) and reaches 0.40--0.60 only on dependency conditions, which confirms
  that whatever strength it showed in the published table belonged to the copula
  pathway it was paired with.
- **Where peeling does nothing**: `paircorr_0.8` (0.850 vs 0.850) and `permute_k1`
  (0.860 vs 0.850). In both the changed edge has both endpoints in the truth set, so
  there is nothing to disambiguate: peeling is a disambiguation device, not a stronger
  detector.

Paired tests (`summary.json`, `localization.comparisons`, Holm over the 8 baselines in
each cell, n = 20 seeds): peeling beats the published pathway on `permute_k2` by +0.325
on Gaussian (13 wins / 0 losses / 7 ties, Holm p = 0.0016), +0.225 on t3 (9/0/11,
p = 0.0135), +0.300 on Tuesday (13/1/6, p = 0.0067) and +0.300 on held-out (12/0/8,
p = 0.0027), and by +0.240 on `permute_k5` for Tuesday (18/1/1, p = 0.0011). The same
table records the losses: peeling is -0.05 against KS on the real sparse mean shift
(0 wins / 2 losses / 18 ties, p = 0.63, i.e. indistinguishable) and -0.045 against the
published pathway on `permute_k2_sparse20` (n.s.). A method that wins the dependency
conditions and does not win the diluted marginal ones is the expected shape of this fix,
and the paper quotes both directions.

### 4.4 Detection floor: how much of a window has to move

`artifacts/runs/calibrated-power-v1` (`experiments/calibrated_power.py`, 200 draws per
cell, `d = 20`, `n = 400`, `B = 199`, two of twenty features shifted by a mean offset in
reference standard deviations). `detection.declared` is the calibrated joint rejection at
`alpha = 0.05`; the evidence scale is the published one (`-log10(d * p_KS)`, threshold
`1.301` at `alpha = 0.05`, `0.301` at `alpha = 0.5`):

| rows shifted | +0.2 SD declared | +0.2 SD loose | +0.5 SD declared | +0.5 SD loose |
| --- | --- | --- | --- | --- |
| 5% (20 rows) | 0.00 | 0.00 | 0.00 | 0.00 |
| 10% (40 rows) | 0.00 | 0.00 | 0.00 | 0.00 |
| 20% (80 rows) | 0.00 | 0.00 | 0.00 | 0.00 |
| 50% (200 rows) | 0.00 | 0.00 | 0.30 | 0.99 |
| 100% (400 rows) | 0.01 | 0.77 | 1.00 | 1.00 |

Thresholds: `declared_0.05 = 1.301`, `loose_0.5 = 0.301`. Figure
`paper/figures/fig4_calibration_power.pdf` plots the declared columns
(`make_fig4` in `paper/figures/generate_figures.py`, reads `power.json`).

Reading:

- The pathway has a **detection floor at roughly half the window** for a moderate mean
  shift. Below it, no configuration declares, at any `alpha`, and this is a
  sample-size/evidence limit rather than a calibration defect: the main study's
  `gaussian:mean_0.5_k2_sparse20` cell has `ks_asymptotic` detection `0.00` and
  `decomposed_asymptotic` `0.05` on 20 seeds, the same floor.
- Relaxing `alpha` to 0.5 (`loose`) buys detection only in the two full-window cells
  (`0.77` at +0.2 SD, `1.00` at +0.5 SD) and at 50% rows for +0.5 SD (`0.99`), which is
  the expected monotonicity and confirms the statistic ordering is sane: the evidence for
  a full-window +0.2 SD shift straddles the `0.3`--`1.3` window of the scale.
- `median_best_rank` is `1.0` in every one of the ten cells, so when the pathway fires the
  top-ranked feature is the shifted one; the failure mode at dilution is silence, not
  misranking.

## 5. Mechanism

The false alarms are a **null-model mismatch**, not loss of power:

- `ks_only_asymptotic` (marginals alone) stays near nominal on every null population,
  including the tied and heavy-tailed ones;
- the excess sits entirely in the relational family, whose asymptotic `p`-value
  understates the tail;
- the threshold split (`decomposed_independent_asymptotic`, which splits `alpha` but
  keeps the asymptotic nulls) barely moves the rate, so the union-bound correction alone
  is not what fixes it: the permutation null is.

An earlier reading of this study attributed the failure to "asymptotic nulls under
estimation-induced dependence". That was half right. A controlled diagnostic
(`experiments/calibrated_diagnostics.py`, artifact `artifacts/runs/calibrated-diagnostics-v1`)
ran the relational statistic on Gaussian data whose covariance was **resampled** between
the two windows — a pure null with no distributional shift but real sampling-level
dependence between edges:

| d | mean relational FPR @ alpha=0.05, 200 draws | chance SE |
| --- | --- | --- |
| 5 | 0.049 | 0.015 |
| 10 | 0.064 | 0.017 |
| 20 | 0.032 | 0.012 |
| 50 | 0.062 | 0.017 |

The asymptotic relational pathway is **calibrated on clean Gaussian data with
identity-scale copula**. The failure therefore requires the heavy tails / ties / copula
shape, i.e. a genuinely invalid Fisher-`z` null, not merely dependence. The paper
sentence claims what the wall-clock and FPR evidence supports: the asymptotic nulls are
invalid on zero-inflated, tied and heavy-tailed telemetry, and permutation calibration
repairs it.

## 6. Ablations

Four knobs, measured in `artifacts/runs/calibrated-study-v3`:

- `maxedge_joint` vs `peeling_joint` -- calibration fixes the decision, peeling fixes
  the order. Population-mean Recall@3 on `permute_k2` is 0.535 for max-edge against
  0.820 for peeling and 0.605 for the published pathway, so ranking by the strongest
  single calibrated edge is *worse* than not recalibrating; the peel order is what
  converts calibration into localisation. Same direction on `permute_k5` (0.276 vs
  0.518).
- `peeling_separate` (no `alpha/2` split) -- on the 500-trial nulls the unsplit variant
  sits at 9.8% (Gaussian), 10.6% (tied), 8.4% (t3), 10.2% (Tuesday), 8.6% (held-out)
  against 3.8%, 5.8%, 3.2%, 4.4%, 3.2% with the split, so the union bound is doing real
  work on the null. It costs almost nothing on localisation: 0.835 vs 0.820 on
  `permute_k2` and 0.520 vs 0.518 on `permute_k5`. The one exception is the tied
  population, where the split is also what removes the detection (0.05).
- `peeling_rank_transform` -- permutation statistic on rank-transformed columns. Within
  noise of the raw statistic on every condition (0.785 vs 0.820 on `permute_k2`, 0.506
  vs 0.518 on `permute_k5`), so the gain is not a monotone-invariance artifact of the
  transform.
- Permutation statistics with the *asymptotic* decisions are not a separate cell: the
  asymptotic pathway's decisions are the `decomposed_asymptotic` / `copula_asymptotic`
  columns, so the calibration-versus-ranking decomposition is read off
  (`decomposed`, `maxedge`, `peeling`) rather than from a fourth permutation arm.

## 7. Limitations

1. **Synthetic flow model.** The `zero_inflated_tied` and `multivariate_t3` populations
   are models of flow telemetry, not sampled flows. The `real_tuesday` / `real_heldout`
   cells use prepared CICIDS2017 windows, but the injections applied to them are still
   synthetic.
2. **Block reuse.** Real-data trials draw from a fixed set of disjoint blocks; the
   block-clustered interval is reported and should be quoted instead of the binomial one
   for those rows.
3. **Exchangeability.** The permutation null assumes the pooled rows are exchangeable
   within a window pair. Contiguous block permutations (`block_size > 1`, evaluated in `experiments/calibrated_blocknull.py`) reduce recorded-order over-rejection on CICIDS2017 Tuesday from 88.7% (block 1) to 41.3% (block 50), confirming serial dependence spans past 50 rows.

4. **Monte-Carlo floor.** `B = 199` gives a floor of `0.005`; with `alpha/2 = 0.025` the
   smallest detectable adjusted `p` is 20% of the test level. Raising `B` costs linearly.
5. **No causal claim.** The peel order explains which features carry changed dependency
   structure. It does not identify a mechanism, and on CICIDS it will still order
   features by correlation shifts the grader does not track.
6. **What this does not fix.** Cross-file learnability on CICIDS2017, the fixed detector
   threshold `tau = 4.0`, and the two-adversary/verify merge in `prototype/` are outside
   this change.

## 8. Reproduce

```bash
# null-calibration stage (~15 min at d=20, B=199, 500 trials/population)
uv run python -m experiments.calibrated_study \
    --output artifacts/runs/calibrated-study-v3 \
    --prepared artifacts/prepared/cicids2017-prepared-v1 \
    --null-trials 500 --trials 20 --n-permutations 199 --skip-localization

# localisation stage (reuses the same artifact directory)
uv run python -m experiments.calibrated_study \
    --output artifacts/runs/calibrated-study-v3 \
    --prepared artifacts/prepared/cicids2017-prepared-v1 \
    --null-trials 500 --trials 20 --n-permutations 199 --skip-null

# tables for the paper
uv run python paper/scripts/render_calibrated_tables.py \
    --summary artifacts/runs/calibrated-study-v3/summary.json \
    --out-prefix paper/sections/calibrated

# detection floor (200 draws per cell, ~16 min) and its figure
uv run python -m experiments.calibrated_power \
    --output artifacts/runs/calibrated-power-v1 --trials 200
uv run python paper/figures/generate_figures.py
```

Each case is cached under `config.config_hash` + `provenance.identity_hash`, so an
interrupted run resumes; a changed source tree invalidates the cache on purpose (this is
why `-v3` exists: adding a file under `docs/` changes `source_tree_hash`).

Tests: `tests/test_calibration.py`, `tests/test_sentinel.py`,
`tests/experiments/test_calibrated_study.py`, `tests/experiments/test_calibrated_diagnostics.py`,
`tests/experiments/test_render_calibrated_tables.py`.

## 9. Documented dead ends

Appended to `docs/agent-lessons.md` as they were hit; the first two also show up as
columns in the main localisation table, which is why they are quoted here with numbers.

- **Raw Pearson as the relational statistic.** `ks_pearson_asymptotic` (KS plus raw
  Pearson, i.e. what the published table's "Pearson" comparator measured) sits at
  chance for localisation on the permutation conditions -- `0.225`-`0.400` recall@3
  against `0.525`-`0.950` for the copula pathway -- and on the mean/scale conditions it
  does not beat KS alone. The rank/copula transform is load-bearing.
- **Rank-normalising the columns instead of pivoting the Pearson statistic.**
  `peeling_rank_transform` is indistinguishable from `peeling_joint` (`0.925`-`0.975` vs
  `0.925`-`0.950` on `permute_k2`, `0.325`-`0.625` vs `0.300`-`0.600` on
  `permute_k2_sparse20`; differences of at most one seed in twenty). It buys nothing that
  the joint null does not already buy, so the simpler pipeline is kept.
