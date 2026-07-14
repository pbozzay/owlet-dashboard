from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from app.models import OwletReading
from app.owlet_client import OwletClient
from app.quality import is_offline_reading
from app.store import ReadingStore

logger = logging.getLogger(__name__)

ReadOnce = Callable[[], Awaitable[OwletReading]]
TokenSnapshot = Callable[[], dict[str, Any]]


def _parse_clock(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, str) or ":" not in value:
        return None
    try:
        hour, minute = (int(part) for part in value.split(":", 1))
    except ValueError:
        return None
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return hour, minute
    return None


def _day_start_local(now_local: datetime, prefs: dict[str, Any]) -> datetime:
    """The day begins when the night ends (default 7 AM local)."""
    night_end = _parse_clock(prefs.get("night_end")) or (7, 0)
    start = now_local.replace(hour=night_end[0], minute=night_end[1], second=0, microsecond=0)
    if start > now_local:
        start -= timedelta(days=1)
    return start


def _fmt_duration(seconds: float) -> str:
    minutes = int(round(seconds / 60))
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


def _fmt_clock(moment: datetime) -> str:
    hour = moment.hour % 12 or 12
    return f"{hour}:{moment.minute:02d} {'PM' if moment.hour >= 12 else 'AM'}"


class Poller:
    def __init__(
        self,
        store: ReadingStore,
        read_once: ReadOnce,
        interval_seconds: int = 30,
        account_id: int | None = None,
        token_snapshot: TokenSnapshot | None = None,
    ):
        self.store = store
        self.read_once = read_once
        self.interval_seconds = interval_seconds
        self.account_id = account_id
        self.token_snapshot = token_snapshot
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._last_alert_o2: float | None = None
        self._last_alert_at = float("-inf")   # monotonic clock starts near 0 on fresh boots
        self._last_readiness_key: str | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="owlet-poller")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                reading = await self.read_once()
                await self.store.insert_reading(reading, account_id=self.account_id)
                await self._check_custom_alert(reading)
                await self._persist_tokens()
                logger.info(
                    "stored owlet reading serial=%s hr=%s spo2=%s",
                    reading.device_serial,
                    reading.heart_rate,
                    reading.oxygen_saturation,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Owlet poll failed; will retry")
            try:
                # The evening readiness report should still fire when the sock
                # is offline — it summarizes the day, not the current reading.
                await self._maybe_send_readiness()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Readiness report failed; will retry")
            await asyncio.sleep(self.interval_seconds)

    async def _check_custom_alert(self, reading: OwletReading) -> None:
        """User-configurable low-O2 alert: crossing below the account's chosen
        threshold writes a critical notification row, which the shell then
        surfaces as a bell item, badge, toast, and system notification."""
        if self.account_id is None:
            return
        if is_offline_reading(reading) or reading.oxygen_saturation is None:
            self._last_alert_o2 = None
            return
        value = float(reading.oxygen_saturation)
        previous = self._last_alert_o2
        self._last_alert_o2 = value
        try:
            account = await self.store.get_account(self.account_id)
        except KeyError:
            return
        prefs = account.get("dashboard_preferences") or {}
        threshold = prefs.get("o2_alert_threshold")
        if not isinstance(threshold, (int, float)) or threshold <= 0:
            return
        crossed = value < threshold and (previous is None or previous >= threshold)
        rate_limited = (asyncio.get_event_loop().time() - self._last_alert_at) < 600
        if not crossed or rate_limited:
            return
        self._last_alert_at = asyncio.get_event_loop().time()
        await self.store.insert_custom_notification(
            account_id=self.account_id,
            device_serial=reading.device_serial,
            recorded_at=reading.recorded_at,
            event_type="custom_low_oxygen",
            severity="critical",
            title=f"O2 dipped to {value:.0f}%",
            message=f"Below your {int(threshold)}% alert level.",
            heart_rate=reading.heart_rate,
            oxygen_saturation=value,
        )

    async def _maybe_send_readiness(self) -> None:
        """Evening prep report: at the user's chosen local time, summarize the
        day so far (awake time, naps, feeds) into an info notification. The
        recorded_at is the scheduled moment itself, so the unique notification
        index dedupes across poll ticks and restarts."""
        if self.account_id is None:
            return
        try:
            account = await self.store.get_account(self.account_id)
        except KeyError:
            return
        prefs = account.get("dashboard_preferences") or {}
        report_time = _parse_clock(prefs.get("readiness_report_time"))
        if report_time is None:
            return
        offset = prefs.get("tz_offset_minutes")
        tz = timezone(timedelta(minutes=int(offset) if isinstance(offset, (int, float)) else 0))
        now_local = datetime.now(tz)
        fire_local = now_local.replace(
            hour=report_time[0], minute=report_time[1], second=0, microsecond=0
        )
        # Not due yet, or so overdue (collector was down all evening) that a
        # "tonight's prep" ping would land mid-night and just be noise.
        if now_local < fire_local or now_local - fire_local > timedelta(hours=2):
            return
        fire_key = fire_local.astimezone(timezone.utc).isoformat()
        if self._last_readiness_key == fire_key:
            return
        self._last_readiness_key = fire_key
        day_start = _day_start_local(now_local, prefs)
        title, message, device_serial = await self._readiness_summary(day_start, now_local)
        await self.store.insert_custom_notification(
            account_id=self.account_id,
            device_serial=device_serial,
            recorded_at=fire_key,
            event_type="night_readiness",
            severity="info",
            title=title,
            message=message,
        )

    async def _readiness_summary(
        self, day_start: datetime, now_local: datetime
    ) -> tuple[str, str, str]:
        span_hours = max(1, int((now_local - day_start).total_seconds() // 3600) + 2)
        rows = await self.store.get_analysis_readings(
            hours=span_hours, account_ids=[self.account_id]
        )
        rows = [r for r in rows if r.recorded_at >= day_start]
        rows.sort(key=lambda r: r.recorded_at)
        awake_s = sleep_s = 0.0
        naps: list[tuple[datetime, datetime]] = []
        nap_start: datetime | None = None
        nap_end: datetime | None = None
        device_serial = rows[-1].device_serial if rows else "readiness"
        for prev, cur in zip(rows, rows[1:], strict=False):
            duration = min((cur.recorded_at - prev.recorded_at).total_seconds(), 300.0)
            state = None if prev.sleep_state is None else str(prev.sleep_state)
            if state == "1":
                awake_s += duration
            elif state in ("8", "15"):
                sleep_s += duration
            asleep = state in ("8", "15")
            if asleep:
                if nap_end is not None and (prev.recorded_at - nap_end).total_seconds() > 600:
                    if nap_start and (nap_end - nap_start).total_seconds() >= 900:
                        naps.append((nap_start, nap_end))
                    nap_start = None
                if nap_start is None:
                    nap_start = prev.recorded_at
                nap_end = cur.recorded_at
        if nap_start and nap_end and (nap_end - nap_start).total_seconds() >= 900:
            naps.append((nap_start, nap_end))
        feeds = [
            e
            for e in await self.store.get_care_events(
                hours=span_hours, account_ids=[self.account_id]
            )
            if e.get("kind") == "Feeding"
            and datetime.fromisoformat(str(e["at"])) >= day_start
        ]
        tz = now_local.tzinfo
        parts = []
        if naps:
            nap_total = sum((end - start).total_seconds() for start, end in naps)
            last_end = max(end for _, end in naps).astimezone(tz)
            parts.append(
                f"{len(naps)} nap{'s' if len(naps) != 1 else ''} totalling "
                f"{_fmt_duration(nap_total)}, the last ending {_fmt_clock(last_end)}."
            )
        else:
            parts.append("No naps registered today.")
        if feeds:
            last_feed = max(
                datetime.fromisoformat(str(e["at"])) for e in feeds
            ).astimezone(tz)
            parts.append(
                f"{len(feeds)} feed{'s' if len(feeds) != 1 else ''} logged, "
                f"last at {_fmt_clock(last_feed)}."
            )
        title = f"Tonight's prep — {_fmt_duration(awake_s)} awake today"
        return title, " ".join(parts), device_serial

    async def _persist_tokens(self) -> None:
        if self.account_id is None or self.token_snapshot is None:
            return
        tokens = self.token_snapshot()
        await self.store.update_account_tokens(
            self.account_id,
            api_token=tokens.get("api_token"),
            api_token_expiry=tokens.get("expiry"),
            refresh_token=tokens.get("refresh"),
            status="active",
        )


async def create_account_poller(
    store: ReadingStore,
    account: dict[str, Any],
    interval_seconds: int,
    *,
    password: str | None = None,
) -> tuple[Poller, OwletClient]:
    client = OwletClient(
        email=account.get("email") or None,
        password=password,
        region=str(account.get("region") or "world"),
        api_token=account.get("api_token"),
        api_token_expiry=account.get("api_token_expiry"),
        refresh_token=account.get("refresh_token"),
    )
    await client.connect()
    client.discard_password()
    await store.update_account_tokens(
        int(account["id"]),
        api_token=client.tokens.get("api_token"),
        api_token_expiry=client.tokens.get("expiry"),
        refresh_token=client.tokens.get("refresh"),
        status="active",
    )
    poller = Poller(
        store=store,
        read_once=client.read_once,
        interval_seconds=interval_seconds,
        account_id=int(account["id"]),
        token_snapshot=lambda: client.tokens,
    )
    return poller, client


async def create_owlet_poller(
    store: ReadingStore,
    email: str,
    password: str,
    region: str,
    interval_seconds: int,
    account_id: int,
) -> tuple[Poller, OwletClient]:
    account = {
        "id": account_id,
        "email": email,
        "region": region,
        "api_token": None,
        "api_token_expiry": None,
        "refresh_token": None,
    }
    return await create_account_poller(store, account, interval_seconds, password=password)
