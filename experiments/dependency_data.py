"""Paired Gaussian dependence changes with fixed population marginals."""

import numpy as np

BACKGROUNDS = (0.0, 0.3)
WINDOW_SIZES = (200, 800)
STRENGTHS = (0.0, 0.2, 0.6)
N_FEATURES = 20


def pair_root(rho):
    """Symmetric square root of [[1,rho],[rho,1]]."""
    if not np.isfinite(rho) or abs(rho) >= 1:
        raise ValueError("correlation must be finite and strictly inside (-1,1)")
    a = (np.sqrt(1 + rho) + np.sqrt(1 - rho)) / 2
    b = (np.sqrt(1 + rho) - np.sqrt(1 - rho)) / 2
    return np.array([[a, b], [b, a]])


def case_name(background, window_size, strength):
    return f"background_{background:g}_n_{window_size}_delta_{strength:g}"


def make_dependency_cases(seed):
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(5)]
    raw_train = streams[0].normal(size=(2000, N_FEATURES))
    raw_reference = streams[1].normal(size=(max(WINDOW_SIZES), N_FEATURES))
    raw_current = streams[2].normal(size=(max(WINDOW_SIZES), N_FEATURES))
    pairs = streams[3].permutation(N_FEATURES).reshape(-1, 2)
    target = tuple(int(i) for i in pairs[0])
    tie_order = streams[4].permutation(N_FEATURES)
    cases = []
    for background in BACKGROUNDS:
        transformed = []
        for raw in (raw_train, raw_reference, raw_current):
            data = raw.copy()
            for pair in pairs:
                data[:, pair] = raw[:, pair] @ pair_root(background)
            transformed.append(data)
        train, reference, stable = transformed
        for size in WINDOW_SIZES:
            for strength in STRENGTHS:
                current = stable[:size].copy()
                current[:, target] = raw_current[:size, target] @ pair_root(
                    background + strength
                )
                cases.append(
                    {
                        "case": case_name(background, size, strength),
                        "background": background,
                        "window_size": size,
                        "strength": strength,
                        "train": train,
                        "reference": reference[:size],
                        "current": current,
                        "truth": target if strength else (),
                        "tie_order": tie_order,
                        "pairs": pairs.tolist(),
                    }
                )
    return cases
