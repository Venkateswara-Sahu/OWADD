"""Integrity-checked raw sample scores; callers store receipts in result envelopes."""

from pathlib import Path

import numpy as np

from experiments.metrics.novelty import evaluate_novelty
from experiments.provenance import sha256_file


def save_scores(path: Path, labels, scores):
    path = Path(path)
    evaluate_novelty(labels, scores, 0.0)  # Validate, without selecting a threshold.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        np.savez_compressed(
            stream,
            labels=np.asarray(labels, dtype=np.uint8),
            scores=np.asarray(scores, dtype=np.float64),
        )
    return {
        "sha256": sha256_file(path),
        "n_samples": len(labels),
        "score_direction": "higher_is_novel",
    }


def load_scores(path: Path, receipt):
    path = Path(path)
    if sha256_file(path) != receipt["sha256"]:
        raise ValueError("novelty sidecar checksum mismatch")
    if receipt.get("score_direction") != "higher_is_novel":
        raise ValueError("unsupported score direction")
    with np.load(path, allow_pickle=False) as arrays:
        labels, scores = arrays["labels"], arrays["scores"]
    evaluate_novelty(labels, scores, 0.0)
    if len(labels) != receipt["n_samples"]:
        raise ValueError("novelty sidecar length mismatch")
    return labels, scores
