from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from experiments.streams.types import ChangeEvent


@dataclass(frozen=True)
class EventEvaluation:
    true_events: int
    matched_events: int
    missed_events: int
    false_alarms: int
    duplicate_alerts: int
    event_precision: float | None
    event_recall: float | None
    event_f1: float | None
    delays: tuple[int, ...]
    mean_delay: float | None
    median_delay: float | None
    false_alarms_per_10k: float | None
    average_stable_run_length: float | None


def match_events(
    events: Sequence[ChangeEvent],
    alerts: Sequence[int],
    tolerance_chunks: int,
    *,
    total_samples: int | None = None,
    allow_overlaps: bool = False,
) -> EventEvaluation:
    """Match alerts to change events once, in chronological order."""

    if tolerance_chunks < 0:
        raise ValueError("tolerance_chunks must be non-negative")
    if any(alert < 0 for alert in alerts):
        raise ValueError("alert indices must be non-negative")
    ordered_events = sorted(events, key=lambda item: (item.start_chunk, item.event_id))
    if not allow_overlaps:
        for previous, current in zip(ordered_events, ordered_events[1:]):
            if current.start_chunk <= previous.start_chunk + tolerance_chunks:
                raise ValueError("overlapping event windows are ambiguous")

    ordered_alerts = sorted(enumerate(alerts), key=lambda pair: (pair[1], pair[0]))
    unused = {original_index for original_index, _ in ordered_alerts}
    matched_windows: list[tuple[int, int]] = []
    delays: list[int] = []
    for change in ordered_events:
        window_end = change.start_chunk + tolerance_chunks
        candidate = next(
            (
                (original_index, alert)
                for original_index, alert in ordered_alerts
                if original_index in unused
                and change.start_chunk <= alert <= window_end
            ),
            None,
        )
        if candidate is not None:
            original_index, alert = candidate
            unused.remove(original_index)
            delays.append(alert - change.start_chunk)
            matched_windows.append((change.start_chunk, window_end))

    duplicates = 0
    false_alarms = 0
    for original_index, alert in ordered_alerts:
        if original_index not in unused:
            continue
        if any(start <= alert <= end for start, end in matched_windows):
            duplicates += 1
        else:
            false_alarms += 1

    matched = len(delays)
    missed = len(ordered_events) - matched
    total_alert_penalties = matched + false_alarms + duplicates
    precision = matched / total_alert_penalties if total_alert_penalties else None
    recall = matched / len(ordered_events) if ordered_events else None
    denominator = len(ordered_events) + total_alert_penalties
    f1 = 2 * matched / denominator if denominator else None
    false_alarm_rate = (
        false_alarms / total_samples * 10_000
        if total_samples is not None and total_samples > 0
        else None
    )
    stable_run = (
        total_samples / (false_alarms + 1)
        if total_samples is not None and total_samples > 0
        else None
    )
    return EventEvaluation(
        true_events=len(ordered_events),
        matched_events=matched,
        missed_events=missed,
        false_alarms=false_alarms,
        duplicate_alerts=duplicates,
        event_precision=precision,
        event_recall=recall,
        event_f1=f1,
        delays=tuple(delays),
        mean_delay=float(np.mean(delays)) if delays else None,
        median_delay=float(np.median(delays)) if delays else None,
        false_alarms_per_10k=false_alarm_rate,
        average_stable_run_length=stable_run,
    )
