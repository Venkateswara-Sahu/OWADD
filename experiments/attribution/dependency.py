"""Window-only dependency localization baselines."""

from time import perf_counter

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import train_test_split

from experiments.attribution.base import AttributionScores, validate_inputs

MIN_ROWS = 2


def _windows(reference, current, feature_types):
    left, right = validate_inputs(reference, current, feature_types)
    if (
        min(len(left), len(right)) < MIN_ROWS
        or left.shape[1] < MIN_ROWS
        or any(kind != "numerical" for kind in feature_types)
        or not np.isfinite(left).all()
        or not np.isfinite(right).all()
    ):
        raise ValueError(
            "finite numerical windows with at least two rows/features required"
        )
    return left, right


class CorrelationChangeAttributor:
    name = "max_correlation_change"

    def rank(self, reference, current, feature_types):
        started = perf_counter()
        left, right = _windows(reference, current, feature_types)
        if np.any(left.std(0) == 0) or np.any(right.std(0) == 0):
            raise ValueError("constant columns have undefined Pearson correlation")
        difference = np.abs(
            np.corrcoef(right, rowvar=False) - np.corrcoef(left, rowvar=False)
        )
        np.fill_diagonal(difference, 0)
        return AttributionScores(
            self.name, difference.max(axis=1), (perf_counter() - started) * 1000, {}
        )


class NonlinearPermutationAttributor:
    name = "nonlinear_permutation"

    def __init__(self, seed=0):
        self.seed = seed

    def rank(self, reference, current, feature_types):
        started = perf_counter()
        left, right = _windows(reference, current, feature_types)
        features = np.vstack([left, right])
        labels = np.r_[np.zeros(len(left), dtype=int), np.ones(len(right), dtype=int)]
        train_x, test_x, train_y, test_y = train_test_split(
            features, labels, test_size=0.3, stratify=labels, random_state=self.seed
        )
        model = HistGradientBoostingClassifier(
            max_iter=100,
            learning_rate=0.1,
            max_leaf_nodes=7,
            max_depth=3,
            min_samples_leaf=10,
            l2_regularization=1,
            early_stopping=False,
            random_state=self.seed,
        ).fit(train_x, train_y)
        accuracy = balanced_accuracy_score(test_y, model.predict(test_x))
        importance = permutation_importance(
            model,
            test_x,
            test_y,
            scoring="balanced_accuracy",
            n_repeats=5,
            random_state=self.seed,
            n_jobs=1,
        )
        return AttributionScores(
            self.name,
            np.maximum(importance.importances_mean, 0),
            (perf_counter() - started) * 1000,
            {
                "held_out_balanced_accuracy": float(accuracy),
                "signed_importance": importance.importances_mean.tolist(),
                "importance_std": importance.importances_std.tolist(),
                "train_rows": len(train_y),
                "held_out_rows": len(test_y),
            },
        )
