from __future__ import annotations

import numpy as np
import pytest

from experiments.streams.controlled import ControlledStreamBuilder, ShiftSpec


def test_abrupt_mean_shift_changes_only_declared_features() -> None:
    reference = np.zeros((400, 6), dtype=np.float64)
    spec = ShiftSpec(
        kind="mean",
        features=(1, 4),
        magnitude=2.0,
        event_chunk=3,
        n_chunks=6,
        chunk_size=40,
        seed=7,
    )

    chunks, manifest = ControlledStreamBuilder().build(reference, spec)

    before = np.vstack([chunk.X for chunk in chunks[:2]])
    after = np.vstack([chunk.X for chunk in chunks[2:]])
    np.testing.assert_allclose(
        after[:, [1, 4]].mean(axis=0) - before[:, [1, 4]].mean(axis=0),
        2.0,
        atol=0.2,
    )
    np.testing.assert_allclose(
        after[:, [0, 2, 3, 5]].mean(axis=0),
        before[:, [0, 2, 3, 5]].mean(axis=0),
        atol=0.2,
    )
    assert manifest.events[0].shifted_features == (1, 4)


def test_builder_is_deterministic_and_does_not_mutate_reference() -> None:
    reference = np.arange(1_200, dtype=np.float64).reshape(200, 6)
    original = reference.copy()
    spec = ShiftSpec(
        kind="noise",
        features=(2,),
        magnitude=0.5,
        event_chunk=2,
        n_chunks=4,
        chunk_size=25,
        seed=11,
    )

    first, _ = ControlledStreamBuilder().build(reference, spec)
    second, _ = ControlledStreamBuilder().build(reference, spec)
    different, _ = ControlledStreamBuilder().build(
        reference, dataclass_replace(spec, seed=12)
    )

    assert all(np.array_equal(a.X, b.X) for a, b in zip(first, second))
    assert any(not np.array_equal(a.X, b.X) for a, b in zip(first, different))
    np.testing.assert_array_equal(reference, original)


def test_gradual_shift_reaches_full_magnitude() -> None:
    reference = np.zeros((300, 4), dtype=np.float64)
    spec = ShiftSpec(
        kind="mean",
        pattern="gradual",
        features=(0,),
        magnitude=3.0,
        event_chunk=2,
        end_chunk=4,
        n_chunks=5,
        chunk_size=50,
        seed=3,
    )

    chunks, _ = ControlledStreamBuilder().build(reference, spec)

    assert chunks[1].X[:, 0].mean() == pytest.approx(1.0)
    assert chunks[2].X[:, 0].mean() == pytest.approx(2.0)
    assert chunks[3].X[:, 0].mean() == pytest.approx(3.0)


def test_recurring_shift_records_start_and_return_events() -> None:
    reference = np.zeros((300, 3), dtype=np.float64)
    spec = ShiftSpec(
        kind="mean",
        pattern="recurring",
        features=(1,),
        magnitude=1.5,
        event_chunk=2,
        end_chunk=3,
        n_chunks=5,
        chunk_size=30,
        seed=4,
    )

    chunks, manifest = ControlledStreamBuilder().build(reference, spec)

    assert chunks[1].X[:, 1].mean() == pytest.approx(1.5)
    assert chunks[2].X[:, 1].mean() == pytest.approx(1.5)
    assert chunks[3].X[:, 1].mean() == pytest.approx(0.0)
    assert [event.kind for event in manifest.events] == ["mean", "return"]
    assert [event.start_chunk for event in manifest.events] == [2, 4]


def test_variance_shift_rejects_non_positive_multiplier() -> None:
    with pytest.raises(ValueError, match="variance magnitude must be positive"):
        ShiftSpec(
            kind="variance",
            features=(0,),
            magnitude=0.0,
            event_chunk=2,
            n_chunks=4,
            chunk_size=20,
            seed=1,
        )


def test_categorical_shift_uses_declared_probabilities() -> None:
    reference = np.zeros((500, 2), dtype=np.float64)
    reference[:, 0] = np.tile([0, 1], 250)
    spec = ShiftSpec(
        kind="categorical",
        features=(0,),
        magnitude=1.0,
        event_chunk=2,
        n_chunks=3,
        chunk_size=200,
        seed=9,
        category_probabilities={0: {0.0: 0.1, 1.0: 0.9}},
    )

    chunks, _ = ControlledStreamBuilder().build(reference, spec)

    assert set(np.unique(chunks[1].X[:, 0])) <= {0.0, 1.0}
    assert chunks[1].X[:, 0].mean() == pytest.approx(0.9, abs=0.08)


@pytest.mark.parametrize(
    "spec, message",
    [
        (
            ShiftSpec(
                kind="mean",
                features=(3,),
                magnitude=1.0,
                event_chunk=2,
                n_chunks=3,
                chunk_size=20,
                seed=1,
            ),
            "feature index",
        ),
        (
            ShiftSpec(
                kind="mean",
                pattern="gradual",
                features=(0,),
                magnitude=1.0,
                event_chunk=3,
                end_chunk=2,
                n_chunks=4,
                chunk_size=20,
                seed=1,
            ),
            "end_chunk",
        ),
    ],
)
def test_builder_rejects_invalid_stream_specs(spec: ShiftSpec, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ControlledStreamBuilder().build(np.zeros((100, 3)), spec)


def test_shift_count_cannot_exceed_feature_count() -> None:
    spec = ShiftSpec(
        kind="mean",
        features=(0, 1, 2, 3),
        magnitude=1.0,
        event_chunk=2,
        n_chunks=3,
        chunk_size=20,
        seed=1,
    )

    with pytest.raises(ValueError, match="feature index"):
        ControlledStreamBuilder().build(np.zeros((100, 3)), spec)


def dataclass_replace(spec: ShiftSpec, **changes: object) -> ShiftSpec:
    values = {
        name: getattr(spec, name)
        for name in spec.__dataclass_fields__
    }
    values.update(changes)
    return ShiftSpec(**values)
