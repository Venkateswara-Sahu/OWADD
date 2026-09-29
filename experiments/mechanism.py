"""Frozen trained/untrained/input attribution controls."""

from copy import deepcopy
from hashlib import sha256

import numpy as np
import torch

from experiments.attribution.dependency import CorrelationChangeAttributor
from experiments.attribution.statistical import KSAttributor
from experiments.attribution.two_sided import two_sided_scores
from vigil.attribution import DriftAttributor
from vigil.core.autoencoder import Autoencoder, train_autoencoder


def model_hash(model):
    return sha256(
        b"".join(
            name.encode() + tensor.detach().numpy().tobytes()
            for name, tensor in model.state_dict().items()
        )
    ).hexdigest()


def fit_pair(train, seed, epochs):
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        original = Autoencoder(train.shape[1], hidden_dim=10)
        trained = deepcopy(original)
        initial_hash = model_hash(original)
        train_autoencoder(trained, train, epochs=epochs)
    losses = []
    for model in (original, trained):
        model.eval()
        with torch.no_grad():
            tensor = torch.as_tensor(train, dtype=torch.float32)
            losses.append(float((tensor - model(tensor)).square().mean()))
    return (
        original,
        trained,
        {
            "initial_sha256": initial_hash,
            "trained_sha256": model_hash(trained),
            "initial_loss": losses[0],
            "trained_loss": losses[1],
        },
    )


def score_windows(original, trained, reference, current):
    scores, details = {}, {}
    for prefix, model in (("untrained", original), ("trained", trained)):
        public = DriftAttributor().attribute(model, reference, current)
        variants, diagnostics = two_sided_scores(model, reference, current)
        scores[prefix + "_positive"] = public.feature_contributions
        scores[prefix + "_absolute"] = variants["vigil_absolute_delta"]
        scores[prefix + "_standardized"] = variants["vigil_standardized_absolute_delta"]
        details[prefix] = diagnostics
    input_delta = np.square(current.astype(float)).mean(0) - np.square(
        reference.astype(float)
    ).mean(0)
    scores["squared_input_change"] = np.abs(input_delta)
    details["input_signed_delta"] = input_delta.tolist()
    kinds = ("numerical",) * reference.shape[1]
    scores["kolmogorov_smirnov"] = KSAttributor().rank(reference, current, kinds).scores
    supported = bool(np.all(reference.std(0) > 0) and np.all(current.std(0) > 0))
    details["correlation_supported"] = supported
    scores["max_correlation_change"] = (
        CorrelationChangeAttributor().rank(reference, current, kinds).scores
        if supported
        else np.zeros(reference.shape[1])
    )
    return scores, details
