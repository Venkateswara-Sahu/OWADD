# Dependency-localization screen: results

## Conclusion

The direct Pearson correlation-change baseline has higher mean Recall@3 than all three reconstruction variants in every changed condition. This does not establish statistical separation in every cell, but provides no evidence of a Vigil localization advantage on this test family. The nonlinear classifier becomes useful for strong changes with larger windows, but is unreliable for weak changes. Do not replace Vigil's default or claim state-of-the-art attribution from these results.

## Provenance and verification

- Frozen design: `dependency-screen-protocol.md`. Code checkpoint `819a20d54f7bba1c26a95245ef389ed166557d81`; execution provenance records a clean tree.
- Source SHA256: `4f6279701290fafff290e01549b977373f1417b88d202ee4da166d2fa02e0543`.
- Summary: `artifacts/raw_results/dependency-screen-v1/summary/e7cf645118ce501d/e8bc32a67f33766c/result.json`.
- Summary SHA256: `d173d6ce9fa8429885110fd7b017a3bf040b58a8c424bc4a1f95a90f274276af`.
- Verified20 seeds30-49,2640 raw score vectors,132 groups,72 paired comparisons and one summary. Metadata: protocol_complete=true,not_full_study=true.
- The run completed after the prior conversation interruption. On September28, the same CLI successfully loaded completion-checked results and reproduced the aggregate, before any source/report edits.
- Pre-run regression suite:153 passed in67.00 seconds. Scoped Ruff, Black, compile and whitespace checks passed. Independent standards/spec reviews found no blocking issues, reviewing the staged diff against `55881618f9f9ac30feea49bc86e1b93699848fdc`. The only interpretation note was that runtime has per-method intervals, not paired runtime differences.
- The initial baseline regression attempt was invalidated by source edits during its provenance/resume test; the unchanged148-test baseline passed when rerun without edits. No provenance protection was weakened.
- Public `vigil/` code is unchanged. No official NSL-KDD or CICIDS test evaluation occurred. No repository-wide lint-clean claim; the final attempted repository-wide check was not executed because approval review hit a usage limit.

## Primary results

Recall@3 percentages: fraction of the two changed features recovered among the top three. These are feature-localization metrics, not attack recall or drift-event detection rates. Background denotes each pair's original correlation; weak/strong changes add0.2/0.6 to the selected pair while maintaining population N(0,1) marginals. Results below are means across20 seeds, not pooled conditions.

| Background | Window rows | Change | Original positive | Absolute | Standardized absolute | Correlation baseline | Nonlinear permutation |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| Independent | 200 | Weak | 17.5 | 12.5 | 12.5 | 30 | 15 |
| Independent | 200 | Strong | 20 | 17.5 | 25 | 100 | 37.5 |
| Independent | 800 | Weak | 20 | 5 | 12.5 | 92.5 | 17.5 |
| Independent | 800 | Strong | 30 | 32.5 | 35 | 100 | 100 |
| Correlated0.3 | 200 | Weak | 2.5 | 32.5 | 27.5 | 35 | 12.5 |
| Correlated0.3 | 200 | Strong | 0 | 80 | 82.5 | 100 | 47.5 |
| Correlated0.3 | 800 | Weak | 0 | 45 | 52.5 | 95 | 17.5 |
| Correlated0.3 | 800 | Strong | 0 | 97.5 | 97.5 | 100 | 97.5 |

All11 methods, including the marginal-statistical, random and logistic controls, remain in the saved summary. All four stable conditions have undefined localization recall, not successful localization or a false-alarm estimate.

Selected paired standardized-absolute-minus-correlation Recall@3 differences, in percentage points:

| Background | Rows | Change | Mean difference [95% bootstrap interval] |
| --- | ---: | --- | ---: |
| Independent | 200 | Weak | -17.5 [-40,2.5] |
| Independent | 200 | Strong | -75 [-87.5,-65] |
| Independent | 800 | Weak | -80 [-95,-60] |
| Independent | 800 | Strong | -65 [-80,-47.5] |
| Correlated0.3 | 200 | Weak | -7.5 [-30,15] |
| Correlated0.3 | 200 | Strong | -17.5 [-30,-7.5] |
| Correlated0.3 | 800 | Weak | -42.5 [-60,-25] |
| Correlated0.3 | 800 | Strong | -2.5 [-7.5,0] |

Intervals are deterministic2000-resample percentile intervals over paired seeds, exploratory and unadjusted for multiple comparisons. Zero-width intervals at100% do not imply perfect population performance. Other candidate/baseline paired intervals remain available in the summary.

## Runtime and classifier diagnostics

Across the12 condition-specific means, correlation ranking took approximately0.63-1.09ms per call; original positive reconstruction1.12-2.11ms; absolute0.94-1.64ms; standardized absolute1.07-2.19ms. Nonlinear fitting plus permutation took approximately0.72-1.33seconds per call. Autoencoder fitting is separately recorded per seed/background and excluded from reconstruction-call times. Methods ran serially with numerical-library/PyTorch thread limits of one. These are laptop observations with differing fitting requirements and single calls per seed/condition, not production latency guarantees or a fair amortized deployment-cost comparison.

The nonlinear classifier's mean held-out balanced accuracy was about49.7-50.7% for weak changes and51.7-58.2% for strong changes. Thus high feature-localization recall in the large-window strong-change cases should not be confused with high reference/current classification accuracy. Stable-case means were49.1-50.8%. No classifier threshold was tuned on ground truth.

## Research implications

Correlation changes can be accompanied by decreases in reconstruction error, especially when a model is trained on an already dependent background. Two-sided scoring helps substantially in that setting, yet the direct dependency statistic remains a stronger comparator here. These results do not prove the mechanism of every individual ranking failure.

The benchmark intentionally changes Gaussian Pearson dependence, so it favors a statistic matched to that change family; it is not a universal victory over all drift types. Conversely, comparing only against marginal tests would have understated the available baseline strength. Nonlinear dependencies beyond correlation, negative correlation changes, other dimensions and real-network data remain untested.

Recommended direction: retain this honest failure analysis and narrow the research claim to evaluating when reconstruction-error attribution is useful or misleading. A broader benchmark or systems paper needs additional evidence; adding complexity solely to beat these inspected cases would risk overfitting the research process. No automatic default change, novelty claim, publication, or expanded experiment has been performed.
