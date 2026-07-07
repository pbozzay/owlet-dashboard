from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.models import OwletReading
from app.owlet_client import OwletClient
from app.store import ReadingStore

logger = logging.getLogger(__name__)

ReadOnce = Callable[[], Awaitable[OwletReading]]
TokenSnapshot = Callable[[], dict[str, Any]]


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
            await asyncio.sleep(self.interval_seconds)

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
    account_id: int | None = None,
) -> tuple[Poller, OwletClient]:
    account = {
        "id": account_id or await store.default_account_id(),
        "email": email,
        "region": region,
        "api_token": None,
        "api_token_expiry": None,
        "refresh_token": None,
    }
    return await create_account_poller(store, account, interval_seconds, password=password)
