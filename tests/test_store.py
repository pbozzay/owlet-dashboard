import sqlite3

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


@pytest.mark.asyncio
async def test_store_migrates_legacy_rows_to_default_account(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_serial TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                heart_rate REAL,
                oxygen_saturation REAL,
                battery REAL,
                movement REAL,
                sleep_state TEXT,
                skin_temperature REAL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(device_serial, recorded_at)
            );
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_serial TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                heart_rate REAL,
                oxygen_saturation REAL,
                battery REAL,
                sleep_state TEXT,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(device_serial, recorded_at, event_type)
            );
            CREATE TABLE oxygen_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                label TEXT NOT NULL DEFAULT 'Oxygen challenge',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO readings (device_serial, recorded_at, heart_rate, oxygen_saturation, battery, movement, sleep_state, skin_temperature, raw_json)
            VALUES ('AC123', '2026-07-02T01:00:00+00:00', 120, 98, 100, 0, '1', 32, '{"heart_rate": 120}');
            INSERT INTO notifications (device_serial, recorded_at, event_type, severity, title, message, heart_rate, oxygen_saturation, battery, sleep_state, details_json)
            VALUES ('AC123', '2026-07-02T01:00:00+00:00', 'low_battery', 'warning', 'Low battery', 'Battery low', 120, 98, 10, '1', '{}');
            INSERT INTO metadata (key, value) VALUES ('notifications_schema_version', '5');
            INSERT INTO oxygen_challenges (start_time, end_time, label, notes)
            VALUES ('2026-07-02T00:00:00+00:00', '2026-07-02T00:30:00+00:00', 'Legacy challenge', 'kept');
            """
        )

    store = ReadingStore(db_path)
    await store.init()

    accounts = await store.list_accounts()
    assert len(accounts) == 1
    assert accounts[0]["display_name"] == "Default account"
    default_account_id = accounts[0]["id"]

    with sqlite3.connect(db_path) as db:
        reading_account_ids = [row[0] for row in db.execute("SELECT DISTINCT account_id FROM readings")]
        notification_account_ids = [row[0] for row in db.execute("SELECT DISTINCT account_id FROM notifications")]
        challenge_account_ids = [row[0] for row in db.execute("SELECT DISTINCT account_id FROM oxygen_challenges")]
        reading_indexes = [row[1] for row in db.execute("PRAGMA index_list(readings)")]
        notification_indexes = [row[1] for row in db.execute("PRAGMA index_list(notifications)")]

    assert reading_account_ids == [default_account_id]
    assert notification_account_ids == [default_account_id]
    assert challenge_account_ids == [default_account_id]
    assert "idx_readings_account_device_time_unique" in reading_indexes
    assert "idx_notifications_account_device_event_unique" in notification_indexes


@pytest.mark.asyncio
async def test_store_namespaces_readings_by_account(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    first_account = await store.create_account(email="first@example.com", region="world")
    second_account = await store.create_account(email="second@example.com", region="world")
    reading = normalize_reading(
        {"heart_rate": 120, "oxygen_saturation": 98, "last_updated": "2026-07-02T01:00:00Z"},
        device_serial="AC123",
    )
    other_reading = normalize_reading(
        {"heart_rate": 130, "oxygen_saturation": 96, "last_updated": "2026-07-02T01:00:00Z"},
        device_serial="AC123",
    )

    await store.insert_reading(reading, account_id=first_account["id"])
    await store.insert_reading(other_reading, account_id=second_account["id"])

    first_rows = await store.get_readings(hours=None, account_id=first_account["id"])
    second_rows = await store.get_readings(hours=None, account_id=second_account["id"])
    all_devices = await store.list_devices()
    first_devices = await store.list_devices(account_id=first_account["id"])

    assert [row.heart_rate for row in first_rows] == [120]
    assert [row.heart_rate for row in second_rows] == [130]
    assert len(all_devices) == 2
    assert all_devices[0]["account_id"] in {first_account["id"], second_account["id"]}
    assert len(first_devices) == 1
    assert first_devices[0]["account_id"] == first_account["id"]


@pytest.mark.asyncio
async def test_store_persists_account_tokens_without_password(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    account = await store.create_account(
        email="token@example.com",
        region="world",
        api_token="api-one",
        api_token_expiry=1783000000.0,
        refresh_token="refresh-one",
    )

    await store.update_account_tokens(
        account["id"],
        api_token="api-two",
        api_token_expiry=1784000000.0,
        refresh_token="refresh-two",
        status="active",
    )
    accounts = await store.list_accounts()

    saved = next(item for item in accounts if item["id"] == account["id"])
    assert saved["email"] == "token@example.com"
    assert saved["api_token"] == "api-two"
    assert saved["api_token_expiry"] == 1784000000.0
    assert saved["refresh_token"] == "refresh-two"
    assert saved["status"] == "active"
    assert saved["show_crypto"] is False

    updated = await store.update_account_preferences(account["id"], show_crypto=True, display_name="Night profile")
    assert updated["show_crypto"] is True
    assert updated["display_name"] == "Night profile"
