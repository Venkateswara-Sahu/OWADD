# Vigil Attribution Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a leakage-safe, configuration-driven research benchmark that validates DriftAttributor against known feature shifts, evaluates drift as change events, measures sample-level novelty and runtime, and regenerates an evidence-backed arXiv manuscript.

**Architecture:** Keep `vigil/` as the public library and add an `experiments/` package for dataset adapters, stream construction, baselines, metrics, runners, and analysis. Every run is defined by a validated configuration, writes immutable JSON/NPZ evidence plus provenance, and feeds deterministic aggregation scripts that generate paper tables and figures.

**Tech Stack:** Python 3.10+, NumPy, pandas, SciPy, scikit-learn, PyTorch, PyYAML, psutil, pytest, Matplotlib, River, LaTeX/IEEEtran.

**Spec:** `docs/superpowers/specs/2026-09-19-vigil-attribution-research-design.md`

## Global Constraints

- Supported reference hardware is a 64-bit Windows system with an Intel Core i7-1260P CPU and 16 GB RAM; GPU availability is not assumed.
- Fit every scaler, encoder, threshold, and hyperparameter on training or validation data only; test data is read only after configuration freeze.
- Primary controlled experiments use at least 10 seeds; identical methods receive identical stream manifests.
- Treat drift as an event with one match per tolerance window, never as a positive label on every post-change chunk.
- Keep raw results immutable and keyed by a stable configuration hash; never silently overwrite a completed run.
- Generate paper tables and figures from raw result artifacts; do not hand-transcribe benchmark values.
- Do not claim causal attribution, universal state-of-the-art performance, or production readiness from integrations alone.
- Keep CICIDS2017 memory-bounded by processing one source file at a time and caching only processed partitions.
- Preserve the existing `Vigil` public API and existing operational integrations.
- Use validation evidence to select thresholds and freeze the resulting test configuration in a committed manifest.

## Review Focus

- Duplicate or reordered rows across train/validation/test must be detected through stable row identifiers and rejected before fitting.
- A changed categorical vocabulary in validation/test must map to an explicit unknown representation without refitting the encoder.
- Multiple alerts around one change event must count as one true detection and the remaining alerts as duplicates or false alarms according to the documented matcher.
- A resumed run whose dataset checksum or code/config provenance differs must not reuse the old completion marker.
- Attribution metrics must behave correctly when `k` exceeds the number of features or when no feature is marked shifted; undefined recall must be explicit rather than silently zero.

---

## File Map

### Existing files to modify

- `pyproject.toml` - add research dependencies, console entry points, and experiment package discovery.
- `.gitignore` - ignore downloaded datasets and heavy raw artifacts while allowing schemas, manifests, summaries, and paper outputs intended for version control.
- `vigil/attribution.py` - correct non-causal terminology, make zero-positive-delta behavior explicit, and expose stable score arrays.
- `data/nsl_kdd_loader.py` - retain backward compatibility while delegating research preprocessing to the new leakage-safe adapter.
- `paper/main.tex` - rewrite claims and experimental sections only after validated result generation exists.
- `paper/vigil_paper.bib` - add the final primary-source related work used by the rewritten paper.

### New benchmark foundation files

- `experiments/__init__.py` - package marker.
- `experiments/config.py` - frozen dataclasses, YAML loading, canonical serialization, and configuration hashes.
- `experiments/provenance.py` - Git, environment, hardware, dependency, and dataset-checksum capture.
- `experiments/io.py` - atomic result writes, completion markers, resumption, and compatibility checks.
- `experiments/cli.py` - `prepare`, `run`, `aggregate`, and `paper` commands.
- `experiments/configs/smoke.yaml` - fast end-to-end fixture configuration.

### New streams and datasets files

- `experiments/streams/types.py` - `ChangeEvent`, `StreamChunk`, and `StreamManifest` contracts.
- `experiments/streams/controlled.py` - deterministic numerical, categorical, correlated, gradual, abrupt, and recurring shifts.
- `experiments/datasets/base.py` - leakage-safe dataset/split interface and row-identity validation.
- `experiments/datasets/nsl_kdd.py` - disjoint NSL-KDD pools and train-fitted preprocessing.
- `experiments/datasets/cicids2017.py` - incremental CICIDS2017 audit, cleaning, schema alignment, and chronological partitions.
- `experiments/datasets/audit.py` - audit reports and validation errors shared by dataset adapters.

### New method and metric files

- `experiments/attribution/base.py` - attribution protocol and common result type.
- `experiments/attribution/statistical.py` - mean, standardized mean, KS, Wasserstein, and Jensen-Shannon rankings.
- `experiments/attribution/discriminative.py` - reference-versus-current logistic classifier plus permutation importance.
- `experiments/attribution/vigil_adapter.py` - adapter for `DriftAttributor`.
- `experiments/detection/adapters.py` - Vigil, ADWIN, KSWIN, Page-Hinkley, discriminative, and MMD-compatible adapters.
- `experiments/metrics/attribution.py` - Precision@k, Recall@k, NDCG@k, reciprocal rank, average rank, and stability.
- `experiments/metrics/events.py` - one-to-one event matching, delay, false alarms, and average run length.
- `experiments/metrics/novelty.py` - sample-level classification and ranking metrics.
- `experiments/metrics/stats.py` - paired summaries, bootstrap confidence intervals, and effect sizes.

### New execution and reporting files

- `experiments/runner.py` - common per-configuration execution pipeline.
- `experiments/aggregate.py` - completeness checks and tidy summary tables.
- `experiments/benchmark_system.py` - latency, throughput, and peak-memory measurement.
- `experiments/paper_outputs.py` - LaTeX tables and Matplotlib figures generated from summaries.
- `experiments/configs/controlled_attribution.yaml` - primary controlled study grid.
- `experiments/configs/nsl_kdd.yaml` - validation and frozen NSL-KDD test settings.
- `experiments/configs/cicids2017.yaml` - chronological CICIDS2017 settings.
- `experiments/configs/systems.yaml` - CPU systems benchmark grid.

### New tests

- `tests/experiments/test_config.py`
- `tests/experiments/test_provenance_io.py`
- `tests/experiments/test_controlled_streams.py`
- `tests/experiments/test_attribution_metrics.py`
- `tests/experiments/test_attribution_baselines.py`
- `tests/experiments/test_event_metrics.py`
- `tests/experiments/test_novelty_metrics.py`
- `tests/experiments/test_dataset_splits.py`
- `tests/experiments/test_nsl_kdd_adapter.py`
- `tests/experiments/test_cicids2017_adapter.py`
- `tests/experiments/test_runner.py`
- `tests/experiments/test_aggregation.py`
- `tests/experiments/test_system_benchmark.py`
- `tests/experiments/test_paper_outputs.py`

## Task 1: Establish the validated experiment contract

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `experiments/__init__.py`
- Create: `experiments/config.py`
- Create: `experiments/configs/smoke.yaml`
- Test: `tests/experiments/test_config.py`

**Interfaces:**
- Consumes: standard-library dataclasses, `yaml.safe_load`, and canonical JSON serialization.
- Produces: `ExperimentConfig.from_yaml(path: Path) -> ExperimentConfig`, `ExperimentConfig.canonical_dict() -> dict`, and `ExperimentConfig.config_hash -> str`.

- [ ] **Step 1: Add a failing canonical-hash test**

```python
from pathlib import Path

import pytest

from experiments.config import ExperimentConfig


def test_config_hash_is_key_order_independent(tmp_path: Path) -> None:
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text("seed: 42\ndataset: synthetic\nmethod: vigil\n", encoding="utf-8")
    second.write_text("method: vigil\ndataset: synthetic\nseed: 42\n", encoding="utf-8")

    assert ExperimentConfig.from_yaml(first).config_hash == ExperimentConfig.from_yaml(second).config_hash


def test_config_rejects_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("dataset: synthetic\nseed: 42\nmethod: vigil\nsurprise: true\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown configuration keys"):
        ExperimentConfig.from_yaml(path)
```

- [ ] **Step 2: Run the focused test and confirm the missing module failure**

Run: `python -m pytest tests/experiments/test_config.py -q`

Expected: FAIL because `experiments.config` does not exist.

- [ ] **Step 3: Add the research dependencies and package entry point**

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
research = [
    "matplotlib>=3.8.0",
    "psutil>=5.9.0",
    "pyarrow>=14.0.0",
    "pyyaml>=6.0.1",
    "river>=0.21.0",
]

[project.scripts]
vigil-bench = "experiments.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["vigil*", "experiments*"]
```

Merge the `research` group into the existing optional-dependencies table rather than creating a duplicate table. Update `all` to include `research`.

- [ ] **Step 4: Implement the minimal frozen configuration model**

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ExperimentConfig:
    dataset: str
    method: str
    seed: int
    split: str = "test"
    chunk_size: int = 200
    tolerance_chunks: int = 2
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> "ExperimentConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"unknown configuration keys: {unknown}")
        return cls(**payload)

    def canonical_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def config_hash(self) -> str:
        encoded = json.dumps(
            self.canonical_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return sha256(encoded).hexdigest()[:16]
```

- [ ] **Step 5: Add validation tests for invalid seed, chunk size, and tolerance**

Extend the dataclass with `__post_init__` that raises `ValueError` when `seed < 0`, `chunk_size < 2`, or `tolerance_chunks < 0`. Test each invalid input independently.

- [ ] **Step 6: Add the smoke YAML and artifact ignore policy**

Create `experiments/configs/smoke.yaml`:

```yaml
dataset: synthetic
method: vigil
seed: 42
split: test
chunk_size: 40
tolerance_chunks: 1
params:
  n_reference: 200
  n_chunks: 6
  n_features: 8
```

Add to `.gitignore`:

```gitignore
artifacts/raw_results/
artifacts/cache/
artifacts/datasets/
!artifacts/manifests/
!artifacts/summaries/
!artifacts/figures/
```

- [ ] **Step 7: Run config tests and the existing suite**

Run: `python -m pytest tests/experiments/test_config.py tests/test_autoencoder.py tests/test_drift_detector.py tests/test_sentinel.py -q`

Expected: PASS.

- [ ] **Step 8: Commit the experiment contract**

```powershell
git add pyproject.toml .gitignore experiments/__init__.py experiments/config.py experiments/configs/smoke.yaml tests/experiments/test_config.py
git commit -m "feat: add validated research experiment configuration"
```

## Task 2: Add provenance-safe atomic result storage

**Files:**
- Create: `experiments/provenance.py`
- Create: `experiments/io.py`
- Test: `tests/experiments/test_provenance_io.py`

**Interfaces:**
- Consumes: `ExperimentConfig.config_hash` from Task 1.
- Produces: `capture_provenance(dataset_paths: Sequence[Path]) -> Provenance`, `write_result_atomic(root: Path, envelope: ResultEnvelope) -> Path`, and `load_completed_result(root: Path, config: ExperimentConfig, provenance: Provenance) -> ResultEnvelope | None`.

- [ ] **Step 1: Write failing tests for atomic completion and incompatible resumption**

```python
def test_result_is_complete_only_after_marker(tmp_path, config, provenance):
    envelope = ResultEnvelope(config=config.canonical_dict(), provenance=provenance, metrics={"score": 0.5})
    result_path = write_result_atomic(tmp_path, envelope)
    assert result_path.exists()
    assert result_path.with_suffix(".complete").exists()


def test_changed_dataset_checksum_prevents_resume(tmp_path, config, provenance):
    write_result_atomic(tmp_path, ResultEnvelope(config.canonical_dict(), provenance, {"score": 0.5}))
    changed = dataclasses.replace(provenance, dataset_checksums={"data.csv": "different"})
    assert load_completed_result(tmp_path, config, changed) is None
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `python -m pytest tests/experiments/test_provenance_io.py -q`

Expected: FAIL because the provenance and I/O modules do not exist.

- [ ] **Step 3: Implement checksums and environment capture**

Define frozen `Provenance` with Git commit, dirty flag, Python version, platform, CPU, total RAM, dependency versions, dataset checksums, and UTC timestamp. Compute SHA-256 by streaming 1 MiB blocks so CICIDS files are not loaded into memory.

- [ ] **Step 4: Implement atomic result envelopes**

Use a sibling temporary file, `Path.replace`, and a final `.complete` marker. Key the output directory by both configuration hash and a provenance hash derived from Git commit plus dataset checksums. Never regard a JSON file without its marker as complete.

- [ ] **Step 5: Test interrupted writes and corrupt JSON**

Monkeypatch JSON serialization to raise before replacement and assert that no `.complete` marker exists. Write malformed JSON beside a marker and assert that loading raises `ResultIntegrityError` rather than silently rerunning.

- [ ] **Step 6: Run focused and full tests**

Run: `python -m pytest tests/experiments/test_provenance_io.py tests/experiments/test_config.py -q`

Expected: PASS.

- [ ] **Step 7: Commit provenance storage**

```powershell
git add experiments/provenance.py experiments/io.py tests/experiments/test_provenance_io.py
git commit -m "feat: record immutable experiment provenance"
```

## Task 3: Build deterministic controlled streams with exact ground truth

**Files:**
- Create: `experiments/streams/__init__.py`
- Create: `experiments/streams/types.py`
- Create: `experiments/streams/controlled.py`
- Create: `experiments/configs/controlled_attribution.yaml`
- Test: `tests/experiments/test_controlled_streams.py`

**Interfaces:**
- Consumes: NumPy arrays and validated seeds.
- Produces: `ControlledStreamBuilder.build(reference: np.ndarray, spec: ShiftSpec) -> tuple[list[StreamChunk], StreamManifest]`.

- [ ] **Step 1: Write a failing exact-mean-shift test**

```python
def test_abrupt_mean_shift_changes_only_declared_features():
    reference = np.zeros((400, 6), dtype=np.float64)
    spec = ShiftSpec(kind="mean", features=(1, 4), magnitude=2.0, event_chunk=3, n_chunks=6, chunk_size=40, seed=7)
    chunks, manifest = ControlledStreamBuilder().build(reference, spec)

    before = np.vstack([chunk.X for chunk in chunks[:2]])
    after = np.vstack([chunk.X for chunk in chunks[2:]])
    np.testing.assert_allclose(after[:, [1, 4]].mean(axis=0) - before[:, [1, 4]].mean(axis=0), 2.0, atol=0.2)
    np.testing.assert_allclose(after[:, [0, 2, 3, 5]].mean(axis=0), before[:, [0, 2, 3, 5]].mean(axis=0), atol=0.2)
    assert manifest.events[0].shifted_features == (1, 4)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `python -m pytest tests/experiments/test_controlled_streams.py -q`

Expected: FAIL because controlled stream types do not exist.

- [ ] **Step 3: Implement immutable stream contracts**

Create frozen dataclasses:

```python
@dataclass(frozen=True)
class ChangeEvent:
    event_id: str
    start_chunk: int
    end_chunk: int
    kind: str
    shifted_features: tuple[int, ...]
    magnitude: float


@dataclass(frozen=True)
class StreamChunk:
    chunk_id: int
    X: np.ndarray
    sample_labels: np.ndarray | None = None


@dataclass(frozen=True)
class StreamManifest:
    seed: int
    n_features: int
    chunk_size: int
    events: tuple[ChangeEvent, ...]
```

- [ ] **Step 4: Implement numerical abrupt, gradual, and recurring shifts**

Use `np.random.default_rng(spec.seed)`. Apply gradual magnitude as a linear ramp between `event_chunk` and `end_chunk`. For recurring drift, restore unmodified draws after `end_chunk` and create separate start and return events.

- [ ] **Step 5: Implement variance, categorical-frequency, correlated, and noise shifts**

For categorical shifts, accept declared categorical feature indices and target probability vectors; sample without converting categories to floating interpolations. For correlated shifts, generate a positive-semidefinite covariance perturbation and record every participating feature. Reject invalid category probabilities and non-positive variance multipliers.

- [ ] **Step 6: Add determinism and edge-case tests**

Test identical seeds byte-for-byte, different seeds not identical, feature index bounds, `k > n_features`, invalid gradual intervals, and recurring return events. Confirm the input reference array is never mutated.

- [ ] **Step 7: Add the primary controlled grid**

Create `controlled_attribution.yaml` with seeds `0..9`, feature counts `20` and `100`, shift counts `1`, `3`, `5`, and `10`, effect sizes `0.5`, `1.0`, and `2.0`, and abrupt/gradual/recurring variants. Keep a single smoke subset selectable by CLI.

- [ ] **Step 8: Run tests and commit**

Run: `python -m pytest tests/experiments/test_controlled_streams.py -q`

Expected: PASS.

```powershell
git add experiments/streams experiments/configs/controlled_attribution.yaml tests/experiments/test_controlled_streams.py
git commit -m "feat: generate controlled drift streams"
```

## Task 4: Implement attribution metrics and comparison baselines

**Files:**
- Modify: `vigil/attribution.py`
- Create: `experiments/attribution/__init__.py`
- Create: `experiments/attribution/base.py`
- Create: `experiments/attribution/statistical.py`
- Create: `experiments/attribution/discriminative.py`
- Create: `experiments/attribution/vigil_adapter.py`
- Create: `experiments/metrics/__init__.py`
- Create: `experiments/metrics/attribution.py`
- Test: `tests/experiments/test_attribution_metrics.py`
- Test: `tests/experiments/test_attribution_baselines.py`
- Test: `tests/test_sentinel.py`

**Interfaces:**
- Consumes: reference/current arrays and a shared `feature_types` tuple.
- Produces: `AttributionMethod.rank(reference, current, feature_types) -> AttributionScores` and `evaluate_ranking(scores, shifted_features, ks) -> dict[str, float | None]`.

- [ ] **Step 1: Write hand-checkable failing metric tests**

```python
def test_ranking_metrics_match_known_order():
    scores = np.array([0.1, 0.9, 0.8, 0.2])
    metrics = evaluate_ranking(scores, shifted_features={1, 2}, ks=(1, 2, 5))
    assert metrics["precision@1"] == 1.0
    assert metrics["recall@1"] == 0.5
    assert metrics["precision@2"] == 1.0
    assert metrics["recall@2"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["precision@5"] == pytest.approx(0.5)


def test_empty_ground_truth_has_explicit_undefined_recall():
    metrics = evaluate_ranking(np.array([0.2, 0.1]), shifted_features=set(), ks=(1,))
    assert metrics["recall@1"] is None
```

- [ ] **Step 2: Run the metric tests and confirm failure**

Run: `python -m pytest tests/experiments/test_attribution_metrics.py -q`

Expected: FAIL because the metrics module does not exist.

- [ ] **Step 3: Implement stable ranking metrics**

Use descending stable sort with feature index as the deterministic tie-breaker. Clamp `k` to feature count for selection but divide precision by the number of returned positions, not the requested out-of-range `k`. Implement binary-relevance DCG/NDCG, reciprocal rank, average shifted-feature rank, and Jaccard top-k stability.

- [ ] **Step 4: Define the attribution protocol**

```python
@dataclass(frozen=True)
class AttributionScores:
    method: str
    scores: np.ndarray
    elapsed_ms: float
    metadata: dict[str, object]


class AttributionMethod(Protocol):
    name: str
    def rank(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        feature_types: tuple[str, ...],
    ) -> AttributionScores: ...
```

- [ ] **Step 5: Write failing baseline behavior tests**

Construct a reference matrix where feature 0 changes only in mean, feature 1 only in variance, and feature 2 is categorical with changed frequency. Assert that the expected method ranks its matching changed feature first. Assert unknown feature types raise a descriptive `ValueError`.

- [ ] **Step 6: Implement statistical baselines**

Implement absolute mean difference, pooled standardized mean difference, KS statistic, Wasserstein distance, and Jensen-Shannon divergence with Laplace smoothing. Numerical-only methods must return `NaN` for categorical features and the aggregator must exclude unsupported cells rather than converting them to zero.

- [ ] **Step 7: Implement the discriminative baseline**

Use a `Pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed))` and held-out permutation importance measured by balanced accuracy. Split the combined reference/current discriminator dataset with stratification and a fixed seed.

- [ ] **Step 8: Correct DriftAttributor terminology and zero-delta behavior**

Replace “caused,” “causal contribution,” and “responsible” in public docstrings with “associated with reconstruction-error increase.” When every delta is non-positive, return zero contributions plus `metadata["no_positive_delta"] = True`; do not emit a uniform ranking that falsely implies evidence.

- [ ] **Step 9: Add the Vigil attribution adapter and regression tests**

The adapter accepts a fitted autoencoder and exposes the full `feature_error_delta` score vector. Update sentinel tests to assert existing top-feature output remains available when positive deltas exist and is explicitly zero when none exist.

- [ ] **Step 10: Run the attribution suite and commit**

Run: `python -m pytest tests/experiments/test_attribution_metrics.py tests/experiments/test_attribution_baselines.py tests/test_sentinel.py -q`

Expected: PASS.

```powershell
git add vigil/attribution.py experiments/attribution experiments/metrics tests/experiments/test_attribution_metrics.py tests/experiments/test_attribution_baselines.py tests/test_sentinel.py
git commit -m "feat: validate drift feature attribution"
```

## Task 5: Replace chunk recall with one-to-one event evaluation

**Files:**
- Create: `experiments/metrics/events.py`
- Create: `experiments/detection/__init__.py`
- Create: `experiments/detection/adapters.py`
- Test: `tests/experiments/test_event_metrics.py`

**Interfaces:**
- Consumes: `Sequence[ChangeEvent]`, alert chunk indices, and `tolerance_chunks`.
- Produces: `match_events(events, alerts, tolerance_chunks) -> EventEvaluation` and detector adapters exposing `update(X, labels=None) -> list[Alert]`.

- [ ] **Step 1: Write failing one-to-one event-matching tests**

```python
def test_duplicate_alerts_do_not_inflate_true_positives():
    events = [ChangeEvent("e1", 10, 10, "mean", (2,), 1.0)]
    result = match_events(events, alerts=[10, 11, 12], tolerance_chunks=2)
    assert result.true_events == 1
    assert result.matched_events == 1
    assert result.duplicate_alerts == 2
    assert result.event_recall == 1.0


def test_alert_before_event_is_false_alarm():
    events = [ChangeEvent("e1", 10, 10, "mean", (2,), 1.0)]
    result = match_events(events, alerts=[9], tolerance_chunks=2)
    assert result.false_alarms == 1
    assert result.missed_events == 1
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python -m pytest tests/experiments/test_event_metrics.py -q`

Expected: FAIL because event metrics do not exist.

- [ ] **Step 3: Implement greedy chronological one-to-one matching**

For each event in chronological order, match the earliest still-unmatched alert in `[event.start_chunk, event.start_chunk + tolerance_chunks]`. Classify additional alerts inside an already matched window as duplicates. Alerts outside every window are false alarms. Compute delay from the matched alert only.

- [ ] **Step 4: Implement event metrics**

Return event precision, recall, F1, delays, missed events, false alarms per 10,000 samples, duplicate alerts, and average stable run length. Explicitly define precision as `None` when no alerts exist and recall as `None` when no events exist.

- [ ] **Step 5: Add boundary and overlap tests**

Test alerts at both tolerance boundaries, two nearby non-overlapping events, overlapping windows, no events, no alerts, unsorted input, and negative alert indices. Reject ambiguous overlapping ground-truth windows unless the caller selects an explicit `allow_overlaps=True` policy.

- [ ] **Step 6: Add detector adapters**

Implement adapters for Vigil, River ADWIN/KSWIN/Page-Hinkley, a logistic discriminative two-sample detector, and an RBF-MMD detector. All adapters consume chunks and return timestamped alerts. Supervised error-stream variants require labels and set `uses_labels=True` in metadata; they are aggregated separately.

- [ ] **Step 7: Test equal-stream inputs and detector metadata**

Use constant stable chunks to verify no adapter crashes on zero variance. Assert supervised adapters reject missing labels and unsupervised adapters never access labels.

- [ ] **Step 8: Run tests and commit**

Run: `python -m pytest tests/experiments/test_event_metrics.py -q`

Expected: PASS.

```powershell
git add experiments/metrics/events.py experiments/detection tests/experiments/test_event_metrics.py
git commit -m "feat: evaluate drift as change events"
```

## Task 6: Create the resumable runner and statistically valid aggregation

**Files:**
- Create: `experiments/runner.py`
- Create: `experiments/aggregate.py`
- Create: `experiments/metrics/stats.py`
- Create: `experiments/cli.py`
- Test: `tests/experiments/test_runner.py`
- Test: `tests/experiments/test_aggregation.py`

**Interfaces:**
- Consumes: configuration, provenance, stream manifests, method adapters, and metric functions from Tasks 1-5.
- Produces: `run_experiment(config, output_root) -> ResultEnvelope`, `aggregate_results(paths, expected_methods, expected_seeds) -> pd.DataFrame`, and CLI commands.

- [ ] **Step 1: Write a failing smoke-run test**

```python
def test_smoke_run_is_resumable(tmp_path):
    config = ExperimentConfig.from_yaml(Path("experiments/configs/smoke.yaml"))
    first = run_experiment(config, tmp_path)
    second = run_experiment(config, tmp_path)
    assert first.result_id == second.result_id
    assert second.metadata["resumed"] is True
```

- [ ] **Step 2: Run runner tests and confirm failure**

Run: `python -m pytest tests/experiments/test_runner.py -q`

Expected: FAIL because the runner does not exist.

- [ ] **Step 3: Implement the execution pipeline**

Load or construct the dataset, validate schema and splits, build the stream and manifest, fit only on the reference/training partition, run methods on identical chunks, compute metrics, capture provenance, and atomically write the result. Derive NumPy, Python, scikit-learn, and PyTorch seeds from the configuration seed.

- [ ] **Step 4: Add failure envelopes**

On an exception, write a non-complete failure JSON containing configuration, provenance, exception class, message, and traceback. Never create a completion marker. The next run may retry the same configuration.

- [ ] **Step 5: Write failing aggregation-integrity tests**

Assert aggregation rejects one missing seed, a method evaluated on a different stream-manifest hash, incompatible dataset checksums, `NaN` primary metrics without an explicit undefined reason, and mixed supervised/unsupervised comparisons in one ranking table.

- [ ] **Step 6: Implement paired summaries and confidence intervals**

Group by dataset, shift family, magnitude, method, and metric. Compute count, mean, standard deviation, and a deterministic paired bootstrap 95% confidence interval. Add paired effect sizes relative to DriftAttributor using identical seeds/manifests.

- [ ] **Step 7: Implement CLI commands**

Support:

```text
vigil-bench run --config experiments/configs/smoke.yaml --output artifacts/raw_results
vigil-bench aggregate --input artifacts/raw_results --output artifacts/summaries
vigil-bench paper --input artifacts/summaries --output paper
```

Return non-zero exit codes for invalid configurations, incomplete comparisons, and corrupt artifacts.

- [ ] **Step 8: Run the smoke workflow**

Run: `vigil-bench run --config experiments/configs/smoke.yaml --output artifacts/raw_results`

Expected: one completed result with manifest, provenance, attribution metrics, and event metrics.

Run the same command again.

Expected: resume without recomputation.

- [ ] **Step 9: Run tests and commit**

Run: `python -m pytest tests/experiments/test_runner.py tests/experiments/test_aggregation.py -q`

Expected: PASS.

```powershell
git add experiments/runner.py experiments/aggregate.py experiments/metrics/stats.py experiments/cli.py tests/experiments/test_runner.py tests/experiments/test_aggregation.py
git commit -m "feat: run and aggregate reproducible benchmarks"
```

## Task 7: Rebuild NSL-KDD with disjoint research splits

**Files:**
- Create: `experiments/datasets/__init__.py`
- Create: `experiments/datasets/base.py`
- Create: `experiments/datasets/audit.py`
- Create: `experiments/datasets/nsl_kdd.py`
- Modify: `data/nsl_kdd_loader.py`
- Create: `experiments/configs/nsl_kdd.yaml`
- Test: `tests/experiments/test_dataset_splits.py`
- Test: `tests/experiments/test_nsl_kdd_adapter.py`

**Interfaces:**
- Consumes: original NSL-KDD train and test files.
- Produces: `PreparedDataset(reference, validation, test, feature_names, feature_types, row_ids, checksums)` and deterministic multi-event stream manifests.

- [ ] **Step 1: Write failing split-overlap and unknown-category tests**

```python
def test_split_validator_rejects_duplicate_row_ids():
    with pytest.raises(DataLeakageError, match="overlap"):
        validate_disjoint_ids({"train": {"a", "b"}, "test": {"b", "c"}})


def test_unseen_category_does_not_refit_encoder():
    preprocessor = fit_preprocessor(training_frame)
    categories_before = tuple(preprocessor.named_transformers_["cat"].categories_[0])
    transformed = preprocessor.transform(frame_with_unseen_category)
    assert tuple(preprocessor.named_transformers_["cat"].categories_[0]) == categories_before
    assert np.isfinite(transformed).all()
```

- [ ] **Step 2: Run dataset tests and confirm failure**

Run: `python -m pytest tests/experiments/test_dataset_splits.py tests/experiments/test_nsl_kdd_adapter.py -q`

Expected: FAIL because dataset adapters do not exist.

- [ ] **Step 3: Implement the dataset contract and audit report**

Define immutable split records with `X`, `y`, stable SHA-256 row IDs computed from raw rows, and source identity. Validate disjointness before preprocessing. Produce an audit JSON containing row counts, class counts, duplicate counts, missing values, infinities, and schema.

- [ ] **Step 4: Implement train-fitted preprocessing**

Use a scikit-learn `ColumnTransformer` with `OneHotEncoder(handle_unknown="ignore", sparse_output=False)` for categorical columns and `MinMaxScaler` fitted only on training numeric columns. Persist feature names and feature types. Validation/test numerical values outside the training range may remain outside `[0, 1]`; do not refit or clip silently.

- [ ] **Step 5: Implement disjoint NSL-KDD pools**

Use `KDDTrain+.txt` only for reference/training and validation pools, split by stable row hash with a committed seed. Use `KDDTest+.txt` exclusively for final test streams. Remove exact duplicate raw rows before splitting and record removal counts.

- [ ] **Step 6: Construct multi-event NSL-KDD streams**

Build stable normal intervals separated by attack-family transitions. Create distinct validation and test manifests. Avoid sampling with replacement unless a minority class cannot fill a chunk; if replacement is necessary, record it and exclude duplicate samples from uncertainty calculations.

- [ ] **Step 7: Preserve the legacy loader**

Keep `load_nsl_kdd(split)` behavior for package users, but update its docstring to state that it is not the leakage-safe research pipeline and point to `experiments.datasets.nsl_kdd`.

- [ ] **Step 8: Add validation/freeze configuration**

The config must separate `mode: tune` from `mode: test`. Tuning writes `artifacts/manifests/nsl_kdd_frozen.json` containing selected parameters and validation provenance. Test mode refuses to run unless this frozen manifest exists and matches the current dataset checksum.

- [ ] **Step 9: Run audits, tests, and smoke benchmark**

Run: `python -m pytest tests/experiments/test_dataset_splits.py tests/experiments/test_nsl_kdd_adapter.py -q`

Run: `vigil-bench run --config experiments/configs/nsl_kdd.yaml --mode smoke --output artifacts/raw_results`

Expected: PASS and a completed leakage audit.

- [ ] **Step 10: Commit the NSL-KDD pipeline**

```powershell
git add experiments/datasets data/nsl_kdd_loader.py experiments/configs/nsl_kdd.yaml tests/experiments/test_dataset_splits.py tests/experiments/test_nsl_kdd_adapter.py
git commit -m "feat: add leakage-safe NSL-KDD evaluation"
```

## Task 8: Add a chronological, memory-bounded CICIDS2017 adapter

**Files:**
- Create: `experiments/datasets/cicids2017.py`
- Create: `experiments/configs/cicids2017.yaml`
- Test: `tests/experiments/test_cicids2017_adapter.py`
- Create after audit: `artifacts/manifests/cicids2017_audit.json`

**Interfaces:**
- Consumes: locally supplied CICIDS2017 CSV files and their documented day/file identities.
- Produces: audited Monday reference/training data, Tuesday validation data, and Wednesday-Friday test streams with aligned schemas and stable row IDs.

- [ ] **Step 1: Create tiny representative CSV fixtures in the test**

Use temporary files representing Monday benign data, Tuesday brute-force data, and Wednesday mixed benign/DoS data. Include whitespace-padded column names, `Infinity`, `NaN`, a duplicate row, and an unseen label.

- [ ] **Step 2: Write failing incremental-audit tests**

Assert the adapter strips column whitespace, normalizes label whitespace without merging distinct labels, records and removes exact duplicates, rejects non-finite feature rows under the configured policy, and never calls `pandas.concat` on all source files at once.

- [ ] **Step 3: Run the focused test and verify failure**

Run: `python -m pytest tests/experiments/test_cicids2017_adapter.py -q`

Expected: FAIL because the adapter does not exist.

- [ ] **Step 4: Implement incremental file audit**

Read each file in configurable chunks, calculate raw and cleaned counts, schema differences, label counts, duplicates, missing values, infinities, timestamp parse failures, and SHA-256. Write the audit atomically. Abort if required columns or parseable timestamps are absent.

- [ ] **Step 5: Implement the chronological split policy**

Use Monday (`Monday-WorkingHours.pcap_ISCX.csv`) as benign reference/training, Tuesday files as validation, and Wednesday through Friday files as test. Preserve row order after timestamp parsing within each file and documented day order across files. Do not randomly rebalance primary streams.

- [ ] **Step 6: Implement train-only schema and preprocessing**

Drop `Flow ID`, source/destination IP, and raw timestamp from model inputs after using them to create stable row identities and order. Document the exact drop list in the audit. Fit imputation/scaling only on Monday. Align later files to the Monday feature schema and reject unexplained missing required features.

- [ ] **Step 7: Add memory-bound and chronology tests**

Assert maximum configured read chunk size is honored, transformed partitions are written one at a time, chronological ordering is monotonic inside each partition, and test data cannot invoke `.fit()` on the preprocessor.

- [ ] **Step 8: Add the experiment configuration**

Define source filename patterns, `read_chunk_rows: 100000`, split days, dropped identifiers, stable-label mapping, validation tuning grid, test tolerance, and cache paths. Dataset locations must be CLI/config inputs rather than hard-coded user paths.

- [ ] **Step 9: Run the fixture tests, then the real audit**

Run: `python -m pytest tests/experiments/test_cicids2017_adapter.py -q`

Expected: PASS.

Run after the user has supplied/downloaded the dataset:

```powershell
vigil-bench prepare --config experiments/configs/cicids2017.yaml --data-root <CICIDS2017-directory> --output artifacts/datasets/cicids2017
```

Expected: processed day partitions plus `artifacts/manifests/cicids2017_audit.json`; no benchmark starts if audit validation fails.

- [ ] **Step 10: Commit code and the small audit manifest, not raw data**

```powershell
git add experiments/datasets/cicids2017.py experiments/configs/cicids2017.yaml tests/experiments/test_cicids2017_adapter.py artifacts/manifests/cicids2017_audit.json
git commit -m "feat: add chronological CICIDS2017 evaluation"
```

## Task 9: Correct sample-level novelty evaluation

**Files:**
- Create: `experiments/metrics/novelty.py`
- Modify: `experiments/runner.py`
- Test: `tests/experiments/test_runner.py`
- Test: `tests/experiments/test_novelty_metrics.py`

**Interfaces:**
- Consumes: per-sample novelty scores, binary known/novel ground truth, and validation-selected threshold.
- Produces: `evaluate_novelty(y_true, scores, threshold) -> NoveltyEvaluation` with sample metrics and optional chunk-presence metrics under separate names.

- [ ] **Step 1: Write failing sample-level novelty tests**

Use a six-sample hand-checkable vector and assert precision, recall, F1, false-positive rate, AUROC, and AUPRC. Test all-known and all-novel cases and require undefined AUROC/AUPRC to be represented as `None` with a reason.

- [ ] **Step 2: Implement sample-level metrics**

Use scikit-learn classification metrics with explicit zero-division behavior. Name chunk-level metrics `chunk_presence_*`; never expose them under `novelty_recall`.

- [ ] **Step 3: Add prevalence grids**

Extend controlled configurations to evaluate novelty proportions of 1%, 5%, 10%, 25%, and 50%. Choose density/score thresholds on validation data and reuse the frozen threshold for test runs.

- [ ] **Step 4: Integrate raw novelty scores into result envelopes**

Store per-sample scores and labels in compressed NPZ sidecars referenced by JSON result envelopes. Verify array length and checksum on load.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/experiments/test_runner.py tests/experiments/test_novelty_metrics.py -q`

Expected: PASS.

```powershell
git add experiments/metrics/novelty.py experiments/runner.py experiments/configs/controlled_attribution.yaml tests/experiments/test_runner.py tests/experiments/test_novelty_metrics.py
git commit -m "feat: evaluate novelty at sample level"
```

## Task 10: Add ablations and CPU systems measurements

**Files:**
- Create: `experiments/benchmark_system.py`
- Create: `experiments/configs/systems.yaml`
- Modify: `experiments/runner.py`
- Test: `tests/experiments/test_system_benchmark.py`

**Interfaces:**
- Consumes: fitted methods, chunk sizes, feature counts, warmup count, and repeat count.
- Produces: median/p95 latency, samples per second, attribution overhead, adaptation cost, and process peak RSS with hardware provenance.

- [ ] **Step 1: Write a failing timing-summary test**

Monkeypatch `time.perf_counter_ns` with deterministic values and assert median, p95, and throughput calculations. Assert warmup observations are excluded.

- [ ] **Step 2: Implement timing and memory measurement**

Use `perf_counter_ns`, `psutil.Process().memory_info().rss`, one CPU process, and configurable PyTorch thread count. Measure fit, detection, attribution, and adaptation separately. Record raw timings as well as summaries.

- [ ] **Step 3: Add the systems configuration**

Use chunk sizes `50`, `200`, `1000`, and `5000`; feature counts `41`, `122`, `500`, and `1000`; five warmups; thirty measured repeats; and CPU thread counts `1` and a documented capped default.

- [ ] **Step 4: Add method ablations**

Support frozen versus adaptive primary autoencoder, single versus dual autoencoder, attribution disabled versus enabled, buffer-size grid, replication-count grid, and validation-selected threshold grid. Ensure each ablation changes one factor relative to a named reference configuration.

- [ ] **Step 5: Add realistic assertions**

Tests should assert non-negative times, internally consistent throughput, hardware metadata presence, and successful behavior for zero detected drift. Do not assert a fragile absolute millisecond target in CI.

- [ ] **Step 6: Run tests and commit**

Run: `python -m pytest tests/experiments/test_system_benchmark.py -q`

Expected: PASS.

```powershell
git add experiments/benchmark_system.py experiments/configs/systems.yaml experiments/runner.py tests/experiments/test_system_benchmark.py
git commit -m "feat: benchmark Vigil ablations and runtime"
```

## Task 11: Generate paper tables and figures from validated evidence

**Files:**
- Create: `experiments/paper_outputs.py`
- Test: `tests/experiments/test_paper_outputs.py`
- Create: `paper/tables/.gitkeep`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: complete aggregated summary tables with provenance and expected seed counts.
- Produces: stable LaTeX tables and PDF/PNG figures whose metadata includes the summary hash.

- [ ] **Step 1: Write failing fixture-output tests**

Provide a small summary fixture and assert exact method order, escaped LaTeX names, mean/CI formatting, explicit missing-value rendering, and deterministic output bytes. Assert incomplete seed groups raise `IncompleteEvidenceError`.

- [ ] **Step 2: Implement table generation**

Generate separate tables for controlled attribution, event detection, sample-level novelty, ablations, and systems performance. Include `n`, mean, uncertainty, units, and supervised/unsupervised labels where relevant.

- [ ] **Step 3: Implement figures**

Generate attribution performance by shift type/magnitude, delay-versus-false-alarm tradeoff, novelty precision-recall, latency scaling, and ablation plots. Use accessible colors, readable labels, vector PDF output, and 300-DPI PNG previews.

- [ ] **Step 4: Embed evidence hashes**

Write a companion `paper/generated-results.json` mapping each output to the input summary hash, generation command, Git commit, and UTC timestamp. Refuse to generate from mixed dataset checksums or incomplete methods.

- [ ] **Step 5: Update ignore rules**

Keep large raw artifacts ignored, but explicitly track `paper/tables/*.tex`, `paper/figures/*.pdf`, `paper/figures/*.png`, and `paper/generated-results.json`.

- [ ] **Step 6: Run tests and commit**

Run: `python -m pytest tests/experiments/test_paper_outputs.py -q`

Expected: PASS.

```powershell
git add experiments/paper_outputs.py tests/experiments/test_paper_outputs.py paper/tables/.gitkeep .gitignore
git commit -m "feat: generate paper outputs from evidence"
```

## Task 12: Execute the primary studies and freeze results

**Files:**
- Create: `artifacts/manifests/controlled_study.json`
- Create: `artifacts/manifests/nsl_kdd_frozen.json`
- Create: `artifacts/manifests/cicids2017_frozen.json`
- Create: `artifacts/summaries/attribution.csv`
- Create: `artifacts/summaries/detection.csv`
- Create: `artifacts/summaries/novelty.csv`
- Create: `artifacts/summaries/systems.csv`

**Interfaces:**
- Consumes: all preceding code and configurations.
- Produces: complete, validated evidence used by the manuscript.

- [ ] **Step 1: Run all smoke tests and the complete unit suite**

Run: `python -m pytest -q`

Expected: PASS with no skipped integrity tests.

- [ ] **Step 2: Run controlled attribution experiments**

Run: `vigil-bench run --config experiments/configs/controlled_attribution.yaml --output artifacts/raw_results`

Expected: all declared seeds, shift types, magnitudes, methods, and manifests complete.

- [ ] **Step 3: Aggregate and inspect controlled results before expanding**

Run: `vigil-bench aggregate --input artifacts/raw_results --study controlled_attribution --output artifacts/summaries`

Gate: If DriftAttributor does not beat random ranking on controlled shifts, stop paper execution and open a method-redesign task. If simple baselines dominate, document conditions and decide whether to improve the method using validation streams or narrow the claim.

- [ ] **Step 4: Tune and freeze NSL-KDD parameters**

Run validation mode, write `nsl_kdd_frozen.json`, then run test mode exactly once per frozen configuration. Any change after viewing test results creates a new explicitly exploratory study, not a replacement test result.

- [ ] **Step 5: Audit, tune, freeze, and test CICIDS2017**

Complete the dataset audit first. Run Tuesday validation for parameter selection, freeze the manifest, then run Wednesday-Friday test streams without fitting or threshold changes.

- [ ] **Step 6: Run novelty and systems studies**

Run prevalence grids and systems configurations. Check that every result records hardware and that raw timing distributions are retained.

- [ ] **Step 7: Validate evidence completeness**

Run aggregation with strict expected seeds/methods. Investigate failures; never drop failed seeds only because they reduce performance. Record any excluded run and a method-independent exclusion reason.

- [ ] **Step 8: Commit lightweight manifests and summaries**

```powershell
git add artifacts/manifests artifacts/summaries
git commit -m "results: freeze Vigil attribution benchmarks"
```

Do not commit raw CICIDS2017 data or large per-sample result arrays.

## Task 13: Rewrite and verify the manuscript

**Files:**
- Modify: `paper/main.tex`
- Modify: `paper/vigil_paper.bib`
- Create: `paper/tables/*.tex`
- Modify/Create: `paper/figures/*`
- Create: `paper/generated-results.json`
- Modify: `paper/README.md`

**Interfaces:**
- Consumes: frozen summaries and generated paper outputs from Tasks 11-12.
- Produces: an arXiv-ready PDF whose claims map to evidence hashes.

- [ ] **Step 1: Rewrite the contribution statement before inserting numbers**

State that the dual-autoencoder detector derives from OWADD and that this paper contributes reconstruction-error feature localization, its controlled evaluation, network-stream experiments, and reproducible implementation. Remove “causal contribution,” “exact features responsible,” and unsupported “production-ready” language.

- [ ] **Step 2: Expand related work using verified primary sources**

Cover explainable drift, drift localization, attribution in evolving streams, autoencoder reconstruction explanations, unsupervised network drift, and OWADD. Verify every citation against the source and avoid novelty claims broader than the literature review supports.

- [ ] **Step 3: Replace the experimental protocol and results**

Describe disjoint splits, train-only preprocessing, validation freeze, event matching, controlled feature ground truth, baselines, seed counts, uncertainty, and hardware. Replace all legacy chunk-recall and 5.8x statements unless independently reproduced under the new protocol.

- [ ] **Step 4: Insert generated tables and figures**

Use `\input{tables/<name>.tex}` for generated tables and reference generated figures. Every numerical statement in prose must be traceable to a table/figure or summary field.

- [ ] **Step 5: Add limitations and reproducibility sections**

Disclose simulated NSL-KDD chronology, CICIDS2017 limitations, associational attribution, dataset-specific generalization, adaptation contamination risk, CPU-only evaluation, and any negative results. Document exact commands and environment setup.

- [ ] **Step 6: Build and inspect the PDF**

Run from `paper/`:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Expected: successful build with no undefined references or citations.

- [ ] **Step 7: Render every page and visually inspect it**

Use Poppler `pdftoppm -png -r 150 main.pdf artifacts/paper-review/page`. Inspect every page for overflow, clipped equations, unreadable plots, table collisions, blank spill pages, inconsistent references, and incorrect colors.

- [ ] **Step 8: Run claim and artifact verification**

Search the manuscript for legacy metrics, causal language, manually typed result percentages, undefined citations, and filenames absent from `generated-results.json`. Re-run `python -m pytest -q` and regenerate paper outputs from summaries in a clean temporary directory; compare hashes.

- [ ] **Step 9: Commit the verified manuscript**

```powershell
git add paper/main.tex paper/vigil_paper.bib paper/tables paper/figures paper/generated-results.json paper/README.md
git commit -m "paper: rewrite Vigil around validated attribution evidence"
```

## Task 14: Final reproducibility and release gate

**Files:**
- Modify: `README.md`
- Modify: `README_PYPI.md`
- Create: `REPRODUCIBILITY.md`
- Create: `artifacts/manifests/release-verification.json`

**Interfaces:**
- Consumes: final code, frozen evidence, and manuscript.
- Produces: a documented release candidate suitable for a tagged repository snapshot and arXiv source upload.

- [ ] **Step 1: Document the minimal reproduction path**

Specify environment creation, optional research dependency installation, dataset acquisition locations, checksum verification, smoke run, full configurations, aggregation, and paper build. Separate commands that require externally downloaded CICIDS data.

- [ ] **Step 2: Correct public project claims**

Update README and package copy to distinguish engineering features from research evidence. Replace the old headline metrics with generated validated results or neutral wording if the new evidence is inconclusive.

- [ ] **Step 3: Verify from a clean environment**

Create a new virtual environment, install `.[research,dev]`, run the full tests, execute the smoke configuration, aggregate it, and rebuild the paper. Record commands, dependency lock information, output hashes, and status in `release-verification.json`.

- [ ] **Step 4: Check the arXiv package**

Verify the source archive contains `main.tex`, bibliography, generated tables, figures, and required style assets, but excludes datasets, raw results, secrets, local paths, and temporary render files.

- [ ] **Step 5: Run final repository checks**

Run:

```powershell
python -m pytest -q
ruff check .
black --check .
git status --short
```

Expected: all tests and checks pass; only intentionally ignored raw artifacts remain outside version control.

- [ ] **Step 6: Commit the release documentation**

```powershell
git add README.md README_PYPI.md REPRODUCIBILITY.md artifacts/manifests/release-verification.json
git commit -m "docs: add Vigil research reproducibility guide"
```

At this point, request an independent whole-branch code and manuscript review. Do not upload to arXiv until review findings are resolved and the completion criteria in the approved specification are checked one by one.
