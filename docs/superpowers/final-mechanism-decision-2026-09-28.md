# Final mechanism investigation and research decision

## Decision

Stop pursuing the current Vigil attribution implementation as a generally superior new method. The declared continuation heuristic was not met. Preserve Vigil as an engineering project and preserve these experiments as reproducible evidence of limitations. Do not automatically replace the default, add further methods, or submit an arXiv paper claiming superiority.

Training is not useless, nor is trained attribution merely identical to squared input change. It adds useful localization information in some dependent-data settings, but can also hurt localization. Those conditional gains are insufficient to justify the original broad research claim, especially because simple KS/correlation baselines remain stronger on the tested families. A focused empirical paper remains a possibility, not an established contribution or publication-ready artifact; novelty relative to prior work is unresolved.

## Verification and provenance

- Frozen pre-result protocol: `final-mechanism-protocol.md`.
- Clean execution checkpoint: `4c23d7854258cbe239150f9c652182f7935e3fe7`.
- Source SHA256: `5fc1e5cac31a27399841e7d1cc319e0d9e02484bd4cec2f56bcfb2027b11eb26`.
- Prepared CICIDS manifest SHA256: `50f1f31fe0468fdca76a08e2ea3b660588e631962431afb466c18d73e389e95b`. The runner additionally checked Monday/Tuesday array and metadata hashes against that manifest. No held-out day files were opened by this experiment.
- Summary: `artifacts/raw_results/final-mechanism-v1/summary/75f88d2df816a2b0/6f5252fecd8b15a0/result.json`.
- Summary SHA256: `9c0d83a5b8cca47227a46f6f213d6241126f6f8136a977d19acba8198f8e09a7`.
- Verified20 seeds50-69,4320 score vectors,216 case/method groups and96 paired comparisons. Metadata confirms protocol_complete=true and not_full_study=true. The same CLI successfully completion-checked all saved seeds and reproduced the aggregate before this report was written.
- Twenty real evaluation blocks contain32000 distinct row IDs, with2000 separate training IDs. Selection excludes the Monday[0:2000]/Tuesday[0:600] previously used in the recorded preparation smoke. Prior integrity/preprocessing inspection is not claimed to be absent: these were unused for recorded model evaluation, not pristine unseen raw data.
-156 tests passed in93.86 seconds after review repair. Scoped Ruff, Black, compile and whitespace checks passed. Repository-wide Ruff remains214 pre-existing findings; no global lint-clean claim.
- Independent standards review found no actionable issue. Specification review required all real/no-injection localization metrics to be undefined, since natural drift is unknown; a failing regression assertion was added, the fix passed, and the reviewer confirmed resolution. Review used the staged precommit diff against `84f51b85d90b4c8f9d3608f750c4f7226f993264`.
- No public `vigil/` changes, no official held-out network test inference, and no hyperparameter tuning from this run.

## Does training add information?

The trained and untrained networks start from identical cloned weights. Real-data training reconstruction loss decreased in all20 seeds: mean initial1.04596 to mean trained0.24485. Thus optimization occurred, but lower reconstruction loss alone is not evidence of better feature localization.

The principal matched comparison uses absolute reconstruction-error changes versus untrained absolute changes and absolute squared-input changes. Mean Recall@3 percentages are shown below. This measures recovery of the two injected feature indices, not attack detection or causal explanation.

| Condition | Trained absolute | Untrained absolute | Squared-input change | Relevant simple baseline |
| --- | ---: | ---: | ---: | --- |
| Synthetic small mean +0.5 | 32.5 | 57.5 | 62.5 | KS100 |
| Synthetic large mean +2 | 100 | 100 | 100 | KS100 |
| Synthetic SDx0.5 | 92.5 | 100 | 100 | KS100 |
| Synthetic SDx2 | 100 | 100 | 100 | KS100 |
| Synthetic correlation0.8, independent background | 20 | 7.5 | 7.5 | Correlation100 |
| Synthetic correlated background0.3, strong+0.6,800 rows | 97.5 | 10 | 12.5 | Correlation100 |
| Real-data mean+0.5 | 20 | 12.5 | 12.5 | KS100 |
| Real-data mean+2 | 50 | 35 | 35 | KS100 |
| Real-data SDx0.5 | 15 | 10 | 10 | KS100 |
| Real-data SDx2 | 25 | 27.5 | 27.5 | KS100 |
| Real-data column permutation | 27.5 | 10 | 10 | Correlation65 |

These are representative, explicitly named cells, not a pooled headline. All18 synthetic and6 real-data conditions and all nine methods remain in the summary. In particular, every dependency-grid condition is retained, including weak changes and independent backgrounds where training gains were uncertain.

Selected paired Recall@3 differences, percentage points with exploratory95% seed-bootstrap intervals:

- Synthetic small mean: trained-minus-untrained -25 [-45,-5]; trained-minus-input -30 [-47.5,-12.5]. Training materially worsened this test.
- Synthetic correlated background0.3,strong+0.6,800 rows: trained-minus-untrained +87.5 [77.5,95]; trained-minus-input +85 [72.5,95]. Training added useful information here, although correlation ranking still scored100%.
- Real-data large mean: +15 [5,27.5] against either matched control.
- Real-data permutation: +17.5 [5,32.5] against either matched control.
- Real-data small mean: +7.5 [-7.5,22.5]; SDx0.5:+5 [-7.5,17.5]; SDx2:-2.5 [-10,5], against either control. These intervals do not establish improvement.

Real-data trained positive-only Recall@3 for mean+0.5/mean+2/SDx0.5/SDx2/permutation was35/55/20/32.5/40%; trained reference-standardized scores were25/47.5/20/37.5/42.5%. Thus the absolute rule is not universally the strongest reconstruction variant; even these other variants remain below the relevant simple baseline in these cells. Corresponding trained-versus-untrained paired summaries are saved, rather than being replaced by the absolute-only narrative.

Trained-absolute versus squared-input feature-score Spearman agreement was moderate, not near identity: mean agreement across real-data seed blocks was about0.42-0.47 depending on case, and0.31-0.48 in the independent synthetic cases. This is descriptive evidence that learned reconstruction changes rankings, not proof that those changes are useful or causal.

## Applying the agreed stop rule

The heuristic required positive paired absolute-rule intervals against both untrained and input controls in at least two shift families on both sources. Real-data mean/permutation conditions provide two families with selected gains, but synthetic gains meeting both comparisons are confined to dependency changes in an already correlated background. Synthetic mean/variance cases do not meet the criterion and include a clear small-mean regression. The conjunction therefore fails.

Decision: close this superiority-method investigation. Do not reinterpret the mixed results as proof that autoencoders never help, or claim that the project has no engineering value. The defensible conclusion is narrower: this fixed architecture, training budget and attribution family do not demonstrate consistent added localization value over appropriate simple baselines in these tests.

## Limits on interpretation

- Controlled injections into real flow features are semi-synthetic, potentially off-manifold and not necessarily physically valid traffic records. Permuting a column can change relationships with multiple unmodified columns. Injected-column truth is not uniquely identified causal ground truth.
- Tuesday windows were shuffled within disjoint chronological blocks; this is not a live, chronological deployment evaluation. The common Monday training pool and fixed feature subset make real-data bootstrap intervals conditional on that selection.
- The prepared cache already used Monday-only min-max scaling and conservative feature-vector deduplication. This experiment added centering/sample-SD scaling fitted only on the reserved Monday training rows. No Tuesday fitting, imputation or clipping occurred.
- Zero missing/nonfinite values were allowed. Correlation metrics would be marked unsupported for constant-column windows; all changed real-data correlation groups in this run have20 defined seeds. Real/no-injection metrics are all undefined, never false-alarm or success estimates.
- The samples are small, intervals are exploratory and unadjusted, and the study followed inspected development experiments. No broad statistical or novelty guarantee follows. Different training budgets, architectures, data or shift types might behave differently; those are outside this final bounded investigation.

## Practical handoff

Keep the source, protocol and raw results. Describe Vigil on the CV as an implemented drift-monitoring/research evaluation project with reproducible baseline comparisons, not a proven novel or superior algorithm. Do not list an unpublished paper as an accepted publication or achievement. The next decision is about packaging existing engineering work or selecting a different research question, not another automatic experiment on these same inspected cases.
