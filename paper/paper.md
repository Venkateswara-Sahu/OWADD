---
title: "Vigil: Unsupervised Drift & Novelty Monitoring for Tabular Network Streams with Calibrated Copula-KS Attribution"
tags:
  - Python
  - machine learning
  - concept drift
  - novelty detection
  - feature attribution
  - network security
  - Gaussian copula
authors:
  - name: Venkateswara Sahu
    affiliation: 1
affiliations:
  - name: Department of Computer Science and Engineering, Lovely Professional University, Punjab, India
    index: 1
date: 1 November 2026
bibliography: vigil_paper.bib
---

# Summary

Machine learning models deployed in Security Operations Centers (SOCs) and network traffic monitors operate in non-stationary environments where traffic distributions shift continuously and ground-truth labels are unavailable in real time [@gama2014survey]. While unsupervised drift detectors can alert operators *when* a distributional shift occurs, high-dimensional tabular streams require *feature-level drift attribution* so analysts can distinguish univariate volume surges (*marginal shifts*) from broken protocol invariants (*relational shifts*).

**Vigil** (`vigil-drift`) is an open-source Python library and MLOps system for label-free concept drift detection, open-world novelty recognition, and **Decomposed & Permutation-Calibrated Copula-KS Attribution** on tabular data streams. Building upon the dual-autoencoder Open World Autoencoding Drift Detection (OWADD) paradigm [@komorniczak2026owadd], Vigil contributes:

1. **Decomposed & Calibrated Copula-KS Attribution (`DriftAttributor`, `compute_calibrated_scores`):** A fast (`7.6 ms` at `d=20, n=400`) asymptotic decomposition combining two-sample Kolmogorov-Smirnov marginal log-evidence with within-window van der Waerden rank-normal Fisher-$z$ relational log-evidence, paired with an opt-in Westfall–Young max-statistic permutation calibration (`0.30–0.38 s` at `B=199`) with an $\alpha/2$ family split and greedy vertex-cover edge peeling.
2. **Continuous Post-Drift State Synchronization (`Vigil`):** Fixes two streaming state-machine flaws in reference dual-autoencoder detectors—post-drift warm-up blindness across consecutive attack windows and pre-adaptation error buffer desynchronization—and provides non-adaptive frozen-reference modes (`frozen` / `verified_only`) alongside adaptive updates.
3. **Production MLOps Stack:** A thread-safe FastAPI microservice (`api/`), a Streamlit SOC dashboard (`dashboard/`), Apache Kafka streaming integration (`kafka_pipeline/`), Apache Airflow quality-gated retraining DAGs (`airflow/`), and a provenance-verified benchmark harness (`experiments/`).

# Statement of Need

Classical streaming concept drift detectors—such as ADWIN [@bifet2007adwin], KSWIN [@raab2020kswin], and Page-Hinkley [@page1954continuous] implemented in `river` [@montiel2021river]—monitor a single scalar error stream and typically require ground-truth labels at inference time. Unsupervised autoencoder monitors [@sakurada2014anomaly; @komorniczak2026owadd] eliminate the label requirement by monitoring reconstruction error $e_A(x) = \|x - A(x)\|_2^2$, and practitioners commonly rank features by their change in squared reconstruction error $\Delta_j$.

Our 40-seed controlled mechanism study across synthetic and improved CICIDS2017 [@sharafaldin2018cicids; @engelen2021troubleshooting] flow windows showed empirically that autoencoder reconstruction attribution suffers from a **regime dichotomy**, while asymptotic relational thresholds fail under real network telemetry:

- **Univariate Marginal Blindness:** On small univariate mean shifts ($+0.5\sigma$), a trained bottleneck autoencoder achieves only $32.5\%$ Recall@3—worse than an untrained random-weight network ($57.5\%$) and univariate Kolmogorov-Smirnov tests ($100.0\%$)—due to bottleneck pass-through and cross-feature decoder error smearing.
- **Relational Miscalibration under Heavy Tails and Ties:** On multivariate dependency shifts, trained autoencoders jump from $10.0\%$ to $97.5\%$ Recall@3 while univariate KS drops to $15.0\%$. However, on 500 genuine-null windows from normal-only NSL-KDD traffic, raw Pearson Fisher-$z$ rejects $98.4\%$ of unchanged pairs and even rank-normal Gaussian-copula Fisher-$z$ rejects $82.2\%$ ($57.8\%\text{--}59.0\%$ on CICIDS2017) against a nominal $5\%$, because normal marginals do not imply a bivariate-normal joint copula.

# Methodology & Empirical Validation

When drift is detected between reference features $X_{\mathrm{ref}}$ and current features $X_{\mathrm{cur}}$:

- **Fast Decomposed Mode (`mode="decomposed"`):** Evaluates Bonferroni-scaled KS marginal evidence $E_{\mathrm{marg}}(j)$ and van der Waerden normal-score Fisher-$z$ relational evidence $E_{\mathrm{rel}}(j)$ in $7.6\,\mathrm{ms}$ median ($d = 20, n = 400$), achieving **100.0% Recall@3** on dense univariate CICIDS2017 shifts and **1.000 MRR** on column permutations (`65.0%` Val / `55.0%` Test Recall@3).
- **Calibrated Peeling Mode (`mode="calibrated"`):** Pools $(X_{\mathrm{ref}}, X_{\mathrm{cur}})$ across $B = 199$ label permutations (with optional contiguous `block_size` for local dependence), splits $\alpha$ across the two families ($\alpha/2$ each), and greedily peels the significant-edge graph by $\sum_k z_{jk}^2$. Across 500 null trials per pool, FWER returns to **3.2%–5.8%** (**3.4%** on normal-only NSL-KDD) on exchangeable windows, while two-feature column-permutation Recall@3 improves from **65.0% to 95.0%** on CICIDS2017 (`n = 400`, Holm $p < 0.05$). On raw capture-ordered CICIDS2017 streams, autocorrelation extends beyond 50 rows (`41.3%` rejection at `block_size=50`), establishing row exchangeability as an explicit scope boundary.
- **5-Seed NSL-KDD Continuity Check [@tavallaee2009nsl]:** Across 5 seeds (`42..46`, 50 chunks $\times$ 200 samples; 5 negative chunks, where an always-alarm baseline reaches `94.7%` F1), `Vigil` achieves **100.0 ± 0.0% precision**, **97.9 ± 1.9% F1** in non-adaptive `verified_only` mode (**89.9 ± 2.9% F1** in adaptive `auto` mode), and a **1.0-chunk detection delay**.

# Availability

`Vigil` is released under the MIT License at [https://github.com/Venkateswara-Sahu/OWADD](https://github.com/Venkateswara-Sahu/OWADD) and is installable via `pip install vigil-drift`.

# References
