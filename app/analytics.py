from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Literal

from app.models import OwletReading

Bucket = Literal["hour", "day"]

SLEEP_STATE_LABELS = {
    "0": "inactive",
    "1": "awake",
    "8": "light sleep",
    "15": "deep sleep",
}
SLEEP_STATES = {"8", "15"}
AWAKE_STATE = "1"
MAX_DURATION_GAP_SECONDS = 30 * 60
LOW_OXYGEN_SAMPLE_THRESHOLD = 92
BREATHING_TREND_THRESHOLD = 0.5


def sleep_state_label(value: str | int | float | None) -> str:
    if value is None:
        return "unknown"
    key = str(value)
    return SLEEP_STATE_LABELS.get(key, f"state {key}")


def build_rollups(readings: list[OwletReading], bucket: Bucket = "hour") -> list[dict[str, Any]]:
    groups: dict[datetime, list[tuple[OwletReading, int]]] = defaultdict(list)
    for index, reading in enumerate(readings):
        groups[_bucket_start(reading.recorded_at, bucket)].append(
            (reading, _duration_to_next(readings, index))
        )

    rollups = []
    for bucket_start in sorted(groups):
        pairs = groups[bucket_start]
        rows = [pair[0] for pair in pairs]
        durations = [pair[1] for pair in pairs]
        sleep_seconds = sum(
            duration
            for reading, duration in pairs
            if _normalized_sleep_state(reading) in SLEEP_STATES
        )
        awake_seconds = sum(
            duration
            for reading, duration in pairs
            if _normalized_sleep_state(reading) == AWAKE_STATE
        )
        light_seconds = sum(
            duration for reading, duration in pairs if _normalized_sleep_state(reading) == "8"
        )
        deep_seconds = sum(
            duration for reading, duration in pairs if _normalized_sleep_state(reading) == "15"
        )
        rollups.append(
            {
                "bucket": bucket,
                "bucket_start": bucket_start.isoformat(),
                "bucket_label": _bucket_label(bucket_start, bucket),
                "samples": len(rows),
                "avg_heart_rate": _avg([row.heart_rate for row in rows]),
                "avg_oxygen_saturation": _avg([row.oxygen_saturation for row in rows]),
                "min_oxygen_saturation": _min([row.oxygen_saturation for row in rows]),
                "avg_movement": _avg([row.movement for row in rows]),
                "sleep_seconds": sleep_seconds,
                "light_sleep_seconds": light_seconds,
                "deep_sleep_seconds": deep_seconds,
                "awake_seconds": awake_seconds,
                "duration_seconds": sum(durations),
            }
        )
    return rollups


def build_insights(readings: list[OwletReading]) -> dict[str, Any]:
    if not readings:
        return {
            "count": 0,
            "latest": None,
            "breathing": _empty_breathing(),
            "sleep": _empty_sleep(),
        }

    latest = readings[-1]
    oxygen_values = [row.oxygen_saturation for row in readings if row.oxygen_saturation is not None]
    midpoint = max(1, len(oxygen_values) // 2)
    previous_avg = _avg(oxygen_values[:midpoint])
    recent_avg = _avg(oxygen_values[midpoint:]) if oxygen_values[midpoint:] else previous_avg
    delta = None if previous_avg is None or recent_avg is None else round(recent_avg - previous_avg, 2)
    direction = _breathing_direction(delta)

    sleep = _sleep_summary(readings)
    latest_dict = latest.model_dump(mode="json", exclude={"raw"})
    latest_dict["sleep_state_label"] = sleep_state_label(latest.sleep_state)

    return {
        "count": len(readings),
        "first_recorded_at": readings[0].recorded_at.isoformat(),
        "last_recorded_at": latest.recorded_at.isoformat(),
        "latest": latest_dict,
        "breathing": {
            "direction": direction,
            "delta_avg_oxygen": delta,
            "previous_avg_oxygen": previous_avg,
            "recent_avg_oxygen": recent_avg,
            "avg_oxygen_saturation": _avg(oxygen_values),
            "min_oxygen_saturation": _min(oxygen_values),
            "low_oxygen_samples": sum(1 for value in oxygen_values if value < LOW_OXYGEN_SAMPLE_THRESHOLD),
            "low_oxygen_threshold": LOW_OXYGEN_SAMPLE_THRESHOLD,
            "plain_language": _breathing_sentence(direction, delta),
        },
        "sleep": sleep,
    }


def _sleep_summary(readings: list[OwletReading]) -> dict[str, Any]:
    sleep_seconds = 0
    light_sleep_seconds = 0
    deep_sleep_seconds = 0
    awake_seconds = 0
    inactive_seconds = 0

    for index, reading in enumerate(readings):
        duration = _duration_to_next(readings, index)
        state = _normalized_sleep_state(reading)
        if state == "8":
            light_sleep_seconds += duration
            sleep_seconds += duration
        elif state == "15":
            deep_sleep_seconds += duration
            sleep_seconds += duration
        elif state == AWAKE_STATE:
            awake_seconds += duration
        elif state == "0":
            inactive_seconds += duration

    latest = readings[-1]
    return {
        "sleep_seconds": sleep_seconds,
        "light_sleep_seconds": light_sleep_seconds,
        "deep_sleep_seconds": deep_sleep_seconds,
        "awake_seconds": awake_seconds,
        "inactive_seconds": inactive_seconds,
        "sleep_hours": round(sleep_seconds / 3600, 2),
        "awake_hours": round(awake_seconds / 3600, 2),
        "sleep_state": latest.sleep_state,
        "sleep_state_label": sleep_state_label(latest.sleep_state),
    }


def _empty_breathing() -> dict[str, Any]:
    return {
        "direction": "unknown",
        "delta_avg_oxygen": None,
        "previous_avg_oxygen": None,
        "recent_avg_oxygen": None,
        "avg_oxygen_saturation": None,
        "min_oxygen_saturation": None,
        "low_oxygen_samples": 0,
        "low_oxygen_threshold": LOW_OXYGEN_SAMPLE_THRESHOLD,
        "plain_language": "Not enough data yet.",
    }


def _empty_sleep() -> dict[str, Any]:
    return {
        "sleep_seconds": 0,
        "light_sleep_seconds": 0,
        "deep_sleep_seconds": 0,
        "awake_seconds": 0,
        "inactive_seconds": 0,
        "sleep_hours": 0,
        "awake_hours": 0,
        "sleep_state": None,
        "sleep_state_label": "unknown",
    }


def _duration_to_next(readings: list[OwletReading], index: int) -> int:
    if index >= len(readings) - 1:
        return 0
    delta = readings[index + 1].recorded_at - readings[index].recorded_at
    seconds = int(delta.total_seconds())
    if seconds <= 0 or seconds > MAX_DURATION_GAP_SECONDS:
        return 0
    return seconds


def _bucket_start(dt: datetime, bucket: Bucket) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    if bucket == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    if bucket == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(f"Unsupported bucket: {bucket}")


def _bucket_label(dt: datetime, bucket: Bucket) -> str:
    if bucket == "hour":
        return f"{dt.strftime('%b')} {dt.day}, {_hour_label(dt)}"
    return f"{dt.strftime('%b')} {dt.day}"


def _hour_label(dt: datetime) -> str:
    hour = dt.hour % 12 or 12
    suffix = "AM" if dt.hour < 12 else "PM"
    return f"{hour} {suffix}"


def _normalized_sleep_state(reading: OwletReading) -> str | None:
    return None if reading.sleep_state is None else str(reading.sleep_state)


def _avg(values: list[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 2)


def _min(values: list[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return min(clean)


def _breathing_direction(delta: float | None) -> str:
    if delta is None:
        return "unknown"
    if delta > BREATHING_TREND_THRESHOLD:
        return "improving"
    if delta < -BREATHING_TREND_THRESHOLD:
        return "worsening"
    return "stable"


def _breathing_sentence(direction: str, delta: float | None) -> str:
    if direction == "improving":
        return f"Average oxygen is trending up by {delta} points in the recent half of this window."
    if direction == "worsening":
        return f"Average oxygen is trending down by {abs(delta or 0)} points in the recent half of this window."
    if direction == "stable":
        return "Average oxygen is roughly stable across this window."
    return "Not enough oxygen data yet."
