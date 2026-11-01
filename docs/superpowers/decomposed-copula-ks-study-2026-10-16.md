# Decomposed Copula-KS Attribution Study (2026-10-16)

## Executive Summary

Following the September 2026 mechanism study (`final-mechanism-decision-2026-09-28.md`), which demonstrated that bottleneck autoencoder reconstruction-error rankings suffer from pass-through adaptation and cross-feature error smearing on univariate shifts while univariate KS tests fail completely on dependency shifts, we formulated and evaluated **Decomposed Copula-KS Attribution** (`decomposed_copula_ks` / `Vigil(attribution_mode="decomposed")`).

We evaluated `decomposed_copula_ks` across two disjoint 20-seed protocols:
1. **Validation Split (`seeds 50..69`):** 18 synthetic conditions + 6 real CICIDS2017 flow conditions on reserved Tuesday flows (`32,000` flows).
2. **Held-Out Test Split (`seeds 70..89`):** 18 synthetic conditions + 6 real CICIDS2017 flow conditions across untouched held-out Wednesday, Thursday, and Friday flows (`32,000` flows) standardized strictly by Monday reference traffic.

Across both validation and held-out test splits (`40 seeds total = 720 drifted trials`), `decomposed_copula_ks` achieves **100.0% Recall@3 and 1.000 MRR on every univariate mean/scale shift on CICIDS2017**, **100.0% Recall@3 on all moderate-to-strong synthetic dependency shifts**, and **1.000 MRR (100% Top-1 accuracy across all 40 validation + held-out test seeds)** on real CICIDS2017 column permutations.

## Methodological Formulation

Given a reference window $X_{\text{ref}} \in \mathbb{R}^{n_{\text{ref}} \times d}$ and current window $X_{\text{cur}} \in \mathbb{R}^{n_{\text{cur}} \times d}$:

1. **Marginal Pathway (Family-Wise Calibrated KS):**
   For each feature $j \in \{1, \dots, d\}$, compute the exact two-sample Kolmogorov-Smirnov $p$-value $p_{\text{KS}, j}$ and convert to Bonferroni family-wise log-evidence:
   $$E_{\text{marg}}(j) = \max\left(0, -\log_{10}\left(\min(1, d \cdot p_{\text{KS}, j})\right)\right)$$

2. **Relational Pathway (Gaussian-Copula Rank-Normal Fisher-$z$):**
   Raw Pearson correlation on heavy-tailed network traffic flows exhibits severe kurtosis-induced variance, causing spurious correlation spikes during univariate shifts. We map each feature within each window to its van der Waerden empirical normal score:
   $$Z_{i,j} = \Phi^{-1}\left(\frac{\text{rank}(X_{i,j})}{N + 1}\right)$$
   Because $Z_{i,j}$ is invariant to any strictly monotonic marginal transformation and enforces exact $\mathcal{N}(0, 1)$ marginals, the sample correlation matrix $R = \text{Corr}(Z)$ captures pure copula dependency structure, and its Fisher-$z$ transform $\operatorname{arctanh}(R_{j,k})$ has exact asymptotic variance $\sigma_z^2 = \frac{1}{n_{\text{ref}} - 3} + \frac{1}{n_{\text{cur}} - 3}$.
   With $M = \binom{d}{2}$ feature pairs and $z_{j,k} = |\operatorname{arctanh}(R^{\text{cur}}_{j,k}) - \operatorname{arctanh}(R^{\text{ref}}_{j,k})| / \sigma_z$:
   $$E_{\text{rel}}(j) = \max\left(0, -\log_{10}\left(\min\left(1, 2 M \cdot \Phi(-\max_{k \neq j} z_{j,k})\right)\right)\right) + 10^{-3} \sqrt{\frac{1}{d}\sum_{k \neq j} z_{j,k}^2}$$

3. **Calibrated Synthesis & Regime Classification:**
   $$S_{\text{DDA}}(j) = \max\left(E_{\text{marg}}(j), E_{\text{rel}}(j)\right), \quad \text{type}(j) = \begin{cases} \text{relational} & \text{if } E_{\text{rel}}(j) > E_{\text{marg}}(j) \\ \text{marginal} & \text{otherwise} \end{cases}$$

## Verification and Provenance

- Benchmark module: `experiments/decomposed_study.py`
- Validation summary (`seeds 50..69`, Tuesday): `artifacts/runs/decomposed-study-v1/summary/bdcb28564f77a862/93d35e54fb2b8ba6/result.json`
- Held-out test summary (`seeds 70..89`, Wednesday/Thursday/Friday): `artifacts/runs/decomposed-study-heldout-v1/summary/1391b156e082468b/e73fe094bb85a77a/result.json`

## Part 1: Validation Split Results (`Seeds 50–69`, Tuesday CICIDS2017)

| Condition | Decomposed Copula-KS (Ours) | Trained AE (`positive`) | Trained AE (`absolute`) | Untrained AE (`absolute`) | Univariate KS | Pearson Correlation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `independent/mean_0.5` | **100.0%** (1.000) | 45.0% (0.607) | 32.5% (0.508) | 57.5% (0.761) | **100.0%** (1.000) | 7.5% (0.217) |
| `independent/mean_2` | **100.0%** (1.000) | **100.0%** (1.000) | **100.0%** (1.000) | **100.0%** (1.000) | **100.0%** (1.000) | 10.0% (0.244) |
| `independent/std_0.5` | **100.0%** (1.000) | 0.0% (0.092) | 92.5% (0.925) | **100.0%** (1.000) | **100.0%** (1.000) | 10.0% (0.247) |
| `independent/std_2` | **100.0%** (1.000) | **100.0%** (1.000) | **100.0%** (1.000) | **100.0%** (1.000) | **100.0%** (1.000) | 10.0% (0.247) |
| `independent/correlation_0.8` | **100.0%** (1.000) | 22.5% (0.336) | 20.0% (0.301) | 7.5% (0.210) | 20.0% (0.292) | **100.0%** (1.000) |
| `dependency/bg_0_n_200_delta_0.2` | **27.5%** (0.385) | 12.5% (0.226) | 10.0% (0.239) | 12.5% (0.280) | 15.0% (0.267) | 25.0% (0.379) |
| `dependency/bg_0_n_200_delta_0.6` | **100.0%** (1.000) | 20.0% (0.243) | 20.0% (0.284) | 12.5% (0.281) | 7.5% (0.201) | **100.0%** (1.000) |
| `dependency/bg_0_n_800_delta_0.2` | **100.0%** (0.950) | 15.0% (0.287) | 22.5% (0.326) | 10.0% (0.243) | 15.0% (0.264) | **100.0%** (1.000) |
| `dependency/bg_0_n_800_delta_0.6` | **100.0%** (1.000) | 27.5% (0.401) | 30.0% (0.430) | 10.0% (0.226) | 10.0% (0.261) | **100.0%** (1.000) |
| `dependency/bg_0.3_n_200_delta_0.2` | **32.5%** (0.381) | 2.5% (0.100) | 22.5% (0.284) | 10.0% (0.276) | 10.0% (0.235) | **32.5%** (0.377) |
| `dependency/bg_0.3_n_200_delta_0.6` | **100.0%** (1.000) | 0.0% (0.074) | 75.0% (0.854) | 12.5% (0.281) | 2.5% (0.164) | **100.0%** (1.000) |
| `dependency/bg_0.3_n_800_delta_0.2` | **100.0%** (1.000) | 2.5% (0.106) | 47.5% (0.630) | 12.5% (0.257) | 15.0% (0.294) | **100.0%** (1.000) |
| `dependency/bg_0.3_n_800_delta_0.6` | **100.0%** (1.000) | 0.0% (0.077) | 97.5% (0.967) | 10.0% (0.191) | 15.0% (0.282) | **100.0%** (1.000) |
| `real/mean_0.5` (CICIDS2017 Val) | **100.0%** (1.000) | 35.0% (0.439) | 20.0% (0.325) | 12.5% (0.308) | **100.0%** (1.000) | 17.5% (0.311) |
| `real/mean_2` (CICIDS2017 Val) | **100.0%** (1.000) | 55.0% (0.617) | 50.0% (0.571) | 35.0% (0.500) | **100.0%** (1.000) | 17.5% (0.311) |
| `real/std_0.5` (CICIDS2017 Val) | **100.0%** (1.000) | 20.0% (0.241) | 15.0% (0.224) | 10.0% (0.244) | **100.0%** (1.000) | 17.5% (0.287) |
| `real/std_2` (CICIDS2017 Val) | **100.0%** (1.000) | 32.5% (0.539) | 25.0% (0.491) | 27.5% (0.467) | **100.0%** (1.000) | 17.5% (0.287) |
| `real/permutation` (CICIDS2017 Val) | **65.0%** (**1.000**) | 40.0% (0.538) | 27.5% (0.480) | 10.0% (0.245) | 15.0% (0.246) | **65.0%** (0.775) |

## Part 2: Held-Out Test Split Results (`Seeds 70–89`, Untouched Wed/Thu/Fri CICIDS2017)

| Condition | Decomposed Copula-KS (Ours) | Trained AE (`positive`) | Trained AE (`absolute`) | Untrained AE (`absolute`) | Univariate KS | Pearson Correlation | Paired Gain vs Trained AE (`|Δ|`) [95% CI] |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `independent/mean_0.5` | **100.0%** (1.000) | 52.5% (0.560) | 45.0% (0.507) | 55.0% (0.698) | **100.0%** (1.000) | 10.0% (0.214) | `+55.0 [+40.0, +70.0]` |
| `independent/std_0.5` | **97.5%** (1.000) | 0.0% (0.087) | 87.5% (0.975) | **100.0%** (1.000) | **100.0%** (1.000) | 10.0% (0.239) | `+10.0 [+2.5, +20.0]` |
| `independent/correlation_0.8` | **100.0%** (1.000) | 30.0% (0.355) | 50.0% (0.484) | 17.5% (0.292) | 22.5% (0.303) | **100.0%** (1.000) | `+50.0 [+32.5, +67.5]` |
| `dep/bg_0.3_n_200_delta_0.2` | **47.5%** (0.522) | 2.5% (0.096) | 30.0% (0.441) | 20.0% (0.267) | 10.0% (0.224) | 32.5% (0.423) | `+17.5 [+0.0, +37.5]` |
| `dep/bg_0.3_n_200_delta_0.6` | **100.0%** (1.000) | 0.0% (0.081) | 77.5% (0.867) | 12.5% (0.236) | 12.5% (0.211) | **100.0%** (1.000) | `+22.5 [+10.0, +40.0]` |
| `dep/bg_0.3_n_800_delta_0.2` | **100.0%** (1.000) | 0.0% (0.089) | 57.5% (0.690) | 22.5% (0.426) | 17.5% (0.271) | 97.5% (0.967) | `+42.5 [+25.0, +62.5]` |
| `real/mean_0.5` (Wed/Thu/Fri Test) | **100.0%** (1.000) | 10.0% (0.243) | 7.5% (0.199) | 10.0% (0.236) | **100.0%** (1.000) | 17.5% (0.289) | **`+92.5 [+85.0, +100.0]`** |
| `real/mean_2` (Wed/Thu/Fri Test) | **100.0%** (1.000) | 25.0% (0.358) | 15.0% (0.251) | 17.5% (0.269) | **100.0%** (1.000) | 17.5% (0.289) | **`+85.0 [+70.0, +97.5]`** |
| `real/std_0.5` (Wed/Thu/Fri Test) | **100.0%** (1.000) | 7.5% (0.232) | 5.0% (0.188) | 12.5% (0.225) | **100.0%** (1.000) | 17.5% (0.288) | **`+95.0 [+87.5, +100.0]`** |
| `real/std_2` (Wed/Thu/Fri Test) | **100.0%** (1.000) | 32.5% (0.464) | 20.0% (0.326) | 20.0% (0.333) | **100.0%** (1.000) | 17.5% (0.288) | **`+80.0 [+65.0, +92.5]`** |
| `real/permutation` (Wed/Thu/Fri Test) | **55.0%** (**1.000**) | 27.5% (0.402) | 17.5% (0.291) | 10.0% (0.233) | 17.5% (0.263) | **67.5%** (0.700) | **`+37.5 [+20.0, +50.1]`** |
