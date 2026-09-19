from __future__ import annotations

import numpy as np
import pytest

from experiments.detection.adapters import (
    MMDDetectorAdapter,
    RiverScalarDetectorAdapter,
)
from experiments.metrics.events import match_events
from experiments.streams.types import ChangeEvent


def event(start: int, event_id: str = "e1") -> ChangeEvent:
    return ChangeEvent(event_id, start, start, "mean", (2,), 1.0)


def test_duplicate_alerts_do_not_inflate_true_positives() -> None:
    result = match_events([event(10)], alerts=[10, 11, 12], tolerance_chunks=2)

    assert result.true_events == 1
    assert result.matched_events == 1
    assert result.duplicate_alerts == 2
    assert result.event_recall == 1.0


def test_alert_before_event_is_false_alarm() -> None:
    result = match_events([event(10)], alerts=[9], tolerance_chunks=2)

    assert result.false_alarms == 1
    assert result.missed_events == 1


def test_boundaries_and_unsorted_alerts_are_handled() -> None:
    result = match_events(
        [event(5, "a"), event(10, "b")],
        alerts=[12, 5],
        tolerance_chunks=2,
        total_samples=2_000,
    )

    assert result.matched_events == 2
    assert result.delays == (0, 2)
    assert result.false_alarms_per_10k == 0.0


def test_no_alerts_and_no_events_have_explicit_undefined_metrics() -> None:
    no_alerts = match_events([event(3)], [], tolerance_chunks=1)
    assert no_alerts.event_precision is None
    assert no_alerts.event_recall == 0.0

    no_events = match_events([], [], tolerance_chunks=1)
    assert no_events.event_precision is None
    assert no_events.event_recall is None


def test_overlapping_windows_are_rejected_by_default() -> None:
    with pytest.raises(ValueError, match="overlapping event windows"):
        match_events([event(5, "a"), event(6, "b")], [], tolerance_chunks=2)

    result = match_events(
        [event(5, "a"), event(6, "b")],
        [5, 6],
        tolerance_chunks=2,
        allow_overlaps=True,
    )
    assert result.matched_events == 2


def test_negative_alert_indices_are_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        match_events([event(2)], [-1], tolerance_chunks=1)


def test_supervised_scalar_adapter_requires_labels() -> None:
    adapter = RiverScalarDetectorAdapter.page_hinkley(uses_labels=True)

    with pytest.raises(ValueError, match="labels are required"):
        adapter.update(np.zeros((20, 3)))
    assert adapter.metadata["uses_labels"] is True


def test_unsupervised_mmd_adapter_handles_constant_chunks() -> None:
    adapter = MMDDetectorAdapter(threshold=0.1)

    assert adapter.update(np.zeros((20, 3))) == []
    assert adapter.update(np.zeros((20, 3))) == []
    assert adapter.metadata["uses_labels"] is False
