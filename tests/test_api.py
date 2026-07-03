import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import normalize_reading
from app.store import ReadingStore


@pytest.mark.asyncio
async def test_api_returns_readings_and_summary(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    await store.insert_reading(
        normalize_reading(
            {"heart_rate": 120, "oxygen_saturation": 98, "last_updated": "2026-07-02T01:00:00Z"},
            "AC123",
        )
    )
    await store.insert_reading(
        normalize_reading(
            {"heart_rate": 130, "oxygen_saturation": 96, "last_updated": "2026-07-02T02:00:00Z"},
            "AC123",
        )
    )

    app = create_app(store=store, start_poller=False)

    with TestClient(app) as client:
        readings = client.get("/api/readings?hours=24").json()
        summary = client.get("/api/summary?hours=24").json()

    assert len(readings) == 2
    assert readings[0]["device_serial"] == "AC123"
    assert readings[1]["heart_rate"] == 130
    assert "raw" not in readings[0]
    assert summary["count"] == 2
    assert summary["heart_rate"]["trend"] == "up"

    with TestClient(app) as client:
        raw_readings = client.get("/api/readings?hours=24&include_raw=true").json()

    assert raw_readings[0]["raw"]["heart_rate"] == 120


@pytest.mark.asyncio
async def test_api_defaults_to_all_data_and_still_supports_hours_filter(tmp_path):
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
                "AC123",
            )
        )

    app = create_app(store=store, start_poller=False)

    with TestClient(app) as client:
        all_readings = client.get("/api/readings").json()
        recent_readings = client.get("/api/readings?hours=24").json()
        all_summary = client.get("/api/summary").json()

    assert [row["heart_rate"] for row in all_readings] == [110, 120, 130]
    assert [row["heart_rate"] for row in recent_readings] == [120, 130]
    assert all_summary["window"] == "all"
    assert all_summary["count"] == 3


def test_dashboard_endpoint_serves_html(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    app = create_app(store=store, start_poller=False)

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Owlet History" in response.text
    assert "/api/readings" in response.text
    assert "All stored data" in response.text
    assert "Readings table" in response.text
