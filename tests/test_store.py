import pytest

from app.models import normalize_reading
from app.store import ReadingStore


def test_normalize_reading_accepts_common_pyowlet_property_names():
    raw = {
        "heart_rate": 128,
        "oxygen_saturation": 97,
        "battery": 84,
        "movement": 12,
        "sleep_state": "LIGHT_SLEEP",
        "skin_temperature": 36.4,
        "last_updated": "2026-07-02T03:04:05Z",
    }

    reading = normalize_reading(raw, device_serial="AC123")

    assert reading.device_serial == "AC123"
    assert reading.heart_rate == 128
    assert reading.oxygen_saturation == 97
    assert reading.battery == 84
    assert reading.movement == 12
    assert reading.sleep_state == "LIGHT_SLEEP"
    assert reading.skin_temperature == 36.4
    assert reading.recorded_at.isoformat().startswith("2026-07-02T03:04:05")


def test_normalize_reading_accepts_legacy_ayla_property_names():
    raw = {
        "HEART_RATE": 121,
        "OXYGEN_LEVEL": 96,
        "BATT_LEVEL": 77,
        "MOVEMENT": 3,
        "SLEEP_STATE": 2,
        "SKIN_TEMPERATURE": 36.1,
        "timestamp": 1782951845,
    }

    reading = normalize_reading(raw, device_serial="AC999")

    assert reading.heart_rate == 121
    assert reading.oxygen_saturation == 96
    assert reading.battery == 77
    assert reading.movement == 3
    assert reading.sleep_state == "2"
    assert reading.skin_temperature == 36.1


@pytest.mark.asyncio
async def test_store_inserts_and_queries_recent_readings(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()

    first = normalize_reading(
        {"heart_rate": 120, "oxygen_saturation": 98, "last_updated": "2026-07-02T01:00:00Z"},
        device_serial="AC123",
    )
    second = normalize_reading(
        {"heart_rate": 130, "oxygen_saturation": 96, "last_updated": "2026-07-02T02:00:00Z"},
        device_serial="AC123",
    )

    await store.insert_reading(first)
    await store.insert_reading(second)
    rows = await store.get_readings(hours=24)

    assert [row.heart_rate for row in rows] == [120, 130]
    assert [row.oxygen_saturation for row in rows] == [98, 96]

    summary = await store.get_summary(hours=24)
    assert summary["count"] == 2
    assert summary["heart_rate"]["avg"] == 125
    assert summary["heart_rate"]["trend"] == "up"
    assert summary["oxygen_saturation"]["trend"] == "down"


@pytest.mark.asyncio
async def test_store_can_return_all_readings_or_recent_window(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()

    for timestamp, hr in [
        ("2026-06-30T02:00:00Z", 110),
        ("2026-07-02T01:00:00Z", 120),
        ("2026-07-02T02:00:00Z", 130),
    ]:
        await store.insert_reading(
            normalize_reading(
                {"heart_rate": hr, "oxygen_saturation": 97, "last_updated": timestamp},
                device_serial="AC123",
            )
        )

    all_rows = await store.get_readings(hours=None)
    recent_rows = await store.get_readings(hours=24)
    summary = await store.get_summary(hours=None)

    assert [row.heart_rate for row in all_rows] == [110, 120, 130]
    assert [row.heart_rate for row in recent_rows] == [120, 130]
    assert summary["count"] == 3
    assert summary["window"] == "all"
    assert summary["first_recorded_at"].startswith("2026-06-30")
    assert summary["last_recorded_at"].startswith("2026-07-02")
