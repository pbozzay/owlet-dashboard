"""Fill collection gaps from Owlet's own history services.

The live feed this app polls (Ayla device properties) remembers only the last few
minutes, so time the collector was off used to be a permanent gap. The Owlet app's
History screen comes from separate services that keep 10-minute vital averages and
minute-by-minute sleep states for weeks. This module pulls those, signed in with the
Firebase refresh token pyowletapi already stores (no password, live Ayla session
untouched), and stores them as one reading per minute because the charts break their
lines at gaps over 90 s. Backfilled rows carry raw_json "source" = HISTORY_SOURCE and
never replace or crowd live readings.

Run by hand with ``python -m app.owlet_history`` (``--days N``, ``--remove``,
``--account ID``).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
import urllib.parse
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from pyowletapi.const import REGION_INFO

from app.config import Settings
from app.store import HISTORY_SOURCE, ReadingStore

logger = logging.getLogger(__name__)

__all__ = [
    "HISTORY_SOURCE",
    "HistoryBackfill",
    "HistoryMinute",
    "OwletHistoryClient",
    "backfill_account",
]

DEVICE_VERSION = "smartSock4"  # what the Owlet app sends for a Dream Sock; "SS3" is rejected
CHUNK_SECONDS = 7 * 86400
PAUSE_SECONDS = 2.5  # sleep-data allows ~25 requests/min, vital-data ~45/min
RECENT_DAYS = 7  # daily refresh window once the first run has completed
MAX_RATE_LIMIT_WAIT_SECONDS = 120
MINUTE = 60

# pyowletapi signs in as the Android app; its refresh token only works with that identity.
_ANDROID_HEADERS = {
    "X-Android-Package": "com.owletcare.owletcare",
    "X-Android-Cert": "2A3BC26DB0B8B0792DBE28E6FFDC2598F9B12B74",
}

Fetch = Callable[[str, str, dict[str, str], dict[str, str] | None], Awaitable[Any]]
Sleep = Callable[[float], Awaitable[None]]


class OwletHistoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class HistoryMinute:
    recorded_at: datetime
    heart_rate: float | None
    oxygen_saturation: float | None
    movement: float | None
    sleep_state: str | None
    raw: dict[str, Any]


def chunk_ranges(start: int, end: int, step: int = CHUNK_SECONDS) -> list[tuple[int, int]]:
    ranges = []
    while start < end:
        ranges.append((start, min(start + step, end)))
        start += step
    return ranges


def _data(payload: Any) -> dict[str, Any]:
    return (payload.get("data") or {}) if isinstance(payload, dict) else {}


def _at(values: list[Any] | None, index: int) -> Any:
    return values[index] if values and index < len(values) else None


def _round(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


def _windows(payload: Any) -> Iterable[dict[str, Any]]:
    data = _data(payload)
    heart, oxygen = data.get("heartRate") or {}, data.get("oxygen") or {}
    movement = data.get("movement") or {}
    valid = (data.get("counts") or {}).get("validSamples")
    for i, start in enumerate(data.get("timeWindowStartTimes") or []):
        yield {
            "start": int(start),
            "first": _at(data.get("firstReadingTimes"), i),
            "last": _at(data.get("lastReadingTimes"), i),
            "heart_rate": _round(_at(heart.get("avg"), i), 1),
            "oxygen": _round(_at(oxygen.get("avg"), i), 1),
            "movement": _round(_at(movement.get("avg"), i), 2),
            "raw": {
                "source": HISTORY_SOURCE,
                "window_start": datetime.fromtimestamp(int(start), UTC).isoformat(),
                "heart_rate_min": _at(heart.get("min"), i),
                "heart_rate_max": _at(heart.get("max"), i),
                "oxygen_min": _at(oxygen.get("min"), i),
                "oxygen_max": _at(oxygen.get("max"), i),
                "valid_samples": _at(valid, i),
            },
        }


def history_minutes(
    vitals_payloads: Iterable[Any], sleep_payloads: Iterable[Any]
) -> list[HistoryMinute]:
    """Expand 10-minute windows into one reading per minute, sorted and unique.

    Each minute carries its window's averages and that minute's sleep state. Windows
    returned by overlapping requests are merged, and because Owlet's windows are ~602 s
    apart (not 600), a boundary minute is given only to the earlier window.
    """
    windows = {
        window["start"]: window for payload in vitals_payloads for window in _windows(payload)
    }
    sleep_by_minute: dict[int, Any] = {}
    for payload in sleep_payloads:
        data = _data(payload)
        for t, code in zip(
            data.get("timeWindowStartTimes") or [], data.get("sleepStates") or [], strict=False
        ):
            sleep_by_minute[int(t) - int(t) % MINUTE] = code

    minutes: list[HistoryMinute] = []
    next_free: int | None = None
    for start in sorted(windows):
        window = windows[start]
        first = int(window["first"] if window["first"] is not None else start)
        last = int(window["last"] if window["last"] is not None else start + 599)
        first -= first % MINUTE
        if next_free is not None:
            first = max(first, next_free)
        next_free = max(next_free or 0, last - last % MINUTE + MINUTE)
        for minute in range(first, last - last % MINUTE + 1, MINUTE):
            code = sleep_by_minute.get(minute)
            minutes.append(
                HistoryMinute(
                    recorded_at=datetime.fromtimestamp(minute, UTC),
                    heart_rate=window["heart_rate"],
                    oxygen_saturation=window["oxygen"],
                    movement=window["movement"],
                    sleep_state=None if code is None else str(code),
                    raw=window["raw"],
                )
            )
    return minutes


def without_live(minutes: list[HistoryMinute], live_minutes: Iterable[int]) -> list[HistoryMinute]:
    """Drop minutes that have live data in the same or an adjacent minute."""
    live = set(live_minutes)
    return [
        m
        for m in minutes
        if not any(
            int(m.recorded_at.timestamp()) + offset in live for offset in (-MINUTE, 0, MINUTE)
        )
    ]


def _retry_wait(reset_header: str | None, attempt: int) -> int:
    """Owlet sends x-ratelimit-reset as seconds remaining; an epoch-style value is read as
    an absolute time. Capped so an unexpected header can't park the job for hours."""
    if reset_header and reset_header.isdigit():
        value = int(reset_header)
        seconds = value - int(time.time()) if value > 10**9 else value
        return max(1, min(seconds + 1, MAX_RATE_LIMIT_WAIT_SECONDS))
    return min(5 * attempt, MAX_RATE_LIMIT_WAIT_SECONDS)


class OwletHistoryClient:
    """Reads Owlet's vital-data and sleep-data services for one account's first baby profile."""

    def __init__(
        self,
        region: str,
        refresh_token: str,
        *,
        fetch: Fetch | None = None,
        sleep: Sleep = asyncio.sleep,
        timezone: str = "UTC",
    ):
        if region not in REGION_INFO:
            raise ValueError(f"unknown Owlet region {region!r}")
        self.region = region
        self._refresh_token = refresh_token
        self._suffix = ".eu" if region == "europe" else ""
        self._timezone = timezone
        self._fetch = fetch or self._http_fetch
        self._sleep = sleep
        self._session: aiohttp.ClientSession | None = None
        self._id_token: str | None = None
        self._profile_path: str | None = None

    async def vitals(self, start: int, end: int) -> Any:
        query = urllib.parse.urlencode(
            {"resolution": 600, "startTime": start, "endTime": end, "version": DEVICE_VERSION}
        )
        return await self._get(
            f"https://vital-data{self._suffix}.owletdata.com{await self._profile()}/vitals?{query}"
        )

    async def sleep(self, start: int, end: int) -> Any:
        query = urllib.parse.urlencode(
            {
                "startTime": start,
                "endTime": end,
                "timeZone": self._timezone,
                "returnBodyPositions": "True",
                "version": DEVICE_VERSION,
            }
        )
        return await self._get(
            f"https://sleep-data{self._suffix}.owletdata.com{await self._profile()}/sleep?{query}"
        )

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def _sign_in(self) -> str:
        """Firebase refresh token -> 1-hour ID token; returns the Owlet account id."""
        key = REGION_INFO[self.region]["apiKey"]
        payload = await self._fetch(
            "POST",
            f"https://securetoken.googleapis.com/v1/token?key={key}",
            dict(_ANDROID_HEADERS),
            {"grantType": "refresh_token", "refreshToken": self._refresh_token},
        )
        self._id_token = payload["id_token"]
        return str(payload["user_id"])

    async def _profile(self) -> str:
        if self._profile_path is None:
            account_id = await self._sign_in()
            payload = await self._get(
                f"https://accounts{self._suffix}.owletdata.com/v2/accounts/{account_id}/profiles"
            )
            profiles = (payload or {}).get("profiles") or []
            name = str(profiles[0].get("name") or "") if profiles else ""
            if not name.startswith("accounts/"):
                raise OwletHistoryError("no usable baby profile on this Owlet account")
            self._profile_path = f"/v1/{name}"  # accounts/<id>/profiles/<id>, as the APIs use
        return self._profile_path

    async def _get(self, url: str) -> Any:
        return await self._fetch("GET", url, {"Authorization": f"Bearer {self._id_token}"}, None)

    async def _http_fetch(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        form: dict[str, str] | None,
        attempts: int = 4,
    ) -> Any:
        """JSON over aiohttp, waiting out rate limits (429) and retrying 5xx."""
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))
        host = urllib.parse.urlsplit(url).netloc  # error messages name the host only
        attempt = 0
        while True:
            attempt += 1
            async with self._session.request(method, url, headers=headers, data=form) as response:
                if response.status < 400:
                    return await response.json(content_type=None)
                if (response.status != 429 and response.status < 500) or attempt == attempts:
                    raise OwletHistoryError(f"{host} answered HTTP {response.status}")
                reset = response.headers.get("x-ratelimit-reset") or response.headers.get(
                    "Retry-After"
                )
                wait = _retry_wait(reset, attempt)
            logger.warning("%s answered HTTP %s; retrying in %s s", host, response.status, wait)
            await self._sleep(wait)


async def _default_pause() -> None:
    await asyncio.sleep(PAUSE_SECONDS)


async def backfill_account(
    store: ReadingStore,
    account_id: int,
    device_serial: str,
    client: OwletHistoryClient,
    *,
    days: int,
    end: int | None = None,
    pause: Callable[[], Awaitable[None]] | None = None,
) -> int:
    """Fetch `days` of history ending at `end` (default now) and store it; returns rows written."""
    end = int(end if end is not None else time.time())
    pause = pause or _default_pause
    vitals, sleep = [], []
    chunks = chunk_ranges(end - days * 86400, end)
    for i, (start, stop) in enumerate(chunks):
        vitals.append(await client.vitals(start, stop))
        sleep.append(await client.sleep(start, stop))
        if i < len(chunks) - 1:
            await pause()
    minutes = history_minutes(vitals, sleep)
    if not minutes:
        return 0
    margin = timedelta(seconds=MINUTE)
    live = await store.live_reading_minutes(
        account_id, device_serial, minutes[0].recorded_at - margin, minutes[-1].recorded_at + margin
    )
    return await store.upsert_history_minutes(
        account_id, device_serial, without_live(minutes, live)
    )


async def _record_completed(store: ReadingStore, account_id: int, days: int, written: int) -> None:
    await store.set_history_backfill_state(
        account_id,
        {
            "completed_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "days": days,
            "minutes": written,
        },
    )


class HistoryBackfill:
    """The poller's daily history job for one linked account."""

    def __init__(
        self,
        store: ReadingStore,
        account_id: int,
        region: str,
        *,
        refresh_token: Callable[[], str | None],
        device_serial: Callable[[], str | None],
        initial_days: int = 90,
        recent_days: int = RECENT_DAYS,
        client_factory: Callable[[str, str], Any] = OwletHistoryClient,
        pause: Callable[[], Awaitable[None]] | None = None,
    ):
        self.store = store
        self.account_id = account_id
        self.region = region
        self.refresh_token = refresh_token
        self.device_serial = device_serial
        self.initial_days = initial_days
        self.recent_days = recent_days
        self.client_factory = client_factory
        self.pause = pause

    async def run_once(self) -> int:
        token, serial = self.refresh_token(), self.device_serial()
        if not token or not serial:
            return 0
        completed_before = await self.store.history_backfill_state(self.account_id)
        days = self.recent_days if completed_before else self.initial_days
        client = self.client_factory(self.region, token)
        try:
            written = await backfill_account(
                self.store, self.account_id, serial, client, days=days, pause=self.pause
            )
        finally:
            await client.close()
        await _record_completed(self.store, self.account_id, days, written)
        logger.info(
            "history backfill account_id=%s days=%s minutes=%s", self.account_id, days, written
        )
        return written


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.owlet_history",
        description="Backfill gaps from Owlet's history services (10-minute averages).",
    )
    parser.add_argument(
        "--days", type=int, help="how many days back (default: HISTORY_BACKFILL_DAYS)"
    )
    parser.add_argument(
        "--remove", action="store_true", help="delete backfilled history instead, then exit"
    )
    parser.add_argument("--account", type=int, help="only this dashboard account id")
    args = parser.parse_args(argv)
    settings = Settings()
    store = ReadingStore(settings.database_path)
    accounts = [
        account
        for account in await store.list_accounts()
        if args.account is None or int(account["id"]) == args.account
    ]
    if args.remove:
        removed = 0
        for account in accounts:
            removed += await store.delete_history_minutes(int(account["id"]))
            await store.set_history_backfill_state(int(account["id"]), None)
        print(f"Removed {removed} backfilled minutes.")
        return 0
    days = args.days or settings.history_backfill_days
    for account in accounts:
        account_id = int(account["id"])
        if account.get("status") != "active" or not account.get("refresh_token"):
            continue
        serial = await store.latest_live_device_serial(account_id)
        if not serial:
            print(f"account {account_id}: no live readings yet, skipped")
            continue
        client = OwletHistoryClient(
            str(account.get("region") or "world"), str(account["refresh_token"])
        )
        try:
            written = await backfill_account(store, account_id, serial, client, days=days)
        finally:
            await client.close()
        await _record_completed(store, account_id, days, written)
        print(f"account {account_id}: {written} minutes added or refreshed ({days} days)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
