import pytest


def test_sample_metrics_use_scores_and_individual_ground_truth():
    from experiments.metrics.novelty import evaluate_novelty

    result = evaluate_novelty([0, 1, 0, 1, 0, 1], [0.1, 0.9, 0.8, 0.7, 0.2, 0.3], 0.5)
    assert result.precision == pytest.approx(2 / 3)
    assert result.recall == pytest.approx(2 / 3)
    assert result.f1 == pytest.approx(2 / 3)
    assert result.false_positive_rate == pytest.approx(1 / 3)
    assert result.auroc == pytest.approx(7 / 9)
    assert result.average_precision == pytest.approx((1 + 2 / 3 + 3 / 4) / 3)


@pytest.mark.parametrize("labels", [[0, 0], [1, 1]])
def test_single_class_ranking_metrics_are_explicitly_unreported(labels):
    from experiments.metrics.novelty import evaluate_novelty

    result = evaluate_novelty(labels, [0.1, 0.9], 0.5)
    assert result.auroc is None
    assert result.average_precision is None
    assert "auroc" in result.undefined_reasons
    assert "average_precision" in result.undefined_reasons


@pytest.mark.parametrize(
    "labels,scores,threshold",
    [
        ([], [], 0.5),
        ([0, 2], [0.1, 0.9], 0.5),
        ([0], [0.1, 0.9], 0.5),
        ([0, 1], [0.1, float("nan")], 0.5),
        ([0, 1], [0.1, 0.9], float("inf")),
    ],
)
def test_invalid_novelty_inputs_are_rejected(labels, scores, threshold):
    from experiments.metrics.novelty import evaluate_novelty

    with pytest.raises(ValueError):
        evaluate_novelty(labels, scores, threshold)


def test_ties_are_novel_and_zero_predictions_are_not_fake_perfect_precision():
    from experiments.metrics.novelty import evaluate_novelty

    assert evaluate_novelty([0, 1], [0.1, 0.5], 0.5).recall == 1
    result = evaluate_novelty([0, 1], [0.1, 0.2], 0.5)
    assert result.precision is None
    assert result.recall == result.f1 == 0


def test_score_sidecar_roundtrip_rejects_tampering_and_overwrite(tmp_path):
    from experiments.novelty_scores import save_scores, load_scores
    import numpy as np

    path = tmp_path / "scores.npz"
    receipt = save_scores(path, [0, 1], [0.2, 0.8])
    labels, scores = load_scores(path, receipt)
    np.testing.assert_array_equal(labels, [0, 1])
    np.testing.assert_allclose(scores, [0.2, 0.8])
    with pytest.raises(FileExistsError):
        save_scores(path, [0, 1], [0.3, 0.7])
    with pytest.raises(ValueError, match="length"):
        load_scores(path, {**receipt, "n_samples": 3})
    with path.open("ab") as file:
        file.write(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        load_scores(path, receipt)
