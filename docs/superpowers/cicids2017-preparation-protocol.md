# CICIDS2017 corrected-variant preparation protocol

This is preparation for a research benchmark, not evidence of detector quality or paper readiness.

## Fixed choices

- Source: the separately acquired CNS2022 corrected archive, never mixed with original CICIDS2017 CSVs.
- Monday is reference/training, Tuesday validation, Wednesday-Friday held-out test days. Test data is inspected for source integrity and prepared, not used to select model parameters.
- Ordering is retrospective flow-start time, then original row position for ties. Source dates must match July 3-7, 2017. The CSV clock has no timezone suffix; no timezone-dependent detection-delay claims are made. Start-time ordering must not be presented as operational availability of completed-flow features.
- Attempted attacks map to BENIGN for primary evaluation, following the correction authors' suggested fallback. Original labels and categories remain in metadata for a separately declared sensitivity analysis. Unknown non-attempted labels are preserved, not merged.
- Drop `id`, `Flow ID`, `Src IP`, `Dst IP`, `Src Port`, `Timestamp`, `Label`, and `Attempted Category` from predictors. The ephemeral source port is removed as an identifier-like field. Destination port and protocol remain numeric source features in this preparation version; this representation should be disclosed, not described as categorical one-hot encoding.
- Reject malformed dates, schema changes, missing labels, contradictory attempted metadata, non-benign Monday records, and empty cleaned partitions. Exclude nonfinite numeric rows; no imputation.
- Duplicate identity is the SHA-256 of the canonical float64 predictor vector, excluding identifiers, timestamp and labels. Normalize signed zero. This deliberately removes identical vectors even when their source IDs or labels differ. Keep the earliest day, then earliest time, then source position. Never remove earlier training observations because a future day repeats them. Record observed label conflicts.
- This is more conservative than raw-row deduplication and can remove legitimate repeated flows. Thus prevalence is natural only within the retained, deduplicated population, not identical to the source population. Report removal rates and label counts alongside any evaluation; no randomized balancing.
- Fit incremental min-max scaling only on retained Monday data. Do not clip later values into the training range. Feature values above one are valid evidence of out-of-training-range observations, not grounds to refit.

## Resource and integrity safeguards

Read 25,000 rows at a time, use disk-backed SQLite identities and sorting, and write one memory-mapped float32 day partition at a time. No whole-dataset concatenation. Metadata retains row identity, timestamp, mapped label, original label, and attempted category.

Output directories must be new. Interrupted/failed runs have no completed manifest and must not be consumed. The manifest records source SHA-256, source/environment provenance, split rules, scaler parameters, counts, and checksums of every transformed array and metadata file. Readers check those hashes before yielding bounded chunks. Source bytes are hashed again after ingestion. Raw source archives are never modified.

```powershell
python -m experiments.cli prepare --config experiments/configs/cicids2017.yaml --archive '<original checkout>/data/raw/cicids2017-improved/CICIDS2017_improved.zip' --output artifacts/datasets/cicids2017-improved/prepared-v1
```

The manifest's `complete` means preparation completed, not that benchmark design, label correctness, or scientific validity is proven. No CICIDS2017 model training, threshold selection, final-test evaluation, or event-ground-truth definition is performed by this command.

## Verified preparation checkpoint, 22 September 2026

The real run completed with 83 predictor columns and the following retained population:

| Day | Raw rows | Nonfinite removed | Duplicate vectors removed | Retained |
| --- | ---: | ---: | ---: | ---: |
| Monday | 371,624 | 3 | 20,689 | 350,932 |
| Tuesday | 322,078 | 0 | 24,850 | 297,228 |
| Wednesday | 496,641 | 1 | 36,520 | 460,120 |
| Thursday | 362,076 | 1 | 65,118 | 296,957 |
| Friday | 547,557 | 0 | 115,825 | 431,732 |

Total: 1,836,969 retained from 2,099,976 source rows. Five nonfinite rows and 263,002 feature-vector duplicates were removed (12.5243% total exclusions). Friday had 7,370 duplicate encounters whose original label differed from the previously retained representative. This is an encounter count, not a count of unique contradictory groups.

Removal is not class-neutral: Friday Portscan drops from 159,066 source rows to 86,245 retained rows; Thursday Infiltration - Portscan drops from 71,767 to 41,179. The primary deduplicated protocol was fixed before this run, but final research claims require a separately declared sensitivity analysis of duplicate policy. Do not describe this as unchanged real-traffic prevalence.

Independent cache validation verified all ten artifact checksums, all transformed values finite, monotonic per-day timestamps, metadata identities matching the disk-backed canonical records, and global identity uniqueness. Retained class counts are preserved in `artifacts/manifests/cicids2017_improved_population.json`; preparation provenance and parameters are in `artifacts/manifests/cicids2017_improved_prepared.json`. Large caches and raw archives remain ignored by Git.

Full automated suite: 105 passed. A separate integration smoke run fitted two epochs on the first 2,000 retained Monday rows and processed the first 600 Tuesday rows in three chunks; outputs were finite. Seed 42, two Torch threads, frozen model weights, threshold 0.3 (not selected), and source identity are saved in `artifacts/raw_results/cicids2017_preparation_smoke.json`. This verifies software integration only: no performance claim, no threshold tuning and no held-out test inference. Wednesday-Friday data was prepared and integrity-audited, not model-evaluated.

Outstanding research gates: duplicate-policy sensitivity, attempted-label sensitivity, independently supported event definitions, validation-only selection across seeds and fair baselines, and a reviewed publication freeze before held-out evaluation. Task 8 data preparation is not completion of those research gates.
