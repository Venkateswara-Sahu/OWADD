"""Sample-level novelty: label 1 and larger scores mean novel, not known."""

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


@dataclass(frozen=True)
class NoveltyEvaluation:
    n_samples: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float | None
    recall: float | None
    f1: float | None
    false_positive_rate: float | None
    auroc: float | None
    average_precision: float | None
    undefined_reasons: dict[str, str]


def evaluate_novelty(y_true, scores, threshold) -> NoveltyEvaluation:
    """Evaluate a supplied frozen threshold; never select it from evaluated labels.

    Prediction uses score >= threshold. Average precision is the noninterpolated
    PR summary, not trapezoidal PR area. Both ranking metrics are withheld for
    single-class populations by reporting policy.
    """
    labels, values = np.asarray(y_true), np.asarray(scores, dtype=float)
    if (
        labels.ndim != 1
        or values.ndim != 1
        or labels.shape != values.shape
        or not len(labels)
    ):
        raise ValueError("nonempty aligned one-dimensional arrays required")
    if not np.isin(labels, [0, 1]).all() or not np.isfinite(values).all():
        raise ValueError("binary labels and finite scores required")
    if np.ndim(threshold) != 0 or not np.isfinite(threshold):
        raise ValueError("finite scalar threshold required")
    truth, predicted = labels.astype(bool), values >= threshold
    tp = int(np.sum(truth & predicted))
    fp = int(np.sum(~truth & predicted))
    fn = int(np.sum(truth & ~predicted))
    tn = int(np.sum(~truth & ~predicted))
    reasons = {}

    def ratio(name, numerator, denominator, reason):
        if not denominator:
            reasons[name] = reason
            return None
        return numerator / denominator

    precision = ratio("precision", tp, tp + fp, "no predicted novel samples")
    recall = ratio("recall", tp, tp + fn, "no true novel samples")
    f1 = ratio("f1", 2 * tp, 2 * tp + fp + fn, "no true or predicted novel samples")
    fpr = ratio("false_positive_rate", fp, fp + tn, "no known samples")
    auroc = ap = None
    if len(np.unique(labels)) == 2:
        auroc = float(roc_auc_score(labels, values))
        ap = float(average_precision_score(labels, values))
    else:
        reasons.update(
            auroc="single-class population",
            average_precision="single-class population; unreported by policy",
        )
    return NoveltyEvaluation(
        len(labels), tp, fp, fn, tn, precision, recall, f1, fpr, auroc, ap, reasons
    )
