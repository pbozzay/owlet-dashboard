from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models import OwletReading


class NotificationEvent(BaseModel):
    device_serial: str
    recorded_at: str
    event_type: str
    severity: str = "info"
    title: str
    message: str
    heart_rate: float | None = None
    oxygen_saturation: float | None = None
    battery: float | None = None
    sleep_state: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


ALERT_RULES = [
    ("critical_oxygen", "critical", "Critical oxygen alert", "Owlet critical oxygen alert is active.", ("critical_oxygen_alert", "CRIT_OX_ALRT")),
    ("low_oxygen", "critical", "Low oxygen alert", "Owlet low oxygen alert is active.", ("low_oxygen_alert", "LOW_OX_ALRT")),
    ("critical_battery", "critical", "Critical battery alert", "Owlet critical battery alert is active.", ("critical_battery_alert", "CRIT_BATT_ALRT")),
    ("low_battery", "warning", "Low battery alert", "Owlet low battery alert is active.", ("low_battery_alert", "LOW_BATT_ALRT")),
    ("sock_disconnected", "warning", "Sock disconnected", "Owlet reports that the sock is disconnected.", ("sock_disconnected", "SOCK_DISCON_ALRT")),
    ("sock_off", "warning", "Sock off", "Owlet reports that the sock is off.", ("sock_off", "SOCK_OFF")),
    ("lost_power", "warning", "Base lost power", "Owlet base station lost-power alert is active.", ("lost_power_alert", "LOST_POWER_ALRT")),
    ("low_heart_rate", "warning", "Low heart rate alert", "Owlet low heart-rate alert is active.", ("low_heart_rate_alert", "LOW_HR_ALRT")),
    ("high_heart_rate", "warning", "High heart rate alert", "Owlet high heart-rate alert is active.", ("high_heart_rate_alert", "HIGH_HR_ALRT")),
    ("high_oxygen", "info", "High oxygen alert", "Owlet high oxygen alert is active.", ("high_oxygen_alert", "HIGH_OX_ALRT")),
]

ALERT_MASK_BITS = {
    16: ("sock_disconnected", "warning", "Sock disconnected", "Owlet reports that the sock is disconnected."),
    64: ("sock_off", "warning", "Sock off", "Owlet reports that the sock is off."),
    256: ("low_battery", "warning", "Low battery alert", "Owlet low battery alert is active."),
}


def extract_notifications(reading: OwletReading) -> list[NotificationEvent]:
    events: list[NotificationEvent] = []
    for event_type, severity, title, message, keys in ALERT_RULES:
        active, source = _any_active(reading.raw, keys)
        if active:
            events.append(_event(reading, event_type, severity, title, message, {"source": source}))

    _append_alert_mask_events(reading, events)

    return events


def _append_alert_mask_events(reading: OwletReading, events: list[NotificationEvent]) -> None:
    alerts_mask = _raw_value(reading.raw, "alerts_mask")
    mask_value = _numeric(alerts_mask)
    if mask_value in (None, 0):
        return

    mask = int(mask_value)
    known_bits = 0
    existing_types = {event.event_type for event in events}
    for bit, (event_type, severity, title, message) in ALERT_MASK_BITS.items():
        if not mask & bit:
            continue
        known_bits |= bit
        if event_type in existing_types:
            continue
        events.append(
            _event(
                reading,
                event_type,
                severity,
                title,
                message,
                {"source": "alerts_mask", "value": mask, "bit": bit},
            )
        )
        existing_types.add(event_type)

    unknown_bits = mask & ~known_bits
    if unknown_bits:
        events.append(
            _event(
                reading,
                "alerts_mask",
                "warning",
                "Owlet alert flag",
                f"Owlet REAL_TIME_VITALS alert mask has unknown bit(s): {unknown_bits}.",
                {"source": "alerts_mask", "value": mask, "unknown_bits": unknown_bits},
            )
        )


def _measured_title(reading: OwletReading, event_type: str, title: str) -> str:
    """Lead with what was actually measured, not just which alert tripped.
    Zero vitals mean the sock wasn't reporting, so they never decorate."""
    if "oxygen" in event_type and reading.oxygen_saturation:
        return f"{title} — {reading.oxygen_saturation:.0f}%"
    if "battery" in event_type and reading.battery:
        return f"{title} — {reading.battery:.0f}%"
    if "heart_rate" in event_type and reading.heart_rate:
        return f"{title} — {reading.heart_rate:.0f} bpm"
    return title


def _event(
    reading: OwletReading,
    event_type: str,
    severity: str,
    title: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> NotificationEvent:
    title = _measured_title(reading, event_type, title)
    return NotificationEvent(
        device_serial=reading.device_serial,
        recorded_at=reading.recorded_at.isoformat(),
        event_type=event_type,
        severity=severity,
        title=title,
        message=message,
        heart_rate=reading.heart_rate,
        oxygen_saturation=reading.oxygen_saturation,
        battery=reading.battery,
        sleep_state=reading.sleep_state,
        details=details or {},
    )


def _any_active(raw: dict[str, Any], keys: tuple[str, ...]) -> tuple[bool, str | None]:
    for key in keys:
        value = _raw_value(raw, key)
        if _truthy(value):
            return True, key
    return False, None


def _raw_value(raw: dict[str, Any], key: str) -> Any | None:
    if key not in raw:
        return None
    value = raw[key]
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, "", "0", 0, 0.0, "false", "False", "FALSE"):
        return False
    return True


def _numeric(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
