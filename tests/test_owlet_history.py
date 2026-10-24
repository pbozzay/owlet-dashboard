import asyncio
import contextlib
import json
import sqlite3
import time
from datetime import UTC, datetime

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from app import owlet_history as oh
from app.config import Settings
from app.models import normalize_reading
from app.poller import Poller
from app.store import ReadingStore

# 2026-10-20T19:00:00Z
T0 = 1792522800
DAY = 86400


def vitals_payload(*windows):
    """windows: (start, first_reading, last_reading, heart_rate_avg) tuples."""
    n = len(windows)
    return {
        "data": {
            "timeWindowStartTimes": [w[0] for w in windows],
            "firstReadingTimes": [w[1] for w in windows],
            "lastReadingTimes": [w[2] for w in windows],
            "counts": {"validSamples": [419] * n},
            "heartRate": {"avg": [w[3] for w in windows], "min": [104] * n, "max": [140] * n},
            "oxygen": {"avg": [97.25] * n, "min": [94] * n, "max": [99] * n},
            "movement": {"avg": [1.333] * n},
        },
        "cameraData": None,
    }


def sleep_payload(*states):
    """states: (epoch, code) tuples, one per minute."""
    return {
        "data": {
            "timeWindowStartTimes": [s[0] for s in states],
            "sleepStates": [s[1] for s in states],
            "bodyPositions": [],
            "positionTimes": [],
        },
        "sessions": [],
    }


ONE_WINDOW = vitals_payload((T0, T0 + 5, T0 + 595, 121.4375))


def iso(epoch):
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def test_chunk_ranges_splits_into_weekly_windows():
    assert oh.chunk_ranges(0, 20 * DAY) == [(0, 7 * DAY), (7 * DAY, 14 * DAY), (14 * DAY, 20 * DAY)]
    assert oh.chunk_ranges(5, 5) == []


def test_each_window_becomes_one_minute_per_minute_it_covers_carrying_its_averages():
    minutes = oh.history_minutes([ONE_WINDOW], [])
    assert [m.recorded_at.isoformat() for m in minutes] == [iso(T0 + i * 60) for i in range(10)]
    assert {m.heart_rate for m in minutes} == {121.4}
    assert (minutes[0].oxygen_saturation, minutes[0].movement) == (97.2, 1.33)


def test_minutes_carry_the_sleep_state_owlet_recorded_for_that_minute():
    minutes = oh.history_minutes([ONE_WINDOW], [sleep_payload((T0, 8), (T0 + 60, 15))])
    assert [m.sleep_state for m in minutes[:3]] == ["8", "15", None]


def test_a_minute_shared_by_two_overlapping_windows_is_assigned_once():
    # Real windows are ~602 s apart and the last reading can land in the next window.
    payload = vitals_payload((T0, T0 + 5, T0 + 601, 120.0), (T0 + 602, T0 + 605, T0 + 1195, 130.0))
    times = [m.recorded_at for m in oh.history_minutes([payload], [])]
    assert len(times) == len(set(times)) == 20
    assert times == sorted(times)


def test_the_same_window_returned_by_two_requests_is_counted_once():
    assert len(oh.history_minutes([ONE_WINDOW, ONE_WINDOW], [])) == 10


def test_minutes_are_tagged_as_history_and_keep_the_window_extremes():
    raw = oh.history_minutes([ONE_WINDOW], [])[0].raw
    assert raw["source"] == oh.HISTORY_SOURCE
    assert (raw["heart_rate_min"], raw["heart_rate_max"], raw["valid_samples"]) == (104, 140, 419)


def test_empty_or_missing_payloads_give_no_minutes():
    assert oh.history_minutes([{"data": None}, {}, None], [None]) == []


def test_minutes_with_live_data_in_the_same_or_an_adjacent_minute_are_dropped():
    kept = oh.without_live(oh.history_minutes([ONE_WINDOW], []), live_minutes=[T0 + 300])
    times = [m.recorded_at.isoformat() for m in kept]
    assert len(times) == 7  # drops T0+240, T0+300, T0+360
    assert iso(T0 + 180) in times and iso(T0 + 300) not in times
    assert iso(T0 + 420) in times


class FakeOwlet:
    """Stands in for Google's token service and Owlet's history services."""

    def __init__(self, vitals=ONE_WINDOW, sleep=None, profiles=None):
        self.vitals, self.sleep = vitals, sleep or sleep_payload()
        self.profiles = profiles or [{"name": "accounts/acct1/profiles/prof1"}]
        self.calls: list[tuple[str, str, dict, dict | None]] = []

    async def __call__(self, method, url, headers, form=None):
        self.calls.append((method, url, headers, form))
        if "securetoken.googleapis.com" in url:
            return {
                "id_token": "id-token",
                "user_id": "acct1",
                "refresh_token": form["refreshToken"],
            }
        if url.endswith("/profiles"):
            return {"profiles": self.profiles}
        if "/vitals?" in url:
            return self.vitals
        if "/sleep?" in url:
            return self.sleep
        raise AssertionError(f"unexpected request {method} {url}")

    def urls(self, fragment):
        return [url for _, url, _, _ in self.calls if fragment in url]


@pytest.mark.asyncio
async def test_client_signs_in_with_the_refresh_token_and_reads_eu_history_services():
    fake = FakeOwlet()
    client = oh.OwletHistoryClient("europe", "refresh-1", fetch=fake)
    assert await client.vitals(T0, T0 + DAY) == ONE_WINDOW
    await client.sleep(T0, T0 + DAY)

    (token_call,) = [c for c in fake.calls if "securetoken" in c[1]]
    assert token_call[3] == {"grantType": "refresh_token", "refreshToken": "refresh-1"}
    assert fake.urls("https://accounts.eu.owletdata.com/v2/accounts/acct1/profiles")
    (vitals_url,) = fake.urls("/vitals?")
    assert vitals_url.startswith(
        "https://vital-data.eu.owletdata.com/v1/accounts/acct1/profiles/prof1/vitals?"
    )
    assert "resolution=600" in vitals_url and "version=smartSock4" in vitals_url
    assert fake.urls("https://sleep-data.eu.owletdata.com/v1/accounts/acct1/profiles/prof1/sleep?")
    assert all(
        c[2].get("Authorization") == "Bearer id-token"
        for c in fake.calls
        if "owletdata.com" in c[1]
    )


@pytest.mark.asyncio
async def test_client_uses_world_hosts_for_world_accounts_and_signs_in_once():
    fake = FakeOwlet()
    client = oh.OwletHistoryClient("world", "refresh-1", fetch=fake)
    await client.vitals(T0, T0 + DAY)
    await client.vitals(T0 + DAY, T0 + 2 * DAY)
    assert fake.urls("https://vital-data.owletdata.com/")
    profile_lookups = [url for url in fake.urls("/profiles") if url.endswith("/profiles")]
    assert len(fake.urls("securetoken")) == 1 and len(profile_lookups) == 1


@pytest.mark.asyncio
async def test_client_refuses_a_profile_listing_it_does_not_understand():
    client = oh.OwletHistoryClient(
        "europe", "refresh-1", fetch=FakeOwlet(profiles=[{"name": "something-else"}])
    )
    with pytest.raises(oh.OwletHistoryError):
        await client.vitals(T0, T0 + DAY)


@contextlib.asynccontextmanager
async def owlet_stub(responses):
    """A local HTTP server answering with the given (status, headers, body) in order."""
    requests: list[str] = []

    async def handler(request):
        requests.append(request.method + " " + request.path)
        status, headers, body = responses.pop(0)
        return web.Response(status=status, headers=headers, text=json.dumps(body))

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    server = TestServer(app)
    await server.start_server()
    try:
        yield server, requests
    finally:
        await server.close()


def client_with_recorded_sleeps():
    waits: list[float] = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    return oh.OwletHistoryClient("europe", "refresh-1", sleep=fake_sleep), waits


@pytest.mark.asyncio
async def test_http_fetch_waits_out_a_rate_limit_then_succeeds():
    client, waits = client_with_recorded_sleeps()
    async with owlet_stub([(429, {"x-ratelimit-reset": "7"}, {}), (200, {}, {"ok": 1})]) as (
        server,
        requests,
    ):
        assert await client._http_fetch("GET", str(server.make_url("/v")), {}, None) == {"ok": 1}
    await client.close()
    assert len(requests) == 2 and waits == [8]


@pytest.mark.asyncio
async def test_http_fetch_caps_rate_limit_waits_and_reads_epoch_style_resets():
    client, waits = client_with_recorded_sleeps()
    soon = str(int(time.time()) + 30)
    async with owlet_stub(
        [
            (429, {"x-ratelimit-reset": "99999"}, {}),
            (429, {"x-ratelimit-reset": soon}, {}),
            (200, {}, {}),
        ]
    ) as (server, _):
        await client._http_fetch("GET", str(server.make_url("/v")), {}, None)
    await client.close()
    assert waits[0] == oh.MAX_RATE_LIMIT_WAIT_SECONDS
    assert 25 <= waits[1] <= 35


@pytest.mark.asyncio
async def test_http_fetch_does_not_retry_client_errors_and_names_only_the_host():
    client, waits = client_with_recorded_sleeps()
    async with owlet_stub([(401, {}, {})]) as (server, requests):
        with pytest.raises(oh.OwletHistoryError) as err:
            await client._http_fetch(
                "GET", str(server.make_url("/v1/accounts/secret-id")), {}, None
            )
    await client.close()
    assert len(requests) == 1 and waits == []
    assert "secret-id" not in str(err.value) and "401" in str(err.value)


@pytest.mark.asyncio
async def test_http_fetch_gives_up_after_repeated_server_errors_and_closes_its_session():
    client, waits = client_with_recorded_sleeps()
    async with owlet_stub([(503, {}, {})] * 4) as (server, requests):
        with pytest.raises(oh.OwletHistoryError):
            await client._http_fetch("GET", str(server.make_url("/v")), {}, None)
    session = client._session
    await client.close()
    assert len(requests) == 4 and waits == [5, 10, 15]
    assert session.closed


async def seeded_store(tmp_path, *, live_at=None):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    account = await store.create_account(
        email="parent@example.test", region="europe", refresh_token="refresh-1"
    )
    live = normalize_reading(
        {"hr": 130, "ox": 96, "data_updated_at": iso(live_at or T0 + 30 * DAY)}, "DSN1"
    )
    await store.insert_reading(live, account_id=account["id"])
    return store, int(account["id"])


def rows(store):
    with sqlite3.connect(store.db_path) as con:
        return con.execute(
            "SELECT recorded_at, heart_rate, json_extract(raw_json, '$.source') FROM readings ORDER BY recorded_at"
        ).fetchall()


async def no_pause():
    return None


@pytest.mark.asyncio
async def test_backfill_adds_history_minutes_for_the_sock(tmp_path):
    store, account_id = await seeded_store(tmp_path)
    client = oh.OwletHistoryClient("europe", "refresh-1", fetch=FakeOwlet())
    added = await oh.backfill_account(
        store, account_id, "DSN1", client, days=7, end=T0 + DAY, pause=no_pause
    )
    history = [r for r in rows(store) if r[2] == oh.HISTORY_SOURCE]
    assert added == len(history) == 10


@pytest.mark.asyncio
async def test_store_upsert_leaves_a_live_reading_at_the_same_minute_untouched(tmp_path):
    live_at = T0 + 30 * DAY
    store, account_id = await seeded_store(tmp_path, live_at=live_at)
    clash = oh.HistoryMinute(
        datetime.fromtimestamp(live_at, UTC), 99.0, 99.0, 0.0, None, {"source": oh.HISTORY_SOURCE}
    )
    other = oh.HistoryMinute(
        datetime.fromtimestamp(live_at + 60, UTC),
        98.0,
        98.0,
        0.0,
        None,
        {"source": oh.HISTORY_SOURCE},
    )
    written = await store.upsert_history_minutes(account_id, "DSN1", [clash, other])
    assert written == 1
    assert (iso(live_at), 130.0, None) in rows(store)


@pytest.mark.asyncio
async def test_store_reports_live_minutes_as_distinct_minute_buckets(tmp_path):
    store, account_id = await seeded_store(tmp_path, live_at=T0 + 5)
    for offset in (10, 65):
        reading = normalize_reading(
            {"hr": 130, "ox": 96, "data_updated_at": iso(T0 + offset)}, "DSN1"
        )
        await store.insert_reading(reading, account_id=account_id)
    start, end = datetime.fromtimestamp(T0 - 60, UTC), datetime.fromtimestamp(T0 + 600, UTC)
    assert await store.live_reading_minutes(account_id, "DSN1", start, end) == [T0, T0 + 60]


@pytest.mark.asyncio
async def test_backfill_never_overwrites_or_crowds_live_readings(tmp_path):
    store, account_id = await seeded_store(tmp_path, live_at=T0 + 300)
    client = oh.OwletHistoryClient("europe", "refresh-1", fetch=FakeOwlet())
    await oh.backfill_account(
        store, account_id, "DSN1", client, days=7, end=T0 + DAY, pause=no_pause
    )
    all_rows = rows(store)
    assert (iso(T0 + 300), 130.0, None) in all_rows
    assert len([r for r in all_rows if r[2] == oh.HISTORY_SOURCE]) == 7


@pytest.mark.asyncio
async def test_rerunning_refreshes_values_and_keeps_older_history(tmp_path):
    store, account_id = await seeded_store(tmp_path)
    older = OwletHistoryClientFor(
        vitals_payload((T0 - 7 * DAY, T0 - 7 * DAY + 5, T0 - 7 * DAY + 595, 110.0))
    )
    await oh.backfill_account(
        store, account_id, "DSN1", older, days=14, end=T0 + DAY, pause=no_pause
    )
    revised = OwletHistoryClientFor(vitals_payload((T0, T0 + 5, T0 + 595, 125.0)))
    await oh.backfill_account(
        store, account_id, "DSN1", revised, days=7, end=T0 + DAY, pause=no_pause
    )
    revised_again = OwletHistoryClientFor(vitals_payload((T0, T0 + 5, T0 + 595, 126.0)))
    await oh.backfill_account(
        store, account_id, "DSN1", revised_again, days=7, end=T0 + DAY, pause=no_pause
    )

    history = [r for r in rows(store) if r[2] == oh.HISTORY_SOURCE]
    assert len(history) == 20
    assert {r[1] for r in history if r[0] >= iso(T0)} == {126.0}


def OwletHistoryClientFor(vitals):
    return oh.OwletHistoryClient("europe", "refresh-1", fetch=FakeOwlet(vitals=vitals))


@pytest.mark.asyncio
async def test_deleting_history_leaves_live_readings(tmp_path):
    store, account_id = await seeded_store(tmp_path)
    await oh.backfill_account(
        store,
        account_id,
        "DSN1",
        OwletHistoryClientFor(ONE_WINDOW),
        days=7,
        end=T0 + DAY,
        pause=no_pause,
    )
    assert await store.delete_history_minutes() == 10
    assert [r[2] for r in rows(store)] == [None]


class RecordingClient:
    """Fake OwletHistoryClient that records how far back each run reached."""

    instances: list["RecordingClient"] = []

    def __init__(self, region, refresh_token):
        self.region, self.refresh_token, self.vitals_calls = region, refresh_token, 0
        RecordingClient.instances.append(self)

    async def vitals(self, start, end):
        self.vitals_calls += 1
        return ONE_WINDOW

    async def sleep(self, start, end):
        return sleep_payload()

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_first_run_reaches_far_back_and_later_runs_only_refresh_recent_days(tmp_path):
    store, account_id = await seeded_store(tmp_path)
    RecordingClient.instances = []
    job = oh.HistoryBackfill(
        store,
        account_id,
        "europe",
        refresh_token=lambda: "refresh-1",
        device_serial=lambda: "DSN1",
        initial_days=90,
        recent_days=7,
        client_factory=RecordingClient,
        pause=no_pause,
    )
    assert await job.run_once() == 10
    await job.run_once()
    first, later = RecordingClient.instances
    # 90 days vs 7 days, in weekly requests
    assert (first.vitals_calls, later.vitals_calls) == (13, 1)
    assert first.region == "europe" and first.refresh_token == "refresh-1"
    state = await store.history_backfill_state(account_id)
    assert state["days"] == 7 and state["minutes"] == 10 and "completed_at" in state


def recording_job(store, account_id, **overrides):
    options = dict(
        refresh_token=lambda: "refresh-1",
        device_serial=lambda: "DSN1",
        initial_days=90,
        recent_days=7,
        client_factory=RecordingClient,
        pause=no_pause,
    )
    options.update(overrides)
    return oh.HistoryBackfill(store, account_id, "europe", **options)


@pytest.mark.asyncio
async def test_a_first_run_that_finds_nothing_to_add_still_counts_as_done(tmp_path):
    # live data for every minute Owlet will return, so nothing gets written
    store, account_id = await seeded_store(tmp_path, live_at=T0)
    for offset in range(60, 600, 60):
        reading = normalize_reading(
            {"hr": 130, "ox": 96, "data_updated_at": iso(T0 + offset)}, "DSN1"
        )
        await store.insert_reading(reading, account_id=account_id)
    RecordingClient.instances = []
    job = recording_job(store, account_id)
    assert await job.run_once() == 0
    assert await job.run_once() == 0
    first, later = RecordingClient.instances
    assert (first.vitals_calls, later.vitals_calls) == (13, 1)


@pytest.mark.asyncio
async def test_a_failed_first_run_is_repeated_in_full(tmp_path):
    store, account_id = await seeded_store(tmp_path)
    RecordingClient.instances = []

    class FlakyClient(RecordingClient):
        async def vitals(self, start, end):
            if len(RecordingClient.instances) == 1:
                raise oh.OwletHistoryError("vital-data answered HTTP 503")
            return await super().vitals(start, end)

    job = recording_job(store, account_id, client_factory=FlakyClient)
    with pytest.raises(oh.OwletHistoryError):
        await job.run_once()
    assert await store.history_backfill_state(account_id) is None
    assert await job.run_once() == 10
    assert RecordingClient.instances[1].vitals_calls == 13


@pytest.mark.asyncio
async def test_job_waits_until_it_has_a_login_and_a_sock(tmp_path):
    store, account_id = await seeded_store(tmp_path)
    RecordingClient.instances = []
    job = oh.HistoryBackfill(
        store,
        account_id,
        "europe",
        refresh_token=lambda: None,
        device_serial=lambda: "DSN1",
        client_factory=RecordingClient,
        pause=no_pause,
    )
    assert await job.run_once() == 0
    assert RecordingClient.instances == []


@pytest.mark.asyncio
async def test_poller_runs_the_history_job_alongside_polling_and_stops_it(tmp_path):
    store, account_id = await seeded_store(tmp_path)

    class CountingJob:
        runs = 0

        async def run_once(self):
            CountingJob.runs += 1
            return 0

    async def read_once():
        return normalize_reading({"hr": 120, "ox": 97}, "DSN1")

    poller = Poller(
        store,
        read_once,
        interval_seconds=3600,
        account_id=account_id,
        history=CountingJob(),
        history_interval_seconds=0.01,
        history_initial_delay_seconds=0,
    )
    poller.start()
    for _ in range(100):
        if CountingJob.runs >= 2:
            break
        await asyncio.sleep(0.01)
    await poller.stop()
    runs_at_stop = CountingJob.runs
    await asyncio.sleep(0.05)
    assert runs_at_stop >= 2
    assert CountingJob.runs == runs_at_stop


@pytest.mark.asyncio
async def test_a_failed_history_run_is_retried_well_before_the_next_daily_run(tmp_path):
    store, account_id = await seeded_store(tmp_path)

    class FlakyJob:
        runs = 0

        async def run_once(self):
            FlakyJob.runs += 1
            if FlakyJob.runs == 1:
                raise oh.OwletHistoryError("vital-data answered HTTP 503")
            return 0

    async def read_once():
        return normalize_reading({"hr": 120, "ox": 97}, "DSN1")

    poller = Poller(
        store,
        read_once,
        interval_seconds=3600,
        account_id=account_id,
        history=FlakyJob(),
        history_interval_seconds=3600,
        history_retry_seconds=0.01,
        history_initial_delay_seconds=0,
    )
    poller.start()
    for _ in range(100):
        if FlakyJob.runs >= 2:
            break
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.05)
    await poller.stop()
    assert FlakyJob.runs == 2  # one retry, then back to the daily interval


def test_history_backfill_setting_can_be_turned_off():
    assert Settings(_env_file=None).history_days == 90  # type: ignore[call-arg]
    assert Settings(_env_file=None, HISTORY_BACKFILL=False).history_days == 0  # type: ignore[call-arg]
    assert Settings(_env_file=None, HISTORY_BACKFILL_DAYS=30).history_days == 30  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_command_line_remove_deletes_only_backfilled_history(tmp_path, monkeypatch, capsys):
    store, account_id = await seeded_store(tmp_path)
    await oh.backfill_account(
        store,
        account_id,
        "DSN1",
        OwletHistoryClientFor(ONE_WINDOW),
        days=7,
        end=T0 + DAY,
        pause=no_pause,
    )
    await store.set_history_backfill_state(
        account_id, {"completed_at": iso(T0), "days": 90, "minutes": 10}
    )
    monkeypatch.setenv("DATABASE_PATH", str(store.db_path))
    assert await oh.main(["--remove"]) == 0
    assert "Removed 10" in capsys.readouterr().out
    assert [r[2] for r in rows(store)] == [None]
    assert await store.history_backfill_state(account_id) is None


@pytest.mark.asyncio
async def test_command_line_can_target_one_account(tmp_path, monkeypatch, capsys):
    store, first = await seeded_store(tmp_path)
    second = int((await store.create_account(email="other@example.test", refresh_token="r2"))["id"])
    for account_id in (first, second):
        await oh.backfill_account(
            store,
            account_id,
            "DSN1",
            OwletHistoryClientFor(ONE_WINDOW),
            days=7,
            end=T0 + DAY,
            pause=no_pause,
        )
    monkeypatch.setenv("DATABASE_PATH", str(store.db_path))
    assert await oh.main(["--remove", "--account", str(second)]) == 0
    assert "Removed 10" in capsys.readouterr().out
    assert len([r for r in rows(store) if r[2] == oh.HISTORY_SOURCE]) == 10


@pytest.mark.asyncio
async def test_command_line_backfills_each_linked_sock(tmp_path, monkeypatch, capsys):
    store, account_id = await seeded_store(tmp_path)
    RecordingClient.instances = []
    monkeypatch.setattr(oh, "OwletHistoryClient", RecordingClient)
    monkeypatch.setattr(oh, "PAUSE_SECONDS", 0)
    monkeypatch.setenv("DATABASE_PATH", str(store.db_path))
    assert await oh.main(["--days", "7"]) == 0
    assert "10 minutes" in capsys.readouterr().out
    (client,) = RecordingClient.instances
    assert (client.region, client.refresh_token, client.vitals_calls) == ("europe", "refresh-1", 1)


def test_minute_raw_payload_is_json_and_names_its_window():
    minute = oh.history_minutes([ONE_WINDOW], [])[0]
    assert json.loads(json.dumps(minute.raw))["window_start"] == iso(T0)
    assert minute.recorded_at == datetime.fromtimestamp(T0, UTC)
