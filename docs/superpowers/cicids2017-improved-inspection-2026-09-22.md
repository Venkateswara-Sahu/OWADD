# Corrected CICIDS2017 candidate inspection

## Acquisition

Downloaded 22 September 2026 following user approval to inspect the corrected variant. This remains separate from the original CICIDS2017 export; no model training or protocol substitution has occurred.

- Primary source: [CNS 2022 authors' dataset directory](https://intrusion-detection.distrinet-research.be/CNS2022/Datasets/).
- Download: https://intrusion-detection.distrinet-research.be/CNS2022/Datasets/CICIDS2017_improved.zip
- Local archive in original OWADD checkout: `data/raw/cicids2017-improved/CICIDS2017_improved.zip`.
- Archive bytes: 343,549,013.
- Computed SHA-256: `97fdb91d339e2d8cf5627f981b831e5e7e400b981c58181c451a38fd03c48883`.
- No separately published checksum was obtained. This computed digest pins our downloaded bytes, not an independently verified release.
- Five CSV members, one per weekday. Inspected directly inside ZIP; no archive-supplied scripts executed and no files extracted.

## Reproduction and boundaries

Run from the research worktree:

```powershell
python scripts/inspect_cicids2017_improved.py --archive '<original checkout>/data/raw/cicids2017-improved/CICIDS2017_improved.zip' --output artifacts/datasets/cicids2017-improved/source-profile.json
```

The profile reads every row in 25,000-row chunks, checks matching schemas, ISO-shaped timestamps, parse failures, backward steps, label/category consistency, and numeric finiteness. ZIP members are read to EOF, checking their CRC. It excludes identifiers, addresses, timestamp, label, and Attempted Category from numeric-feature profiling. It does not check duplicates, cross-split leakage, semantic label correctness, or establish timestamp timezone from the CSV alone. The output is inspection evidence, not benchmark approval.

A synthetic three-row ZIP verified that the profiler detects one backward step, one malformed timestamp, and one nonfinite row, while accepting consistent attempted-attack metadata.

## Completed full-source profile

All five members were read successfully: 2,099,976 rows and 91 matching columns. Every timestamp passed the ISO-shape and parsing checks, and every file's timestamps fall on its named July 2017 weekday. There were zero missing labels, invalid attempted categories, or disagreements between attempted-label wording and category metadata. This resolves the observed missing-AM/PM obstacle for this candidate, not all data-quality concerns.

| Day | Rows | Backward steps in raw order | Nonfinite numeric rows |
| --- | ---: | ---: | ---: |
| Monday | 371,624 | 174,479 | 3 |
| Tuesday | 322,078 | 152,339 | 0 |
| Wednesday | 496,641 | 196,756 | 1 |
| Thursday | 362,076 | 165,271 | 1 |
| Friday | 547,557 | 248,931 | 0 |

Monday contains only BENIGN labels. There are 11,979 attempted-attack rows across the other days. None have been remapped. Five nonfinite rows remain (about 0.00024% of all rows); their exact feature-level causes and removal policy require the preparation audit.

Recommendation: this variant is a more viable chronological-study candidate than the original export. Build a variant-specific adapter rather than passing it to the original adapter: identifier names, schema, label metadata, and timestamp format differ. Stable chronological sorting with an explicit tie-break, duplicate checks excluding row IDs, label-policy freezing, and training-only preprocessing remain required. A flow's start time also precedes availability of its completed-flow features; decide whether the replay is retrospective start-time ordering or an operational completion-time stream before claiming real-time performance.

## Label policy before any modelling

The authors' [download guidance](https://intrusion-detection.distrinet-research.be/CNS2022/Dataset_Download.html) advises against treating attempted attacks as a separate model class and suggests benign relabelling when uncertain. This is methodological guidance, not an instruction silently applied to our data. Preserve original labels and categories for traceability; decide and record the evaluation mapping before tuning. `Attempted Category` is label-derived and must never enter predictors.

The [authors' CICIDS2017 documentation](https://intrusion-detection.distrinet-research.be/CNS2022/CICIDS2017.html) specifies UTC attack intervals. The raw CSV timestamps lack an explicit timezone suffix, so their timezone interpretation still needs confirmation against generation code or aligned source events.
