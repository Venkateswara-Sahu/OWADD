from __future__ import annotations

from time import perf_counter_ns

import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from experiments.attribution.base import AttributionScores, validate_inputs


class DiscriminativeAttributor:
    name = "discriminative_permutation"

    def __init__(self, seed: int = 0, repeats: int = 5) -> None:
        self.seed = seed
        self.repeats = repeats

    def rank(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        feature_types: tuple[str, ...],
    ) -> AttributionScores:
        left, right = validate_inputs(reference, current, feature_types)
        started = perf_counter_ns()
        features = np.vstack([left, right])
        labels = np.concatenate(
            [np.zeros(len(left), dtype=int), np.ones(len(right), dtype=int)]
        )
        train_x, test_x, train_y, test_y = train_test_split(
            features,
            labels,
            test_size=0.3,
            stratify=labels,
            random_state=self.seed,
        )
        model = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        random_state=self.seed,
                    ),
                ),
            ]
        )
        model.fit(train_x, train_y)
        accuracy = balanced_accuracy_score(test_y, model.predict(test_x))
        importance = permutation_importance(
            model,
            test_x,
            test_y,
            scoring="balanced_accuracy",
            n_repeats=self.repeats,
            random_state=self.seed,
        )
        elapsed_ms = (perf_counter_ns() - started) / 1_000_000
        return AttributionScores(
            method=self.name,
            scores=np.maximum(importance.importances_mean, 0.0),
            elapsed_ms=elapsed_ms,
            metadata={"held_out_balanced_accuracy": float(accuracy)},
        )
