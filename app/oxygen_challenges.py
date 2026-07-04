from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.analytics import (
    AWAKE_STATE,
    LOW_OXYGEN_SAMPLE_THRESHOLD,
    MAX_DURATION_GAP_SECONDS,
    SLEEP_STATES,
)
from app.models import OwletReading
from app.quality import is_offline_reading

CRITICAL_OXYGEN_SAMPLE_THRESHOLD = 88


def parse_time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def serialize_time(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    return parse_time(value).isoformat()


def reading_in_period(
    reading: OwletReading,
    start: datetime,
    end: datetime,
    *,
    include_end: bool = True,
) -> bool:
    if include_end:
        return start <= reading.recorded_at <= end
    return start <= reading.recorded_at < end


def reading_in_any_period(reading: OwletReading, intervals: list[tuple[datetime, datetime]]) -> bool:
    return any(reading_in_period(reading, start, end) for start, end in intervals)


def period_summary(
    readings: list[OwletReading],
    start: datetime,
    end: datetime,
    *,
    include_end: bool = True,
) -> dict[str, Any]:
    period = [reading for reading in readings if reading_in_period(reading, start, end, include_end=include_end)]
    valid = [reading for reading in period if not is_offline_reading(reading)]
    oxygen_values = [reading.oxygen_saturation for reading in valid if reading.oxygen_saturation is not None]
    heart_values = [reading.heart_rate for reading in valid if reading.heart_rate is not None]
    durations = _state_durations(period)
    return {
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "duration_seconds": max(0, int((end - start).total_seconds())),
        "total_samples": len(period),
        "valid_samples": len(valid),
        "offline_samples": len(period) - len(valid),
        "avg_oxygen_saturation": _avg(oxygen_values),
        "min_oxygen_saturation": _min(oxygen_values),
        "avg_heart_rate": _avg(heart_values),
        "max_heart_rate": _max(heart_values),
        "low_oxygen_samples": sum(1 for value in oxygen_values if value < LOW_OXYGEN_SAMPLE_THRESHOLD),
        "critical_oxygen_samples": sum(1 for value in oxygen_values if value < CRITICAL_OXYGEN_SAMPLE_THRESHOLD),
        "sleep_seconds": durations["sleep_seconds"],
        "awake_seconds": durations["awake_seconds"],
        "inactive_seconds": durations["inactive_seconds"],
    }


def compare_summaries(current: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any]:
    return {
        "avg_oxygen_delta": _delta(current.get("avg_oxygen_saturation"), prior.get("avg_oxygen_saturation")),
        "min_oxygen_delta": _delta(current.get("min_oxygen_saturation"), prior.get("min_oxygen_saturation")),
        "avg_heart_rate_delta": _delta(current.get("avg_heart_rate"), prior.get("avg_heart_rate")),
        "low_oxygen_delta": (current.get("low_oxygen_samples") or 0) - (prior.get("low_oxygen_samples") or 0),
        "critical_oxygen_delta": (current.get("critical_oxygen_samples") or 0) - (prior.get("critical_oxygen_samples") or 0),
        "sleep_seconds_delta": (current.get("sleep_seconds") or 0) - (prior.get("sleep_seconds") or 0),
    }


def challenge_analysis(
    challenge: dict[str, Any],
    readings: list[OwletReading],
    fallback_end: datetime | None = None,
) -> dict[str, Any]:
    start = parse_time(challenge["start_time"])
    end = parse_time(challenge["end_time"]) if challenge.get("end_time") else fallback_end or _latest_time(readings) or datetime.now(start.tzinfo)
    if end < start:
        end = start
    duration = end - start
    prior_start = start - duration
    current = period_summary(readings, start, end)
    prior = period_summary(readings, prior_start, start, include_end=False)
    payload = {
        **challenge,
        "start_time": start.isoformat(),
        "end_time": end.isoformat() if challenge.get("end_time") else None,
        "effective_end_time": end.isoformat(),
        "active": not bool(challenge.get("end_time")),
        "summary": current,
        "prior_summary": prior,
        "comparison": compare_summaries(current, prior),
    }
    return payload


def _state_durations(readings: list[OwletReading]) -> dict[str, int]:
    sleep_seconds = 0
    awake_seconds = 0
    inactive_seconds = 0
    for index, reading in enumerate(readings):
        if is_offline_reading(reading):
            continue
        duration = _duration_to_next(readings, index)
        state = None if reading.sleep_state is None else str(reading.sleep_state)
        if state in SLEEP_STATES:
            sleep_seconds += duration
        elif state == AWAKE_STATE:
            awake_seconds += duration
        elif state == "0":
            inactive_seconds += duration
    return {
        "sleep_seconds": sleep_seconds,
        "awake_seconds": awake_seconds,
        "inactive_seconds": inactive_seconds,
    }


def _duration_to_next(readings: list[OwletReading], index: int) -> int:
    if index >= len(readings) - 1:
        return 0
    delta = readings[index + 1].recorded_at - readings[index].recorded_at
    seconds = int(delta.total_seconds())
    if seconds <= 0 or seconds > MAX_DURATION_GAP_SECONDS:
        return 0
    return seconds


def _latest_time(readings: list[OwletReading]) -> datetime | None:
    return readings[-1].recorded_at if readings else None


def _avg(values: Sequence[float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(sum(clean) / len(clean), 2) if clean else None


def _min(values: Sequence[float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return min(clean) if clean else None


def _max(values: Sequence[float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return max(clean) if clean else None


def _delta(current: float | int | None, prior: float | int | None) -> float | None:
    if current is None or prior is None:
        return None
    return round(float(current) - float(prior), 2)
