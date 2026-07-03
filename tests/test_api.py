import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import normalize_reading
from app.store import ReadingStore


def _test_settings(**kwargs):
    return Settings(_env_file=None, **kwargs)  # type: ignore[call-arg]


async def _seed_reading(store: ReadingStore, timestamp: str, *, hr=120, spo2=96, sleep_state=1):
    await store.insert_reading(
        normalize_reading(
            {
                "heart_rate": hr,
                "oxygen_saturation": spo2,
                "sleep_state": sleep_state,
                "last_updated": timestamp,
                "battery": 100,
            },
            "AC123",
        )
    )


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

    app = create_app(store=store, settings=_test_settings(), start_poller=False)

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

    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        all_readings = client.get("/api/readings").json()
        recent_readings = client.get("/api/readings?hours=24").json()
        all_summary = client.get("/api/summary").json()

    assert [row["heart_rate"] for row in all_readings] == [110, 120, 130]
    assert [row["heart_rate"] for row in recent_readings] == [120, 130]
    assert all_summary["window"] == "all"
    assert all_summary["count"] == 3


@pytest.mark.asyncio
async def test_api_exposes_insights_and_rollups(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    await _seed_reading(store, "2026-07-03T10:00:00Z", hr=100, spo2=92, sleep_state=8)
    await _seed_reading(store, "2026-07-03T10:30:00Z", hr=110, spo2=93, sleep_state=15)
    await _seed_reading(store, "2026-07-03T11:00:00Z", hr=120, spo2=96, sleep_state=1)
    await _seed_reading(store, "2026-07-03T11:30:00Z", hr=130, spo2=97, sleep_state=1)

    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        insights = client.get("/api/insights").json()
        rollups = client.get("/api/rollups?bucket=hour").json()

    assert insights["breathing"]["direction"] == "improving"
    assert insights["sleep"]["sleep_seconds"] == 3600
    assert rollups["bucket"] == "hour"
    assert [row["avg_oxygen_saturation"] for row in rollups["rollups"]] == [92.5, 96.5]


def test_dashboard_endpoint_serves_html(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Owlet Dashboard" in response.text
    assert "/api/readings" in response.text
    assert "All stored data" in response.text
    assert '<option selected value="24">24 hours</option>' in response.text
    assert '<option value="72">3 days</option>' in response.text
    assert '<option value="168">7 days</option>' in response.text
    assert '<option value="all">All stored data</option>' in response.text
    assert '<option value="5m">5 minutes</option>' in response.text
    assert '<button id="download" class="icon-button"' in response.text
    assert "chartjs-plugin-zoom" in response.text
    assert response.text.index("id=\"vitalsChart\"") < response.text.index("Today at a glance")
    assert response.text.index("id=\"rollupChart\"") < response.text.index("id=\"stateChart\"")
    assert "Today at a glance" in response.text
    assert "Breathing trend" in response.text
    assert "Drill-down" in response.text


def test_basic_auth_protects_dashboard_and_api_when_configured(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    settings = _test_settings(
        owlet_basic_auth_username="parent",
        owlet_basic_auth_password="secret-pass",
    )
    app = create_app(store=store, settings=settings, start_poller=False)

    with TestClient(app) as client:
        unauthenticated = client.get("/")
        wrong_password = client.get("/api/health", auth=("parent", "wrong"))
        authenticated = client.get("/api/health", auth=("parent", "secret-pass"))

    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["www-authenticate"] == 'Basic realm="Owlet History"'
    assert wrong_password.status_code == 401
    assert authenticated.status_code == 200
