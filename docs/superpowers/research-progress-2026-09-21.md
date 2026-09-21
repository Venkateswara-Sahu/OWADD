# Research checkpoint: 21 September 2026

This is implementation and data-audit evidence, not a performance result or an arXiv-readiness claim.

## Verified changes

- Completed results reject sequential overwrites; their completion markers bind the saved bytes with SHA-256. This is accidental-change detection, not an adversarial signature or a concurrent-writer guarantee.
- Resume identities include the source-tree content, dependency versions, and environment, excluding the capture timestamp. Modified and untracked, non-ignored files contribute to source identity.
- Aggregation ignores unfinished records, rejects checksum mismatches, requires complete method/seed coverage per dataset/shift-family/magnitude, rejects duplicate pairs, and computes paired effects separately per scenario.
- The synthetic runner emits the primary metric expected by aggregation, identifies output as smoke-only, and rejects unsupported methods instead of labeling Vigil output as another method.
- The NSL-KDD adapter deduplicates feature vectors, removes train/test overlap, fits preprocessing only on the normal reference pool, and constructs streams without record reuse.

## Local NSL-KDD audit

One row represents a supplied connection record. Identity is the 41-feature vector, excluding label and difficulty. Consequently these counts describe duplicate feature vectors, not necessarily duplicate underlying network events.

| Check | Observed |
| --- | ---: |
| Within-training feature duplicates removed | 16 |
| Within-test feature duplicates removed | 57 |
| Remaining test vectors also present in training, removed | 654 |
| Normal-only reference rows | 50,400 |
| Validation rows | 75,557 |
| Retained test rows | 21,833 |
| Encoded feature dimensions | 77 |

The audit uses seed 42 and a 0.25 hash allocation for normal validation rows. All training-file attacks go to validation; the reference is normal-only. These pools are not representative class-balanced random partitions. Test data is inspected for schema and duplicate auditing, not used to fit transformations or select parameters. Numerical test values outside the reference range remain outside [0, 1].

The overlap is a high-confidence leakage risk for a naive train/test evaluation. Filtering it changes the evaluated population, so future paper comparisons must disclose this protocol rather than imply direct comparability with published unfiltered scores. No temporal ordering is claimed for the constructed NSL-KDD streams.

Source files: `data/raw/KDDTrain+.txt` and `data/raw/KDDTest+.txt` in the original checkout. SHA-256:

- Train: `1b86d2f957b33082081bba410fe129b475efebcc13c9014c3f447c8271aadf95`
- Test: `fa46b0935342616aa83b7c2578db355b6a7aaabbc492248172c7a1e8b7ab8f84`

Inspectable audit implementation: `experiments/datasets/audit.py`, with transformation and duplicate rules in `experiments/datasets/nsl_kdd.py`. The saved full audit is under `artifacts/raw_results/dataset_audits/524d1a94a7ec34be/160c71b0cb07cb0d/result.json`; it records the dirty source identity at execution, before subsequent formatting and this checkpoint. Raw audit artifacts remain local and ignored by Git.

Reproduce from the research worktree:

```powershell
python -m experiments.datasets.audit --train '<original-checkout>/data/raw/KDDTrain+.txt' --test '<original-checkout>/data/raw/KDDTest+.txt' --output artifacts/raw_results/dataset_audits
```

## Remaining gates

Task 7 is **in progress**, not complete: validation-only tuning, the frozen configuration gate, and the NSL-KDD benchmark CLI path remain to be implemented. Earlier task completion entries certify their historical tests, not that all scientific correctness issues have been exhausted.

Before primary runs, also finish general study-grid dispatch and pairing, eliminate reference-row reuse from the synthetic evaluation stream, audit event false-alarm denominators and baseline signal comparability, and tighten controlled correlation/categorical-shift semantics. Single-seed smoke uncertainty is not publication evidence. Concurrent writes to the same result identity are not supported.

The remaining research plan includes CICIDS2017 audit/chronology, sample-level novelty, systems measurements, >=10-seed controlled comparisons, generated figures/tables, manuscript revision, and final independent review. No new performance, novelty, or superiority claim is warranted yet.
