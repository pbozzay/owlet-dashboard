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
    battery_minutes: float | None = None
    movement: float | None = None
    sleep_state: str | None = None
    sock_disconnected: bool = False
    sock_off: bool = False
    skin_temperature: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


def _first_present(raw: dict[str, Any], names: tuple[str, ...]) -> Any | None:
    for name in names:
        if name in raw and raw[name] not in (None, ""):
            return raw[name]
    return None


def _to_float(value: Any) -> float | None:
    value = _scalar(value)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _scalar(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def _to_bool(value: Any) -> bool:
    value = _scalar(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "none", "null", "off"}
    return False


def raw_flag_active(raw: dict[str, Any], *names: str) -> bool:
    return any(_to_bool(raw.get(name)) for name in names)


def raw_alert_mask_has(raw: dict[str, Any], bit: int) -> bool:
    value = _to_float(raw.get("alerts_mask"))
    return value is not None and bool(int(value) & bit)


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
    battery_minutes = _first_present(raw, ("battery_minutes", "btt", "BATTERY_MINUTES"))
    sleep_state = _first_present(raw, ("sleep_state", "SLEEP_STATE"))
    sock_disconnected = raw_flag_active(raw, "sock_disconnected", "SOCK_DISCON_ALRT") or raw_alert_mask_has(raw, 16)
    sock_off = raw_flag_active(raw, "sock_off", "SOCK_OFF") or raw_alert_mask_has(raw, 64)

    return OwletReading(
        device_serial=device_serial,
        recorded_at=recorded_at,
        heart_rate=_to_float(_first_present(raw, ("heart_rate", "HEART_RATE", "hr"))),
        oxygen_saturation=_to_float(
            _first_present(raw, ("oxygen_saturation", "oxygen_level", "OXYGEN_LEVEL", "ox"))
        ),
        battery=_to_float(battery),
        battery_minutes=_to_float(battery_minutes),
        movement=_to_float(_first_present(raw, ("movement", "MOVEMENT", "mv", "movement_bucket"))),
        sleep_state=None if sleep_state is None else str(sleep_state),
        sock_disconnected=sock_disconnected,
        sock_off=sock_off,
        skin_temperature=_to_float(
            _first_present(raw, ("skin_temperature", "SKIN_TEMPERATURE", "st"))
        ),
        raw=raw,
    )
