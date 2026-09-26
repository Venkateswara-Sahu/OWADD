# Per-class missed-detection diagnostic — 26 September 2026

Read-only analysis of the existing development scores. No model training, threshold selection, official test-file access or changes to source evidence were performed. This is exploratory diagnosis of the already-inspected development population.

## Identity checks and calculation

The training source SHA-256 was verified as `1b86d2f957b33082081bba410fe129b475efebcc13c9014c3f447c8271aadf95`. Original labels were reconstructed with `prepare_frames(training_frame, None, seed=42)` and `development_protocol(..., n_reference=2000, novel_classes=NOVEL_CLASSES)`. The resulting full protocol identity, preprocessing fingerprint and ordered development row IDs exactly matched the original pilot summary.

The pilot summary and sensitivity-result completion checksums passed. All 30 original seed/method result envelopes, calibration freezes and score sidecars were validated with the existing `_read_source` integrity checks. Binary score labels matched the reconstructed ordered labels. The seed/method grid was exactly 0–9 x Vigil/Isolation Forest/constant.

Both thresholds were read from the existing sensitivity artifact's full-population records, not recalculated. Original thresholds also matched the original freezes. Each run's reconstructed true-positive count matched the saved full-population sensitivity count. For each original attack label, recall is the count of scores >= threshold divided by that class's reporting count. Table values are arithmetic means across ten seeds; intervals use the existing `bootstrap_mean_ci` defaults (2,000 resamples, seed 0). Normal samples are excluded from attack recall.

Inputs, relative to `artifacts/raw_results/`:

- `novelty-development-v1/summary/54bcc79de8c1bc0f/d0b6bd37e457c477/result.json`, SHA-256 `79ac313be79e36ff7f300b4e414e60411fc31f4c20abd3d933e80e13c16ef411`.
- `novelty-sensitivity-v1/b63563584dc76310/dfb4b793ad7cdc1b/result.json`, SHA-256 `3c33fab2f7a99109261a933027db8604bb9d290fd0471ada45a71079d97f6f4a`.
- The 30 original result/freeze/raw-score bundles referenced by those artifacts.

## All 22 attack classes

All recall values and intervals below are percentages. `n` counts distinct reporting observations, not seeds. Low-FPR means the previously selected calibration 1%-FPR target, not a guaranteed reporting FPR. Mean misses can be fractional because they average ten model runs.

| Class | n | Vigil original recall | Vigil low-FPR recall | Vigil low-FPR seed CI | IF low-FPR recall | Vigil mean misses |
|---|---:|---:|---:|---:|---:|---:|
| back | 478 | 10.63 | 0.13 | 0.04–0.21 | 0.23 | 477.4 |
| buffer_overflow | 15 | 74.00 | 4.00 | 2.00–6.00 | 0.00 | 14.4 |
| ftp_write | 4 | 90.00 | 0.00 | 0.00–0.00 | 5.00 | 4.0 |
| guess_passwd | 27 | 100.00 | 20.74 | 1.48–48.15 | 94.07 | 21.4 |
| imap | 6 | 100.00 | 80.00 | 75.00–83.33 | 48.33 | 1.2 |
| ipsweep | 1797 | 99.98 | 75.30 | 58.68–87.08 | 24.14 | 443.8 |
| land | 8 | 100.00 | 100.00 | 100.00–100.00 | 100.00 | 0.0 |
| loadmodule | 5 | 92.00 | 40.00 | 40.00–40.00 | 8.00 | 3.0 |
| multihop | 4 | 100.00 | 35.00 | 27.50–42.50 | 30.00 | 2.6 |
| neptune | 20607 | 100.00 | 90.44 | 89.01–91.64 | 99.90 | 1970.9 |
| nmap | 746 | 97.57 | 73.51 | 60.70–83.28 | 20.24 | 197.6 |
| perl | 2 | 100.00 | 0.00 | 0.00–0.00 | 0.00 | 2.0 |
| phf | 2 | 50.00 | 0.00 | 0.00–0.00 | 0.00 | 2.0 |
| pod | 101 | 100.00 | 84.06 | 76.83–91.29 | 0.20 | 16.1 |
| portsweep | 1465 | 99.99 | 86.10 | 82.02–89.89 | 91.11 | 203.7 |
| rootkit | 5 | 72.00 | 0.00 | 0.00–0.00 | 0.00 | 5.0 |
| satan | 1817 | 94.22 | 58.20 | 57.94–58.45 | 60.92 | 759.5 |
| smurf | 1323 | 100.00 | 69.40 | 66.42–72.45 | 0.39 | 404.8 |
| spy | 1 | 100.00 | 0.00 | 0.00–0.00 | 0.00 | 1.0 |
| teardrop | 446 | 100.00 | 98.90 | 98.88–98.95 | 7.78 | 4.9 |
| warezclient | 445 | 46.72 | 0.63 | 0.56–0.67 | 0.63 | 442.2 |
| warezmaster | 10 | 92.00 | 4.00 | 0.00–12.00 | 0.00 | 9.6 |

These intervals quantify variability across trained model seeds on the same rows, not uncertainty about future examples of a class. In particular, a [0,0] interval with one or two examples is not evidence of precisely zero population recall. Twelve classes have fewer than 30 reporting examples; this count is a descriptive small-sample warning, not a statistical reliability cutoff. No class is excluded from the table or macro average.

## What the pooled metric hides

| Method | Original equal-class macro recall | Low-FPR equal-class macro recall | Low-FPR sample-weighted recall |
|---|---:|---:|---:|
| Vigil | 87.23% | 41.84% | 82.99% |
| Isolation Forest | 80.19% | 26.86% | 80.84% |
| Constant | 100.00% | 0.00% | 0.00% |

Macro recall weights all 22 attack classes equally; it is not a replacement for operational prevalence-weighted performance. `neptune` contributes 20,607 of 29,314 attack examples (about 70%), strongly influencing pooled recall. Its stricter-threshold mean miss count is 1,970.9; `satan` contributes another 759.5 misses. These are the largest absolute miss contributors, even though `back` and `warezclient` have much worse class recall.

Lowering the false-alert burden has uneven costs. `back` was already weak at the original threshold (10.63% recall), so it is not solely a consequence of the new operating point. `warezclient` drops from 46.72% to 0.63%. Both have hundreds of examples, making them more actionable development failure patterns than the single `spy` observation. `guess_passwd`, `ipsweep` and `nmap` also show substantial seed variability at the stricter threshold.

Isolation Forest is not uniformly better or worse: it is much stronger on this `guess_passwd` and `neptune` subset, whereas Vigil is stronger on several other classes. Neither this table nor the pooled metric supports a universal superiority claim. Constant predictions demonstrate why recall alone cannot establish useful detection: the original constant model has 100% recall with 100% normal false positives.

## Research implications

This identifies where errors occur, not why the representation or KDE fails. Do not claim a causal mechanism from class-level metrics. Do not retune thresholds per attack class using these outcomes: labels would not be available at inference and repeated reporting-pool optimization would compromise evaluation.

The next scientific priority is the approved primary contribution: controlled feature-attribution evaluation against simple baselines. Carry these novelty limitations into the paper. Any later novelty-method change should be motivated and tuned on calibration/training data, then checked with a separately declared split/dataset protocol before final official-test evaluation. A good paper must disclose class-specific failures rather than presenting the pooled recall as broad attack coverage.

No production source or automated tests changed for this read-only diagnostic. The prior 139-test result is historical, not a new test-suite run in this diagnostic.
