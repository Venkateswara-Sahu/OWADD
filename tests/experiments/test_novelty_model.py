# ruff: noqa: PLR2004
"""Analytic score fixtures are software checks, not benchmark evidence."""

import numpy as np
import pytest
import torch
from sklearn.neighbors import KernelDensity

from vigil.core.autoencoder import Autoencoder


def zero_model():
    model = Autoencoder(1, hidden_dim=2)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    return model


def test_negative_log_density_preserves_extreme_tail_ranking():
    from experiments.novelty_model import FrozenNoveltyScorer

    model = zero_model()
    kde = KernelDensity(bandwidth=1.0).fit(np.zeros((2, 1)))
    scorer = FrozenNoveltyScorer(
        model, kde, preprocessing_id="fixture-scale", reference_id="fixture-ref"
    )
    # Zero reconstruction: MSE=x^2; standard normal -log pdf = MSE^2/2+c.
    scores = scorer(np.array([[0.0], [2.0], [10.0], [20.0]]))
    np.testing.assert_allclose(
        scores,
        [0.9189385332046727, 8.918938533204673, 5000.918938533205, 80000.9189385332],
        rtol=1e-12,
    )
    assert np.isfinite(scores).all()
    assert scores[3] > scores[2]  # Exponentiating either would underflow to zero.


def test_snapshot_identity_binds_weights_kde_and_preprocessing():
    from experiments.novelty_model import FrozenNoveltyScorer

    model = zero_model()
    kde = KernelDensity(bandwidth=1.0).fit(np.zeros((2, 1)))

    def snapshot(**kwargs):
        return FrozenNoveltyScorer(
            model,
            kde,
            preprocessing_id=kwargs.get("preprocessing_id", "scale-v1"),
            reference_id=kwargs.get("reference_id", "ref-v1"),
        )

    scorer = snapshot()
    original_id = scorer.model_id
    assert original_id == snapshot().model_id
    assert original_id != snapshot(preprocessing_id="scale-v2").model_id
    assert original_id != snapshot(reference_id="ref-v2").model_id
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.fill_(0.5)
    assert original_id != snapshot().model_id
    changed_weights_id = snapshot().model_id
    kde.fit(np.ones((2, 1)))
    assert changed_weights_id != snapshot().model_id
    # Refitting source objects must not mutate a previously frozen scorer.
    np.testing.assert_allclose(scorer([[0.0]]), [0.9189385332046727])
    assert scorer.model_id == original_id
    with pytest.raises(AttributeError):
        scorer.model_id = "changed"


def test_batched_scoring_preserves_order_and_rejects_invalid_inputs():
    from experiments.novelty_model import FrozenNoveltyScorer

    scorer = FrozenNoveltyScorer(
        zero_model(),
        KernelDensity(bandwidth=1.0).fit(np.zeros((2, 1))),
        preprocessing_id="scale",
        reference_id="ref",
        batch_size=2,
    )
    np.testing.assert_allclose(
        scorer([[2.0], [0.0], [1.0]]),
        [8.918938533204673, 0.9189385332046727, 1.4189385332046727],
    )
    for invalid in ([], [1.0], [[1.0, 2.0]], [[np.nan]], [[np.inf]], [[1e100]]):
        with pytest.raises(ValueError, match="features"):
            scorer(invalid)
    # Float32-representable input can still overflow the reconstruction MSE.
    with pytest.raises(ValueError, match="reconstruction"):
        scorer([[1e30]])


def test_constructor_rejects_unfitted_or_ambiguous_state():
    from experiments.novelty_model import FrozenNoveltyScorer

    fitted = KernelDensity().fit(np.zeros((2, 1)))
    for override in (
        {"preprocessing_id": ""},
        {"reference_id": ""},
        {"batch_size": 0},
        {"batch_size": True},
        {"batch_size": 1.5},
        {"kde": KernelDensity()},
        {"kde": KernelDensity().fit(np.zeros((2, 2)))},
    ):
        arguments = dict(
            autoencoder=zero_model(),
            kde=fitted,
            preprocessing_id="scale",
            reference_id="ref",
        )
        arguments.update(override)
        with pytest.raises(ValueError):
            FrozenNoveltyScorer(**arguments)


def test_fitted_vigil_connects_to_validation_freeze_without_adaptation(tmp_path):
    from experiments.datasets.base import DatasetSplit
    from experiments.novelty_model import FrozenNoveltyScorer
    from experiments.novelty_protocol import (
        evaluate_frozen,
        freeze_threshold,
        make_protocol,
        score_pool,
    )
    from vigil import Vigil

    def split(values, labels, prefix):
        return DatasetSplit(
            np.array(values)[:, None],
            np.array(labels),
            tuple(f"{prefix}-{i}" for i in range(len(values))),
        )

    protocol = make_protocol(
        split([0.0, 0.1, 0.2, 0.3], ["known"] * 4, "r"),
        split([0.05, 0.15, 2.0, 3.0], ["known"] * 2 + ["novel"] * 2, "v"),
        split([0.07, 0.17, 2.5, 3.5], ["known"] * 2 + ["novel"] * 2, "t"),
        known_classes={"known"},
        novel_classes={"novel"},
    )
    options = dict(
        preprocessing_id="fixture-identity-transform",
        reference_id=protocol.reference.identity,
        batch_size=2,
    )
    with pytest.raises(ValueError, match="fitted"):
        FrozenNoveltyScorer.from_vigil(Vigil(), **options)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(17)
        sentinel = Vigil(
            hidden_dim=2,
            initial_epochs=2,
            update_epochs=1,
            n_replications=2,
            sample_size=2,
        )
        sentinel.fit(protocol.reference.X, verbose=False)
    scorer = FrozenNoveltyScorer.from_vigil(sentinel, **options)
    validation = score_pool(protocol.validation, scorer)
    legacy = sentinel.detect(protocol.validation.X)
    np.testing.assert_allclose(
        np.exp(-validation.values), legacy.novelty_result.density_scores, rtol=1e-6
    )
    path = tmp_path / "freeze.json"
    freeze_threshold(
        path,
        protocol,
        validation,
        np.unique(validation.values),
        model_id=scorer.model_id,
    )
    before = scorer(protocol.test.X)
    sentinel.fit(np.ones((8, 1)) * 50, verbose=False)
    np.testing.assert_array_equal(scorer(protocol.test.X), before)
    result = evaluate_frozen(
        path, protocol, score_pool(protocol.test, scorer), model_id=scorer.model_id
    )
    assert result.n_samples == 4
