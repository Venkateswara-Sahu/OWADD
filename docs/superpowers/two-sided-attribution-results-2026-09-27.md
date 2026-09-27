# Two-sided attribution ablation: results

## Outcome

Two-sided reconstruction-error scoring substantially improves variance-decrease localization in these Gaussian simulations, but worsens small-mean-shift localization. Reference standardization does not provide a consistent improvement over the simpler absolute change. Neither candidate should replace the existing default on this evidence. Public Vigil code is unchanged; both candidates remain experimental.

## Verified execution

- Frozen protocol: `two-sided-attribution-protocol.md`, declared before the real run.
- Code checkpoint: `ab9e27d2fa4fd1874fc860b3767a461c5a0a4c5f`, clean working tree during execution.
- Source hash: `20cf3323ad3713418349cd36f6458ff0f6b71128ff2f7ad80f0d35c5d5f7f9e1`.
- Summary: `artifacts/raw_results/two-sided-attribution-v1/summary/e8216e1e162ab1b1/22ab1e90e00a5303/result.json`.
- Summary SHA256: `470320a8c3d4052b520b38fb1c745ff4c74d3a0b4f7e9a1acc56e2a1a207fb6f`.
- Seeds10-29,20 epochs, nine methods and six cases:20 seed results,1080 score vectors,54 groups,90 paired comparisons, plus one summary. Metadata confirms protocol_complete=true and not_full_study=true.
- A second identical CLI invocation completion-checked the saved results and reproduced the summary. Source/document edits occurred only afterward.
- 148 tests passed in68.85 seconds. Scoped Ruff, Black, compile checks and staged diff whitespace check passed. Repository-wide Ruff still reports214 pre-existing findings; no repository-wide lint-clean claim. No configured typechecker was found.
- Independent standards and specification reviews reported no actionable findings. They inspected the staged precommit diff against pinned `8debac5fe7be9b901ccc8f500b5415f2449904c0`, an explicit adaptation of branch-diff review for the managed detached worktree.
- No public `vigil/` changes and no official NSL-KDD/CICIDS test evaluation.

## Localization results

Mean Recall@3, in percent: proportion of the two shifted features recovered among the top three. This is not attack-detection recall. All comparisons below use matching seeds10-29; do not compare a candidate on these seeds with the prior screen's seeds0-9 as a paired effect.

| Case | Original positive-only | Absolute | Reference-standardized absolute | KS | Wasserstein |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mean +0.5 | 47.5 | 40.0 | 37.5 | 100 | 100 |
| Mean +2 | 97.5 | 97.5 | 100 | 100 | 100 |
| Standard deviation x0.5 | 0 | 97.5 | 97.5 | 100 | 100 |
| Standard deviation x2 | 100 | 100 | 100 | 100 | 100 |
| Correlation0.8 | 20.0 | 35.0 | 30.0 | 15.0 | 12.5 |

Random ranking has12.5% observed Recall@3 in each shifted case (theoretical expectation15%); the same random ranking is reused within each seed. Stable-null recall remains undefined. Every method, metric and interval, including mean-difference and logistic/permutation baselines, is retained in the summary rather than discarded from analysis.

Selected paired candidate-minus-original Recall@3 differences, in percentage points, with deterministic95% percentile bootstrap intervals:

| Case | Absolute difference [interval] | Standardized difference [interval] |
| --- | ---: | ---: |
| Mean +0.5 | -7.5 [-15,0] | -10 [-20,-2.5] |
| Mean +2 | 0 [0,0] | +2.5 [0,7.5] |
| Standard deviation x0.5 | +97.5 [92.5,100] | +97.5 [92.5,100] |
| Standard deviation x2 | 0 [0,0] | 0 [0,0] |
| Correlation0.8 | +15 [0,32.5] | +10 [-2.5,27.5] |

For correlation, absolute-minus-KS is+20 points [0,42.5], and standardized-minus-KS is+15 [-5,37.5]. These include zero and do not establish a dependency-localization advantage. Standardized-minus-absolute is-5 points [-12.5,0] for correlation and-2.5 [-12.5,7.5] for small mean shifts. No consistent standardization gain is established.

Intervals are exploratory, unadjusted for the many comparisons, based on only20 synthetic seeds. Degenerate intervals do not establish perfect population performance. All raw signed changes and reference scales are saved to permit audit of the ranking rule.

## Implications and next research gate

The controlled ablation supports retaining negative error changes as potentially useful localization evidence; discarding them was a consequential limitation of the original rule for variance decreases. It does not make absolute change universally better: unshifted features with large negative fluctuations can compete with weak positive shifts. The observed small-mean regression is consistent with that tradeoff, not a separately demonstrated mechanism.

Keep the original and both candidate variants explicitly named, with the simple absolute variant as a candidate for further evaluation rather than a promoted default. KS/Wasserstein remain stronger on small mean shifts and at least as good on the tested marginal variance shifts. No novelty or overall superiority claim is warranted.

Before broadening the paper's claims, the next useful test is a separately declared dependency-focused experiment with a direct correlation-change baseline and a stronger nonlinear comparator. Fresh seeds alone are insufficient to establish broad generalization; vary background dependence, dimensions, shift strengths and sample sizes without retrospectively selecting only favorable cases. Real-network validation, event metrics and compute measurements remain pending. This report does not authorize or perform that expanded experiment.
