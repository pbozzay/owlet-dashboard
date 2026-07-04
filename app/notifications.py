from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models import OwletReading
from app.quality import is_offline_reading


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


def extract_notifications(reading: OwletReading) -> list[NotificationEvent]:
    events: list[NotificationEvent] = []
    for event_type, severity, title, message, keys in ALERT_RULES:
        active, source = _any_active(reading.raw, keys)
        if active:
            events.append(_event(reading, event_type, severity, title, message, {"source": source}))

    if is_offline_reading(reading):
        events.append(
            _event(
                reading,
                "offline_zero_vitals",
                "warning",
                "Offline / sock off",
                "Heart rate or oxygen dropped to zero, so this period is treated as no-signal/offline.",
                {
                    "source": "derived_zero_vitals",
                    "heart_rate": reading.heart_rate,
                    "oxygen_saturation": reading.oxygen_saturation,
                },
            )
        )

    alerts_mask = _raw_value(reading.raw, "alerts_mask")
    if _numeric(alerts_mask) not in (None, 0):
        events.append(
            _event(
                reading,
                "alerts_mask",
                "warning",
                "Owlet alert flag",
                f"Owlet REAL_TIME_VITALS alert mask is {alerts_mask}.",
                {"source": "alerts_mask", "value": alerts_mask},
            )
        )

    return events


def _event(
    reading: OwletReading,
    event_type: str,
    severity: str,
    title: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> NotificationEvent:
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
