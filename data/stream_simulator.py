"""
Stream Simulator
================
Simulates a real-time high-velocity data stream from the NSL-KDD dataset.

In real production systems (IoT sensors, financial transactions, network
traffic), data arrives continuously. This simulator mimics that behaviour
by yielding fixed-size chunks from the dataset in order, optionally injecting
synthetic concept drift at configurable timestamps.

The stream structure used to evaluate OWADD:
  - Phase 1 (chunks 0–N1):  Normal traffic only → stable reference distribution
  - Phase 2 (chunks N1–N2): Attack traffic injected → concept drift event
  - Phase 3 (chunks N2+):   New attack type added → novel class emergence
"""

import numpy as np
from dataclasses import dataclass
from typing import Generator


@dataclass
class StreamChunk:
    """
    A single batch from the simulated data stream.

    Attributes
    ----------
    chunk_id : int
    X : np.ndarray, shape (chunk_size, n_features)
    labels : np.ndarray, shape (chunk_size,)  — true labels (for evaluation only)
    is_drift_point : bool — True if this chunk begins a drift event (ground truth)
    is_novelty_point : bool — True if this chunk introduces a new attack class
    dominant_class : str — Most common label in this chunk
    """
    chunk_id: int
    X: np.ndarray
    labels: np.ndarray
    is_drift_point: bool
    is_novelty_point: bool
    dominant_class: str


class StreamSimulator:
    """
    Simulates a non-stationary tabular data stream from the NSL-KDD dataset.

    Constructs a stream with configurable drift and novelty injection points,
    matching the experimental design of arXiv:2605.29834.

    Parameters
    ----------
    X : np.ndarray
        Full normalised feature matrix (from nsl_kdd_loader.load_nsl_kdd).
    y : np.ndarray
        Label array corresponding to X.
    chunk_size : int
        Number of samples per stream batch. Paper uses 200. Default: 200.
    drift_after_chunk : int
        Chunk index after which attack traffic is injected (drift event).
        Default: 5 (after 5 stable chunks).
    novelty_after_chunk : int
        Chunk index after which a brand-new attack class appears.
        Default: 15.
    novelty_proportion : float
        Fraction of each chunk (after novelty point) that is novel class.
        Default: 0.2 (20%, paper range: 5%–30%).
    seed : int
        Random seed for reproducibility.
    """

    def __init__(
        self,
        X: np.ndarray,
        y: np.ndarray,
        chunk_size: int = 200,
        drift_after_chunk: int = 5,
        novelty_after_chunk: int = 15,
        novelty_proportion: float = 0.2,
        seed: int = 42,
    ):
        self.X = X
        self.y = y
        self.chunk_size = chunk_size
        self.drift_after_chunk = drift_after_chunk
        self.novelty_after_chunk = novelty_after_chunk
        self.novelty_proportion = novelty_proportion
        self.rng = np.random.default_rng(seed)

        # Separate indices by class
        self._class_indices = {
            cls: np.where(y == cls)[0]
            for cls in np.unique(y)
        }

        # Define stream phases
        all_classes = list(np.unique(y))
        self._normal_classes = ["normal"]
        self._attack_classes = [c for c in all_classes if c != "normal"]

        # Reserve last attack class as the "novel" class
        self._novel_class = self._attack_classes[-1] if self._attack_classes else None
        self._known_attack_classes = self._attack_classes[:-1]

    @property
    def n_features(self) -> int:
        return self.X.shape[1]

    def _sample_class(self, cls: str, n: int) -> np.ndarray:
        """Sample n rows from a specific class with replacement."""
        idx = self._class_indices.get(cls, np.array([]))
        if len(idx) == 0:
            return np.zeros((n, self.n_features), dtype=np.float32)
        chosen = self.rng.choice(idx, size=n, replace=True)
        return self.X[chosen]

    def _build_chunk(self, chunk_id: int) -> StreamChunk:
        """Build a single stream chunk according to the current phase."""
        n = self.chunk_size
        is_drift = False
        is_novelty = False

        if chunk_id <= self.drift_after_chunk:
            # Phase 1: pure normal traffic
            X_chunk = self._sample_class("normal", n)
            labels = np.array(["normal"] * n)

        elif chunk_id <= self.novelty_after_chunk:
            # Phase 2: mixed normal + known attacks (concept drift)
            is_drift = (chunk_id == self.drift_after_chunk + 1)
            n_attack = n // 2
            n_normal = n - n_attack
            attack_cls = self.rng.choice(self._known_attack_classes or ["normal"])
            X_chunk = np.vstack([
                self._sample_class("normal", n_normal),
                self._sample_class(attack_cls, n_attack),
            ])
            labels = np.array(["normal"] * n_normal + [attack_cls] * n_attack)

        else:
            # Phase 3: novel class appears
            is_novelty = (chunk_id == self.novelty_after_chunk + 1)
            n_novel = int(n * self.novelty_proportion)
            n_known = n - n_novel
            attack_cls = self.rng.choice(self._known_attack_classes or ["normal"])
            X_known = np.vstack([
                self._sample_class("normal", n_known // 2),
                self._sample_class(attack_cls, n_known - n_known // 2),
            ])
            X_novel = self._sample_class(self._novel_class or "normal", n_novel)
            X_chunk = np.vstack([X_known, X_novel])
            labels = np.array(
                ["normal"] * (n_known // 2)
                + [attack_cls] * (n_known - n_known // 2)
                + [self._novel_class or "normal"] * n_novel
            )

        # Shuffle within chunk
        shuffle_idx = self.rng.permutation(len(X_chunk))
        X_chunk = X_chunk[shuffle_idx].astype(np.float32)
        labels = labels[shuffle_idx]

        unique, counts = np.unique(labels, return_counts=True)
        dominant = unique[np.argmax(counts)]

        return StreamChunk(
            chunk_id=chunk_id,
            X=X_chunk,
            labels=labels,
            is_drift_point=is_drift,
            is_novelty_point=is_novelty,
            dominant_class=str(dominant),
        )

    def stream(self, n_chunks: int = 30) -> Generator[StreamChunk, None, None]:
        """
        Yield stream chunks one at a time.

        Parameters
        ----------
        n_chunks : int
            Total number of chunks to generate.

        Yields
        ------
        StreamChunk
        """
        for chunk_id in range(1, n_chunks + 1):
            yield self._build_chunk(chunk_id)
