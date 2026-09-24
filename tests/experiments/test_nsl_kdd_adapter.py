# ruff: noqa: PLR2004
# Literal expected counts and SHA-256 length are deliberate fixture assertions.
import numpy as np
import pandas as pd

from experiments.datasets.nsl_kdd import fit_preprocessor


def test_validation_preparation_requires_no_test_frame():
    from experiments.datasets.nsl_kdd import prepare_frames

    train = pd.DataFrame(
        {"duration": range(60), "label": ["normal"] * 40 + ["attack"] * 20}
    )
    dataset = prepare_frames(train, None, seed=7)
    assert len(dataset.reference.X) > 0
    assert len(dataset.validation.X) > 0
    assert dataset.test.X.shape == (0, 1)
    assert dataset.test.row_ids == ()
    assert dataset.audit["test_loaded"] is False
    assert len(dataset.audit["preprocessing_sha256"]) == 64


def test_prepare_frames_keeps_duplicates_and_future_categories_out_of_training():
    from experiments.datasets.nsl_kdd import prepare_frames

    train = pd.DataFrame(
        {
            "protocol_type": ["tcp"] * 40,
            "duration": list(range(40)),
            "label": ["normal"] * 30 + ["attack"] * 10,
            "difficulty": [1] * 40,
        }
    )
    test = pd.DataFrame(
        {
            "protocol_type": ["tcp", "new"],
            "duration": [0, 1000],
            "label": ["normal", "novel"],
            "difficulty": [9, 1],
        }
    )
    dataset = prepare_frames(train, test, seed=7)
    ids = [
        set(part.row_ids)
        for part in (dataset.reference, dataset.validation, dataset.test)
    ]
    assert not ids[0] & ids[1]
    assert not ids[0] & ids[2]
    assert not ids[1] & ids[2]
    assert set(dataset.reference.y) == {"normal"}
    assert len(dataset.test.X) == 1
    assert dataset.audit["test_overlap_removed"] == 1
    assert not any("new" in name for name in dataset.feature_names)
    assert dataset.test.X[0, -1] > 1


def test_unseen_category_does_not_refit_encoder() -> None:
    training_frame = pd.DataFrame(
        {"protocol_type": ["tcp", "udp"], "duration": [0.0, 10.0]}
    )
    unseen = pd.DataFrame({"protocol_type": ["icmp"], "duration": [20.0]})
    preprocessor = fit_preprocessor(
        training_frame,
        categorical_columns=("protocol_type",),
        numerical_columns=("duration",),
    )
    encoder = preprocessor.named_transformers_["cat"]
    categories_before = tuple(encoder.categories_[0])

    transformed = preprocessor.transform(unseen)

    assert tuple(encoder.categories_[0]) == categories_before
    assert np.isfinite(transformed).all()
    assert transformed[0, -1] > 1.0


def test_stream_does_not_reuse_rows_and_records_returns():
    from experiments.datasets.base import DatasetSplit
    from experiments.datasets.nsl_kdd import build_network_stream

    split = DatasetSplit(
        np.arange(240).reshape(120, 2).astype(float),
        np.array(["normal"] * 80 + ["attack"] * 40),
        tuple(str(i) for i in range(120)),
    )
    chunks, manifest, row_ids = build_network_stream(
        split, attack_classes=("attack",), chunk_size=10, interval_chunks=2, seed=4
    )
    assert len(chunks) == 6
    assert len(row_ids) == len(set(row_ids)) == 60
    assert [e.start_chunk for e in manifest.events] == [3, 5]
    assert manifest.events[0].shifted_features == ()


def test_network_stream_rejects_insufficient_rows():
    import pytest

    from experiments.datasets.base import DatasetSplit
    from experiments.datasets.nsl_kdd import build_network_stream

    split = DatasetSplit(
        np.zeros((3, 2)), np.array(["normal", "normal", "attack"]), ("a", "b", "c")
    )
    with pytest.raises(ValueError, match="insufficient"):
        build_network_stream(
            split, attack_classes=("attack",), chunk_size=10, interval_chunks=2
        )
