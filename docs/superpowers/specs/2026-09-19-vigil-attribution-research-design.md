# Vigil Attribution-First Research Redesign

**Date:** 2026-09-19
**Status:** Approved design
**Primary goal:** Produce a scientifically defensible, reproducible arXiv preprint centered on label-free feature localization for drift in network traffic streams.

## 1. Background and Motivation

Vigil is an open-source Python system that extends the dual-autoencoder drift and novelty-detection framework described by Komorniczak's OWADD work. The existing project adds feature-level reconstruction-error attribution, an online API, model adaptation, and operational integrations including Kafka, Airflow, MLflow, FastAPI, and Streamlit.

The current manuscript demonstrates substantial engineering work, but its evaluation does not yet justify its strongest research claims. In particular:

- persistent post-change chunks are treated as independent positive drift events, which disadvantages change-point detectors;
- attribution outputs are presented without ground-truth localization evaluation;
- novelty recall is measured at chunk level rather than sample level;
- reference and stream samples may be drawn from the same source pool;
- results rely on one simulated stream, one dataset, and one seed;
- causal and production-readiness language exceeds the available evidence.

This redesign makes DriftAttributor the primary research contribution and treats the inherited drift detector, deployment system, and online adaptation as supporting components.

## 2. Research Objective

The paper will evaluate the following central claim:

> Changes in per-feature autoencoder reconstruction error can provide useful, label-free localization of distribution drift in network traffic streams.

The intended contribution is not a wholly new drift-detection architecture. It is a lightweight diagnostic method, a controlled evaluation protocol for drift localization, and a reproducible streaming implementation.

## 3. Research Questions and Hypotheses

### RQ1: Localization accuracy

Does DriftAttributor correctly rank features that are known to have been shifted?

**H1:** DriftAttributor performs better than random feature ranking across multiple shift types, magnitudes, and dimensionalities.

### RQ2: Comparative value

When does reconstruction-error attribution outperform or complement simpler statistical localization methods?

**H2:** DriftAttributor provides particular value for multivariate or correlated shifts that are not fully characterized by univariate mean differences.

### RQ3: Detection reliability

Can the underlying detector identify discrete change events without excessive false alarms or delay?

**H3:** The OWADD-style detector remains competitive with appropriate unsupervised baselines under event-based evaluation.

### RQ4: Operational cost

Is feature attribution inexpensive enough to use in an online stream-processing system?

**H4:** Attribution adds a small, measurable fraction of total per-chunk inference latency on CPU.

These hypotheses are falsifiable. The implementation and reporting must preserve negative or inconclusive results.

## 4. Claimed Contributions

Subject to experimental support, the manuscript will claim:

1. A lightweight, label-free feature-ranking method based on changes in autoencoder reconstruction error.
2. A controlled benchmark protocol for evaluating feature-level drift explanations against known shifted features.
3. Evaluation across controlled shifts and at least two network-traffic datasets.
4. A reproducible open-source streaming implementation with automatically generated paper results.

The manuscript will not claim causal attribution, an entirely original drift-detection architecture, universal state-of-the-art performance, or production readiness based only on the existence of integrations.

## 5. Scope

### Included

- DriftAttributor validation and comparison.
- Event-based evaluation of the existing drift detector.
- Sample-level novelty evaluation.
- Leakage-safe NSL-KDD evaluation.
- A chronological or time-aware CICIDS2017 evaluation.
- Controlled abrupt, gradual, recurring, numerical, categorical, and correlated shifts.
- Ablation, sensitivity, latency, throughput, and memory experiments.
- Reproducible configurations, manifests, raw results, aggregation, figures, and tables.
- Revision of the LaTeX paper after the experiments are complete.

### Excluded from this paper version

- Dashboard redesign.
- Expansion of Kafka or Airflow functionality unrelated to measurement.
- A comprehensive poisoning-defense or safe-adaptation framework.
- Claims of causal feature importance.
- Threshold selection using test results.
- Additional datasets that do not answer a defined generalization question.

The current adaptive update mechanism may be included as an ablation, but poisoning resistance is reserved for future work.

## 6. Dataset Design

### 6.1 Controlled shift benchmark

Controlled streams provide exact feature-level ground truth. Each experiment starts from a stable reference distribution and applies one or more documented transformations.

Required shift families:

- single-feature mean shifts;
- single-feature variance shifts;
- simultaneous shifts in 3, 5, and 10 features;
- categorical-frequency shifts;
- correlated-feature shifts;
- irrelevant noise-feature shifts;
- abrupt drift;
- gradual drift;
- recurring drift that returns to the reference distribution.

Each applicable shift family must include small, medium, and large magnitudes. The generator must save a manifest containing the seed, reference interval, event time, event type, shifted feature indices, magnitude, duration, and expected detection window.

Every primary controlled configuration will initially run with 10 seeds. Seed count may be increased if confidence intervals or ranking stability remain too wide.

### 6.2 NSL-KDD

NSL-KDD remains in the study for continuity with the existing manuscript. It must be described as a simulated stream constructed from a non-temporal benchmark.

Requirements:

- disjoint reference/training, validation, and test sample pools;
- no sampling of reference rows into validation or test chunks;
- preprocessing fitted on training data only;
- threshold and hyperparameter selection on validation streams only;
- multiple transition events separated by stable intervals;
- multiple deterministic stream realizations;
- frozen configurations before test evaluation;
- recorded class distributions, row identities, and split checksums.

### 6.3 CICIDS2017

CICIDS2017 supplies a more realistic network-traffic evaluation. Processing must remain practical on a 12th-generation Intel Core i7-1260P CPU with 16 GB RAM.

Requirements:

- process source files incrementally rather than loading the complete dataset at once;
- preserve chronological ordering where reliable timestamps are available;
- use distinct time periods for training/reference, validation, and test;
- remove identifiers or leakage-prone columns when justified and document every removal;
- fit preprocessing only on the training period;
- cache processed partitions in a compact format;
- retain natural prevalence unless an experiment explicitly studies prevalence;
- document source files, checksums, labels, timestamps, and excluded records.

The exact chronological split will be selected only after a data audit verifies timestamp quality, attack periods, duplicates, missing values, and label consistency.

### 6.4 Dataset integrity checks

Automated validation must reject runs with:

- overlapping row identities across splits;
- preprocessing learned from validation or test data;
- inconsistent feature schemas;
- non-finite values after preprocessing;
- undocumented categorical-vocabulary changes;
- absent provenance or checksums;
- non-deterministic stream construction under a fixed seed.

## 7. Methods and Baselines

### 7.1 Attribution methods

DriftAttributor will be evaluated against:

1. random feature ranking as a lower-bound sanity check;
2. absolute mean difference;
3. standardized mean difference;
4. per-feature Kolmogorov-Smirnov statistic for numerical features;
5. per-feature Wasserstein distance for numerical features;
6. Jensen-Shannon divergence for categorical or consistently discretized features;
7. a lightweight discriminative reference-versus-current classifier with coefficients or permutation importance.

SHAP may be used as a secondary analysis for the discriminative classifier if its computational cost is manageable. It is not required for every configuration.

Every baseline must receive the same reference and current windows. Methods that do not support a feature type must report that limitation instead of silently substituting another representation.

### 7.2 Drift-detection methods

The detection study will include:

- Vigil's OWADD-style reconstruction-error detector;
- ADWIN;
- KSWIN;
- Page-Hinkley;
- a discriminative two-sample detector;
- an unsupervised multivariate distance method such as MMD or a documented windowed distance detector.

Scalar detectors must receive a clearly defined signal. A supervised error signal must not be presented as equivalent to an unsupervised feature-distribution signal; supervised variants, if retained, will be reported separately.

### 7.3 Novelty detection

The existing frozen-autoencoder/KDE novelty component will be evaluated at sample level. Chunk-level novelty-presence detection may be reported only as a secondary operational metric.

## 8. Metrics

### 8.1 Attribution metrics

Controlled shifts will report:

- Precision@1, @3, @5, and @10;
- Recall@1, @3, @5, and @10 where defined;
- NDCG@k;
- mean reciprocal rank;
- average rank of shifted features;
- top-1 localization accuracy;
- ranking stability across seeds;
- attribution execution time.

Real network streams without exact feature-cause ground truth may report stability, agreement, and domain plausibility, but these must not be called localization accuracy.

### 8.2 Event-based detection metrics

A ground-truth transition is one event. An alert within a predefined tolerance window after the event counts as one detection. Additional alerts do not produce additional true positives.

The evaluation will report:

- event precision, recall, and F1;
- mean and median detection delay;
- number of missed events;
- false alarms per 10,000 samples;
- average run length during stable periods;
- results broken down by drift type and magnitude.

Tolerance windows must be fixed using validation data and documented before test evaluation.

### 8.3 Novelty metrics

- sample-level precision, recall, and F1;
- AUROC and AUPRC;
- false-positive rate on known samples;
- performance at multiple novelty prevalences;
- optional chunk-level novelty-presence metrics under a separately named protocol.

### 8.4 Statistical reporting

Stochastic results will report the number of runs, mean, standard deviation, and 95% confidence intervals where appropriate. Paired comparisons will use identical stream realizations. Effect sizes will accompany inferential tests. Overlapping uncertainty or negligible effect sizes must not be described as clear superiority.

## 9. Software Architecture

Research code will remain separate from the core public API.

```text
vigil/                    Core library
  core/                   Autoencoders, drift, and novelty detection
  attribution/            DriftAttributor and reusable attribution APIs

experiments/
  configs/                Versioned experiment definitions
  datasets/               Dataset adapters and split logic
  streams/                Controlled shifts and event generation
  baselines/              Attribution and detection competitors
  metrics/                Localization, event, and novelty metrics
  runners/                Experiment execution
  analysis/               Aggregation and statistical comparisons

artifacts/
  manifests/              Seeds, splits, versions, and shift ground truth
  raw_results/            Immutable per-run outputs
  summaries/              Aggregated tables and confidence intervals
  figures/                Automatically generated figures

paper/
  main.tex
  tables/                 Generated LaTeX tables
  figures/                Generated publication figures
```

The exact package/file decomposition may follow repository conventions as implementation proceeds, but the boundaries between library behavior, experiment construction, raw evidence, and paper presentation must remain explicit.

## 10. Configuration and Provenance

Every experiment will use a validated, versioned configuration containing:

- dataset and split identity;
- preprocessing configuration;
- stream and change-event definition;
- seed;
- method and hyperparameters;
- tolerance window;
- requested metrics;
- output location.

A stable configuration hash will identify a run. Completed hashes will be resumable and must not be overwritten silently.

Each raw result will record:

- Git commit;
- configuration hash;
- dataset and split checksums;
- Python and dependency versions;
- hardware and operating system;
- all relevant seeds;
- start time, finish time, and duration;
- raw alerts, scores, predictions, and rankings;
- warnings and failure state.

Paper tables and figures must be generated from raw result artifacts. Benchmark values must not be transcribed manually into LaTeX.

## 11. Execution and Resource Constraints

The supported reference machine is a 64-bit Windows system with an Intel Core i7-1260P CPU and 16 GB RAM. GPU availability is not assumed.

The experiment runner will:

- process one expensive experiment at a time by default;
- cache preprocessing;
- stream or partition CICIDS2017 processing;
- provide a fast smoke-test mode;
- resume completed configuration hashes;
- cap configurable CPU-thread usage;
- write partial failure records without treating them as valid results.

Aggregation must reject incomplete seed sets, mismatched dataset hashes, inconsistent feature schemas, non-finite primary metrics, and comparisons where methods did not receive identical test streams.

## 12. Test Strategy

The implementation requires automated tests for:

- split non-overlap;
- train-only preprocessing;
- deterministic output for fixed seeds;
- exact application of controlled feature shifts;
- correctness of event matching and tolerance windows;
- correctness of attribution metrics using hand-checkable examples;
- configuration validation and hashing;
- raw-result serialization and resumption;
- rejection of incomplete or incompatible result groups;
- regeneration of paper tables from fixture results;
- preservation of the existing Vigil public API.

Smoke tests will use small synthetic streams and must run quickly. Full benchmark runs are not required in the unit-test suite.

## 13. Implementation Stages

### Stage 1: Benchmark foundation

Implement configuration validation, deterministic seeding, provenance manifests, leakage-safe dataset interfaces, event-based metrics, smoke mode, and aggregation.

### Stage 2: Controlled attribution benchmark

Implement controlled shift generators, attribution baselines, localization metrics, and multi-seed analysis. Inspect whether DriftAttributor provides value before expanding the paper.

### Stage 3: Correct drift evaluation

Implement multiple transition types, stable intervals, event matching, false-alarm measurement, and fair baseline adapters. Retire the existing persistent-positive chunk recall from research claims.

### Stage 4: Network datasets

Rebuild NSL-KDD evaluation with non-overlapping splits, then audit and add CICIDS2017 using chronological partitions.

### Stage 5: Ablation and systems evaluation

Measure frozen versus adaptive models, single versus dual autoencoders, chunk/buffer/threshold sensitivity, replication count, latency, throughput, attribution overhead, and peak memory.

### Stage 6: Paper rewrite

Rewrite the manuscript around the validated results. Expand related work, define the relationship to OWADD precisely, add threats to validity and reproducibility sections, and generate all numerical tables and figures from saved artifacts.

## 14. Decision Rules for Unexpected Results

- If a simple statistical baseline consistently outperforms DriftAttributor, do not conceal the result. Diagnose failure modes and either improve the method using validation experiments or narrow the contribution to the conditions where it adds value.
- If attribution does not outperform random ranking on controlled shifts, pause the paper rewrite and treat this as a method-design failure.
- If detection is not competitive under event-based metrics, retain detection as infrastructure and avoid a performance-superiority claim.
- If CICIDS2017 cannot support a trustworthy chronological split because of data quality, document the issue and replace it with a dataset whose temporal protocol can be defended.
- If computation exceeds laptop constraints, reduce redundant configurations or use justified stratified partitions before reducing seed count or compromising split integrity.

## 15. Manuscript Structure

The revised paper will contain:

1. Introduction and scoped contributions.
2. Related work on unsupervised drift detection, drift localization, and explainable streaming systems.
3. Method, including a precise distinction between inherited OWADD components and the new attribution method.
4. Experimental protocol, datasets, split integrity, baselines, metrics, and statistical procedure.
5. Controlled attribution results.
6. Event-based detection and sample-level novelty results.
7. Ablation and systems measurements.
8. Limitations and threats to validity.
9. Reproducibility statement.
10. Conclusion using only experimentally supported language.

## 16. ArXiv-Ready Completion Criteria

The work is ready for an arXiv preprint only when:

- every primary claim maps to a reported experiment;
- attribution is evaluated against known shifted features;
- at least two network datasets are included;
- train/validation/test and preprocessing leakage checks pass;
- event-based metrics replace persistent chunk-level recall;
- primary controlled results cover at least 10 seeds;
- uncertainty is reported;
- meaningful attribution and detection baselines are included;
- novelty claims use sample-level metrics;
- latency and memory results identify the hardware and protocol;
- every paper number is reproducible from saved raw results;
- the complete automated test suite passes in a documented environment;
- weak, negative, and inconclusive results are disclosed;
- the final rendered PDF has no citation, layout, figure, or table defects.

## 17. Success Definition

Success is not defined as obtaining a predetermined improvement percentage. The project succeeds if it produces a transparent, reproducible answer to the research questions and a manuscript whose claims remain defensible under the implemented protocol.
