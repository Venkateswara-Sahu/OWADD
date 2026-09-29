# Novelty prevalence and low-FPR sensitivity — 25 September 2026

All 360 per-seed evaluations completed: 10 seeds x 3 methods x 2 operating points x 6 populations (full development pool plus five prevalence scenarios). No model was retrained. Original calibration freezes were not modified; official test data was not read.

## Evidence

- Declared protocol: `novelty-prevalence-protocol-2026-09-25.md`.
- Analysis code: clean commit `e639bf940b60060a20256ea3663c0e1ad5ec94a2`, source-tree SHA-256 `b3f84ef55658f39dfe65a1ee4e50878fe745ff0b4af181f4f863bd05d86594c9`.
- Source pilot: original 30 retained runs from commit `41d9281`; all original result, freeze and raw-score checksums were verified.
- Output: `artifacts/raw_results/novelty-sensitivity-v1/b63563584dc76310/dfb4b793ad7cdc1b/result.json`.
- Output SHA-256: `3c33fab2f7a99109261a933027db8604bb9d290fd0471ada45a71079d97f6f4a`.
- Output retains 360 individual records, 36 grouped summaries, every selected threshold, calibration FPR, sampled-index hashes, and 120 source artifact checksums. A second invocation reproduced the results and successfully resumed the same completed output.

## Central result at 1% attacks

Each scenario contains 8,000 distinct samples: 80 attacks and 7,920 normal records. Values are means over ten model seeds, using identical sample indices.

| Method / operating point | Precision | Recall | F1 | Normal FPR | False alerts | True alerts |
|---|---:|---:|---:|---:|---:|---:|
| Vigil / original calibration-F1 | 7.58% | 97.38% | 14.07% | 12.020% | 952.0 | 77.9 |
| Vigil / calibration 1%-FPR target | 45.54% | 82.50% | 58.65% | 0.999% | 79.1 | 66.0 |
| Isolation Forest / original calibration-F1 | 5.44% | 97.38% | 10.30% | 17.617% | 1395.3 | 77.9 |
| Isolation Forest / calibration 1%-FPR target | 41.95% | 80.25% | 55.09% | 1.122% | 88.9 | 64.2 |
| Constant / original all-novel prediction | 1.00% | 100.00% | 1.98% | 100.000% | 7920.0 | 80.0 |
| Constant / low-FPR no-novel prediction | Undefined | 0.00% | 0.00% | 0.000% | 0.0 | 0.0 |

For Vigil's exploratory low-FPR point, seed-bootstrap 95% intervals are precision [44.66%, 46.42%], recall [81.00%, 83.87%], F1 [57.99%, 59.35%], and normal FPR [0.952%, 1.043%]. Mean false alerts have interval [75.4, 82.6]. These are conditional model-seed intervals, not population/generalization confidence bounds. No paired significance claim versus Isolation Forest is made here.

## Vigil across prevalence scenarios

| Attack prevalence | Original precision | Original recall | Low-FPR precision | Low-FPR recall | Low-FPR F1 |
|---|---:|---:|---:|---:|---:|
| 1% | 7.58% | 97.38% | 45.54% | 82.50% | 58.65% |
| 5% | 30.09% | 98.02% | 81.49% | 84.67% | 83.03% |
| 10% | 47.22% | 97.55% | 90.43% | 83.38% | 86.74% |
| 25% | 72.61% | 97.19% | 96.35% | 82.85% | 89.07% |
| 50% | 89.02% | 97.53% | 98.79% | 84.00% | 90.78% |

Different scenarios reuse observations and have different sampled attack compositions. They are paired sensitivity analyses, not independent replications or realistic traffic replays. Sampling is without replacement within each scenario. Scores/rankings are unchanged when the threshold changes; AP and AUROC therefore do not improve merely from choosing the low-FPR point.

## Interpretation

The original high F1 on the 77.58%-attack development pool hid a large false-alert burden. Calibration-only FPR control makes the operating point much more useful at lower prevalence, but sacrifices recall. At 1% attacks, even the revised point still produces more false alerts than true alerts on average. This is not production readiness.

The maximum empirical calibration FPR across the low-FPR cases was 0.99185%. On the complete development reporting pool, Vigil's low-FPR setting achieved mean FPR 1.0213%, recall 82.9873%, F1 90.5376%; Isolation Forest achieved FPR 1.1358%, recall 80.8354%, F1 89.2327%. A calibration target does not guarantee the same FPR on unseen data.

This new operating point is explicitly exploratory: the investigation followed inspection of earlier development results. Its threshold uses only known calibration scores, but the reporting pool has already been examined. Keep the final official test untouched until the broader experiment protocol is frozen.

Next priorities are per-class recall/missed-attack analysis (especially rare classes), independent split/dataset validation, and the primary feature-attribution research. Do not repeatedly tune against this reporting pool or claim that threshold adjustment improves the underlying representation. The paper still needs controlled attribution baselines, CICIDS2017 evaluation, systems measurements and final held-out evidence.

## Verification

139 tests passed. Scoped Ruff/Black checks passed; repository-wide Ruff still reports 214 findings elsewhere. Independent specification review found no issue; standards review identified duplicate prevalence settings inflating the number of bootstrap observations. Five failing regression cases reproduced the missing validation, then passed after duplicate/invalid settings were rejected. This is scoped review, not whole-branch or manuscript approval.
