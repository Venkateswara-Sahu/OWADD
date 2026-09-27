# Two-sided attribution ablation: frozen development protocol

Declared before running seeds10-29. User approved keeping original Vigil unchanged, adding absolute and reference-standardized error changes, identical per-seed models/windows, and paired uncertainty. This is a follow-up development experiment motivated by inspected seeds0-9, not independent proof of novelty or publication readiness.

## Fixed design

- Reuse the independent Gaussian generator and all six cases of `attribution-screen-protocol.md`: stable, mean+0.5/+2, standard-deviation x0.5/x2, correlation0.8. Seeds10-29,20 epochs,hidden width10; training/reference/current sizes2000/200/200,20 features,two shifted features. All methods use identical windows and common independent tie permutations. No changes to model architecture, training, public attribution, data generation, adaptation, or gating.
- Original: normalized positive mean squared reconstruction-error change.
- `vigil_absolute_delta`: absolute current-minus-reference mean squared reconstruction-error change. Save signed change as direction.
- `vigil_standardized_absolute_delta`: divide that absolute change by the reference window's sample standard deviation of per-row squared reconstruction errors (`ddof=1`). Denominator is `max(reference_sd,1e-12)` per feature. Save reference SD and floor. This is an effect-scale ranking, not a calibrated test statistic, probability or causal attribution. The fixed absolute floor is a numerical guard and has scale sensitivity; extreme scores on constant features are possible.
- Both candidates are experimental helpers under `experiments/attribution`, not replacements for `vigil/attribution.py`. Same fitted model for all three. Retain the seven original methods and add these two, giving54 case/method groups and1080 score vectors.
- CPU float32 inference and mean errors match the original rule; reference SD computed in float64. Restore model modes and do not train or compute gradients. Reject invalid, mismatched, empty/nonfinite windows and fewer than two reference rows.
- Preserve raw scores, signed deltas, denominators, seeds, input/model/source hashes, all original ranking metrics, and completion-checked resume behavior. Version2 configuration prevents reuse of version1 results. Reduced smoke configurations explicitly mark protocol_complete=false; true requires precisely seeds10-29 and20 epochs.

## Analysis and checks

Primary descriptive measure: Recall@3 by shift family, retaining stable null as undefined. Report other original ranking metrics as supporting results. Compute candidate-minus-baseline differences within each seed for both candidates against all seven originals, plus standardized-minus-absolute:15 comparisons per case. Deterministic2000-resample percentile95% bootstrap intervals over20 paired seed differences. Intervals are unadjusted exploratory intervals, not a familywise significance claim. Lower average shifted rank is better; higher other localization metrics is better. No grand mean combining easy and hard shift families. No changes based on these outcomes and reruns relabeled as fresh evidence.

Test-first checks: analytic direction/magnitude/SD fixture, zero-variance finite output, invalid inputs, mode/gradient preservation, repeatability, unchanged public positive-only behavior, complete paired integration and resumability. Run full regression suite, scoped lint/format checks and independent code/spec reviews before the real run. Commit the code/protocol, run from a clean checkpoint, verify resumption before writing the result report.

Correlation remains diagnostic only: no stronger dependency baseline is introduced in this bounded ablation. These Gaussian simulations do not establish performance on categorical features, real network shifts, event detection or runtime suitability. Official network test sets remain untouched.
