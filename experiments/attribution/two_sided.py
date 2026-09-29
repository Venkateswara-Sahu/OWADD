"""Experimental two-sided reconstruction-error rankings; not drift tests."""

import numpy as np
import torch

REFERENCE_SD_FLOOR = 1e-12
MIN_REFERENCE_ROWS = 2
WINDOW_NDIM = 2


def two_sided_scores(model, reference, current):
    """Rank absolute mean-error changes, optionally scaled by reference SD.

    Scores are not probabilities or causal contributions. Retain signed changes
    and the reference-only denominator so every ranking is auditable.
    """
    reference, current = np.asarray(reference), np.asarray(current)
    if (
        reference.ndim != WINDOW_NDIM
        or current.ndim != WINDOW_NDIM
        or reference.shape[0] < MIN_REFERENCE_ROWS
        or current.shape[0] == 0
        or reference.shape[1] == 0
        or reference.shape[1] != current.shape[1]
        or not np.isfinite(reference).all()
        or not np.isfinite(current).all()
    ):
        raise ValueError(
            "finite matching windows and at least two reference rows required"
        )
    modes = [(module, module.training) for module in model.modules()]
    model.eval()
    try:
        with torch.no_grad():
            left = torch.as_tensor(reference, dtype=torch.float32)
            right = torch.as_tensor(current, dtype=torch.float32)
            ref_errors = (left - model(left)).square()
            cur_errors = (right - model(right)).square()
            delta = (cur_errors.mean(0) - ref_errors.mean(0)).cpu().numpy()
            reference_sd = ref_errors.double().std(0, correction=1).cpu().numpy()
    finally:
        for module, training in modes:
            module.training = training
    absolute = np.abs(delta.astype(float))
    denominator = np.maximum(reference_sd, REFERENCE_SD_FLOOR)
    return {
        "vigil_absolute_delta": absolute,
        "vigil_standardized_absolute_delta": absolute / denominator,
    }, {
        "signed_delta": delta.tolist(),
        "reference_sd": reference_sd.tolist(),
        "sd_floor": REFERENCE_SD_FLOOR,
    }
