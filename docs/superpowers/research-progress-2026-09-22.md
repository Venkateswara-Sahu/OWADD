# Validation workflow checkpoint — 22 September 2026

## Implemented

The NSL-KDD CLI now supports separate `--mode smoke`, `--mode tune`, and `--mode test` paths. Training/reference preprocessing and validation use only `KDDTrain+.txt`. Smoke and tuning hash `KDDTest+.txt` for identity but do not parse its rows or train/select parameters from them.

Tuning retains every candidate result and freezes the highest validation event F1, with ties resolved by fewer false alarms and then higher threshold. The manifest contains complete validation evidence, configuration, provenance, dataset checksums, and an integrity digest. It cannot be silently overwritten. Test mode requires it before loading data, checks both source checksums, and rejects changes to the requested protocol other than replacing the candidate threshold with the frozen selection.

The network runner uses frozen autoencoder weights (`update_epochs=0`), while retaining the detector's stable-chunk error-buffer updates. This is a frozen-model baseline, not a demonstrated safe online-learning system. Attack labels define evaluation events and validation selection; they are not fed to the detector. No feature-localization ground truth is asserted for these network transitions.

Known events with no alerts now receive event F1 = 0, rather than an undefined value, using `2 * matched / (true_events + total_alerts)`. Precision can remain undefined when no alerts exist. Stable-only average run length is explicitly unreported because the current event helper does not provide the needed exposure accounting.

## Local pilot evidence, not final test results

The two-epoch smoke run evaluated 600 distinct validation rows and missed all four events. It is retained at `artifacts/raw_results/nsl_smoke/684206f5a20ab37e/51a54d766ae61c15/result.json`.

The validation pilot used seed 42, 2,000 normal reference rows, 20 training epochs, 200-row chunks, five-chunk intervals, two-chunk event tolerance, and two named attack classes (`neptune`, `satan`). It evaluated four transitions across 5,000 distinct validation rows. All five trial audits report `test_loaded: false`.

| Threshold | Matched events / 4 | False alarms | Duplicate alerts | Event F1 |
| --- | ---: | ---: | ---: | ---: |
| 0.05 | 4 | 1 | 0 | 8/9 |
| 0.10 | 0 | 5 | 0 | 0 |
| 0.20 | 2 | 2 | 0 | 0.5 |
| 0.30 | 4 | 0 | 0 | 1 |
| 0.50 | 4 | 0 | 0 | 1 |

The declared tie-break selected 0.50. This is a single-seed development pilot, not evidence of generalization or a monotonic threshold/recall tradeoff. The detector updates its error buffer conditionally, so different thresholds can change the later detector state; the nonmonotonic pattern needs multi-seed investigation rather than selecting a flattering operating point.

The complete pilot manifest is `artifacts/raw_results/nsl_validation_pilot/frozen.json`; raw trials are in its `trials/` sibling. These artifacts record the dirty source identity at execution and remain ignored by Git. This pilot freeze is deliberately not the official publication manifest. Final-test performance has not been measured here. A generated-data integration test exercises tune/freeze/test and rejects later checksum changes without spending the real held-out test set.

## Commands

From the research worktree, substitute the original checkout's raw-file paths:

```powershell
python -m experiments.cli run --config experiments/configs/nsl_kdd.yaml --mode smoke --train '<path>/KDDTrain+.txt' --test '<path>/KDDTest+.txt' --output artifacts/raw_results/nsl_smoke
python -m experiments.cli run --config experiments/configs/nsl_kdd.yaml --mode tune --train '<path>/KDDTrain+.txt' --test '<path>/KDDTest+.txt' --frozen '<new-pilot-manifest>.json' --output artifacts/raw_results/nsl_validation_pilot/trials
```

Do not overwrite the saved pilot or call this a final study. Before publication testing, freeze a reviewed, committed protocol and validate baseline comparability, event exposure metrics, multiple seeds, and the second dataset. The current threshold-selection helper supports one paired seed/protocol, not selection across a multi-seed study.

## Next dependencies

The original project's `data/raw` directory contains NSL-KDD only. CICIDS2017 needs a supplied data directory with the timestamp-bearing flow files before a real chronological audit can run. No chronological claims or second-dataset results have been made. The remaining controlled-study, novelty, latency, paper-generation, and final-review gates in the approved plan still apply.
