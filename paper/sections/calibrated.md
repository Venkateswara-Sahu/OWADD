Study version: `2`
Permutations: 199, alpha: 0.05
Null trials: 500, localization seeds: 20
Datasets: 5, conditions: 14

## Null calibration

| null population | Decomposed (published) | Decomposed, alpha split | KS only | Copula (Fisher-$z$) | Pearson (raw) | Calibrated, max-edge | Calibrated, peeling | Calibrated, peeling, alpha not split | Calibrated, peeling, rank copula |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Gaussian | 8.6% [6.4-11.4] | 3.8% [2.4-5.9] | 3.8% [2.4-5.9] | 4.8% [3.2-7.0] | 4.4% [2.9-6.6] | 3.8% [2.4-5.9] | 3.8% [2.4-5.9] | 9.8% [7.5-12.7] | 3.4% [2.1-5.4] |
| Zero-inflated, tied | 9.8% [7.5-12.7] | 7.4% [5.4-10.0] | 0.2% [0.0-1.1] | 9.6% [7.3-12.5] | 100.0% [99.2-100.0] | 5.8% [4.1-8.2] | 5.8% [4.1-8.2] | 10.6% [8.2-13.6] | 5.2% [3.6-7.5] |
| Multivariate $t_3$ | 45.8% [41.5-50.2] | 36.2% [32.1-40.5] | 2.6% [1.5-4.4] | 44.8% [40.5-49.2] | 100.0% [99.2-100.0] | 3.2% [2.0-5.1] | 3.2% [2.0-5.1] | 8.4% [6.3-11.2] | 3.4% [2.1-5.4] |
| CICIDS2017 Tuesday (no injection) | 59.0% [54.6-63.2] | 54.4% [50.0-58.7] | 2.0% [1.1-3.6] | 59.0% [54.6-63.2] | 100.0% [99.2-100.0] | 4.4% [2.9-6.6] | 4.4% [2.9-6.6] | 10.2% [7.8-13.2] | 3.8% [2.4-5.9] |
| CICIDS2017 held-out (no injection) | 57.8% [53.4-62.1] | 53.2% [48.8-57.5] | 1.2% [0.6-2.6] | 57.8% [53.4-62.1] | 99.8% [98.9-100.0] | 3.2% [2.0-5.1] | 3.2% [2.0-5.1] | 8.6% [6.4-11.4] | 3.2% [2.0-5.1] |

Real-data rows are genuine nulls: both windows are drawn from one
row-disjoint 800-row block of a single split, so nothing has changed
beyond sampling. Trials resample a fixed set of blocks, so the
block-clustered intervals (`ci95_block` in `summary.json`) are the
ones to quote: gaussian=20, zero_inflated_tied=20, multivariate_t3=20, real_tuesday=40, real_heldout=40.

## Localization

| dataset | condition | chance | Decomposed R@3 | KS R@3 | Copula R@3 | Pearson R@3 | Max-edge R@3 | Peeling R@3 | Peeling (rank) R@3 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gaussian | mean_0.2_k2 | 15.0% | 55.0% | 72.5% | 22.5% | 25.0% | 67.5% | 67.5% | 67.5% |
| gaussian | mean_0.5_k2 | 15.0% | 100.0% | 100.0% | 22.5% | 25.0% | 100.0% | 100.0% | 100.0% |
| gaussian | mean_0.5_k2_sparse20 | 15.0% | 32.5% | 27.5% | 30.0% | 22.5% | 30.0% | 30.0% | 35.0% |
| gaussian | mean_0.5_k2_sparse5 | 15.0% | 25.0% | 15.0% | 25.0% | 22.5% | 20.0% | 20.0% | 22.5% |
| gaussian | paircorr_0.3_k2 | 15.0% | 70.0% | 17.5% | 70.0% | 70.0% | 67.5% | 67.5% | 60.0% |
| gaussian | paircorr_0.8_k2 | 15.0% | 100.0% | 17.5% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| gaussian | permute_k1 | 15.0% | 100.0% | 10.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| gaussian | permute_k2 | 15.0% | 62.5% | 17.5% | 62.5% | 52.5% | 55.0% | 95.0% | 87.5% |
| gaussian | permute_k2_sparse20 | 15.0% | 37.5% | 17.5% | 47.5% | 37.5% | 37.5% | 37.5% | 37.5% |
| gaussian | permute_k5 | 15.0% | 32.0% | 11.0% | 32.0% | 26.0% | 24.0% | 59.0% | 57.0% |
| gaussian | scale_0.5_k2 | 15.0% | 100.0% | 100.0% | 22.5% | 25.0% | 100.0% | 100.0% | 100.0% |
| gaussian | scale_0.5_k2_sparse20 | 15.0% | 30.0% | 27.5% | 22.5% | 22.5% | 35.0% | 35.0% | 30.0% |
| gaussian | scale_2_k2 | 15.0% | 100.0% | 100.0% | 22.5% | 25.0% | 100.0% | 100.0% | 100.0% |
| multivariate_t3 | mean_0.2_k2 | 15.0% | 40.0% | 70.0% | 10.0% | 7.5% | 55.0% | 55.0% | 60.0% |
| multivariate_t3 | mean_0.5_k2 | 15.0% | 92.5% | 100.0% | 10.0% | 7.5% | 100.0% | 100.0% | 100.0% |
| multivariate_t3 | mean_0.5_k2_sparse20 | 15.0% | 15.0% | 32.5% | 12.5% | 7.5% | 20.0% | 20.0% | 22.5% |
| multivariate_t3 | mean_0.5_k2_sparse5 | 15.0% | 15.0% | 7.5% | 15.0% | 7.5% | 7.5% | 7.5% | 17.5% |
| multivariate_t3 | paircorr_0.3_k2 | 15.0% | 60.0% | 7.5% | 60.0% | 37.5% | 60.0% | 60.0% | 60.0% |
| multivariate_t3 | paircorr_0.8_k2 | 15.0% | 100.0% | 7.5% | 100.0% | 77.5% | 100.0% | 100.0% | 100.0% |
| multivariate_t3 | permute_k1 | 15.0% | 100.0% | 0.0% | 100.0% | 65.0% | 100.0% | 100.0% | 100.0% |
| multivariate_t3 | permute_k2 | 15.0% | 70.0% | 7.5% | 70.0% | 45.0% | 65.0% | 92.5% | 92.5% |
| multivariate_t3 | permute_k2_sparse20 | 15.0% | 40.0% | 7.5% | 42.5% | 15.0% | 30.0% | 30.0% | 32.5% |
| multivariate_t3 | permute_k5 | 15.0% | 36.0% | 18.0% | 36.0% | 32.0% | 32.0% | 58.0% | 59.0% |
| multivariate_t3 | scale_0.5_k2 | 15.0% | 100.0% | 100.0% | 10.0% | 7.5% | 100.0% | 100.0% | 100.0% |
| multivariate_t3 | scale_0.5_k2_sparse20 | 15.0% | 12.5% | 25.0% | 12.5% | 7.5% | 20.0% | 20.0% | 17.5% |
| multivariate_t3 | scale_2_k2 | 15.0% | 97.5% | 100.0% | 10.0% | 7.5% | 97.5% | 97.5% | 100.0% |
| real_heldout | mean_0.2_k2 | 15.0% | 100.0% | 100.0% | 15.0% | 12.5% | 100.0% | 100.0% | 100.0% |
| real_heldout | mean_0.5_k2 | 15.0% | 100.0% | 100.0% | 15.0% | 12.5% | 100.0% | 100.0% | 100.0% |
| real_heldout | mean_0.5_k2_sparse20 | 15.0% | 57.5% | 100.0% | 57.5% | 15.0% | 92.5% | 95.0% | 87.5% |
| real_heldout | mean_0.5_k2_sparse5 | 15.0% | 40.0% | 32.5% | 42.5% | 15.0% | 35.0% | 35.0% | 47.5% |
| real_heldout | paircorr_0.3_k2 | 15.0% | 55.0% | 15.0% | 55.0% | 30.0% | 55.0% | 55.0% | 57.5% |
| real_heldout | paircorr_0.8_k2 | 15.0% | 60.0% | 15.0% | 60.0% | 25.0% | 60.0% | 60.0% | 60.0% |
| real_heldout | permute_k1 | 15.0% | 100.0% | 5.0% | 100.0% | 60.0% | 100.0% | 100.0% | 100.0% |
| real_heldout | permute_k2 | 15.0% | 65.0% | 15.0% | 65.0% | 37.5% | 57.5% | 95.0% | 97.5% |
| real_heldout | permute_k2_sparse20 | 15.0% | 62.5% | 15.0% | 62.5% | 22.5% | 57.5% | 60.0% | 62.5% |
| real_heldout | permute_k5 | 15.0% | 31.0% | 16.0% | 31.0% | 26.0% | 29.0% | 60.0% | 60.0% |
| real_heldout | scale_0.5_k2 | 15.0% | 100.0% | 100.0% | 15.0% | 12.5% | 100.0% | 100.0% | 100.0% |
| real_heldout | scale_0.5_k2_sparse20 | 15.0% | 60.0% | 97.5% | 55.0% | 20.0% | 85.0% | 85.0% | 85.0% |
| real_heldout | scale_2_k2 | 15.0% | 100.0% | 100.0% | 15.0% | 12.5% | 100.0% | 100.0% | 100.0% |
| real_tuesday | mean_0.2_k2 | 15.0% | 100.0% | 100.0% | 17.5% | 10.0% | 100.0% | 100.0% | 100.0% |
| real_tuesday | mean_0.5_k2 | 15.0% | 100.0% | 100.0% | 17.5% | 10.0% | 100.0% | 100.0% | 100.0% |
| real_tuesday | mean_0.5_k2_sparse20 | 15.0% | 60.0% | 100.0% | 55.0% | 20.0% | 95.0% | 95.0% | 95.0% |
| real_tuesday | mean_0.5_k2_sparse5 | 15.0% | 42.5% | 55.0% | 40.0% | 15.0% | 57.5% | 57.5% | 60.0% |
| real_tuesday | paircorr_0.3_k2 | 15.0% | 55.0% | 27.5% | 55.0% | 32.5% | 55.0% | 55.0% | 57.5% |
| real_tuesday | paircorr_0.8_k2 | 15.0% | 65.0% | 27.5% | 65.0% | 30.0% | 65.0% | 65.0% | 62.5% |
| real_tuesday | permute_k1 | 15.0% | 100.0% | 20.0% | 100.0% | 55.0% | 100.0% | 100.0% | 100.0% |
| real_tuesday | permute_k2 | 15.0% | 65.0% | 27.5% | 65.0% | 40.0% | 57.5% | 95.0% | 92.5% |
| real_tuesday | permute_k2_sparse20 | 15.0% | 60.0% | 27.5% | 60.0% | 22.5% | 50.0% | 52.5% | 60.0% |
| real_tuesday | permute_k5 | 15.0% | 34.0% | 19.0% | 34.0% | 24.0% | 29.0% | 58.0% | 60.0% |
| real_tuesday | scale_0.5_k2 | 15.0% | 100.0% | 100.0% | 17.5% | 10.0% | 100.0% | 100.0% | 100.0% |
| real_tuesday | scale_0.5_k2_sparse20 | 15.0% | 67.5% | 100.0% | 55.0% | 15.0% | 90.0% | 90.0% | 90.0% |
| real_tuesday | scale_2_k2 | 15.0% | 100.0% | 100.0% | 17.5% | 10.0% | 100.0% | 100.0% | 100.0% |
| zero_inflated_tied | mean_0.2_k2 | 15.0% | 100.0% | 100.0% | 12.5% | 12.5% | 100.0% | 100.0% | 100.0% |
| zero_inflated_tied | mean_0.5_k2 | 15.0% | 100.0% | 100.0% | 12.5% | 12.5% | 100.0% | 100.0% | 100.0% |
| zero_inflated_tied | mean_0.5_k2_sparse20 | 15.0% | 100.0% | 100.0% | 75.0% | 12.5% | 100.0% | 100.0% | 100.0% |
| zero_inflated_tied | mean_0.5_k2_sparse5 | 15.0% | 17.5% | 47.5% | 17.5% | 12.5% | 32.5% | 32.5% | 35.0% |
| zero_inflated_tied | paircorr_0.3_k2 | 15.0% | 72.5% | 20.0% | 75.0% | 20.0% | 67.5% | 67.5% | 60.0% |
| zero_inflated_tied | paircorr_0.8_k2 | 15.0% | 100.0% | 20.0% | 100.0% | 45.0% | 100.0% | 100.0% | 100.0% |
| zero_inflated_tied | permute_k1 | 15.0% | 25.0% | 25.0% | 25.0% | 20.0% | 30.0% | 30.0% | 5.0% |
| zero_inflated_tied | permute_k2 | 15.0% | 40.0% | 20.0% | 40.0% | 25.0% | 32.5% | 32.5% | 22.5% |
| zero_inflated_tied | permute_k2_sparse20 | 15.0% | 12.5% | 20.0% | 15.0% | 15.0% | 10.0% | 10.0% | 12.5% |
| zero_inflated_tied | permute_k5 | 15.0% | 26.0% | 20.0% | 25.0% | 21.0% | 24.0% | 24.0% | 17.0% |
| zero_inflated_tied | scale_0.5_k2 | 15.0% | 100.0% | 100.0% | 12.5% | 12.5% | 100.0% | 100.0% | 100.0% |
| zero_inflated_tied | scale_0.5_k2_sparse20 | 15.0% | 97.5% | 100.0% | 22.5% | 15.0% | 97.5% | 97.5% | 97.5% |
| zero_inflated_tied | scale_2_k2 | 15.0% | 100.0% | 100.0% | 12.5% | 12.5% | 100.0% | 100.0% | 100.0% |

## Paired significance tests

| cell | baseline | peeling | baseline R@3 | delta | W/L/T | raw p | Holm p | n |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gaussian:mean_0.2_k2 | copula_asymptotic | 67.5 | 22.5 | 45.0 | 14/1/5 | 0.001 | 0.012 | 20 |
| gaussian:mean_0.2_k2 | decomposed_asymptotic | 67.5 | 55.0 | 12.5 | 4/0/16 | 0.059 | 0.411 | 20 |
| gaussian:mean_0.2_k2 | decomposed_bonferroni | 67.5 | 55.0 | 12.5 | 4/0/16 | 0.059 | 0.411 | 20 |
| gaussian:mean_0.2_k2 | ks_asymptotic | 67.5 | 72.5 | -5.0 | 0/2/18 | 0.157 | 0.629 | 20 |
| gaussian:mean_0.2_k2 | ks_pearson_asymptotic | 67.5 | 57.5 | 10.0 | 3/0/17 | 0.102 | 0.512 | 20 |
| gaussian:mean_0.2_k2 | maxedge_joint | 67.5 | 67.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.2_k2 | pearson_asymptotic | 67.5 | 25.0 | 42.5 | 13/1/6 | 0.002 | 0.016 | 20 |
| gaussian:mean_0.2_k2 | peeling_rank_transform | 67.5 | 67.5 | 0.0 | 1/2/17 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.2_k2 | peeling_separate | 67.5 | 67.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2 | copula_asymptotic | 100.0 | 22.5 | 77.5 | 19/0/1 | 0.000 | 0.001 | 20 |
| gaussian:mean_0.5_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2 | ks_pearson_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2 | pearson_asymptotic | 100.0 | 25.0 | 75.0 | 18/0/2 | 0.000 | 0.001 | 20 |
| gaussian:mean_0.5_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse20 | copula_asymptotic | 30.0 | 30.0 | 0.0 | 4/4/12 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse20 | decomposed_asymptotic | 30.0 | 32.5 | -2.5 | 2/3/15 | 0.655 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse20 | decomposed_bonferroni | 30.0 | 32.5 | -2.5 | 2/3/15 | 0.655 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse20 | ks_asymptotic | 30.0 | 27.5 | 2.5 | 4/3/13 | 0.792 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse20 | ks_pearson_asymptotic | 30.0 | 22.5 | 7.5 | 3/0/17 | 0.083 | 0.749 | 20 |
| gaussian:mean_0.5_k2_sparse20 | maxedge_joint | 30.0 | 30.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse20 | pearson_asymptotic | 30.0 | 22.5 | 7.5 | 4/1/15 | 0.180 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse20 | peeling_rank_transform | 30.0 | 35.0 | -5.0 | 1/3/16 | 0.317 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse20 | peeling_separate | 30.0 | 30.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse5 | copula_asymptotic | 20.0 | 25.0 | -5.0 | 2/4/14 | 0.414 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse5 | decomposed_asymptotic | 20.0 | 25.0 | -5.0 | 1/3/16 | 0.317 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse5 | decomposed_bonferroni | 20.0 | 25.0 | -5.0 | 1/3/16 | 0.317 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse5 | ks_asymptotic | 20.0 | 15.0 | 5.0 | 3/2/15 | 0.480 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse5 | ks_pearson_asymptotic | 20.0 | 22.5 | -2.5 | 1/2/17 | 0.564 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse5 | maxedge_joint | 20.0 | 20.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse5 | pearson_asymptotic | 20.0 | 22.5 | -2.5 | 2/3/15 | 0.655 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse5 | peeling_rank_transform | 20.0 | 22.5 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| gaussian:mean_0.5_k2_sparse5 | peeling_separate | 20.0 | 20.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:paircorr_0.3_k2 | copula_asymptotic | 67.5 | 70.0 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| gaussian:paircorr_0.3_k2 | decomposed_asymptotic | 67.5 | 70.0 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| gaussian:paircorr_0.3_k2 | decomposed_bonferroni | 67.5 | 70.0 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| gaussian:paircorr_0.3_k2 | ks_asymptotic | 67.5 | 17.5 | 50.0 | 15/1/4 | 0.001 | 0.007 | 20 |
| gaussian:paircorr_0.3_k2 | ks_pearson_asymptotic | 67.5 | 70.0 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| gaussian:paircorr_0.3_k2 | maxedge_joint | 67.5 | 67.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:paircorr_0.3_k2 | pearson_asymptotic | 67.5 | 70.0 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| gaussian:paircorr_0.3_k2 | peeling_rank_transform | 67.5 | 60.0 | 7.5 | 3/0/17 | 0.083 | 0.666 | 20 |
| gaussian:paircorr_0.3_k2 | peeling_separate | 67.5 | 67.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:paircorr_0.8_k2 | copula_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:paircorr_0.8_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:paircorr_0.8_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:paircorr_0.8_k2 | ks_asymptotic | 100.0 | 17.5 | 82.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| gaussian:paircorr_0.8_k2 | ks_pearson_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:paircorr_0.8_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:paircorr_0.8_k2 | pearson_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:paircorr_0.8_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:paircorr_0.8_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k1 | copula_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k1 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k1 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k1 | ks_asymptotic | 100.0 | 10.0 | 90.0 | 18/0/2 | 0.000 | 0.000 | 20 |
| gaussian:permute_k1 | ks_pearson_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k1 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k1 | pearson_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k1 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k1 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k2 | copula_asymptotic | 95.0 | 62.5 | 32.5 | 13/0/7 | 0.000 | 0.002 | 20 |
| gaussian:permute_k2 | decomposed_asymptotic | 95.0 | 62.5 | 32.5 | 13/0/7 | 0.000 | 0.002 | 20 |
| gaussian:permute_k2 | decomposed_bonferroni | 95.0 | 62.5 | 32.5 | 13/0/7 | 0.000 | 0.002 | 20 |
| gaussian:permute_k2 | ks_asymptotic | 95.0 | 17.5 | 77.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| gaussian:permute_k2 | ks_pearson_asymptotic | 95.0 | 52.5 | 42.5 | 17/0/3 | 0.000 | 0.000 | 20 |
| gaussian:permute_k2 | maxedge_joint | 95.0 | 55.0 | 40.0 | 16/0/4 | 0.000 | 0.000 | 20 |
| gaussian:permute_k2 | pearson_asymptotic | 95.0 | 52.5 | 42.5 | 17/0/3 | 0.000 | 0.000 | 20 |
| gaussian:permute_k2 | peeling_rank_transform | 95.0 | 87.5 | 7.5 | 3/0/17 | 0.083 | 0.167 | 20 |
| gaussian:permute_k2 | peeling_separate | 95.0 | 97.5 | -2.5 | 0/1/19 | 0.317 | 0.317 | 20 |
| gaussian:permute_k2_sparse20 | copula_asymptotic | 37.5 | 47.5 | -10.0 | 2/6/12 | 0.157 | 1.000 | 20 |
| gaussian:permute_k2_sparse20 | decomposed_asymptotic | 37.5 | 37.5 | 0.0 | 3/3/14 | 1.000 | 1.000 | 20 |
| gaussian:permute_k2_sparse20 | decomposed_bonferroni | 37.5 | 37.5 | 0.0 | 3/3/14 | 1.000 | 1.000 | 20 |
| gaussian:permute_k2_sparse20 | ks_asymptotic | 37.5 | 17.5 | 20.0 | 8/2/10 | 0.046 | 0.410 | 20 |
| gaussian:permute_k2_sparse20 | ks_pearson_asymptotic | 37.5 | 32.5 | 5.0 | 3/2/15 | 0.480 | 1.000 | 20 |
| gaussian:permute_k2_sparse20 | maxedge_joint | 37.5 | 37.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k2_sparse20 | pearson_asymptotic | 37.5 | 37.5 | 0.0 | 2/2/16 | 1.000 | 1.000 | 20 |
| gaussian:permute_k2_sparse20 | peeling_rank_transform | 37.5 | 37.5 | 0.0 | 1/1/18 | 1.000 | 1.000 | 20 |
| gaussian:permute_k2_sparse20 | peeling_separate | 37.5 | 37.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:permute_k5 | copula_asymptotic | 59.0 | 32.0 | 27.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| gaussian:permute_k5 | decomposed_asymptotic | 59.0 | 32.0 | 27.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| gaussian:permute_k5 | decomposed_bonferroni | 59.0 | 32.0 | 27.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| gaussian:permute_k5 | ks_asymptotic | 59.0 | 11.0 | 48.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| gaussian:permute_k5 | ks_pearson_asymptotic | 59.0 | 26.0 | 33.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| gaussian:permute_k5 | maxedge_joint | 59.0 | 24.0 | 35.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| gaussian:permute_k5 | pearson_asymptotic | 59.0 | 26.0 | 33.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| gaussian:permute_k5 | peeling_rank_transform | 59.0 | 57.0 | 2.0 | 2/0/18 | 0.180 | 0.359 | 20 |
| gaussian:permute_k5 | peeling_separate | 59.0 | 59.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_0.5_k2 | copula_asymptotic | 100.0 | 22.5 | 77.5 | 19/0/1 | 0.000 | 0.001 | 20 |
| gaussian:scale_0.5_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_0.5_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_0.5_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_0.5_k2 | ks_pearson_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_0.5_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_0.5_k2 | pearson_asymptotic | 100.0 | 25.0 | 75.0 | 18/0/2 | 0.000 | 0.001 | 20 |
| gaussian:scale_0.5_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_0.5_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_0.5_k2_sparse20 | copula_asymptotic | 35.0 | 22.5 | 12.5 | 6/1/13 | 0.059 | 0.411 | 20 |
| gaussian:scale_0.5_k2_sparse20 | decomposed_asymptotic | 35.0 | 30.0 | 5.0 | 3/1/16 | 0.317 | 1.000 | 20 |
| gaussian:scale_0.5_k2_sparse20 | decomposed_bonferroni | 35.0 | 30.0 | 5.0 | 3/1/16 | 0.317 | 1.000 | 20 |
| gaussian:scale_0.5_k2_sparse20 | ks_asymptotic | 35.0 | 27.5 | 7.5 | 4/1/15 | 0.180 | 0.944 | 20 |
| gaussian:scale_0.5_k2_sparse20 | ks_pearson_asymptotic | 35.0 | 25.0 | 10.0 | 4/0/16 | 0.046 | 0.364 | 20 |
| gaussian:scale_0.5_k2_sparse20 | maxedge_joint | 35.0 | 35.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_0.5_k2_sparse20 | pearson_asymptotic | 35.0 | 22.5 | 12.5 | 5/0/15 | 0.025 | 0.228 | 20 |
| gaussian:scale_0.5_k2_sparse20 | peeling_rank_transform | 35.0 | 30.0 | 5.0 | 2/0/18 | 0.157 | 0.944 | 20 |
| gaussian:scale_0.5_k2_sparse20 | peeling_separate | 35.0 | 35.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_2_k2 | copula_asymptotic | 100.0 | 22.5 | 77.5 | 19/0/1 | 0.000 | 0.001 | 20 |
| gaussian:scale_2_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_2_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_2_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_2_k2 | ks_pearson_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_2_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_2_k2 | pearson_asymptotic | 100.0 | 25.0 | 75.0 | 18/0/2 | 0.000 | 0.001 | 20 |
| gaussian:scale_2_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| gaussian:scale_2_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.2_k2 | copula_asymptotic | 55.0 | 10.0 | 45.0 | 14/0/6 | 0.001 | 0.004 | 20 |
| multivariate_t3:mean_0.2_k2 | decomposed_asymptotic | 55.0 | 40.0 | 15.0 | 5/0/15 | 0.034 | 0.169 | 20 |
| multivariate_t3:mean_0.2_k2 | decomposed_bonferroni | 55.0 | 40.0 | 15.0 | 5/0/15 | 0.034 | 0.169 | 20 |
| multivariate_t3:mean_0.2_k2 | ks_asymptotic | 55.0 | 70.0 | -15.0 | 0/6/14 | 0.014 | 0.086 | 20 |
| multivariate_t3:mean_0.2_k2 | ks_pearson_asymptotic | 55.0 | 7.5 | 47.5 | 15/0/5 | 0.000 | 0.003 | 20 |
| multivariate_t3:mean_0.2_k2 | maxedge_joint | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.2_k2 | pearson_asymptotic | 55.0 | 7.5 | 47.5 | 15/0/5 | 0.000 | 0.003 | 20 |
| multivariate_t3:mean_0.2_k2 | peeling_rank_transform | 55.0 | 60.0 | -5.0 | 0/2/18 | 0.157 | 0.472 | 20 |
| multivariate_t3:mean_0.2_k2 | peeling_separate | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2 | copula_asymptotic | 100.0 | 10.0 | 90.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| multivariate_t3:mean_0.5_k2 | decomposed_asymptotic | 100.0 | 92.5 | 7.5 | 3/0/17 | 0.083 | 0.500 | 20 |
| multivariate_t3:mean_0.5_k2 | decomposed_bonferroni | 100.0 | 92.5 | 7.5 | 3/0/17 | 0.083 | 0.500 | 20 |
| multivariate_t3:mean_0.5_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2 | ks_pearson_asymptotic | 100.0 | 32.5 | 67.5 | 18/0/2 | 0.000 | 0.001 | 20 |
| multivariate_t3:mean_0.5_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2 | pearson_asymptotic | 100.0 | 7.5 | 92.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| multivariate_t3:mean_0.5_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse20 | copula_asymptotic | 20.0 | 12.5 | 7.5 | 6/2/12 | 0.366 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse20 | decomposed_asymptotic | 20.0 | 15.0 | 5.0 | 4/2/14 | 0.414 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse20 | decomposed_bonferroni | 20.0 | 15.0 | 5.0 | 4/2/14 | 0.414 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse20 | ks_asymptotic | 20.0 | 32.5 | -12.5 | 1/6/13 | 0.059 | 0.529 | 20 |
| multivariate_t3:mean_0.5_k2_sparse20 | ks_pearson_asymptotic | 20.0 | 7.5 | 12.5 | 7/2/11 | 0.096 | 0.765 | 20 |
| multivariate_t3:mean_0.5_k2_sparse20 | maxedge_joint | 20.0 | 20.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse20 | pearson_asymptotic | 20.0 | 7.5 | 12.5 | 7/2/11 | 0.096 | 0.765 | 20 |
| multivariate_t3:mean_0.5_k2_sparse20 | peeling_rank_transform | 20.0 | 22.5 | -2.5 | 2/3/15 | 0.655 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse20 | peeling_separate | 20.0 | 20.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse5 | copula_asymptotic | 7.5 | 15.0 | -7.5 | 0/3/17 | 0.083 | 0.749 | 20 |
| multivariate_t3:mean_0.5_k2_sparse5 | decomposed_asymptotic | 7.5 | 15.0 | -7.5 | 0/3/17 | 0.083 | 0.749 | 20 |
| multivariate_t3:mean_0.5_k2_sparse5 | decomposed_bonferroni | 7.5 | 15.0 | -7.5 | 0/3/17 | 0.083 | 0.749 | 20 |
| multivariate_t3:mean_0.5_k2_sparse5 | ks_asymptotic | 7.5 | 7.5 | 0.0 | 2/2/16 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse5 | ks_pearson_asymptotic | 7.5 | 7.5 | 0.0 | 2/2/16 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse5 | maxedge_joint | 7.5 | 7.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse5 | pearson_asymptotic | 7.5 | 7.5 | 0.0 | 2/2/16 | 1.000 | 1.000 | 20 |
| multivariate_t3:mean_0.5_k2_sparse5 | peeling_rank_transform | 7.5 | 17.5 | -10.0 | 2/6/12 | 0.157 | 0.944 | 20 |
| multivariate_t3:mean_0.5_k2_sparse5 | peeling_separate | 7.5 | 7.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.3_k2 | copula_asymptotic | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.3_k2 | decomposed_asymptotic | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.3_k2 | decomposed_bonferroni | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.3_k2 | ks_asymptotic | 60.0 | 7.5 | 52.5 | 17/0/3 | 0.000 | 0.001 | 20 |
| multivariate_t3:paircorr_0.3_k2 | ks_pearson_asymptotic | 60.0 | 37.5 | 22.5 | 8/0/12 | 0.007 | 0.053 | 20 |
| multivariate_t3:paircorr_0.3_k2 | maxedge_joint | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.3_k2 | pearson_asymptotic | 60.0 | 37.5 | 22.5 | 8/0/12 | 0.007 | 0.053 | 20 |
| multivariate_t3:paircorr_0.3_k2 | peeling_rank_transform | 60.0 | 60.0 | 0.0 | 1/1/18 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.3_k2 | peeling_separate | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.8_k2 | copula_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.8_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.8_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.8_k2 | ks_asymptotic | 100.0 | 7.5 | 92.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| multivariate_t3:paircorr_0.8_k2 | ks_pearson_asymptotic | 100.0 | 77.5 | 22.5 | 6/0/14 | 0.024 | 0.195 | 20 |
| multivariate_t3:paircorr_0.8_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.8_k2 | pearson_asymptotic | 100.0 | 77.5 | 22.5 | 6/0/14 | 0.024 | 0.195 | 20 |
| multivariate_t3:paircorr_0.8_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:paircorr_0.8_k2 | peeling_separate | 100.0 | 97.5 | 2.5 | 1/0/19 | 0.317 | 1.000 | 20 |
| multivariate_t3:permute_k1 | copula_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:permute_k1 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:permute_k1 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:permute_k1 | ks_asymptotic | 100.0 | 0.0 | 100.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| multivariate_t3:permute_k1 | ks_pearson_asymptotic | 100.0 | 65.0 | 35.0 | 7/0/13 | 0.008 | 0.065 | 20 |
| multivariate_t3:permute_k1 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:permute_k1 | pearson_asymptotic | 100.0 | 65.0 | 35.0 | 7/0/13 | 0.008 | 0.065 | 20 |
| multivariate_t3:permute_k1 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:permute_k1 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:permute_k2 | copula_asymptotic | 92.5 | 70.0 | 22.5 | 9/0/11 | 0.003 | 0.013 | 20 |
| multivariate_t3:permute_k2 | decomposed_asymptotic | 92.5 | 70.0 | 22.5 | 9/0/11 | 0.003 | 0.013 | 20 |
| multivariate_t3:permute_k2 | decomposed_bonferroni | 92.5 | 70.0 | 22.5 | 9/0/11 | 0.003 | 0.013 | 20 |
| multivariate_t3:permute_k2 | ks_asymptotic | 92.5 | 7.5 | 85.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| multivariate_t3:permute_k2 | ks_pearson_asymptotic | 92.5 | 45.0 | 47.5 | 14/0/6 | 0.001 | 0.005 | 20 |
| multivariate_t3:permute_k2 | maxedge_joint | 92.5 | 65.0 | 27.5 | 11/0/9 | 0.001 | 0.005 | 20 |
| multivariate_t3:permute_k2 | pearson_asymptotic | 92.5 | 45.0 | 47.5 | 14/0/6 | 0.001 | 0.005 | 20 |
| multivariate_t3:permute_k2 | peeling_rank_transform | 92.5 | 92.5 | 0.0 | 1/1/18 | 1.000 | 1.000 | 20 |
| multivariate_t3:permute_k2 | peeling_separate | 92.5 | 92.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:permute_k2_sparse20 | copula_asymptotic | 30.0 | 42.5 | -12.5 | 0/4/16 | 0.059 | 0.462 | 20 |
| multivariate_t3:permute_k2_sparse20 | decomposed_asymptotic | 30.0 | 40.0 | -10.0 | 0/3/17 | 0.102 | 0.512 | 20 |
| multivariate_t3:permute_k2_sparse20 | decomposed_bonferroni | 30.0 | 40.0 | -10.0 | 0/3/17 | 0.102 | 0.512 | 20 |
| multivariate_t3:permute_k2_sparse20 | ks_asymptotic | 30.0 | 7.5 | 22.5 | 9/1/10 | 0.013 | 0.113 | 20 |
| multivariate_t3:permute_k2_sparse20 | ks_pearson_asymptotic | 30.0 | 15.0 | 15.0 | 6/1/13 | 0.058 | 0.462 | 20 |
| multivariate_t3:permute_k2_sparse20 | maxedge_joint | 30.0 | 30.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:permute_k2_sparse20 | pearson_asymptotic | 30.0 | 15.0 | 15.0 | 6/1/13 | 0.058 | 0.462 | 20 |
| multivariate_t3:permute_k2_sparse20 | peeling_rank_transform | 30.0 | 32.5 | -2.5 | 4/4/12 | 0.763 | 1.000 | 20 |
| multivariate_t3:permute_k2_sparse20 | peeling_separate | 30.0 | 30.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:permute_k5 | copula_asymptotic | 58.0 | 36.0 | 22.0 | 18/0/2 | 0.000 | 0.001 | 20 |
| multivariate_t3:permute_k5 | decomposed_asymptotic | 58.0 | 36.0 | 22.0 | 18/0/2 | 0.000 | 0.001 | 20 |
| multivariate_t3:permute_k5 | decomposed_bonferroni | 58.0 | 36.0 | 22.0 | 18/0/2 | 0.000 | 0.001 | 20 |
| multivariate_t3:permute_k5 | ks_asymptotic | 58.0 | 18.0 | 40.0 | 20/0/0 | 0.000 | 0.001 | 20 |
| multivariate_t3:permute_k5 | ks_pearson_asymptotic | 58.0 | 32.0 | 26.0 | 17/0/3 | 0.000 | 0.001 | 20 |
| multivariate_t3:permute_k5 | maxedge_joint | 58.0 | 32.0 | 26.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| multivariate_t3:permute_k5 | pearson_asymptotic | 58.0 | 32.0 | 26.0 | 17/0/3 | 0.000 | 0.001 | 20 |
| multivariate_t3:permute_k5 | peeling_rank_transform | 58.0 | 59.0 | -1.0 | 0/1/19 | 0.317 | 0.635 | 20 |
| multivariate_t3:permute_k5 | peeling_separate | 58.0 | 59.0 | -1.0 | 0/1/19 | 0.317 | 0.635 | 20 |
| multivariate_t3:scale_0.5_k2 | copula_asymptotic | 100.0 | 10.0 | 90.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| multivariate_t3:scale_0.5_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_0.5_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_0.5_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_0.5_k2 | ks_pearson_asymptotic | 100.0 | 20.0 | 80.0 | 18/0/2 | 0.000 | 0.001 | 20 |
| multivariate_t3:scale_0.5_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_0.5_k2 | pearson_asymptotic | 100.0 | 7.5 | 92.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| multivariate_t3:scale_0.5_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_0.5_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_0.5_k2_sparse20 | copula_asymptotic | 20.0 | 12.5 | 7.5 | 3/0/17 | 0.083 | 0.583 | 20 |
| multivariate_t3:scale_0.5_k2_sparse20 | decomposed_asymptotic | 20.0 | 12.5 | 7.5 | 3/0/17 | 0.083 | 0.583 | 20 |
| multivariate_t3:scale_0.5_k2_sparse20 | decomposed_bonferroni | 20.0 | 12.5 | 7.5 | 3/0/17 | 0.083 | 0.583 | 20 |
| multivariate_t3:scale_0.5_k2_sparse20 | ks_asymptotic | 20.0 | 25.0 | -5.0 | 2/4/14 | 0.414 | 1.000 | 20 |
| multivariate_t3:scale_0.5_k2_sparse20 | ks_pearson_asymptotic | 20.0 | 7.5 | 12.5 | 6/1/13 | 0.059 | 0.529 | 20 |
| multivariate_t3:scale_0.5_k2_sparse20 | maxedge_joint | 20.0 | 20.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_0.5_k2_sparse20 | pearson_asymptotic | 20.0 | 7.5 | 12.5 | 6/1/13 | 0.059 | 0.529 | 20 |
| multivariate_t3:scale_0.5_k2_sparse20 | peeling_rank_transform | 20.0 | 17.5 | 2.5 | 2/1/17 | 0.564 | 1.000 | 20 |
| multivariate_t3:scale_0.5_k2_sparse20 | peeling_separate | 20.0 | 20.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_2_k2 | copula_asymptotic | 97.5 | 10.0 | 87.5 | 19/0/1 | 0.000 | 0.000 | 20 |
| multivariate_t3:scale_2_k2 | decomposed_asymptotic | 97.5 | 97.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_2_k2 | decomposed_bonferroni | 97.5 | 97.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_2_k2 | ks_asymptotic | 97.5 | 100.0 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| multivariate_t3:scale_2_k2 | ks_pearson_asymptotic | 97.5 | 17.5 | 80.0 | 18/0/2 | 0.000 | 0.001 | 20 |
| multivariate_t3:scale_2_k2 | maxedge_joint | 97.5 | 97.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| multivariate_t3:scale_2_k2 | pearson_asymptotic | 97.5 | 7.5 | 90.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| multivariate_t3:scale_2_k2 | peeling_rank_transform | 97.5 | 100.0 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| multivariate_t3:scale_2_k2 | peeling_separate | 97.5 | 100.0 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| real_heldout:mean_0.2_k2 | copula_asymptotic | 100.0 | 15.0 | 85.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:mean_0.2_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.2_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.2_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.2_k2 | ks_pearson_asymptotic | 100.0 | 45.0 | 55.0 | 15/0/5 | 0.000 | 0.003 | 20 |
| real_heldout:mean_0.2_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.2_k2 | pearson_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:mean_0.2_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.2_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.5_k2 | copula_asymptotic | 100.0 | 15.0 | 85.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:mean_0.5_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.5_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.5_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.5_k2 | ks_pearson_asymptotic | 100.0 | 50.0 | 50.0 | 13/0/7 | 0.001 | 0.007 | 20 |
| real_heldout:mean_0.5_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.5_k2 | pearson_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:mean_0.5_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.5_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.5_k2_sparse20 | copula_asymptotic | 95.0 | 57.5 | 37.5 | 15/0/5 | 0.000 | 0.001 | 20 |
| real_heldout:mean_0.5_k2_sparse20 | decomposed_asymptotic | 95.0 | 57.5 | 37.5 | 15/0/5 | 0.000 | 0.001 | 20 |
| real_heldout:mean_0.5_k2_sparse20 | decomposed_bonferroni | 95.0 | 57.5 | 37.5 | 15/0/5 | 0.000 | 0.001 | 20 |
| real_heldout:mean_0.5_k2_sparse20 | ks_asymptotic | 95.0 | 100.0 | -5.0 | 0/2/18 | 0.157 | 0.472 | 20 |
| real_heldout:mean_0.5_k2_sparse20 | ks_pearson_asymptotic | 95.0 | 15.0 | 80.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:mean_0.5_k2_sparse20 | maxedge_joint | 95.0 | 92.5 | 2.5 | 1/0/19 | 0.317 | 0.635 | 20 |
| real_heldout:mean_0.5_k2_sparse20 | pearson_asymptotic | 95.0 | 15.0 | 80.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:mean_0.5_k2_sparse20 | peeling_rank_transform | 95.0 | 87.5 | 7.5 | 3/0/17 | 0.083 | 0.333 | 20 |
| real_heldout:mean_0.5_k2_sparse20 | peeling_separate | 95.0 | 95.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.5_k2_sparse5 | copula_asymptotic | 35.0 | 42.5 | -7.5 | 3/5/12 | 0.366 | 1.000 | 20 |
| real_heldout:mean_0.5_k2_sparse5 | decomposed_asymptotic | 35.0 | 40.0 | -5.0 | 3/4/13 | 0.527 | 1.000 | 20 |
| real_heldout:mean_0.5_k2_sparse5 | decomposed_bonferroni | 35.0 | 40.0 | -5.0 | 3/4/13 | 0.527 | 1.000 | 20 |
| real_heldout:mean_0.5_k2_sparse5 | ks_asymptotic | 35.0 | 32.5 | 2.5 | 5/4/11 | 0.739 | 1.000 | 20 |
| real_heldout:mean_0.5_k2_sparse5 | ks_pearson_asymptotic | 35.0 | 15.0 | 20.0 | 9/3/8 | 0.059 | 0.529 | 20 |
| real_heldout:mean_0.5_k2_sparse5 | maxedge_joint | 35.0 | 35.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:mean_0.5_k2_sparse5 | pearson_asymptotic | 35.0 | 15.0 | 20.0 | 9/3/8 | 0.059 | 0.529 | 20 |
| real_heldout:mean_0.5_k2_sparse5 | peeling_rank_transform | 35.0 | 47.5 | -12.5 | 3/7/10 | 0.166 | 1.000 | 20 |
| real_heldout:mean_0.5_k2_sparse5 | peeling_separate | 35.0 | 35.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.3_k2 | copula_asymptotic | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.3_k2 | decomposed_asymptotic | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.3_k2 | decomposed_bonferroni | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.3_k2 | ks_asymptotic | 55.0 | 15.0 | 40.0 | 15/0/5 | 0.000 | 0.001 | 20 |
| real_heldout:paircorr_0.3_k2 | ks_pearson_asymptotic | 55.0 | 30.0 | 25.0 | 9/0/11 | 0.004 | 0.031 | 20 |
| real_heldout:paircorr_0.3_k2 | maxedge_joint | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.3_k2 | pearson_asymptotic | 55.0 | 30.0 | 25.0 | 9/0/11 | 0.004 | 0.031 | 20 |
| real_heldout:paircorr_0.3_k2 | peeling_rank_transform | 55.0 | 57.5 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| real_heldout:paircorr_0.3_k2 | peeling_separate | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.8_k2 | copula_asymptotic | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.8_k2 | decomposed_asymptotic | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.8_k2 | decomposed_bonferroni | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.8_k2 | ks_asymptotic | 60.0 | 15.0 | 45.0 | 17/0/3 | 0.000 | 0.001 | 20 |
| real_heldout:paircorr_0.8_k2 | ks_pearson_asymptotic | 60.0 | 25.0 | 35.0 | 11/0/9 | 0.002 | 0.017 | 20 |
| real_heldout:paircorr_0.8_k2 | maxedge_joint | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.8_k2 | pearson_asymptotic | 60.0 | 25.0 | 35.0 | 11/0/9 | 0.002 | 0.017 | 20 |
| real_heldout:paircorr_0.8_k2 | peeling_rank_transform | 60.0 | 60.0 | 0.0 | 1/1/18 | 1.000 | 1.000 | 20 |
| real_heldout:paircorr_0.8_k2 | peeling_separate | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:permute_k1 | copula_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:permute_k1 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:permute_k1 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:permute_k1 | ks_asymptotic | 100.0 | 5.0 | 95.0 | 19/0/1 | 0.000 | 0.000 | 20 |
| real_heldout:permute_k1 | ks_pearson_asymptotic | 100.0 | 60.0 | 40.0 | 8/0/12 | 0.005 | 0.037 | 20 |
| real_heldout:permute_k1 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:permute_k1 | pearson_asymptotic | 100.0 | 60.0 | 40.0 | 8/0/12 | 0.005 | 0.037 | 20 |
| real_heldout:permute_k1 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:permute_k1 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:permute_k2 | copula_asymptotic | 95.0 | 65.0 | 30.0 | 12/0/8 | 0.001 | 0.003 | 20 |
| real_heldout:permute_k2 | decomposed_asymptotic | 95.0 | 65.0 | 30.0 | 12/0/8 | 0.001 | 0.003 | 20 |
| real_heldout:permute_k2 | decomposed_bonferroni | 95.0 | 65.0 | 30.0 | 12/0/8 | 0.001 | 0.003 | 20 |
| real_heldout:permute_k2 | ks_asymptotic | 95.0 | 15.0 | 80.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:permute_k2 | ks_pearson_asymptotic | 95.0 | 37.5 | 57.5 | 18/1/1 | 0.000 | 0.002 | 20 |
| real_heldout:permute_k2 | maxedge_joint | 95.0 | 57.5 | 37.5 | 15/0/5 | 0.000 | 0.001 | 20 |
| real_heldout:permute_k2 | pearson_asymptotic | 95.0 | 37.5 | 57.5 | 18/1/1 | 0.000 | 0.002 | 20 |
| real_heldout:permute_k2 | peeling_rank_transform | 95.0 | 97.5 | -2.5 | 0/1/19 | 0.317 | 0.635 | 20 |
| real_heldout:permute_k2 | peeling_separate | 95.0 | 97.5 | -2.5 | 0/1/19 | 0.317 | 0.635 | 20 |
| real_heldout:permute_k2_sparse20 | copula_asymptotic | 60.0 | 62.5 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| real_heldout:permute_k2_sparse20 | decomposed_asymptotic | 60.0 | 62.5 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| real_heldout:permute_k2_sparse20 | decomposed_bonferroni | 60.0 | 62.5 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| real_heldout:permute_k2_sparse20 | ks_asymptotic | 60.0 | 15.0 | 45.0 | 14/0/6 | 0.001 | 0.005 | 20 |
| real_heldout:permute_k2_sparse20 | ks_pearson_asymptotic | 60.0 | 22.5 | 37.5 | 14/1/5 | 0.001 | 0.009 | 20 |
| real_heldout:permute_k2_sparse20 | maxedge_joint | 60.0 | 57.5 | 2.5 | 1/0/19 | 0.317 | 1.000 | 20 |
| real_heldout:permute_k2_sparse20 | pearson_asymptotic | 60.0 | 22.5 | 37.5 | 14/1/5 | 0.001 | 0.009 | 20 |
| real_heldout:permute_k2_sparse20 | peeling_rank_transform | 60.0 | 62.5 | -2.5 | 2/3/15 | 0.655 | 1.000 | 20 |
| real_heldout:permute_k2_sparse20 | peeling_separate | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:permute_k5 | copula_asymptotic | 60.0 | 31.0 | 29.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:permute_k5 | decomposed_asymptotic | 60.0 | 31.0 | 29.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:permute_k5 | decomposed_bonferroni | 60.0 | 31.0 | 29.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:permute_k5 | ks_asymptotic | 60.0 | 16.0 | 44.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:permute_k5 | ks_pearson_asymptotic | 60.0 | 26.0 | 34.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:permute_k5 | maxedge_joint | 60.0 | 29.0 | 31.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:permute_k5 | pearson_asymptotic | 60.0 | 26.0 | 34.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:permute_k5 | peeling_rank_transform | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:permute_k5 | peeling_separate | 60.0 | 60.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_0.5_k2 | copula_asymptotic | 100.0 | 15.0 | 85.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:scale_0.5_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_0.5_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_0.5_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_0.5_k2 | ks_pearson_asymptotic | 100.0 | 45.0 | 55.0 | 15/0/5 | 0.000 | 0.003 | 20 |
| real_heldout:scale_0.5_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_0.5_k2 | pearson_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:scale_0.5_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_0.5_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_0.5_k2_sparse20 | copula_asymptotic | 85.0 | 55.0 | 30.0 | 12/1/7 | 0.003 | 0.019 | 20 |
| real_heldout:scale_0.5_k2_sparse20 | decomposed_asymptotic | 85.0 | 60.0 | 25.0 | 11/1/8 | 0.004 | 0.023 | 20 |
| real_heldout:scale_0.5_k2_sparse20 | decomposed_bonferroni | 85.0 | 60.0 | 25.0 | 11/1/8 | 0.004 | 0.023 | 20 |
| real_heldout:scale_0.5_k2_sparse20 | ks_asymptotic | 85.0 | 97.5 | -12.5 | 0/5/15 | 0.025 | 0.101 | 20 |
| real_heldout:scale_0.5_k2_sparse20 | ks_pearson_asymptotic | 85.0 | 20.0 | 65.0 | 17/0/3 | 0.000 | 0.002 | 20 |
| real_heldout:scale_0.5_k2_sparse20 | maxedge_joint | 85.0 | 85.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_0.5_k2_sparse20 | pearson_asymptotic | 85.0 | 20.0 | 65.0 | 17/0/3 | 0.000 | 0.002 | 20 |
| real_heldout:scale_0.5_k2_sparse20 | peeling_rank_transform | 85.0 | 85.0 | 0.0 | 1/1/18 | 1.000 | 1.000 | 20 |
| real_heldout:scale_0.5_k2_sparse20 | peeling_separate | 85.0 | 85.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_2_k2 | copula_asymptotic | 100.0 | 15.0 | 85.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:scale_2_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_2_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_2_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_2_k2 | ks_pearson_asymptotic | 100.0 | 45.0 | 55.0 | 15/0/5 | 0.000 | 0.003 | 20 |
| real_heldout:scale_2_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_2_k2 | pearson_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_heldout:scale_2_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_heldout:scale_2_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.2_k2 | copula_asymptotic | 100.0 | 17.5 | 82.5 | 19/0/1 | 0.000 | 0.000 | 20 |
| real_tuesday:mean_0.2_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.2_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.2_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.2_k2 | ks_pearson_asymptotic | 100.0 | 52.5 | 47.5 | 13/0/7 | 0.001 | 0.007 | 20 |
| real_tuesday:mean_0.2_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.2_k2 | pearson_asymptotic | 100.0 | 10.0 | 90.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_tuesday:mean_0.2_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.2_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2 | copula_asymptotic | 100.0 | 17.5 | 82.5 | 19/0/1 | 0.000 | 0.000 | 20 |
| real_tuesday:mean_0.5_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2 | ks_pearson_asymptotic | 100.0 | 57.5 | 42.5 | 12/0/8 | 0.002 | 0.011 | 20 |
| real_tuesday:mean_0.5_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2 | pearson_asymptotic | 100.0 | 10.0 | 90.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_tuesday:mean_0.5_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2_sparse20 | copula_asymptotic | 95.0 | 55.0 | 40.0 | 15/0/5 | 0.000 | 0.001 | 20 |
| real_tuesday:mean_0.5_k2_sparse20 | decomposed_asymptotic | 95.0 | 60.0 | 35.0 | 14/0/6 | 0.000 | 0.001 | 20 |
| real_tuesday:mean_0.5_k2_sparse20 | decomposed_bonferroni | 95.0 | 60.0 | 35.0 | 14/0/6 | 0.000 | 0.001 | 20 |
| real_tuesday:mean_0.5_k2_sparse20 | ks_asymptotic | 95.0 | 100.0 | -5.0 | 0/2/18 | 0.157 | 0.629 | 20 |
| real_tuesday:mean_0.5_k2_sparse20 | ks_pearson_asymptotic | 95.0 | 20.0 | 75.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_tuesday:mean_0.5_k2_sparse20 | maxedge_joint | 95.0 | 95.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2_sparse20 | pearson_asymptotic | 95.0 | 20.0 | 75.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_tuesday:mean_0.5_k2_sparse20 | peeling_rank_transform | 95.0 | 95.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2_sparse20 | peeling_separate | 95.0 | 97.5 | -2.5 | 0/1/19 | 0.317 | 0.952 | 20 |
| real_tuesday:mean_0.5_k2_sparse5 | copula_asymptotic | 57.5 | 40.0 | 17.5 | 6/1/13 | 0.053 | 0.372 | 20 |
| real_tuesday:mean_0.5_k2_sparse5 | decomposed_asymptotic | 57.5 | 42.5 | 15.0 | 6/1/13 | 0.058 | 0.372 | 20 |
| real_tuesday:mean_0.5_k2_sparse5 | decomposed_bonferroni | 57.5 | 42.5 | 15.0 | 6/1/13 | 0.058 | 0.372 | 20 |
| real_tuesday:mean_0.5_k2_sparse5 | ks_asymptotic | 57.5 | 55.0 | 2.5 | 6/5/9 | 0.763 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2_sparse5 | ks_pearson_asymptotic | 57.5 | 15.0 | 42.5 | 14/2/4 | 0.003 | 0.023 | 20 |
| real_tuesday:mean_0.5_k2_sparse5 | maxedge_joint | 57.5 | 57.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2_sparse5 | pearson_asymptotic | 57.5 | 15.0 | 42.5 | 14/2/4 | 0.003 | 0.023 | 20 |
| real_tuesday:mean_0.5_k2_sparse5 | peeling_rank_transform | 57.5 | 60.0 | -2.5 | 2/3/15 | 0.655 | 1.000 | 20 |
| real_tuesday:mean_0.5_k2_sparse5 | peeling_separate | 57.5 | 57.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:paircorr_0.3_k2 | copula_asymptotic | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:paircorr_0.3_k2 | decomposed_asymptotic | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:paircorr_0.3_k2 | decomposed_bonferroni | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:paircorr_0.3_k2 | ks_asymptotic | 55.0 | 27.5 | 27.5 | 10/0/10 | 0.002 | 0.021 | 20 |
| real_tuesday:paircorr_0.3_k2 | ks_pearson_asymptotic | 55.0 | 32.5 | 22.5 | 8/1/11 | 0.021 | 0.167 | 20 |
| real_tuesday:paircorr_0.3_k2 | maxedge_joint | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:paircorr_0.3_k2 | pearson_asymptotic | 55.0 | 32.5 | 22.5 | 8/1/11 | 0.021 | 0.167 | 20 |
| real_tuesday:paircorr_0.3_k2 | peeling_rank_transform | 55.0 | 57.5 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| real_tuesday:paircorr_0.3_k2 | peeling_separate | 55.0 | 55.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:paircorr_0.8_k2 | copula_asymptotic | 65.0 | 65.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:paircorr_0.8_k2 | decomposed_asymptotic | 65.0 | 65.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:paircorr_0.8_k2 | decomposed_bonferroni | 65.0 | 65.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:paircorr_0.8_k2 | ks_asymptotic | 65.0 | 27.5 | 37.5 | 12/0/8 | 0.001 | 0.012 | 20 |
| real_tuesday:paircorr_0.8_k2 | ks_pearson_asymptotic | 65.0 | 30.0 | 35.0 | 11/0/9 | 0.002 | 0.017 | 20 |
| real_tuesday:paircorr_0.8_k2 | maxedge_joint | 65.0 | 65.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:paircorr_0.8_k2 | pearson_asymptotic | 65.0 | 30.0 | 35.0 | 11/0/9 | 0.002 | 0.017 | 20 |
| real_tuesday:paircorr_0.8_k2 | peeling_rank_transform | 65.0 | 62.5 | 2.5 | 1/0/19 | 0.317 | 1.000 | 20 |
| real_tuesday:paircorr_0.8_k2 | peeling_separate | 65.0 | 65.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:permute_k1 | copula_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:permute_k1 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:permute_k1 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:permute_k1 | ks_asymptotic | 100.0 | 20.0 | 80.0 | 16/0/4 | 0.000 | 0.001 | 20 |
| real_tuesday:permute_k1 | ks_pearson_asymptotic | 100.0 | 55.0 | 45.0 | 9/0/11 | 0.003 | 0.022 | 20 |
| real_tuesday:permute_k1 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:permute_k1 | pearson_asymptotic | 100.0 | 55.0 | 45.0 | 9/0/11 | 0.003 | 0.022 | 20 |
| real_tuesday:permute_k1 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:permute_k1 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:permute_k2 | copula_asymptotic | 95.0 | 65.0 | 30.0 | 13/1/6 | 0.001 | 0.007 | 20 |
| real_tuesday:permute_k2 | decomposed_asymptotic | 95.0 | 65.0 | 30.0 | 13/1/6 | 0.001 | 0.007 | 20 |
| real_tuesday:permute_k2 | decomposed_bonferroni | 95.0 | 65.0 | 30.0 | 13/1/6 | 0.001 | 0.007 | 20 |
| real_tuesday:permute_k2 | ks_asymptotic | 95.0 | 27.5 | 67.5 | 18/1/1 | 0.000 | 0.002 | 20 |
| real_tuesday:permute_k2 | ks_pearson_asymptotic | 95.0 | 40.0 | 55.0 | 15/0/5 | 0.000 | 0.003 | 20 |
| real_tuesday:permute_k2 | maxedge_joint | 95.0 | 57.5 | 37.5 | 15/0/5 | 0.000 | 0.001 | 20 |
| real_tuesday:permute_k2 | pearson_asymptotic | 95.0 | 40.0 | 55.0 | 15/0/5 | 0.000 | 0.003 | 20 |
| real_tuesday:permute_k2 | peeling_rank_transform | 95.0 | 92.5 | 2.5 | 1/0/19 | 0.317 | 0.635 | 20 |
| real_tuesday:permute_k2 | peeling_separate | 95.0 | 97.5 | -2.5 | 0/1/19 | 0.317 | 0.635 | 20 |
| real_tuesday:permute_k2_sparse20 | copula_asymptotic | 52.5 | 60.0 | -7.5 | 1/4/15 | 0.180 | 1.000 | 20 |
| real_tuesday:permute_k2_sparse20 | decomposed_asymptotic | 52.5 | 60.0 | -7.5 | 1/4/15 | 0.180 | 1.000 | 20 |
| real_tuesday:permute_k2_sparse20 | decomposed_bonferroni | 52.5 | 60.0 | -7.5 | 1/4/15 | 0.180 | 1.000 | 20 |
| real_tuesday:permute_k2_sparse20 | ks_asymptotic | 52.5 | 27.5 | 25.0 | 9/2/9 | 0.026 | 0.179 | 20 |
| real_tuesday:permute_k2_sparse20 | ks_pearson_asymptotic | 52.5 | 22.5 | 30.0 | 11/2/7 | 0.011 | 0.098 | 20 |
| real_tuesday:permute_k2_sparse20 | maxedge_joint | 52.5 | 50.0 | 2.5 | 1/0/19 | 0.317 | 1.000 | 20 |
| real_tuesday:permute_k2_sparse20 | pearson_asymptotic | 52.5 | 22.5 | 30.0 | 11/2/7 | 0.011 | 0.098 | 20 |
| real_tuesday:permute_k2_sparse20 | peeling_rank_transform | 52.5 | 60.0 | -7.5 | 1/3/16 | 0.257 | 1.000 | 20 |
| real_tuesday:permute_k2_sparse20 | peeling_separate | 52.5 | 52.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:permute_k5 | copula_asymptotic | 58.0 | 34.0 | 24.0 | 18/1/1 | 0.000 | 0.001 | 20 |
| real_tuesday:permute_k5 | decomposed_asymptotic | 58.0 | 34.0 | 24.0 | 18/1/1 | 0.000 | 0.001 | 20 |
| real_tuesday:permute_k5 | decomposed_bonferroni | 58.0 | 34.0 | 24.0 | 18/1/1 | 0.000 | 0.001 | 20 |
| real_tuesday:permute_k5 | ks_asymptotic | 58.0 | 19.0 | 39.0 | 18/0/2 | 0.000 | 0.001 | 20 |
| real_tuesday:permute_k5 | ks_pearson_asymptotic | 58.0 | 24.0 | 34.0 | 19/0/1 | 0.000 | 0.001 | 20 |
| real_tuesday:permute_k5 | maxedge_joint | 58.0 | 29.0 | 29.0 | 19/1/0 | 0.000 | 0.001 | 20 |
| real_tuesday:permute_k5 | pearson_asymptotic | 58.0 | 24.0 | 34.0 | 19/0/1 | 0.000 | 0.001 | 20 |
| real_tuesday:permute_k5 | peeling_rank_transform | 58.0 | 60.0 | -2.0 | 0/2/18 | 0.157 | 0.315 | 20 |
| real_tuesday:permute_k5 | peeling_separate | 58.0 | 58.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_0.5_k2 | copula_asymptotic | 100.0 | 17.5 | 82.5 | 19/0/1 | 0.000 | 0.000 | 20 |
| real_tuesday:scale_0.5_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_0.5_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_0.5_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_0.5_k2 | ks_pearson_asymptotic | 100.0 | 50.0 | 50.0 | 14/0/6 | 0.001 | 0.005 | 20 |
| real_tuesday:scale_0.5_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_0.5_k2 | pearson_asymptotic | 100.0 | 10.0 | 90.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_tuesday:scale_0.5_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_0.5_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_0.5_k2_sparse20 | copula_asymptotic | 90.0 | 55.0 | 35.0 | 12/0/8 | 0.001 | 0.007 | 20 |
| real_tuesday:scale_0.5_k2_sparse20 | decomposed_asymptotic | 90.0 | 67.5 | 22.5 | 9/0/11 | 0.003 | 0.016 | 20 |
| real_tuesday:scale_0.5_k2_sparse20 | decomposed_bonferroni | 90.0 | 67.5 | 22.5 | 9/0/11 | 0.003 | 0.016 | 20 |
| real_tuesday:scale_0.5_k2_sparse20 | ks_asymptotic | 90.0 | 100.0 | -10.0 | 0/4/16 | 0.046 | 0.182 | 20 |
| real_tuesday:scale_0.5_k2_sparse20 | ks_pearson_asymptotic | 90.0 | 15.0 | 75.0 | 19/0/1 | 0.000 | 0.001 | 20 |
| real_tuesday:scale_0.5_k2_sparse20 | maxedge_joint | 90.0 | 90.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_0.5_k2_sparse20 | pearson_asymptotic | 90.0 | 15.0 | 75.0 | 19/0/1 | 0.000 | 0.001 | 20 |
| real_tuesday:scale_0.5_k2_sparse20 | peeling_rank_transform | 90.0 | 90.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_0.5_k2_sparse20 | peeling_separate | 90.0 | 90.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_2_k2 | copula_asymptotic | 100.0 | 17.5 | 82.5 | 19/0/1 | 0.000 | 0.000 | 20 |
| real_tuesday:scale_2_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_2_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_2_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_2_k2 | ks_pearson_asymptotic | 100.0 | 50.0 | 50.0 | 14/0/6 | 0.001 | 0.005 | 20 |
| real_tuesday:scale_2_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_2_k2 | pearson_asymptotic | 100.0 | 10.0 | 90.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| real_tuesday:scale_2_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| real_tuesday:scale_2_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.2_k2 | copula_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| zero_inflated_tied:mean_0.2_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.2_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.2_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.2_k2 | ks_pearson_asymptotic | 100.0 | 97.5 | 2.5 | 1/0/19 | 0.317 | 1.000 | 20 |
| zero_inflated_tied:mean_0.2_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.2_k2 | pearson_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| zero_inflated_tied:mean_0.2_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.2_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2 | copula_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| zero_inflated_tied:mean_0.5_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2 | ks_pearson_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2 | pearson_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| zero_inflated_tied:mean_0.5_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse20 | copula_asymptotic | 100.0 | 75.0 | 25.0 | 6/0/14 | 0.023 | 0.162 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse20 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse20 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse20 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse20 | ks_pearson_asymptotic | 100.0 | 25.0 | 75.0 | 18/0/2 | 0.000 | 0.001 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse20 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse20 | pearson_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse20 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse20 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse5 | copula_asymptotic | 32.5 | 17.5 | 15.0 | 8/2/10 | 0.058 | 0.319 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse5 | decomposed_asymptotic | 32.5 | 17.5 | 15.0 | 7/1/12 | 0.034 | 0.305 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse5 | decomposed_bonferroni | 32.5 | 17.5 | 15.0 | 7/1/12 | 0.034 | 0.305 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse5 | ks_asymptotic | 32.5 | 47.5 | -15.0 | 1/6/13 | 0.058 | 0.319 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse5 | ks_pearson_asymptotic | 32.5 | 12.5 | 20.0 | 10/3/7 | 0.046 | 0.319 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse5 | maxedge_joint | 32.5 | 32.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse5 | pearson_asymptotic | 32.5 | 12.5 | 20.0 | 10/3/7 | 0.046 | 0.319 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse5 | peeling_rank_transform | 32.5 | 35.0 | -2.5 | 0/1/19 | 0.317 | 0.952 | 20 |
| zero_inflated_tied:mean_0.5_k2_sparse5 | peeling_separate | 32.5 | 32.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.3_k2 | copula_asymptotic | 67.5 | 75.0 | -7.5 | 1/4/15 | 0.180 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.3_k2 | decomposed_asymptotic | 67.5 | 72.5 | -5.0 | 1/3/16 | 0.317 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.3_k2 | decomposed_bonferroni | 67.5 | 72.5 | -5.0 | 1/3/16 | 0.317 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.3_k2 | ks_asymptotic | 67.5 | 20.0 | 47.5 | 13/2/5 | 0.002 | 0.021 | 20 |
| zero_inflated_tied:paircorr_0.3_k2 | ks_pearson_asymptotic | 67.5 | 20.0 | 47.5 | 13/2/5 | 0.002 | 0.021 | 20 |
| zero_inflated_tied:paircorr_0.3_k2 | maxedge_joint | 67.5 | 67.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.3_k2 | pearson_asymptotic | 67.5 | 20.0 | 47.5 | 13/2/5 | 0.002 | 0.021 | 20 |
| zero_inflated_tied:paircorr_0.3_k2 | peeling_rank_transform | 67.5 | 60.0 | 7.5 | 2/0/18 | 0.180 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.3_k2 | peeling_separate | 67.5 | 67.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.8_k2 | copula_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.8_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.8_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.8_k2 | ks_asymptotic | 100.0 | 20.0 | 80.0 | 20/0/0 | 0.000 | 0.000 | 20 |
| zero_inflated_tied:paircorr_0.8_k2 | ks_pearson_asymptotic | 100.0 | 45.0 | 55.0 | 14/0/6 | 0.001 | 0.005 | 20 |
| zero_inflated_tied:paircorr_0.8_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.8_k2 | pearson_asymptotic | 100.0 | 45.0 | 55.0 | 14/0/6 | 0.001 | 0.005 | 20 |
| zero_inflated_tied:paircorr_0.8_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:paircorr_0.8_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:permute_k1 | copula_asymptotic | 30.0 | 25.0 | 5.0 | 2/1/17 | 0.564 | 1.000 | 20 |
| zero_inflated_tied:permute_k1 | decomposed_asymptotic | 30.0 | 25.0 | 5.0 | 2/1/17 | 0.564 | 1.000 | 20 |
| zero_inflated_tied:permute_k1 | decomposed_bonferroni | 30.0 | 25.0 | 5.0 | 2/1/17 | 0.564 | 1.000 | 20 |
| zero_inflated_tied:permute_k1 | ks_asymptotic | 30.0 | 25.0 | 5.0 | 4/3/13 | 0.705 | 1.000 | 20 |
| zero_inflated_tied:permute_k1 | ks_pearson_asymptotic | 30.0 | 20.0 | 10.0 | 5/3/12 | 0.480 | 1.000 | 20 |
| zero_inflated_tied:permute_k1 | maxedge_joint | 30.0 | 30.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:permute_k1 | pearson_asymptotic | 30.0 | 20.0 | 10.0 | 5/3/12 | 0.480 | 1.000 | 20 |
| zero_inflated_tied:permute_k1 | peeling_rank_transform | 30.0 | 5.0 | 25.0 | 5/0/15 | 0.025 | 0.228 | 20 |
| zero_inflated_tied:permute_k1 | peeling_separate | 30.0 | 30.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:permute_k2 | copula_asymptotic | 32.5 | 40.0 | -7.5 | 1/4/15 | 0.180 | 1.000 | 20 |
| zero_inflated_tied:permute_k2 | decomposed_asymptotic | 32.5 | 40.0 | -7.5 | 1/4/15 | 0.180 | 1.000 | 20 |
| zero_inflated_tied:permute_k2 | decomposed_bonferroni | 32.5 | 40.0 | -7.5 | 1/4/15 | 0.180 | 1.000 | 20 |
| zero_inflated_tied:permute_k2 | ks_asymptotic | 32.5 | 20.0 | 12.5 | 7/2/11 | 0.096 | 0.765 | 20 |
| zero_inflated_tied:permute_k2 | ks_pearson_asymptotic | 32.5 | 25.0 | 7.5 | 6/3/11 | 0.317 | 1.000 | 20 |
| zero_inflated_tied:permute_k2 | maxedge_joint | 32.5 | 32.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:permute_k2 | pearson_asymptotic | 32.5 | 25.0 | 7.5 | 6/3/11 | 0.317 | 1.000 | 20 |
| zero_inflated_tied:permute_k2 | peeling_rank_transform | 32.5 | 22.5 | 10.0 | 4/0/16 | 0.046 | 0.410 | 20 |
| zero_inflated_tied:permute_k2 | peeling_separate | 32.5 | 32.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:permute_k2_sparse20 | copula_asymptotic | 10.0 | 15.0 | -5.0 | 1/3/16 | 0.317 | 1.000 | 20 |
| zero_inflated_tied:permute_k2_sparse20 | decomposed_asymptotic | 10.0 | 12.5 | -2.5 | 1/2/17 | 0.564 | 1.000 | 20 |
| zero_inflated_tied:permute_k2_sparse20 | decomposed_bonferroni | 10.0 | 12.5 | -2.5 | 1/2/17 | 0.564 | 1.000 | 20 |
| zero_inflated_tied:permute_k2_sparse20 | ks_asymptotic | 10.0 | 20.0 | -10.0 | 1/5/14 | 0.102 | 0.922 | 20 |
| zero_inflated_tied:permute_k2_sparse20 | ks_pearson_asymptotic | 10.0 | 15.0 | -5.0 | 3/5/12 | 0.480 | 1.000 | 20 |
| zero_inflated_tied:permute_k2_sparse20 | maxedge_joint | 10.0 | 10.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:permute_k2_sparse20 | pearson_asymptotic | 10.0 | 15.0 | -5.0 | 3/5/12 | 0.480 | 1.000 | 20 |
| zero_inflated_tied:permute_k2_sparse20 | peeling_rank_transform | 10.0 | 12.5 | -2.5 | 2/3/15 | 0.655 | 1.000 | 20 |
| zero_inflated_tied:permute_k2_sparse20 | peeling_separate | 10.0 | 10.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:permute_k5 | copula_asymptotic | 24.0 | 25.0 | -1.0 | 3/4/13 | 0.705 | 1.000 | 20 |
| zero_inflated_tied:permute_k5 | decomposed_asymptotic | 24.0 | 26.0 | -2.0 | 2/4/14 | 0.414 | 1.000 | 20 |
| zero_inflated_tied:permute_k5 | decomposed_bonferroni | 24.0 | 26.0 | -2.0 | 2/4/14 | 0.414 | 1.000 | 20 |
| zero_inflated_tied:permute_k5 | ks_asymptotic | 24.0 | 20.0 | 4.0 | 7/4/9 | 0.285 | 1.000 | 20 |
| zero_inflated_tied:permute_k5 | ks_pearson_asymptotic | 24.0 | 21.0 | 3.0 | 5/3/12 | 0.366 | 1.000 | 20 |
| zero_inflated_tied:permute_k5 | maxedge_joint | 24.0 | 24.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:permute_k5 | pearson_asymptotic | 24.0 | 21.0 | 3.0 | 5/3/12 | 0.366 | 1.000 | 20 |
| zero_inflated_tied:permute_k5 | peeling_rank_transform | 24.0 | 17.0 | 7.0 | 8/2/10 | 0.052 | 0.470 | 20 |
| zero_inflated_tied:permute_k5 | peeling_separate | 24.0 | 24.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2 | copula_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| zero_inflated_tied:scale_0.5_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2 | ks_pearson_asymptotic | 100.0 | 97.5 | 2.5 | 1/0/19 | 0.317 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2 | pearson_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| zero_inflated_tied:scale_0.5_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2_sparse20 | copula_asymptotic | 97.5 | 22.5 | 75.0 | 19/0/1 | 0.000 | 0.001 | 20 |
| zero_inflated_tied:scale_0.5_k2_sparse20 | decomposed_asymptotic | 97.5 | 97.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2_sparse20 | decomposed_bonferroni | 97.5 | 97.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2_sparse20 | ks_asymptotic | 97.5 | 100.0 | -2.5 | 0/1/19 | 0.317 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2_sparse20 | ks_pearson_asymptotic | 97.5 | 20.0 | 77.5 | 19/0/1 | 0.000 | 0.001 | 20 |
| zero_inflated_tied:scale_0.5_k2_sparse20 | maxedge_joint | 97.5 | 97.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2_sparse20 | pearson_asymptotic | 97.5 | 15.0 | 82.5 | 19/0/1 | 0.000 | 0.001 | 20 |
| zero_inflated_tied:scale_0.5_k2_sparse20 | peeling_rank_transform | 97.5 | 97.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_0.5_k2_sparse20 | peeling_separate | 97.5 | 97.5 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_2_k2 | copula_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| zero_inflated_tied:scale_2_k2 | decomposed_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_2_k2 | decomposed_bonferroni | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_2_k2 | ks_asymptotic | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_2_k2 | ks_pearson_asymptotic | 100.0 | 97.5 | 2.5 | 1/0/19 | 0.317 | 1.000 | 20 |
| zero_inflated_tied:scale_2_k2 | maxedge_joint | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_2_k2 | pearson_asymptotic | 100.0 | 12.5 | 87.5 | 20/0/0 | 0.000 | 0.000 | 20 |
| zero_inflated_tied:scale_2_k2 | peeling_rank_transform | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |
| zero_inflated_tied:scale_2_k2 | peeling_separate | 100.0 | 100.0 | 0.0 | 0/0/20 | 1.000 | 1.000 | 20 |

419 of 585 paired tests are not significant.

