from __future__ import annotations

import numpy as np


def bootstrap_mean_ci(
    values: np.ndarray,
    *,
    confidence: float = 0.95,
    n_resamples: int = 2_000,
    seed: int = 0,
) -> tuple[float, float]:
    """Return a deterministic percentile bootstrap interval for the mean."""

    samples = np.asarray(values, dtype=float)
    if samples.ndim != 1 or samples.size == 0:
        raise ValueError("values must be a non-empty one-dimensional array")
    if not np.isfinite(samples).all():
        raise ValueError("values must be finite")
    if samples.size == 1:
        value = float(samples[0])
        return value, value
    rng = np.random.default_rng(seed)
    draws = rng.choice(samples, size=(n_resamples, samples.size), replace=True)
    means = draws.mean(axis=1)
    alpha = (1.0 - confidence) / 2
    return (
        float(np.quantile(means, alpha)),
        float(np.quantile(means, 1.0 - alpha)),
    )


def paired_effect_size(reference: np.ndarray, candidate: np.ndarray) -> float:
    """Return paired Cohen's dz for candidate minus reference."""

    left = np.asarray(reference, dtype=float)
    right = np.asarray(candidate, dtype=float)
    if left.shape != right.shape or left.ndim != 1:
        raise ValueError("paired arrays must be one-dimensional with equal shape")
    differences = right - left
    if differences.size < 2:
        return 0.0
    deviation = differences.std(ddof=1)
    if deviation == 0:
        return 0.0 if differences.mean() == 0 else float(np.sign(differences.mean()) * np.inf)
    return float(differences.mean() / deviation)
