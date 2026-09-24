# Known/novel evaluation and threshold freeze

This implements a research API, not a new performance result or publication freeze. Real held-out NSL-KDD and CICIDS2017 model evaluations have not been run here.

## Contract

`make_protocol(reference, validation, test, known_classes=..., novel_classes=...)` consumes three already prepared `DatasetSplit` objects. It requires disjoint unique source row IDs, aligned finite numeric features, explicitly declared disjoint class sets, and both known/novel observations in validation and test. Every declared known class must occur in reference training, and no novel class may occur there. Arrays are copied and made read-only. Content identities include features, labels, original classes, roles and row IDs.

The caller remains responsible for source-feature duplicate checks and fitting preprocessing exclusively on reference data. The protocol checks source IDs; it cannot prove that a caller assigned honest IDs or trained a model honestly. These are not security boundaries. This dense API is intended for declared experimental pools, not to replace the disk-backed CICIDS preparation reader.

Here, novel means absent from reference/model fitting. Novel class names may appear in both validation and test; this is not a claim of generalization to novel classes unseen during threshold calibration. A class-disjoint novelty study needs an additional explicitly declared protocol.

`score_pool(pool, frozen_scorer)` binds finite scores to their source pool. Higher scores must mean more novel. This differs from the existing KDE density convention. Scorers must not update their model while scoring. A caller-supplied `model_id` must identify fitted parameters, preprocessing and score convention, rather than merely a model family name.

`freeze_threshold(path, protocol, validation_scores, candidates, model_id=...)` accepts only the protocol's validation evidence. Candidates must be distinct and finite. Selection maximizes sample F1, breaks ties by lower known-sample FPR, then higher threshold. It saves every candidate's metrics, the declared class sets, validation prevalence, protocol/model identities, a checksummed raw validation NPZ and an integrity-digested manifest. Existing files cannot be silently overwritten.

`evaluate_frozen(...)` verifies manifest, model, protocol and validation-sidecar identities before applying the chosen threshold to bound test scores. It never selects a threshold from test labels. Missing or altered evidence fails closed. Test labels are used for evaluation and optional explicitly controlled prevalence sampling only.

Freeze manifests are published atomically without overwrite using a same-filesystem hard link. Score files use unique attempt names; interrupted unpublished attempts are preserved as orphan evidence and do not prevent retries. Only files referenced by a completed manifest/result are eligible evidence. This is retry safety, not a claim that the existing general result writer supports concurrent publishers. Filesystems without hard-link support fail closed rather than using a weaker overwrite fallback.

## Runner and prevalence experiments

`experiments.runner.run_novelty_evaluation` saves a standard result envelope plus checksummed test-score sidecar. Resumption checks both the JSON completion marker and raw score sidecar, including equality to the newly supplied score evidence. Its configuration must use `split="test"` and exactly `params={"n_prevalence_samples": N}`. It records natural-population metrics separately from 1%, 5%, 10%, 25%, and 50% novel-population scenarios.

The same frozen threshold is reused throughout. Sampling is deterministic, without replacement within each scenario, and rejects fractional requested class counts or insufficient distinct samples. Use N divisible by 100. The same original observations may appear in several scenarios; these are paired sensitivity scenarios, not independent replications. No threshold is retuned for test prevalence. Prevalence selection uses ground-truth labels and must not be described as natural traffic.

## Verified fixture example

The integration test has 20 known reference records and separate validation/test pools with 100 known and 100 novel records each. Deliberately perfect fixture scores verify persistence, the five exact requested counts, and resumption. A different fixture deliberately reverses the test ranking after calibration and confirms test F1 remains zero instead of allowing retuning. These numbers test the software and are not Vigil accuracy evidence.

## Remaining research work

The frozen Vigil scoring adapter below supplies higher-is-novel scores and fitted-state identities. Choose actual dataset class sets and a validation population before running a study. The API does not automatically nominate attack labels as novel classes or treat mean shifts as novel-class ground truth. Multi-seed model fitting, baseline comparisons, actual novelty experiments, duplicate-policy sensitivity and final whole-branch review remain outstanding.

## Frozen model scoring

`FrozenNoveltyScorer.from_vigil(fitted_vigil, preprocessing_id=..., reference_id=protocol.reference.identity, batch_size=1024)` copies the fitted A_KC and KDE into an independent CPU inference snapshot. It never invokes drift detection, adaptation, training or threshold selection. Refitting the source Vigil instance does not change the snapshot. The underlying public Vigil API remains unchanged.

Scores are **negative log KDE density of per-sample reconstruction MSE**, so higher means more novel. Keeping log-density avoids the ranking ties caused by exponentiating very small densities to zero. It does not promise that all possible finite inputs yield finite scores: nonfinite features, float32 conversion overflow, reconstruction overflow and nonfinite KDE output are rejected explicitly. Both low-error and high-error low-density regions can be novel under KDE; this is not simply a high-reconstruction-error detector.

Inference converts and processes at most `batch_size` rows at a time, retaining a one-dimensional score vector. This bounds inference intermediates, not the caller's input storage, fitted KDE, model fitting, or the dense protocol API. Inputs must have the same feature order and training-fitted preprocessing as reference data.

`scorer.model_id` binds the model architecture, tensor weights, complete pickled fitted KDE state (hashed in memory only), preprocessing/reference identifiers, score convention, execution batch size and Torch/scikit-learn versions. It is runtime-specific, not a cross-version portable model format. No pickle file is loaded or written. Callers must use a checksum of the actual preprocessing state/feature schema for `preprocessing_id`; an arbitrary name is not evidence of correct preprocessing. Likewise, the reference identifier records the caller's attestation, not proof of training history. Underscored internals are not a security boundary and must not be mutated.

Typical order: fit Vigil on declared reference data, take the snapshot, call `score_pool(protocol.validation, scorer)`, freeze thresholds with `model_id=scorer.model_id`, then score the test pool and evaluate using the same identity. The scorer alone does not block premature test access; the study workflow must enforce that ordering. The integration test uses a tiny trained synthetic fixture, not NSL-KDD/CICIDS2017 test data or publication evidence.

## Verification and scoped review

Tests cover class declarations, source overlap, unknown classes in reference, known classes absent from reference, wrong-pool calibration, fixed thresholds against reversed test rankings, model/protocol mismatch, edited manifests and sidecars, exact deterministic prevalence counts, result resumption and interrupted publication recovery. Separate specification and standards reviews identified interruption recovery and inconsistent string-path handling; regression tests reproduced and then verified both fixes. This is a review of this scoped workflow, not final whole-branch approval.

Changed Python files pass Ruff and Black; experiments compile successfully. Repository-wide lint remains non-clean in other files, including Airflow imports/line lengths and duplicate exports in `vigil/__init__.py`. No unrelated lint cleanup or dependency installation was performed.
