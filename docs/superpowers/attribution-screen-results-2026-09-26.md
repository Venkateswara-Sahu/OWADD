# Independent-window attribution screen: results

## Status and provenance

Completed the declared numerical development screen, not the full study. No Vigil model or attribution behavior changed. No official network-data test set was used.

- Code checkpoint: `c22d4fca3bbb5a5d327527b525115f19f46d1930`, clean working tree at execution.
- Source hash: `40a8858e8104516decc521dae0641e09e2658bf882aeb37b7e98775f38095fef`.
- Summary: `artifacts/raw_results/attribution-screen-v1/summary/c855e2d39a9a15f8/1278f5ebc8a8f93d/result.json`.
- Summary SHA256: `2f97c5f15e5a28c356d413d87262a59550772fd9265a14a66aeb365f6a035db9`.
- Ten seeds, six cases, seven methods: 420 score vectors, 42 aggregated groups. A second identical CLI invocation successfully loaded completion-checked results and reproduced the summary.
- Summary metadata: `protocol_complete=true`, `not_full_study=true`. Reduced smoke configurations explicitly carry `protocol_complete=false`.
- Software checks: 141 tests passed in49.03 seconds after the reporting fix; scoped Ruff and Black checks passed. No claim of repository-wide lint cleanliness.
- Independent standards review found no actionable issues. Spec review found smoke/protocol ambiguity; explicit summary tagging and a red-to-green regression assertion resolved it. Review used the staged precommit diff against pinned `92d1b3c090a08d22c932e786dc3351c0c165b7cc`.

## Results

Mean Recall@3: fraction of the two changed features recovered among the top three. Percentages below are localization metrics, not attack detection recall.

| Case | Vigil | Random | Mean difference | Standardized mean | KS | Wasserstein | Logistic permutation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mean +0.5 | 45% | 10% | 100% | 100% | 100% | 100% | 90% |
| Mean +2 | 100% | 10% | 100% | 100% | 100% | 100% | 100% |
| Standard deviation x0.5 | 0% | 10% | 15% | 30% | 100% | 100% | 20% |
| Standard deviation x2 | 100% | 10% | 25% | 10% | 100% | 100% | 10% |
| Correlation 0.8 | 5% | 10% | 10% | 10% | 10% | 5% | 10% |

Vigil's bootstrap95% intervals for these means are respectively [30%,60%], [100%,100%], [0%,0%], [100%,100%], and [0%,15%]. Degenerate intervals describe these ten simulations only, not guaranteed population performance. Full per-method intervals and other metrics are in the summary. Stable-null localization recall is undefined, not a success or false-alarm estimate. The observed random mean is10%; the theoretical expected Recall@3 for uniform random ranking is15%.

## Interpretation and next gate

This screen does not support broad superiority of current Vigil attribution. Simple marginal-distribution baselines are stronger for small mean shifts and variance decreases. Correlation localization is weak across this baseline set; the linear logistic comparator is not a strong dependency-sensitive reference.

The public attribution rule clips negative reconstruction-error changes to zero. This is a plausible structural explanation for variance-decrease failure, not a causal conclusion proved by the screen. Preserving signed direction and evaluating a two-sided standardized change score is a justified next development ablation. It must remain a separately named candidate alongside the frozen original; it is not yet an implemented or validated improvement.

Before any superiority claim: declare that ablation and stronger dependency-sensitive baselines, use new simulation seeds for subsequent evaluation, report paired uncertainty and compute cost, and extend beyond these easy Gaussian windows. The current seeds are development evidence once inspected. Categorical shifts, noise, higher dimension, realistic stream behavior, event detection, network-data validation and systems measurements remain pending. Publication readiness and novelty are not established by this screen.
