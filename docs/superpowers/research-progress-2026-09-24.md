# Sample-level novelty evaluation foundation

The evaluator now consumes one binary ground-truth label and score per sample, with 1 meaning novel and larger scores meaning more novel. Prediction is `score >= threshold`; the threshold is supplied, never selected inside the evaluator. It reports confusion counts, precision, recall, F1, known-sample false-positive rate, AUROC, and noninterpolated average precision. Average precision is named explicitly, not conflated with trapezoidal PR area.

Zero-denominator metrics are `None` with a reason. Single-class AUROC and average precision are withheld by reporting policy. Missing, nonfinite, nonbinary, empty, misaligned, and non-vector inputs are rejected. Tests use a hand-computed six-sample example, single-class cases, threshold ties, and no-alert cases.

Raw labels/scores can be stored in compressed NPZ files with SHA-256, sample-count, and score-direction receipts. Loading verifies these properties and disables pickle. Existing sidecars cannot be overwritten. A failed write does not publish a receipt; callers must not treat an unreferenced NPZ file as completed evidence.

## Outstanding integration gates

Task 9 is not complete: the prevalence grid, validation-only novelty threshold selection/freeze, runner sidecar references and verification on result resume remain to be implemented. No new model-performance results were produced.

Do not reuse controlled mean-shift indicators as novel-class ground truth: a distribution shift need not introduce an unknown class. Define disjoint known/novel pools and the validation/test novelty protocol before wiring metrics into primary results. Existing core KDE density scores point in the opposite direction (higher means known), and exponentiation can underflow; a research adapter must explicitly handle score direction and numerical stability. These are integration requirements, not changes to the existing public API in this checkpoint.

The CICIDS2017 preparation, duplicate-conflict findings and unevaluated held-out model test days remain unchanged.
