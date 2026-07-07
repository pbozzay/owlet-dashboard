import pytest
from fastapi.testclient import TestClient

from app import crypto as crypto_module
from app.config import Settings
from app.main import create_app
from app.models import normalize_reading
from app.store import ReadingStore


def _test_settings(**kwargs):
    return Settings(_env_file=None, **kwargs)  # type: ignore[call-arg]


async def _seed_reading(
    store: ReadingStore,
    timestamp: str,
    *,
    hr=120,
    spo2=96,
    sleep_state=1,
    skin_temp=32,
    device_serial="AC123",
    account_id=None,
):
    await store.insert_reading(
        normalize_reading(
            {
                "heart_rate": hr,
                "oxygen_saturation": spo2,
                "sleep_state": sleep_state,
                "last_updated": timestamp,
                "battery": 100,
                "skin_temperature": skin_temp,
            },
            device_serial,
        ),
        account_id=account_id,
    )


@pytest.mark.asyncio
async def test_account_api_is_public_metadata_only_and_scopes_data(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    first = (await store.list_accounts())[0]
    second = await store.create_account(
        email="second@example.test",
        region="world",
        display_name="Second baby",
        api_token="secret-api-token",
        api_token_expiry=12345,
        refresh_token="secret-refresh-token",
    )
    await _seed_reading(store, "2026-07-02T01:00:00Z", hr=120, spo2=98, device_serial="SAME", account_id=first["id"])
    await _seed_reading(store, "2026-07-02T01:00:00Z", hr=150, spo2=90, device_serial="SAME", account_id=second["id"])
    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        accounts = client.get("/api/accounts").json()["accounts"]
        first_readings = client.get(f"/api/readings?account={first['id']}&hours=24").json()
        second_readings = client.get(f"/api/readings?account={second['id']}&hours=24").json()
        second_devices = client.get(f"/api/devices?account={second['id']}").json()["devices"]
        updated = client.patch(
            f"/api/accounts/{second['id']}",
            json={
                "show_crypto": True,
                "display_name": "Second profile",
                "dashboard_preferences": {
                    "chart_visibility": {"btcPrice": False, "heartRate": True},
                    "chart_settings": {"window": "72", "smoothing": "15", "challenge_bands": False},
                    "secret": "ignored",
                },
            },
        ).json()["account"]

    assert len(accounts) == 2
    second_payload = next(account for account in accounts if account["id"] == second["id"])
    assert second_payload["display_name"] == "Second baby"
    assert second_payload["has_refresh_token"] is True
    assert second_payload["show_crypto"] is False
    assert updated["display_name"] == "Second profile"
    assert updated["show_crypto"] is True
    assert updated["dashboard_preferences"]["chart_visibility"] == {"btcPrice": False, "heartRate": True}
    assert updated["dashboard_preferences"]["chart_settings"]["window"] == "72"
    assert "secret" not in updated["dashboard_preferences"]
    assert "refresh_token" not in second_payload
    assert "api_token" not in second_payload
    assert first_readings[0]["heart_rate"] == 120
    assert second_readings[0]["heart_rate"] == 150
    assert second_devices[0]["account_id"] == second["id"]


@pytest.mark.asyncio
async def test_summary_excludes_zero_offline_vitals_from_metric_averages(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    await _seed_reading(store, "2026-07-02T01:00:00Z", hr=120, spo2=98, skin_temp=31)
    await _seed_reading(store, "2026-07-02T01:05:00Z", hr=0, spo2=0, sleep_state=0, skin_temp=35)
    await _seed_reading(store, "2026-07-02T01:10:00Z", hr=140, spo2=96, skin_temp=33)
    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        summary = client.get("/api/summary?hours=24").json()
        rollups = client.get("/api/rollups?bucket=hour&hours=24").json()

    assert summary["count"] == 3
    assert summary["valid_count"] == 2
    assert summary["offline_count"] == 1
    assert summary["heart_rate"]["avg"] == 130
    assert summary["oxygen_saturation"]["min"] == 96
    assert summary["skin_temperature"]["avg"] == 32
    assert summary["skin_temperature"]["min"] == 31
    assert rollups["rollups"][0]["offline_samples"] == 1
    assert rollups["rollups"][0]["avg_skin_temperature"] == 32


@pytest.mark.asyncio
async def test_sock_disconnected_nonzero_vitals_are_treated_as_offline(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    await _seed_reading(store, "2026-07-02T01:00:00Z", hr=120, spo2=98)
    await store.insert_reading(
        normalize_reading(
            {
                "heart_rate": 120,
                "oxygen_saturation": 98,
                "battery": 95,
                "last_updated": "2026-07-02T01:05:00Z",
                "sock_disconnected": True,
                "SOCK_DISCON_ALRT": {"value": 1},
                "alerts_mask": 16,
            },
            "AC123",
        )
    )
    await _seed_reading(store, "2026-07-02T01:10:00Z", hr=130, spo2=97)
    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        readings = client.get("/api/readings?hours=24").json()
        raw_readings = client.get("/api/readings?hours=24&include_raw=true").json()
        summary = client.get("/api/summary?hours=24").json()
        rollups = client.get("/api/rollups?bucket=hour&hours=24").json()

    assert readings[1]["sock_disconnected"] is True
    assert readings[1]["sock_off"] is False
    assert readings[1]["heart_rate"] == 0
    assert readings[1]["oxygen_saturation"] == 0
    assert readings[1]["movement"] == 0
    assert raw_readings[1]["heart_rate"] == 0
    assert raw_readings[1]["oxygen_saturation"] == 0
    assert raw_readings[1]["raw"]["heart_rate"] == 120
    assert raw_readings[1]["raw"]["oxygen_saturation"] == 98
    assert summary["count"] == 3
    assert summary["valid_count"] == 2
    assert summary["offline_count"] == 1
    assert summary["heart_rate"]["avg"] == 125
    assert summary["oxygen_saturation"]["avg"] == 97.5
    assert rollups["rollups"][0]["offline_samples"] == 1


@pytest.mark.asyncio
async def test_oxygen_challenges_are_stored_and_excluded_from_normal_stats(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    await _seed_reading(store, "2026-07-02T00:00:00Z", hr=120, spo2=98, sleep_state=8, skin_temp=31)
    await _seed_reading(store, "2026-07-02T00:30:00Z", hr=122, spo2=97, sleep_state=8, skin_temp=32)
    await _seed_reading(store, "2026-07-02T01:00:00Z", hr=150, spo2=90, sleep_state=15, skin_temp=40)
    await _seed_reading(store, "2026-07-02T01:30:00Z", hr=155, spo2=89, sleep_state=15, skin_temp=41)
    await _seed_reading(store, "2026-07-02T02:00:00Z", hr=126, spo2=97, sleep_state=1, skin_temp=33)
    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        created = client.post(
            "/api/oxygen-challenges",
            json={
                "start_time": "2026-07-02T01:00:00+00:00",
                "end_time": "2026-07-02T01:30:00+00:00",
                "label": "Nap off oxygen",
            },
        ).json()
        summary = client.get("/api/summary?hours=24").json()
        insights = client.get("/api/insights?hours=24").json()
        detail = client.get(f"/api/oxygen-challenges/{created['id']}").json()
        updated = client.patch(
            f"/api/oxygen-challenges/{created['id']}",
            json={
                "start_time": "2026-07-02T00:55:00+00:00",
                "end_time": "2026-07-02T01:35:00+00:00",
                "label": "Edited oxygen challenge",
                "notes": "Adjusted start/stop times",
            },
        ).json()
        active_again = client.patch(
            f"/api/oxygen-challenges/{created['id']}",
            json={"end_time": None},
        ).json()
        deleted = client.delete(f"/api/oxygen-challenges/{created['id']}").json()
        after_delete = client.get("/api/oxygen-challenges?hours=24").json()

    assert created["label"] == "Nap off oxygen"
    assert summary["challenge_count"] == 2
    assert summary["oxygen_saturation"]["min"] == 97
    assert summary["skin_temperature"]["avg"] == 32
    assert summary["skin_temperature"]["max"] == 33
    assert insights["breathing"]["low_oxygen_samples"] == 0
    assert detail["summary"]["avg_oxygen_saturation"] == 89.5
    assert detail["summary"]["low_oxygen_samples"] == 2
    assert detail["comparison"]["avg_oxygen_delta"] == -7.5
    assert len(detail["readings"]) == 2
    assert updated["label"] == "Edited oxygen challenge"
    assert updated["notes"] == "Adjusted start/stop times"
    assert updated["start_time"].startswith("2026-07-02T00:55:00")
    assert updated["end_time"].startswith("2026-07-02T01:35:00")
    assert active_again["end_time"] is None
    assert active_again["active"] is True
    assert deleted == {"ok": True}
    assert after_delete["total"] == 0


@pytest.mark.asyncio
async def test_oxygen_challenge_list_summaries_honor_device_filter(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    await _seed_reading(store, "2026-07-02T01:00:00Z", hr=120, spo2=90, device_serial="AC123")
    await _seed_reading(store, "2026-07-02T01:30:00Z", hr=122, spo2=92, device_serial="AC123")
    await _seed_reading(store, "2026-07-02T01:00:00Z", hr=150, spo2=70, device_serial="AC999")
    await _seed_reading(store, "2026-07-02T01:30:00Z", hr=152, spo2=72, device_serial="AC999")
    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        client.post(
            "/api/oxygen-challenges",
            json={
                "start_time": "2026-07-02T01:00:00+00:00",
                "end_time": "2026-07-02T01:30:00+00:00",
                "label": "Device-specific challenge",
            },
        )
        ac123 = client.get("/api/oxygen-challenges?hours=24&device=AC123").json()
        ac999 = client.get("/api/oxygen-challenges?hours=24&device=AC999").json()

    assert ac123["items"][0]["summary"]["avg_oxygen_saturation"] == 91
    assert ac999["items"][0]["summary"]["avg_oxygen_saturation"] == 71


@pytest.mark.asyncio
async def test_notifications_endpoint_extracts_alerts_and_offline_periods(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    await store.insert_reading(
        normalize_reading(
            {
                "heart_rate": 0,
                "oxygen_saturation": 0,
                "battery": 82,
                "last_updated": "2026-07-02T01:00:00Z",
                "low_oxygen_alert": True,
                "SOCK_DISCON_ALRT": {"value": 1},
                "alerts_mask": 16,
            },
            "AC123",
        )
    )
    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        response = client.get("/api/notifications?hours=24")

    assert response.status_code == 200
    payload = response.json()
    event_types = {item["event_type"] for item in payload["items"]}
    assert "low_oxygen" in event_types
    assert "sock_disconnected" in event_types
    assert "offline_zero_vitals" not in event_types
    assert "alerts_mask" not in event_types
    assert "Owlet REAL_TIME_VITALS alert mask is 16" not in response.text
    assert payload["total"] == 2


@pytest.mark.asyncio
async def test_notifications_endpoint_does_not_derive_low_oxygen_from_readings(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    for timestamp, spo2 in [
        ("2026-07-02T01:00:00Z", 97),
        ("2026-07-02T01:01:00Z", 91),
        ("2026-07-02T01:02:00Z", 90),
        ("2026-07-02T01:03:00Z", 87),
    ]:
        await _seed_reading(store, timestamp, hr=130, spo2=spo2)
    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        response = client.get("/api/notifications?hours=24")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert "Low oxygen reading" not in response.text
    assert "Critical oxygen reading" not in response.text
    assert "Measured SpO₂ dropped below" not in response.text


@pytest.mark.asyncio
async def test_widget_endpoint_returns_compact_status_payload(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    await _seed_reading(store, "2026-07-02T01:00:00Z", hr=120, spo2=98)
    await _seed_reading(store, "2026-07-02T01:05:00Z", hr=130, spo2=96)
    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        payload = client.get("/api/widget?hours=24").json()

    assert payload["oxygen_now"] == 96
    assert payload["oxygen_avg"] == 97
    assert payload["heart_rate"] == 130
    assert payload["trend"] in {"improving", "worsening", "stable"}


def test_crypto_endpoint_returns_prices_and_btc_series(tmp_path, monkeypatch):
    crypto_module._CACHE.clear()

    def fake_fetch(hours):
        return {
            "available": True,
            "source": "coingecko",
            "window_hours": hours,
            "prices": {
                "bitcoin": {"symbol": "BTC", "usd": 100000, "usd_24h_change": 1.5},
                "ethereum": {"symbol": "ETH", "usd": 4000, "usd_24h_change": -0.5},
                "monero": {"symbol": "XMR", "usd": 300, "usd_24h_change": 0.1},
            },
            "series": {"bitcoin": [{"x": 1, "y": 99000}, {"x": 2, "y": 100000}]},
        }

    monkeypatch.setattr(crypto_module, "fetch_crypto_payload", fake_fetch)
    app = create_app(store=ReadingStore(tmp_path / "owlet.sqlite3"), settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        payload = client.get("/api/crypto?hours=24").json()

    assert payload["available"] is True
    assert payload["prices"]["bitcoin"]["symbol"] == "BTC"
    assert payload["prices"]["ethereum"]["usd_24h_change"] == -0.5
    assert payload["series"]["bitcoin"][-1]["y"] == 100000


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
async def test_api_lists_and_filters_devices(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    await _seed_reading(store, "2026-07-02T01:00:00Z", hr=120, spo2=98, device_serial="AC123")
    await _seed_reading(store, "2026-07-02T02:00:00Z", hr=130, spo2=96, device_serial="AC999")

    token = "test-share-token-123456"
    app = create_app(store=store, settings=_test_settings(owlet_share_token=token), start_poller=False)

    with TestClient(app) as client:
        devices = client.get("/api/devices").json()["devices"]
        readings = client.get("/api/readings?device=AC999").json()
        summary = client.get("/api/summary?device=AC999").json()
        shared_devices_response = client.get(f"/share/{token}/api/devices")
        shared_readings = client.get(f"/share/{token}/api/readings?device=AC999").json()
        shared_summary = client.get(f"/share/{token}/api/summary?device=AC999").json()
        shared_widget = client.get(f"/share/{token}/api/widget?device=AC999").json()

    assert {device["serial"] for device in devices} == {"AC123", "AC999"}
    assert readings[0]["device_serial"] == "AC999"
    assert summary["device_serial"] == "AC999"
    assert summary["count"] == 1
    assert shared_devices_response.status_code == 200
    assert {device["serial"] for device in shared_devices_response.json()["devices"]} == {"AC123", "AC999"}
    assert shared_readings[0]["device_serial"] == "AC999"
    assert shared_summary["device_serial"] == "AC999"
    assert shared_widget["heart_rate"] == 130


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
    assert 'id="profileMenuToggle"' in response.text
    assert 'id="profileAvatar"' in response.text
    assert 'id="profileMenu"' in response.text
    assert 'id="showCryptoSetting"' in response.text
    assert "Crypto widget" in response.text
    assert "BTC card + optional chart line" in response.text
    assert 'id="profileCurrentName"' not in response.text
    assert "Current profile" not in response.text
    assert "Switch profile" not in response.text
    assert "Display preferences" not in response.text
    assert 'id="deviceSelect"' in response.text
    assert 'id="accountSelect"' in response.text
    assert 'id="addAccount"' in response.text
    assert "Link another Owlet account" in response.text
    assert "renderProfileMenu" in response.text
    assert "showCryptoEnabled" in response.text
    assert "updateCurrentAccountPreference" in response.text
    assert "show_crypto" in response.text
    assert "el('profileMenuWrap')?.classList.toggle('share-only-hidden', SHARE_MODE);" in response.text
    assert "cluster.classList.toggle('hidden', SHARE_MODE);" in response.text
    assert "/api/accounts" in response.text
    assert "has_refresh_token" not in response.text
    assert "/api/devices" in response.text
    assert 'id="smoothing"' in response.text
    assert '<option selected value="raw">Raw points</option>' in response.text
    assert '<option value="5">5 min avg</option>' in response.text
    assert 'id="o2AddMenuToggle"' in response.text
    assert 'id="menuVisibleChallenge"' in response.text
    assert 'id="menuNewChallenge"' in response.text
    assert 'id="profileDeviceName"' in response.text
    assert '<button id="download" class="icon-button"' in response.text
    assert 'id="resetZoom"' in response.text
    assert 'id="resetZoomHeader"' in response.text
    assert "Reset view" in response.text
    assert "chartjs-plugin-zoom" in response.text
    assert "mobile-web-app-capable" in response.text
    assert 'rel="manifest"' in response.text
    assert "serviceWorker" in response.text
    assert "offlineBands" in response.text
    assert "rgba(100, 116, 139, 0.14)" in response.text
    assert "Device offline / sock off" in response.text
    assert "row?.sock_disconnected" in response.text
    assert "row?.sock_off" in response.text
    assert "notificationGlyphs" in response.text
    assert "oxygen85Threshold" in response.text
    assert "85% O₂" in response.text
    assert "notificationHoverPriority" in response.text
    assert "attachNotificationHover" in response.text
    assert "function tooltipTitle(items)" in response.text
    assert "title: tooltipTitle" in response.text
    assert "label: tooltipLabel" in response.text
    assert "chartValue(context.parsed.y, '%')" in response.text
    assert "callback: axisTick" in response.text
    assert "notificationHit" in response.text
    assert "hitRadius: 24" in response.text
    assert "/api/notifications" in response.text
    assert "Notifications" in response.text
    assert 'id="dailyInsightsToggle"' in response.text
    assert 'id="dailyInsightsModal"' in response.text
    assert 'id="dailyInsightsChart"' in response.text
    assert "dailyInsightsChart = new Chart" in response.text
    assert "dailyOxygenAvg" in response.text
    assert "dailyOxygenSleep" in response.text
    assert "dailyOxygenWake" in response.text
    assert "dailyHeartRateAvg" in response.text
    assert "dailySkinTempAvg" in response.text
    assert "Skin temp °C" in response.text
    assert "Temp avg" in response.text
    assert "Avg skin temp" in response.text
    assert "renderDailyInsightsChart(periods)" in response.text
    assert "Daily insights" in response.text
    assert "Calendar days. Today is in progress" in response.text
    assert "dailyInsightPeriods" in response.text
    assert "sleepBucket(row) === 'sleeping'" in response.text
    assert "sleepBucket(row) === 'waking'" in response.text
    assert "O₂ sleep" in response.text
    assert "HR wake" in response.text
    assert "offline/sock-off and O₂ challenge samples excluded" in response.text
    assert "/api/crypto" in response.text
    assert 'id="cryptoCard" class="card glance-card crypto-card hidden"' in response.text
    assert 'id="glanceStrip" class="glance-strip crypto-hidden"' in response.text
    assert "showCryptoEnabled()\n        ? fetchJson(`${API_BASE}/api/crypto?hours=${cryptoHours}`)" in response.text
    assert "if (showCryptoEnabled())" in response.text
    assert "id: 'btcPrice'" in response.text
    assert "hidden: preferredDatasetHidden('btcPrice', true)" in response.text
    assert "function syncCryptoChartDataset()" in response.text
    assert "vitalsChart.data.datasets[index].data = cryptoBitcoinPoints()" in response.text
    assert "syncCryptoChartDataset();" in response.text
    assert "BTC price: ${money(context.parsed.y)}" in response.text
    assert "O₂ trend companion" in response.text
    assert "How to read the O₂ trend companion" in response.text
    assert "MACD-style oxygen view" in response.text
    assert "oxygen challenges stay visible as real readings" in response.text
    assert "Offline gaps and oxygen challenges are not bridged" not in response.text
    assert "O₂ avg (%)" in response.text
    assert "30m − 4h signal" in response.text
    assert "Blue line:" not in response.text
    assert "trendLineLabel" not in response.text
    assert "Raw points O₂ avg" not in response.text
    assert "Trend signal" in response.text
    assert "legend: { display: false }" in response.text
    assert "TREND_MAX_SAMPLE_GAP_MS" in response.text
    assert "TREND_MAX_SOURCE_POINTS_DESKTOP = 800" in response.text
    assert "TREND_MAX_SOURCE_POINTS_MOBILE = 420" in response.text
    assert "trendSourceRows" in response.text
    assert "rollingOxygenAverage(shortMinutes, trendRows)" in response.text
    assert "rollingOxygenAverage(longMinutes, trendRows)" in response.text
    assert "y: null" in response.text
    assert "spanGaps: false" in response.text
    assert "Trend gap — offline or missing data." in response.text
    assert "Trend gap — offline, missing data, or O₂ challenge." not in response.text
    assert "function rollingOxygenAverage(minutes, rows = readings)" in response.text
    assert "const offline = isOffline(row) || !Number.isFinite(value)" in response.text
    assert "addGapMarker(time, inChallenge ? 'challenge' : 'offline')" not in response.text
    assert "const inChallenge = timeInIntervals(time, challengeWindows)" not in response.text
    assert "companion-info" in response.text
    assert "companion-header" not in response.text
    assert "requestIdleCallback" in response.text
    assert "hydrateSecondaryData" in response.text
    assert "renderCharts({ deferTrend: true })" in response.text
    assert "historyHoursForSelection" in response.text
    assert "Math.ceil(hours) + HISTORY_PAN_BUFFER_HOURS" in response.text
    assert "defaultVisibleRange" in response.text
    assert "extendPointsToVisibleEdges" in response.text
    assert "readingSeries('heart_rate')" in response.text
    assert "rollingAverageForKey" in response.text
    assert "const value = metricValue(row, key)" in response.text
    assert "if (isOffline(row) || value === null)" in response.text
    assert "key === 'skin_temperature' ? null : 0" in response.text
    assert "reason: key === 'skin_temperature' ? 'missing' : 'offline-zero'" in response.text
    assert "offset: false" in response.text
    assert "hr: { type: 'linear', position: 'left', min: 0" in response.text
    assert "spo2: { type: 'linear', position: 'right', min: 0" in response.text
    assert "id: 'skinTemperature'" in response.text
    assert "readingSeries('skin_temperature')" in response.text
    assert "metric-grid" not in response.text
    assert "renderMetricCards" not in response.text
    assert 'id="metricCards"' not in response.text
    assert "dataQs" in response.text
    assert response.text.count("fetchJson(`${API_BASE}/api/readings?${dataQs}`)") == 1
    assert "refreshInFlight" in response.text
    assert "if (refreshInFlight && !force) return refreshInFlight" in response.text
    assert "attachReadingsTableSelection" in response.text
    assert "selectionAttached" in response.text
    assert "filtered.map((row, index)" not in response.text
    assert "TABLE_ROW_LIMIT = 500" in response.text
    assert "newest ${tableRows.length} of ${filtered.length} loaded" in response.text
    assert "tableRows.map((row, index)" in response.text
    assert "HISTORY_PAN_BUFFER_HOURS = 2" in response.text
    assert "OLDER_HISTORY_CHUNK_HOURS = 24" in response.text
    assert "function chartPoints(points)" in response.text
    assert "downsamplePoints" not in response.text
    assert "CHART_MAX_POINTS" not in response.text
    assert "bucket.forEach(item" not in response.text
    assert "offlineTransition" in response.text
    assert "table.addEventListener('click'" in response.text
    assert "loadOlderHistoryIfNeeded" in response.text
    assert "release near the left edge to load more" in response.text
    assert "oxygenTrendSignal(shortAvg, longAvg)" in response.text
    assert "sleepPhaseHover" in response.text
    assert "sleepBands" in response.text
    assert "stateChartHover" in response.text
    assert "stateTooltip" in response.text
    assert "dayBoundaries" in response.text
    assert "dayBoundaryTimes" in response.text
    assert "state-day-boundary" in response.text
    assert "timeTickValues(range)" in response.text
    assert "sleepStageInfo" in response.text
    assert "sleepHighlightToggle" in response.text
    assert "sleepBallparkToggle" in response.text
    assert "challengeBandsToggle" in response.text
    assert "Guess sleep windows" in response.text
    assert "smoothBallparkIntervals" in response.text
    assert "function rollupBucket()" in response.text
    assert "return '30m';" in response.text
    assert "movementSeconds" in response.text
    assert "awakeLikeSeconds" in response.text
    assert "subtractIntervals" in response.text
    assert "setStateStripHoverFromEvent" in response.text
    assert "attachStateChartHover" in response.text
    assert "id=\"timePan\"" in response.text
    assert "panToSliderValue" in response.text
    assert response.text.index("chart-toolbar") < response.text.index("id=\"vitalsChart\"")
    assert response.text.index("challengeBandsToggle") < response.text.index("id=\"vitalsChart\"")
    assert response.text.index("id=\"vitalsChart\"") < response.text.index("id=\"stateStrip\"") < response.text.index("id=\"oxygenTrendChart\"")
    assert "wheel:" in response.text
    assert "pinch:" in response.text
    assert "selector.value = '6'" not in response.text
    assert "drag: { enabled: !mobile" in response.text
    assert "pan: { enabled: true" in response.text
    assert "onPanComplete: ({ chart }) => { syncZoomFrom(chart); loadOlderHistoryIfNeeded().catch(console.error); }" in response.text
    assert "touch-action: pan-y" in response.text
    assert "attachMobileDragPan" in response.text
    assert "panVisibleWindowByPixels" in response.text
    assert "pointerType === 'touch'" in response.text
    assert "visibleWindowSnapshot" in response.text
    assert "refreshedVisibleRange" in response.text
    assert "sliderAtEnd" in response.text
    assert "onPanComplete" in response.text
    assert "O₂ challenges" in response.text
    assert "O₂ challenge" in response.text
    assert "O₂ challenges / add" not in response.text
    assert "O₂+" in response.text
    assert "Use current graph window" in response.text
    assert "Enter new times…" in response.text
    assert "Add new O₂ challenge" in response.text
    assert "Add one from this popup" in response.text
    assert "data-add-challenge-empty" in response.text
    assert "data-visible-challenge-empty" in response.text
    assert "Use visible chart window" in response.text
    assert "/api/oxygen-challenges" in response.text
    assert "challengeBands" in response.text
    assert "beforeDraw(chart, _args, options)" in response.text
    assert "const isTrendCompanion = chart.canvas.id === 'oxygenTrendChart'" in response.text
    assert "rgba(37, 99, 235, 0.10)" in response.text
    assert "ctx.setLineDash(isTrendCompanion ? [7, 5] : [8, 5])" in response.text
    assert "ctx.strokeRect(left, chartArea.top + 1" in response.text
    assert "rgba(4, 120, 87, .96)" in response.text
    assert "rgba(185, 28, 28, .96)" in response.text
    assert "stateStrip" in response.text
    assert "Challenge data is excluded" in response.text
    assert "challengeEditForm" in response.text
    assert "Save edits" in response.text
    assert "Delete challenge" in response.text
    assert "closeNotificationsPanel" in response.text
    assert "closeChallengesPanel" in response.text
    assert "safeRefresh" in response.text
    assert "Refresh (15s)" in response.text
    assert "initialLoading" in response.text
    assert "Loading Owlet data" in response.text
    assert "setInitialLoading('Loading readings and notifications" in response.text
    assert "hideInitialLoading" in response.text
    assert "titleStatusDot" in response.text
    assert "device-label" in response.text
    assert "mobile-label" in response.text
    assert "O₂ Ch." in response.text
    assert "compactDeviceName" in response.text
    assert "Sock ${digits}" in response.text
    assert "↻ ${secondsUntilRefresh}" in response.text
    assert "barThickness: isMobileViewport() ? 3 : 4" in response.text
    assert "minBarLength: 2" in response.text
    assert '<span class="control-section-title">View</span>' not in response.text
    assert "refreshNote" not in response.text
    assert "batteryStatus" in response.text
    assert "battery_minutes" in response.text
    assert "pill.dataset.detail" in response.text
    assert "batteryStatus').addEventListener('click'" in response.text
    assert "latestBattery" not in response.text
    assert "lowOxygen" not in response.text
    assert "oxygen-value.good" in response.text
    assert "function oxygenValueClass" in response.text
    assert "if (value >= 92) return 'good'" in response.text
    assert "if (value >= 86) return 'caution'" in response.text
    assert "return 'danger'" in response.text
    assert "const visibility = new Map" in response.text
    assert "readings-grid" in response.text
    assert "reading-detail-panel" in response.text
    assert "click any row on the left" in response.text
    assert "selected-row" in response.text
    assert "O₂ now + today" in response.text
    assert "Crypto" in response.text
    assert 'id="installApp"' in response.text
    assert response.text.index("aria-label=\"At a glance\"") < response.text.index("id=\"vitalsChart\"")
    assert 'id="rollupChart"' not in response.text
    assert 'id="stateChart"' not in response.text
    assert response.text.index("Readings table") < response.text.index("Selected reading")
    assert "O₂ now + today" in response.text
    assert "Heart rate" in response.text
    assert response.text.index('id="latestOxygen"') < response.text.index('id="sleepTotal"') < response.text.index('id="cryptoCard"')
    assert "sleepTotal" in response.text
    assert "Crypto" in response.text
    assert "state-legend" not in response.text


def test_pwa_assets_are_served(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    app = create_app(store=store, settings=_test_settings(), start_poller=False)

    with TestClient(app) as client:
        manifest = client.get("/manifest.webmanifest")
        worker = client.get("/sw.js")
        icon = client.get("/icon-192.png")

    assert manifest.status_code == 200
    assert manifest.json()["id"] == "/"
    assert manifest.json()["display"] == "standalone"
    assert manifest.json()["start_url"] == "/"
    assert worker.status_code == 200
    assert "CACHE_NAME" in worker.text
    assert icon.status_code == 200
    assert icon.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_share_link_serves_read_only_dashboard_and_api_without_basic_auth(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    await store.insert_reading(
        normalize_reading(
            {
                "heart_rate": 120,
                "oxygen_saturation": 98,
                "last_updated": "2026-07-02T01:00:00Z",
                "raw": {"secretish": "not exposed"},
            },
            "AC123",
        )
    )
    token = "share-token-with-enough-length"
    settings = _test_settings(
        owlet_basic_auth_username="parent",
        owlet_basic_auth_password="secret-pass",
        owlet_share_token=token,
    )
    app = create_app(store=store, settings=settings, start_poller=False)

    with TestClient(app) as client:
        dashboard = client.get(f"/share/{token}")
        readings = client.get(f"/share/{token}/api/readings?include_raw=true")
        summary = client.get(f"/share/{token}/api/summary?limit=100000&hours=24")
        insights = client.get(f"/share/{token}/api/insights?limit=100000&hours=24")
        rollups = client.get(f"/share/{token}/api/rollups?limit=100000&bucket=hour&hours=24")
        wrong = client.get("/share/wrong-token-with-enough-length")
        normal_api = client.get("/api/health")

    assert dashboard.status_code == 200
    assert f'const API_BASE = "/share/{token}";' in dashboard.text
    assert "Shared read-only view" in dashboard.text
    assert 'rel="manifest"' not in dashboard.text
    assert "serviceWorker.register" in dashboard.text
    assert readings.status_code == 200
    assert readings.json()[0]["heart_rate"] == 120
    assert "raw" not in readings.json()[0]
    assert summary.status_code == 200
    assert insights.status_code == 200
    assert rollups.status_code == 200
    assert rollups.json()["bucket"] == "hour"
    assert wrong.status_code == 404
    assert normal_api.status_code == 401


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
