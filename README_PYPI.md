# Vigil (`vigil-drift`)

**Unsupervised Drift & Novelty Monitoring for Tabular Network Streams with Decomposed & Permutation-Calibrated Copula-KS Attribution.**

[PyPI (`vigil-drift`)](https://pypi.org/project/vigil-drift/) · [Project Site](https://venkateswara-sahu.github.io/OWADD/) · [GitHub Repository](https://github.com/Venkateswara-Sahu/OWADD) · [Research Status](https://github.com/Venkateswara-Sahu/OWADD/blob/main/docs/research-status.md) · [Calibrated Attribution Study](https://github.com/Venkateswara-Sahu/OWADD/blob/main/docs/superpowers/calibrated-attribution-study-2026-10-24.md)

---

## Overview

**Vigil** extends the dual-autoencoder open-world drift and novelty detection framework ([arXiv:2605.29834](https://arxiv.org/abs/2605.29834)) with **Decomposed Copula-KS Attribution** (`Vigil(attribution_mode="decomposed")`) and **Permutation-Calibrated Edge-Peeling Attribution** (`Vigil(attribution_mode="calibrated")`), label-free feature localization engines for non-stationary, heavy-tailed network traffic streams.

### Key Empirical Findings & Methodological Solution

1. **Autoencoder Attribution Dichotomy ([`final-mechanism-decision-2026-09-28.md`](https://github.com/Venkateswara-Sahu/OWADD/blob/main/docs/superpowers/final-mechanism-decision-2026-09-28.md)):** Across 40 seeds on synthetic and CICIDS2017 network flows, training a bottleneck autoencoder substantially improves localization of multi-feature dependency shifts (`10.0%` → `97.5%` Recall@3), but degrades small univariate mean-shift localization (`57.5%` untrained → `32.5%` trained vs. `100.0%` KS) due to bottleneck pass-through and cross-feature decoder error smearing.
2. **Decomposed & Permutation-Calibrated Copula-KS Attribution ([`calibrated-attribution-study-2026-10-24.md`](https://github.com/Venkateswara-Sahu/OWADD/blob/main/docs/superpowers/calibrated-attribution-study-2026-10-24.md)):** Fast `decomposed` mode (`7.6 ms` median at `d=20, n=400`) pairs Bonferroni-scaled Kolmogorov-Smirnov marginal log-evidence with within-window van der Waerden rank-normal (`Φ⁻¹(rank / (N + 1))`) Fisher-z relational shifts, achieving **100.0% Recall@3** on dense CICIDS2017 univariate shifts and **1.000 MRR** on column permutations. Because asymptotic Fisher-z thresholds over-reject on zero-inflated, tied, and non-Gaussian copula telemetry (`57.8%–59.0%` false-alarm rate on unchanged CICIDS2017 windows, `82.6%` on normal-only NSL-KDD), opt-in `calibrated` mode (`0.30–0.38 s` median at `d=20, n=400, B=199`) applies pooled Westfall–Young max-statistic permutation calibration with an `α/2` family split and greedy edge peeling—restoring FWER to **3.2%–5.8%** (`3.4%` on NSL-KDD) on exchangeable windows while lifting two-feature permutation Recall@3 from **65.0% to 95.0%**.
3. **Continuous Streaming Detection (`Vigil`):** Fixes post-drift warm-up blindness and pre-adaptation error buffer desynchronization, achieving **100.0 ± 0.0% precision**, **97.9 ± 1.9% F1** (`verified_only`, frozen reference) and **89.9 ± 2.9% F1** (`auto`), and a **1.0-chunk detection delay** on a 5-seed, 50-chunk NSL-KDD continuity check (note: 5 negative chunks; an always-alarm rule scores `94.7%` F1).

---

## Quick Start

```bash
pip install vigil-drift
```

```python
from vigil import Vigil

sentinel = Vigil(
    feature_names=feature_names,
    top_k_features=5,
    attribution_mode="calibrated",   # 'calibrated', 'decomposed', 'positive_delta', 'absolute_delta', 'standardized_delta'
    adaptation_mode="verified_only", # 'verified_only' / 'frozen' (non-adaptive), or 'auto'
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

*Scope & Boundaries:* Real-data attribution benchmarks on CICIDS2017 inject controlled shifts into reserved Tuesday validation and Wednesday–Friday held-out test flows standardized strictly by Monday training statistics. Recall@3 and MRR measure localization of perturbed feature indices rather than supervised intrusion classification or causal discovery, and permutation p-values require exchangeable rows within a window (or contiguous block permutations via `block_size > 1` when local serial dependence is short).

## License

MIT License. See [LICENSE](https://github.com/Venkateswara-Sahu/OWADD/blob/main/LICENSE).
