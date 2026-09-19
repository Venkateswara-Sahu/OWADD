from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from river.drift import ADWIN, KSWIN, PageHinkley
from scipy.spatial.distance import cdist
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class Alert:
    chunk_id: int
    score: float
    metadata: dict[str, object]


class VigilDetectorAdapter:
    def __init__(self, vigil: object) -> None:
        self.vigil = vigil
        self.chunk_id = 0
        self.metadata = {"uses_labels": False, "method": "vigil"}

    def update(
        self, X: np.ndarray, labels: np.ndarray | None = None
    ) -> list[Alert]:
        self.chunk_id += 1
        result = self.vigil.detect(X)
        if not result.drift_detected:
            return []
        return [Alert(self.chunk_id, result.drift_severity, self.metadata.copy())]


class RiverScalarDetectorAdapter:
    def __init__(self, detector: object, *, uses_labels: bool, method: str) -> None:
        self.detector = detector
        self.chunk_id = 0
        self.metadata = {"uses_labels": uses_labels, "method": method}

    @classmethod
    def adwin(cls, *, uses_labels: bool = False) -> RiverScalarDetectorAdapter:
        return cls(ADWIN(delta=0.002), uses_labels=uses_labels, method="adwin")

    @classmethod
    def kswin(cls, *, uses_labels: bool = False) -> RiverScalarDetectorAdapter:
        return cls(
            KSWIN(window_size=100, stat_size=30),
            uses_labels=uses_labels,
            method="kswin",
        )

    @classmethod
    def page_hinkley(
        cls, *, uses_labels: bool = False
    ) -> RiverScalarDetectorAdapter:
        return cls(
            PageHinkley(), uses_labels=uses_labels, method="page_hinkley"
        )

    def update(
        self, X: np.ndarray, labels: np.ndarray | None = None
    ) -> list[Alert]:
        self.chunk_id += 1
        if self.metadata["uses_labels"]:
            if labels is None:
                raise ValueError("labels are required by this supervised adapter")
            values = np.asarray(labels)
            if values.dtype.kind in {"U", "S", "O"}:
                signal = (values != "normal").astype(float)
            else:
                signal = values.astype(float)
        else:
            signal = np.asarray(X, dtype=float).mean(axis=1)
        detected = False
        for value in signal:
            self.detector.update(float(value))
            detected = bool(self.detector.drift_detected) or detected
        return (
            [Alert(self.chunk_id, 1.0, self.metadata.copy())]
            if detected
            else []
        )


class DiscriminativeDetectorAdapter:
    def __init__(self, threshold: float = 0.7, seed: int = 0) -> None:
        self.threshold = threshold
        self.seed = seed
        self.reference: np.ndarray | None = None
        self.chunk_id = 0
        self.metadata = {
            "uses_labels": False,
            "method": "discriminative_two_sample",
        }

    def update(
        self, X: np.ndarray, labels: np.ndarray | None = None
    ) -> list[Alert]:
        self.chunk_id += 1
        current = np.asarray(X, dtype=float)
        if self.reference is None:
            self.reference = current.copy()
            return []
        features = np.vstack([self.reference, current])
        targets = np.concatenate(
            [np.zeros(len(self.reference), dtype=int), np.ones(len(current), dtype=int)]
        )
        train_x, test_x, train_y, test_y = train_test_split(
            features,
            targets,
            test_size=0.3,
            stratify=targets,
            random_state=self.seed,
        )
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, random_state=self.seed),
        )
        model.fit(train_x, train_y)
        score = float(balanced_accuracy_score(test_y, model.predict(test_x)))
        return (
            [Alert(self.chunk_id, score, self.metadata.copy())]
            if score >= self.threshold
            else []
        )


class MMDDetectorAdapter:
    def __init__(self, threshold: float = 0.1) -> None:
        self.threshold = threshold
        self.reference: np.ndarray | None = None
        self.chunk_id = 0
        self.metadata = {"uses_labels": False, "method": "rbf_mmd"}

    def update(
        self, X: np.ndarray, labels: np.ndarray | None = None
    ) -> list[Alert]:
        self.chunk_id += 1
        current = np.asarray(X, dtype=float)
        if self.reference is None:
            self.reference = current.copy()
            return []
        score = self._mmd(self.reference, current)
        return (
            [Alert(self.chunk_id, score, self.metadata.copy())]
            if score >= self.threshold
            else []
        )

    @staticmethod
    def _mmd(reference: np.ndarray, current: np.ndarray) -> float:
        combined = np.vstack([reference, current])
        squared = cdist(combined, combined, metric="sqeuclidean")
        positive = squared[squared > 0]
        bandwidth = float(np.median(positive)) if positive.size else 1.0
        gamma = 1.0 / max(2.0 * bandwidth, np.finfo(float).eps)
        xx = np.exp(-gamma * cdist(reference, reference, "sqeuclidean"))
        yy = np.exp(-gamma * cdist(current, current, "sqeuclidean"))
        xy = np.exp(-gamma * cdist(reference, current, "sqeuclidean"))
        return float(max(xx.mean() + yy.mean() - 2 * xy.mean(), 0.0))
