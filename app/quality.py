from __future__ import annotations

from app.models import OwletReading


def is_offline_reading(reading: OwletReading) -> bool:
    """Return true when the sock/device is not producing physiological readings.

    Owlet can emit zero-valued vitals when the sock is off-body or disconnected.
    It can also keep returning stale nonzero vitals while explicit sock-off or
    sock-disconnect flags are active. Those rows are useful for graphing coverage
    gaps, but should not contribute to averages, sleep totals, or trend analysis.
    """

    return (
        bool(reading.sock_disconnected)
        or bool(reading.sock_off)
        or _zero_or_negative(reading.heart_rate)
        or _zero_or_negative(reading.oxygen_saturation)
    )


def _zero_or_negative(value: float | int | None) -> bool:
    return value is not None and float(value) <= 0
