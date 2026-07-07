from __future__ import annotations

import logging
from typing import Any

from pyowletapi.api import OwletAPI
from pyowletapi.sock import Sock

from app.models import OwletReading, normalize_reading

logger = logging.getLogger(__name__)


class OwletClient:
    """Small adapter around pyowletapi so the rest of the app stays testable."""

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        region: str = "world",
        *,
        api_token: str | None = None,
        api_token_expiry: float | None = None,
        refresh_token: str | None = None,
    ):
        self.email = email
        self.password = password
        self.region = region
        self.api = OwletAPI(
            region,
            user=email,
            password=password,
            token=api_token,
            expiry=api_token_expiry,
            refresh=refresh_token,
        )
        self.sock: Sock | None = None

    @property
    def tokens(self) -> dict[str, Any]:
        return dict(self.api.tokens)

    def discard_password(self) -> None:
        self.password = None
        if hasattr(self.api, "_password"):
            self.api._password = None  # noqa: SLF001 - pyowletapi has no public password-clear hook.

    async def connect(self) -> None:
        await self.api.authenticate()
        devices_response = await self.api.get_devices()
        devices = _unwrap_devices(devices_response)
        if not devices:
            raise RuntimeError("No Owlet devices found for this account")

        # Prefer Smart Sock / Dream Sock v3 devices, but fall back to first device.
        chosen = devices[0]
        for candidate in devices:
            device = candidate.get("device", candidate)
            model = str(device.get("oem_model") or device.get("model") or "").lower()
            if "ss3" in model or "sock" in model:
                chosen = candidate
                break

        device_data = chosen.get("device", chosen)
        self.sock = Sock(self.api, device_data)
        logger.info("Connected to Owlet device serial=%s", self.sock.serial)

    async def read_once(self) -> OwletReading:
        if self.sock is None:
            await self.connect()
        assert self.sock is not None
        response: dict[str, Any] = await self.sock.update_properties()
        properties = response.get("properties") or {}
        raw_properties = response.get("raw_properties") or {}
        merged = {**raw_properties, **properties}
        return normalize_reading(merged, device_serial=self.sock.serial)

    async def close(self) -> None:
        await self.api.close()


def _unwrap_devices(devices_response: Any) -> list[dict[str, Any]]:
    if isinstance(devices_response, list):
        return devices_response
    if isinstance(devices_response, dict):
        if isinstance(devices_response.get("response"), list):
            return devices_response["response"]
        if isinstance(devices_response.get("devices"), list):
            return devices_response["devices"]
    return []
