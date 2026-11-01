### Family-wise error rate with nothing injected (nominal 5%)

| null population | decomposed (asymptotic) | calibrated joint | calibrated, alpha not split |
| --- | --- | --- | --- |
| gaussian | 8.6% [6.4, 11.4] | 3.8% [2.4, 5.9] | 9.8% [7.5, 12.7] |
| multivariate_t3 | 45.8% [41.5, 50.2] | 3.2% [2.0, 5.1] | 8.4% [6.3, 11.2] |
| real_heldout | 57.8% [53.4, 62.1] | 3.2% [2.0, 5.1] | 8.6% [6.4, 11.4] |
| real_tuesday | 59.0% [54.6, 63.2] | 4.4% [2.9, 6.6] | 10.2% [7.8, 13.2] |
| zero_inflated_tied | 9.8% [7.5, 12.7] | 5.8% [4.1, 8.2] | 10.6% [8.2, 13.6] |

Brackets are 95% Wilson intervals over 500 draws.
Real-data trials resample a fixed set of disjoint blocks, so those
draws are not independent: the distinct block counts are gaussian=20, multivariate_t3=20, real_heldout=40, real_tuesday=40, zero_inflated_tied=20,
and `ci95_block` in `summary.json` is the cluster bootstrap over
blocks (the interval to prefer for the real rows).

### Recall@3 by condition (mean over seeds)

| dataset | condition | chance r@1 | chance r@3 | decomposed | max-edge | peeling | peeling r@1 | rank transform |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| real_heldout | scale_0.5_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| multivariate_t3 | mean_0.5_k2_sparse5 | 0.050 | 0.150 | 0.150 | 0.075 | 0.075 | 0.000 | 0.175 |
| multivariate_t3 | scale_2_k2 | 0.050 | 0.150 | 0.975 | 0.975 | 0.975 | 0.500 | 1.000 |
| multivariate_t3 | mean_0.2_k2 | 0.050 | 0.150 | 0.400 | 0.550 | 0.550 | 0.350 | 0.600 |
| real_tuesday | permute_k2 | 0.050 | 0.150 | 0.650 | 0.575 | 0.950 | 0.500 | 0.925 |
| real_tuesday | scale_2_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| gaussian | mean_0.5_k2_sparse20 | 0.050 | 0.150 | 0.325 | 0.300 | 0.300 | 0.125 | 0.350 |
| zero_inflated_tied | mean_0.2_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| real_tuesday | permute_k2_sparse20 | 0.050 | 0.150 | 0.600 | 0.500 | 0.525 | 0.300 | 0.600 |
| real_heldout | permute_k2_sparse20 | 0.050 | 0.150 | 0.625 | 0.575 | 0.600 | 0.325 | 0.625 |
| real_tuesday | mean_0.5_k2_sparse20 | 0.050 | 0.150 | 0.600 | 0.950 | 0.950 | 0.475 | 0.950 |
| multivariate_t3 | permute_k2_sparse20 | 0.050 | 0.150 | 0.400 | 0.300 | 0.300 | 0.100 | 0.325 |
| real_heldout | permute_k1 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.950 | 1.000 |
| real_heldout | null | - | - | - | - | - | - | - |
| zero_inflated_tied | mean_0.5_k2_sparse20 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| gaussian | permute_k2 | 0.050 | 0.150 | 0.625 | 0.550 | 0.950 | 0.500 | 0.875 |
| real_heldout | paircorr_0.8_k2 | 0.050 | 0.150 | 0.600 | 0.600 | 0.600 | 0.475 | 0.600 |
| multivariate_t3 | permute_k2 | 0.050 | 0.150 | 0.700 | 0.650 | 0.925 | 0.500 | 0.925 |
| real_heldout | permute_k5 | 0.050 | 0.150 | 0.310 | 0.290 | 0.600 | 0.200 | 0.600 |
| zero_inflated_tied | permute_k2_sparse20 | 0.050 | 0.150 | 0.125 | 0.100 | 0.100 | 0.025 | 0.125 |
| zero_inflated_tied | scale_2_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| gaussian | mean_0.5_k2_sparse5 | 0.050 | 0.150 | 0.250 | 0.200 | 0.200 | 0.100 | 0.225 |
| gaussian | null | - | - | - | - | - | - | - |
| real_heldout | scale_2_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| multivariate_t3 | paircorr_0.3_k2 | 0.050 | 0.150 | 0.600 | 0.600 | 0.600 | 0.500 | 0.600 |
| gaussian | scale_0.5_k2_sparse20 | 0.050 | 0.150 | 0.300 | 0.350 | 0.350 | 0.175 | 0.300 |
| real_heldout | mean_0.5_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| real_heldout | mean_0.2_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| zero_inflated_tied | paircorr_0.3_k2 | 0.050 | 0.150 | 0.725 | 0.675 | 0.675 | 0.325 | 0.600 |
| multivariate_t3 | scale_0.5_k2_sparse20 | 0.050 | 0.150 | 0.125 | 0.200 | 0.200 | 0.075 | 0.175 |
| real_tuesday | mean_0.5_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| real_tuesday | permute_k5 | 0.050 | 0.150 | 0.340 | 0.290 | 0.580 | 0.200 | 0.600 |
| multivariate_t3 | mean_0.5_k2_sparse20 | 0.050 | 0.150 | 0.150 | 0.200 | 0.200 | 0.125 | 0.225 |
| multivariate_t3 | permute_k5 | 0.050 | 0.150 | 0.360 | 0.320 | 0.580 | 0.200 | 0.590 |
| real_tuesday | mean_0.2_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| real_tuesday | paircorr_0.8_k2 | 0.050 | 0.150 | 0.650 | 0.650 | 0.650 | 0.425 | 0.625 |
| zero_inflated_tied | mean_0.5_k2_sparse5 | 0.050 | 0.150 | 0.175 | 0.325 | 0.325 | 0.200 | 0.350 |
| zero_inflated_tied | permute_k2 | 0.050 | 0.150 | 0.400 | 0.325 | 0.325 | 0.175 | 0.225 |
| zero_inflated_tied | permute_k5 | 0.050 | 0.150 | 0.260 | 0.240 | 0.240 | 0.100 | 0.170 |
| zero_inflated_tied | mean_0.5_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| gaussian | paircorr_0.3_k2 | 0.050 | 0.150 | 0.700 | 0.675 | 0.675 | 0.425 | 0.600 |
| real_heldout | mean_0.5_k2_sparse5 | 0.050 | 0.150 | 0.400 | 0.350 | 0.350 | 0.125 | 0.475 |
| multivariate_t3 | permute_k1 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.850 | 1.000 |
| gaussian | permute_k1 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.850 | 1.000 |
| real_tuesday | scale_0.5_k2_sparse20 | 0.050 | 0.150 | 0.675 | 0.900 | 0.900 | 0.450 | 0.900 |
| multivariate_t3 | scale_0.5_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| real_heldout | permute_k2 | 0.050 | 0.150 | 0.650 | 0.575 | 0.950 | 0.475 | 0.975 |
| real_tuesday | paircorr_0.3_k2 | 0.050 | 0.150 | 0.550 | 0.550 | 0.550 | 0.425 | 0.575 |
| real_tuesday | permute_k1 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.900 | 1.000 |
| real_tuesday | scale_0.5_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| real_heldout | scale_0.5_k2_sparse20 | 0.050 | 0.150 | 0.600 | 0.850 | 0.850 | 0.425 | 0.850 |
| zero_inflated_tied | permute_k1 | 0.050 | 0.150 | 0.250 | 0.300 | 0.300 | 0.050 | 0.050 |
| zero_inflated_tied | scale_0.5_k2_sparse20 | 0.050 | 0.150 | 0.975 | 0.975 | 0.975 | 0.500 | 0.975 |
| multivariate_t3 | paircorr_0.8_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| multivariate_t3 | mean_0.5_k2 | 0.050 | 0.150 | 0.925 | 1.000 | 1.000 | 0.500 | 1.000 |
| real_heldout | mean_0.5_k2_sparse20 | 0.050 | 0.150 | 0.575 | 0.925 | 0.950 | 0.400 | 0.875 |
| gaussian | mean_0.2_k2 | 0.050 | 0.150 | 0.550 | 0.675 | 0.675 | 0.375 | 0.675 |
| zero_inflated_tied | paircorr_0.8_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| zero_inflated_tied | scale_0.5_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| gaussian | mean_0.5_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| gaussian | scale_2_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| zero_inflated_tied | null | - | - | - | - | - | - | - |
| real_tuesday | mean_0.5_k2_sparse5 | 0.050 | 0.150 | 0.425 | 0.575 | 0.575 | 0.250 | 0.600 |
| gaussian | paircorr_0.8_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| real_heldout | paircorr_0.3_k2 | 0.050 | 0.150 | 0.550 | 0.550 | 0.550 | 0.450 | 0.575 |
| gaussian | permute_k5 | 0.050 | 0.150 | 0.320 | 0.240 | 0.590 | 0.200 | 0.570 |
| multivariate_t3 | null | - | - | - | - | - | - | - |
| gaussian | scale_0.5_k2 | 0.050 | 0.150 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| real_tuesday | null | - | - | - | - | - | - | - |
| gaussian | permute_k2_sparse20 | 0.050 | 0.150 | 0.375 | 0.375 | 0.375 | 0.125 | 0.375 |

Per-instance cost is recorded in each result envelope's metadata
(`timings.total_s`), never in the metrics payload, so identical
re-runs compare equal.

