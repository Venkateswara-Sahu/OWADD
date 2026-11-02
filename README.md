# Vigil

[![CI](https://github.com/Venkateswara-Sahu/OWADD/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Venkateswara-Sahu/OWADD/actions/workflows/ci.yml)

**Unsupervised Drift & Novelty Monitoring for Tabular Network Streams with Decomposed & Permutation-Calibrated Copula-KS Attribution.**

[PyPI (`vigil-drift`)](https://pypi.org/project/vigil-drift/) · [Project Site](https://venkateswara-sahu.github.io/OWADD/) · [Research Status](docs/research-status.md) · [Calibrated Study Report](docs/superpowers/calibrated-attribution-study-2026-10-24.md) · [Decomposed Study Report](docs/superpowers/decomposed-copula-ks-study-2026-10-16.md) · [Mechanism Diagnosis Report](docs/superpowers/final-mechanism-decision-2026-09-28.md)

---

## Overview

**Vigil** extends the dual-autoencoder open-world drift and novelty detection framework ([arXiv:2605.29834](https://arxiv.org/abs/2605.29834)) with **Decomposed Copula-KS Attribution** (`Vigil(attribution_mode="decomposed")`) and **Permutation-Calibrated Edge-Peeling Attribution** (`Vigil(attribution_mode="calibrated")`), label-free feature localization engines for non-stationary, heavy-tailed network traffic streams.

### Key Scientific Findings & Methodological Solution

In our 40-seed controlled mechanism investigation ([`final-mechanism-decision-2026-09-28.md`](docs/superpowers/final-mechanism-decision-2026-09-28.md)) and 500-trial null-calibration study ([`calibrated-attribution-study-2026-10-24.md`](docs/superpowers/calibrated-attribution-study-2026-10-24.md)), we showed empirically that standard bottleneck autoencoder reconstruction-error attribution suffers from a sharp **regime dichotomy**, while asymptotic correlation tests suffer from **null miscalibration**:
1. **Univariate Marginal Blindness:** On small univariate mean shifts (`+0.5 SD`), a trained bottleneck autoencoder achieves only **32.5% Recall@3**—worse than an untrained random network (**57.5%**) and univariate Kolmogorov-Smirnov (**100.0%**) due to bottleneck pass-through and cross-feature reconstruction-error smearing.
2. **Relational Dependency Strength:** Conversely, on multivariate dependency shifts (`n=800, bg=0.3, delta=0.6`), autoencoder training jumps from **10.0% to 97.5% Recall@3** while univariate KS collapses to **15.0%**.
3. **Invalid Asymptotic Fisher-$z$ Nulls on Real Network Flows:** Raw sample Pearson correlation and the naive KS+Pearson hybrid are severely **miscalibrated** when nothing has changed: on 500 genuine-null windows from the normal-only NSL-KDD pool, the hybrid reports drift **98.6%** of the time and raw Pearson alone **98.4%** (against a nominal 5%), while the asymptotic Gaussian-copula Fisher-$z$ pathway still rejects **82.2%** there and **59.0% / 57.8%** of 500 CICIDS2017 Tuesday / held-out windows (`artifacts/runs/real-null-v1`, `artifacts/runs/calibrated-study-v3`). Rank-normal scores make each *marginal* Gaussian (up to ties), not the *joint* copula, so pooled-label permutation calibration is required for valid FWER control.

**Fast Asymptotic Mode (`attribution_mode="decomposed"`):**
`DriftAttributor` decouples feature attribution into two Bonferroni-scaled pathways (`7.6 ms` median at `d=20, n=400`):
- **Marginal Pathway ($E_{\text{marg}}$):** Exact two-sample Kolmogorov-Smirnov test per feature scaled as $-\log_{10}(\min(1, d \cdot p_{\text{KS}}))$.
- **Relational Pathway ($E_{\text{rel}}$):** Within-window van der Waerden rank-normal transformation $\Phi^{-1}(\text{rank}/(N+1))$ (empirical Gaussian copula) followed by pairwise Fisher-$z$ correlation differences across all $M = \binom{d}{2}$ feature pairs, scaled as $-\log_{10}(\min(1, 2M \cdot \Phi(-z_{\max}))) + 10^{-3}\text{RMS}(z_{\text{diff}})$.

### Permutation Calibration & Greedy Edge Peeling (`attribution_mode="calibrated"`)

Because asymptotic Fisher-$z$ thresholds over-reject under non-Gaussian tail dependence and heavy ties, the opt-in `calibrated` mode replaces the asymptotic null with a pooled-window permutation null and greedy vertex-cover edge peeling:

- **Pooled-label permutations.** Reference and current windows are pooled, re-split at random $B$ times (supporting contiguous `block_size > 1` for local serial dependence), and every statistic is recomputed per split; each feature/edge is adjusted against the **family maximum** (Westfall–Young max-statistic $p$-values, add-one corrected), controlling FWER at **3.2%–5.8%** across Gaussian, tied, $t_3$, and CICIDS2017 pools (**3.4%** on normal-only NSL-KDD) when rows are exchangeable.
- **Alpha split.** Marginal and relational families are each tested at $\alpha/2$, controlling their union at $\alpha$ without assuming pathway independence. Calls with $\alpha < 2/(B+1)$ raise `ValueError` rather than silently returning unreachable thresholds.
- **Greedy edge peeling.** Significant relational edges ($p_{jk} \le \alpha/2$) are treated as a graph and peeled greedily by $\sum_k z_{jk}^2$, separating permuted features from unshifted partners and lifting CICIDS2017 two-feature permutation Recall@3 from **65.0% to 95.0%** (`n=400`, Holm $p < 0.05$).

Cost is one pass of $B$ permutations over the pooled windows — **0.30–0.38 s** median at $d=20, n=400, B=199$ and **1.00–1.33 s** at $d=78$ on a laptop CPU (`python -m experiments.calibrated_cost`, [`artifacts/benchmarks/calibrated_cost.json`](artifacts/benchmarks/calibrated_cost.json) and [`calibrated_cost_d78.json`](artifacts/benchmarks/calibrated_cost_d78.json), vs. **7.6 ms** and **30.0 ms** for `decomposed`) — placing it at drift-alert time rather than per-batch time. Note that on raw capture-ordered CICIDS2017 windows, serial autocorrelation extends past 50 flows (`41.3%` null rejection at `block_size=50`), so calibrated $p$-values require exchangeable window draws.

---

## Reproducible Attribution Benchmark (40 Seeds: 20 Validation + 20 Held-Out Test)

Mean **Recall@3 (%)** and **MRR** across 20 Validation seeds (`50..69`, Tuesday CICIDS2017) and 20 untouched Held-Out Test seeds (`70..89`, Wednesday–Friday CICIDS2017) from `experiments/decomposed_study.py` ([full tables & 95% CIs](docs/superpowers/decomposed-copula-ks-study-2026-10-16.md); uniform-random Recall@3 chance line is `3/d = 15.0%`):

| Split / Condition | Decomposed Copula-KS (Ours) | Trained AE (`positive`) | Trained AE (`absolute`) | Untrained AE (`absolute`) | Univariate KS | Pearson Correlation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `independent/mean_0.5` (Val) | **100.0%** (1.000) | 45.0% (0.607) | 32.5% (0.508) | 57.5% (0.761) | **100.0%** (1.000) | 7.5% (0.217) |
| `independent/std_0.5` (Val) | **100.0%** (1.000) | 0.0% (0.092) | 92.5% (0.925) | **100.0%** (1.000) | **100.0%** (1.000) | 10.0% (0.247) |
| `independent/correlation_0.8` (Val) | **100.0%** (1.000) | 22.5% (0.336) | 20.0% (0.301) | 7.5% (0.210) | 20.0% (0.292) | **100.0%** (1.000) |
| `dependency/bg_0_n_800_delta_0.2` (Val) | **100.0%** (0.950) | 15.0% (0.287) | 22.5% (0.326) | 10.0% (0.243) | 15.0% (0.264) | **100.0%** (1.000) |
| `dependency/bg_0.3_n_800_delta_0.6` (Val) | **100.0%** (1.000) | 0.0% (0.077) | 97.5% (0.967) | 10.0% (0.191) | 15.0% (0.282) | **100.0%** (1.000) |
| `real/mean_0.5` (CICIDS2017 Val: Tue) | **100.0%** (1.000) | 35.0% (0.439) | 20.0% (0.325) | 12.5% (0.308) | **100.0%** (1.000) | 17.5% (0.311) |
| `real/std_0.5` (CICIDS2017 Val: Tue) | **100.0%** (1.000) | 20.0% (0.241) | 15.0% (0.224) | 10.0% (0.244) | **100.0%** (1.000) | 17.5% (0.287) |
| `real/permutation` (CICIDS2017 Val: Tue) | **65.0%** (**1.000**) | 40.0% (0.538) | 27.5% (0.480) | 10.0% (0.245) | 15.0% (0.246) | **65.0%** (0.775) |
| `real/mean_0.5` (CICIDS2017 Test: Wed–Fri) | **100.0%** (1.000) | 10.0% (0.243) | 7.5% (0.199) | 10.0% (0.236) | **100.0%** (1.000) | 17.5% (0.289) |
| `real/std_0.5` (CICIDS2017 Test: Wed–Fri) | **100.0%** (1.000) | 7.5% (0.232) | 5.0% (0.188) | 12.5% (0.225) | **100.0%** (1.000) | 17.5% (0.288) |
| `real/permutation` (CICIDS2017 Test: Wed–Fri) | 55.0% (**1.000**) | 27.5% (0.402) | 17.5% (0.291) | 10.0% (0.233) | 17.5% (0.263) | **67.5%** (0.700) |

*Note on interpretation:* Recall@3 and MRR measure localization of the two injected feature indices on synthetic and semi-synthetic CICIDS2017 flow windows, not supervised attack recall or formal causal discovery. On `real/permutation`, `calibrated` mode with greedy edge peeling raises Recall@3 from **65.0% to 95.0%** across both CICIDS2017 splits (`n=400`, [`calibrated-attribution-study-2026-10-24.md`](docs/superpowers/calibrated-attribution-study-2026-10-24.md)).

---

## 5-Seed Streaming Drift & Novelty Benchmark (NSL-KDD + `river` Baselines)

Evaluated via `python -m experiments.nsl_kdd_multiseed` across 5 seeds (`42..46`, Mean $\pm$ SD; 1,000 normal training samples with leakage-free normal-only scaling; 50 stream chunks $\times$ 200 samples; `drift_threshold=0.30`; `attribution_mode="decomposed"`):

| Method | Stream Input | Precision (%) | Recall (%) | F1 Score (%) | Delay (Chunks) | Novelty Recall (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| **Vigil (`verified_only`)** | Unsupervised AE Error | **100.0 ± 0.0** | **96.0 ± 3.6** | **97.9 ± 1.9** | **1.0 ± 0.0** | **96.7 ± 3.0** |
| **Vigil (`auto`)** | Unsupervised AE Error | **100.0 ± 0.0** | **81.8 ± 4.7** | **89.9 ± 2.9** | **1.0 ± 0.0** | **96.7 ± 3.0** |
| ADWIN (`river`) | Supervised 1-NN Error | 100.0 ± 0.0 | 24.9 ± 2.2 | 39.8 ± 2.8 | 4.2 ± 2.0 | — |
| KSWIN (`river`) | Supervised 1-NN Error | 100.0 ± 0.0 | 14.2 ± 5.0 | 24.6 ± 7.6 | 7.0 ± 4.2 | — |
| Page-Hinkley (`river`) | Supervised 1-NN Error | 100.0 ± 0.0 | 20.4 ± 3.3 | 33.8 ± 4.4 | 4.2 ± 2.0 | — |
| ADWIN (`river`) | Unsupervised AE Error | 100.0 ± 0.0 | 4.0 ± 0.9 | 7.7 ± 1.7 | 5.8 ± 4.4 | — |
| KSWIN (`river`) | Unsupervised AE Error | 94.9 ± 2.6 | 64.4 ± 4.0 | 76.7 ± 2.8 | 1.2 ± 0.4 | — |
| Page-Hinkley (`river`) | Unsupervised AE Error | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | — | — |

*Scope note:* This 50-chunk schedule contains 5 normal chunks followed by 45 attack-containing chunks (where an always-alarm rule scores `94.7%` F1 and `verified_only` operates as a non-adaptive frozen-baseline detector); treat it as a state-machine continuity check rather than a multi-regime change-point benchmark.

---

## Quick Start

```bash
git clone https://github.com/Venkateswara-Sahu/OWADD.git
cd OWADD
pip install -e ".[dev,research]"
python -m pytest tests/ -q
```

### Python API

```python
from vigil import Vigil

sentinel = Vigil(
    feature_names=feature_names,
    top_k_features=5,
    attribution_mode="calibrated",   # 'calibrated', 'decomposed', 'positive_delta', 'absolute_delta', 'standardized_delta'
    adaptation_mode="verified_only", # 'verified_only' / 'frozen' (non-adaptive) or 'auto'
    n_permutations=199,
    seed=42,
)
sentinel.fit(baseline_normal_data)

for batch in stream:
    result = sentinel.detect(batch)
    if result.drift_detected and result.attribution:
        for feat in result.attribution.top_features:
            print(f"{feat['feature_name']} ({feat['drift_type']}): {feat['contribution']:.1%}")
```

---

## Architecture & MLOps Integrations

| Component | Description |
| --- | --- |
| `vigil/` | Dual-autoencoder (`A` & `A_KC`), replicated Welch T-test detector (with post-drift warm-up continuity), KDE novelty detector, and `DriftAttributor` (`calibrated`, `decomposed` + reconstruction modes) |
| `experiments/` | Provenance-verified evaluation suite (`calibrated_study.py`, `real_null_calibration.py`, `calibrated_blocknull.py`, `decomposed_study.py`, dataset split & leakage audits) |
| `api/` | Thread-safe FastAPI microservice (`/fit`, `/detect`, `/status`, `/health`) |
| `dashboard/` | Streamlit Signal Observatory: live NSL-KDD stream monitor, interactive Edge-Peeling attribution sandbox, and provenance-locked benchmark explorer |
| `kafka_pipeline/` & `airflow/` | Example streaming consumer/producer and automated retraining DAG with quality gate |

```bash
pip install -e ".[api,dashboard,mlflow,kafka]"
uvicorn api.app:app --host 127.0.0.1 --port 8000
streamlit run dashboard/app.py
```

## License

MIT License. See [LICENSE](LICENSE).
