"""Explicit known/novel pools and validation-only threshold freezing.

Input pools must already have training-only preprocessing and source identity
deduplication. This module checks row IDs, not raw-feature duplicate equivalence.
"""

import json
import os
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import numpy as np

from experiments.datasets.base import validate_disjoint_ids
from experiments.metrics.novelty import evaluate_novelty
from experiments.novelty_scores import load_scores, save_scores

MATRIX_DIMENSIONS = 2
BINARY_CLASS_COUNT = 2


def _digest(value):
    return sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


@dataclass(frozen=True)
class NoveltyPool:
    role: str
    X: np.ndarray
    labels: np.ndarray
    row_ids: tuple[str, ...]
    original_labels: tuple[str, ...]

    @property
    def identity(self):
        return _digest(
            {
                "role": self.role,
                "shape": self.X.shape,
                "features_sha256": sha256(self.X.tobytes()).hexdigest(),
                "labels": self.labels.tolist(),
                "row_ids": self.row_ids,
                "original_labels": self.original_labels,
            }
        )


@dataclass(frozen=True)
class NoveltyProtocol:
    reference: NoveltyPool
    validation: NoveltyPool
    test: NoveltyPool
    known_classes: tuple[str, ...]
    novel_classes: tuple[str, ...]

    @property
    def identity(self):
        return _digest(
            {
                "reference": self.reference.identity,
                "validation": self.validation.identity,
                "test": self.test.identity,
                "known": self.known_classes,
                "novel": self.novel_classes,
            }
        )


def make_protocol(reference, validation, test, *, known_classes, novel_classes):
    known, novel = set(known_classes), set(novel_classes)
    if (
        not known
        or not novel
        or known & novel
        or not all(isinstance(v, str) and v for v in known | novel)
    ):
        raise ValueError("nonempty disjoint named known/novel classes required")
    pools = []
    width = None
    for role, source in zip(
        ("reference", "validation", "test"), (reference, validation, test)
    ):
        X = np.array(source.X, dtype="<f8", order="C", copy=True)
        original = tuple(source.y)
        ids = tuple(source.row_ids)
        if (
            X.ndim != MATRIX_DIMENSIONS
            or not len(X)
            or not X.shape[1]
            or len(original) != len(X)
            or len(ids) != len(X)
        ):
            raise ValueError("nonempty aligned features, labels and row IDs required")
        if not np.isfinite(X).all() or (width is not None and X.shape[1] != width):
            raise ValueError("finite aligned feature schema required")
        width = X.shape[1]
        if not all(isinstance(v, str) and v for v in ids) or len(set(ids)) != len(ids):
            raise ValueError("unique nonempty source row IDs required")
        if set(original) - (known | novel):
            raise ValueError("undeclared source class")
        labels = np.array([label in novel for label in original], dtype=np.uint8)
        if role == "reference" and labels.any():
            raise ValueError("reference contains a declared novel class")
        if role == "reference" and set(original) != known:
            raise ValueError("all known classes must occur in reference")
        if role != "reference" and len(np.unique(labels)) != BINARY_CLASS_COUNT:
            raise ValueError("validation and test require known and novel samples")
        X[X == 0] = 0
        X.flags.writeable = labels.flags.writeable = False
        pools.append(NoveltyPool(role, X, labels, ids, original))
    validate_disjoint_ids({pool.role: set(pool.row_ids) for pool in pools})
    return NoveltyProtocol(*pools, tuple(sorted(known)), tuple(sorted(novel)))


@dataclass(frozen=True)
class ScoredPool:
    pool_identity: str
    role: str
    values: np.ndarray


def score_pool(pool, scorer):
    """Scorer must be frozen and return higher-is-novel scores in input order."""
    values = np.array(scorer(pool.X), dtype=float, copy=True)
    evaluate_novelty(pool.labels, values, 0.0)
    values.flags.writeable = False
    return ScoredPool(pool.identity, pool.role, values)


def _check_scores(pool, scored):
    if scored.role != pool.role or scored.pool_identity != pool.identity:
        raise ValueError(f"{pool.role} score identity mismatch")
    evaluate_novelty(pool.labels, scored.values, 0.0)


def freeze_threshold(path, protocol, validation_scores, candidates, *, model_id):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("model identity required")
    _check_scores(protocol.validation, validation_scores)
    candidates = np.asarray(candidates, dtype=float)
    if (
        candidates.ndim != 1
        or not len(candidates)
        or not np.isfinite(candidates).all()
        or len(np.unique(candidates)) != len(candidates)
    ):
        raise ValueError("distinct finite threshold candidates required")
    trials = []
    for threshold in candidates:
        metrics = evaluate_novelty(
            protocol.validation.labels, validation_scores.values, threshold
        )
        trials.append({"threshold": float(threshold), "metrics": asdict(metrics)})
    chosen = max(
        trials,
        key=lambda t: (
            t["metrics"]["f1"],
            -t["metrics"]["false_positive_rate"],
            t["threshold"],
        ),
    )
    score_path = path.with_name(f"{path.stem}.{uuid4().hex}.validation.npz")
    receipt = save_scores(
        score_path,
        protocol.validation.labels,
        validation_scores.values,
    )
    receipt["file"] = score_path.name
    payload = {
        "schema_version": 1,
        "protocol_id": protocol.identity,
        "model_id": model_id,
        "threshold": chosen["threshold"],
        "validation_trials": trials,
        "validation_scores": receipt,
        "selection_rule": "maximum sample F1; ties: lower FPR then higher threshold",
        "validation_prevalence": float(protocol.validation.labels.mean()),
        "known_classes": protocol.known_classes,
        "novel_classes": protocol.novel_classes,
    }
    payload["integrity_sha256"] = _digest(payload)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, allow_nan=False)
        # Atomic no-overwrite publication on the same filesystem.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return payload


def evaluate_frozen(
    path, protocol, test_scores, *, model_id, prevalence=None, n_samples=None, seed=42
):
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = payload.pop("integrity_sha256")
    if expected != _digest(payload) or payload["schema_version"] != 1:
        raise ValueError("frozen manifest integrity mismatch")
    if payload["model_id"] != model_id:
        raise ValueError("frozen model identity mismatch")
    if payload["protocol_id"] != protocol.identity:
        raise ValueError("frozen protocol identity mismatch")
    receipt = payload["validation_scores"]
    name = receipt["file"]
    if Path(name).name != name or not name.endswith(".npz"):
        raise ValueError("invalid validation evidence filename")
    labels, _ = load_scores(path.parent / name, receipt)
    if not np.array_equal(labels, protocol.validation.labels):
        raise ValueError("validation evidence mismatch")
    _check_scores(protocol.test, test_scores)
    indices = np.arange(len(protocol.test.labels))
    if prevalence is not None:
        indices = prevalence_indices(
            protocol.test.labels, prevalence, n_samples, seed=seed
        )
    elif n_samples is not None:
        raise ValueError("n_samples requires an explicit prevalence")
    return evaluate_novelty(
        protocol.test.labels[indices], test_scores.values[indices], payload["threshold"]
    )


def prevalence_indices(labels, prevalence, n_samples, *, seed):
    labels = np.asarray(labels)
    if labels.ndim != 1 or not np.isin(labels, [0, 1]).all():
        raise ValueError("binary vector required")
    if (
        type(n_samples) is not int
        or n_samples < 1
        or not np.isfinite(prevalence)
        or not 0 < prevalence < 1
    ):
        raise ValueError(
            "positive integer sample count and prevalence between zero and one required"
        )
    novel_count = prevalence * n_samples
    if not np.isclose(novel_count, round(novel_count), rtol=0, atol=1e-9):
        raise ValueError("prevalence must yield an integer novel count")
    novel_count = round(novel_count)
    if not 0 < novel_count < n_samples:
        raise ValueError("both classes required")
    rng = np.random.default_rng(seed)
    selected = []
    for label, count in ((0, n_samples - novel_count), (1, novel_count)):
        candidates = np.flatnonzero(labels == label)
        if len(candidates) < count:
            raise ValueError("insufficient distinct samples for requested prevalence")
        selected.extend(rng.choice(candidates, count, replace=False))
    return rng.permutation(selected)
