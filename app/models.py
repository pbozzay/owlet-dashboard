from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class OwletReading(BaseModel):
    device_serial: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    heart_rate: float | None = None
    oxygen_saturation: float | None = None
    battery: float | None = None
    movement: float | None = None
    sleep_state: str | None = None
    skin_temperature: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


def _first_present(raw: dict[str, Any], names: tuple[str, ...]) -> Any | None:
    for name in names:
        if name in raw and raw[name] not in (None, ""):
            return raw[name]
    return None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_datetime(value: Any) -> datetime:
    if value in (None, ""):
        return datetime.now(UTC)

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)

    text = str(value).strip()
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(UTC)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def normalize_reading(raw: dict[str, Any], device_serial: str) -> OwletReading:
    """Normalize pyowletapi / legacy Ayla property dictionaries into one schema."""

    recorded_at = _to_datetime(
        _first_present(raw, ("last_updated", "lastUpdated", "timestamp", "data_updated_at"))
    )
    battery = _first_present(raw, ("battery", "battery_percentage", "BATT_LEVEL"))
    sleep_state = _first_present(raw, ("sleep_state", "SLEEP_STATE"))

    return OwletReading(
        device_serial=device_serial,
        recorded_at=recorded_at,
        heart_rate=_to_float(_first_present(raw, ("heart_rate", "HEART_RATE", "hr"))),
        oxygen_saturation=_to_float(
            _first_present(raw, ("oxygen_saturation", "oxygen_level", "OXYGEN_LEVEL", "ox"))
        ),
        battery=_to_float(battery),
        movement=_to_float(_first_present(raw, ("movement", "MOVEMENT", "mv", "movement_bucket"))),
        sleep_state=None if sleep_state is None else str(sleep_state),
        skin_temperature=_to_float(
            _first_present(raw, ("skin_temperature", "SKIN_TEMPERATURE", "st"))
        ),
        raw=raw,
    )
