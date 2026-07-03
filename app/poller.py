from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

from app.models import OwletReading
from app.owlet_client import OwletClient
from app.store import ReadingStore

logger = logging.getLogger(__name__)

ReadOnce = Callable[[], Awaitable[OwletReading]]


class Poller:
    def __init__(
        self,
        store: ReadingStore,
        read_once: ReadOnce,
        interval_seconds: int = 30,
    ):
        self.store = store
        self.read_once = read_once
        self.interval_seconds = interval_seconds
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
                await self.store.insert_reading(reading)
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


async def create_owlet_poller(
    store: ReadingStore,
    email: str,
    password: str,
    region: str,
    interval_seconds: int,
) -> tuple[Poller, OwletClient]:
    client = OwletClient(email=email, password=password, region=region)
    await client.connect()
    poller = Poller(
        store=store,
        read_once=client.read_once,
        interval_seconds=interval_seconds,
    )
    return poller, client
