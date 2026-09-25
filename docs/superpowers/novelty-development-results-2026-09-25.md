# NSL-KDD novelty development results — 25 September 2026

The declared pilot completed all 30 method/seed runs. This is development evidence, not final test evaluation, feature-attribution evidence, or an arXiv-readiness claim.

## Evidence and population

- Execution code: clean commit `41d9281198bbcb685f4f84dee5c2b0b8bd19b6b9`, source-tree SHA-256 `a85fe0833202d7f9547a8a16cab0d2b9e0338e623ee0114a6481f9f3a8d23b72`.
- Source: only `KDDTrain+.txt`, SHA-256 `1b86d2f957b33082081bba410fe129b475efebcc13c9014c3f447c8271aadf95`. No official test file loaded or hashed by this pilot.
- 16 duplicate feature vectors removed. Preprocessing fitted on 50,400 normal reference rows; models fitted on the same fixed 2,000-row subset.
- Calibration: 37,773 rows, including 8,469 normal. Development reporting: 37,784 rows, including 8,470 normal and 29,314 attacks. Attack prevalence is **77.5831%**, reflecting this constructed population, not operational traffic prevalence.
- All 22 declared attack classes occur in both calibration and development reporting. They are novel relative to model fitting, not unseen during threshold calibration. Some rare classes have only one or two reporting examples; pooled scores do not establish performance on rare attacks.
- Ten model seeds, 0–9; fixed data pools; no post-result hyperparameter changes. CPU-only, one Torch thread and one Isolation Forest worker.
- Raw root: `artifacts/raw_results/novelty-development-v1`. Summary: `summary/54bcc79de8c1bc0f/d0b6bd37e457c477/result.json`, SHA-256 `79ac313be79e36ff7f300b4e414e60411fc31f4c20abd3d933e80e13c16ef411`.
- Retained 31 completed envelopes (30 runs plus summary), 60 score NPZ files, and 30 calibration freezes. A second full invocation successfully resumed all runs, validating score checksums, frozen identities, recomputed metrics and summary equality.

## Results

Values below are means across ten seeds. AP is noninterpolated average precision. FPR is the fraction of **normal** samples flagged novel.

| Method | AP | AUROC | F1 | Known-sample FPR |
|---|---:|---:|---:|---:|
| Vigil frozen A_KC/KDE | 0.994106 | 0.978686 | 0.968997 | 0.121488 |
| Isolation Forest | 0.993538 | 0.980369 | 0.962041 | 0.177403 |
| Constant score, calibration-selected all-novel prediction | 0.775831 | 0.500000 | 0.873767 | 1.000000 |

Vigil precision/recall means are 0.965175 / 0.972849. Its F1 mean has a 95% seed-bootstrap interval of [0.967830, 0.970169]; its FPR interval is [0.117355, 0.125798]. Isolation Forest F1 interval is [0.961310, 0.962775].

Paired Vigil-minus-Isolation-Forest differences:

- F1: +0.006956, 95% interval [0.005424, 0.008396].
- FPR: -0.055915, interval [-0.079542, -0.033198].
- AP: +0.000568, interval [-0.000089, 0.001263].
- AUROC: -0.001683, interval [-0.003937, 0.000467].

These intervals describe model-seed variability conditional on one fixed split. They do not include uncertainty across datasets, data splits or deployment traffic. The ranking-metric difference intervals include zero: this pilot does not establish a clear ranking advantage for Vigil. At the calibration-selected operating points, Vigil has modestly higher F1 and lower FPR in this specific experiment.

## Interpretation and next gates

The constant baseline obtains 87.38% F1 simply by calling everything novel. Consequently, a large F1 number alone is misleading in this attack-heavy development population. Vigil's 12.15% normal-sample false-positive rate is still a substantial limitation, despite its improvement over this Isolation Forest configuration.

Do not replace the manuscript's old recall with these numbers: the unit, split, class protocol and threshold procedure differ. Do not describe these as a production intrusion detector result or generalization to unseen attack families.

Next: assess the already-frozen thresholds at declared lower prevalences and report false-positive burden; inspect per-class failure patterns without discarding rare classes; examine validation-only low-FPR operating points in a separately versioned exploratory study. CICIDS2017 remains a separate protocol and benchmark. Feature-attribution validation, systems measurements and final official-test evaluation remain required for the paper.

The implementation checkpoint passed 132 tests, scoped Ruff/Black checks and compilation, with independent specification and standards reviews. Repository-wide Ruff still had 214 findings outside the changed files. No source code changed during this real pilot.
