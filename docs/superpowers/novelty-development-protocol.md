# NSL-KDD novelty development pilot

Declared before model results. This is development evidence, not a publication freeze.

- Read only `KDDTrain+.txt`; never open or hash the official test file in this workflow.
- Known class: `normal`. Novel classes: all 22 attack labels observed in that training file: `back`, `buffer_overflow`, `ftp_write`, `guess_passwd`, `imap`, `ipsweep`, `land`, `loadmodule`, `multihop`, `neptune`, `nmap`, `perl`, `phf`, `pod`, `portsweep`, `rootkit`, `satan`, `smurf`, `spy`, `teardrop`, `warezclient`, `warezmaster`.
- Reuse feature-vector deduplication and seed-42 normal-only reference preparation. Missing/nonfinite features fail closed; source label/difficulty never enter features. Hash the fitted preprocessor state.
- Fix a 2,000-row normal reference subset with seed 42, shared by every method and model seed. Preprocessing uses the larger normal reference pool, never calibration/development rows; report both sizes.
- Split the existing validation pool by original class into calibration and development-report halves with seed 42, without replacement. An odd extra observation goes to development. Classes with one remaining row occur only in development. NSL-KDD is non-temporal; this is not chronological replay.
- Threshold selection uses only calibration scores: 51 score quantiles plus a candidate above the maximum; maximize sample F1, tie-break lower FPR then higher threshold. Score the development-report pool only after saving the calibration freeze.
- The generic novelty protocol calls these roles `validation` and `test`; here they mean calibration and development-report, both drawn from the official training file. Every result envelope is explicitly `split=validation`, `evaluation_scope=development_holdout`. This is not evaluation of the official test partition or unseen-during-calibration attack classes.
- Methods: Vigil frozen A_KC/KDE negative log-density (20 training epochs, hidden width 10), Isolation Forest negative score (100 trees, max_samples=min(256, reference size)), and constant zero scores. The constant method can choose all-novel or none-novel on calibration and exposes the effect of class prevalence.
- Model seeds: 0 through 9. Identical fixed row pools across methods/seeds. CPU only, one Torch thread and one Isolation Forest worker. Preserve RNG/thread settings after each fit. No hyperparameter search in this pilot.
- Retain every seed, raw calibration/development scores, threshold candidates, class counts, source/preprocessing/model hashes and software provenance. Resume only integrity-checked completed results. Interrupted unpublished evidence is preserved but not counted.
- Report sample average precision, AUROC, precision, recall, F1 and known-class FPR. Report means and 95% bootstrap intervals across model seeds; these quantify optimization/randomization variability conditional on one fixed data split, not dataset/generalization uncertainty. Paired method differences use matching seeds.

No manuscript/CV performance claim follows from this pilot alone. CICIDS2017 novelty protocol, class-disjoint calibration sensitivity, prevalence sensitivity, multi-split uncertainty, attribution studies and final official-test evaluation remain separate work.

Run from the research checkout with `python -m experiments.novelty_development --train "<absolute-path-to-KDDTrain+.txt>" --output artifacts/raw_results/novelty-development-v1`. The CLI uses the fixed defaults above. It writes checksummed per-seed result envelopes and raw score sidecars, then a completed summary envelope containing row IDs, source audit, class counts and seed-conditional uncertainty. No test-file argument exists.
