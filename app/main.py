from __future__ import annotations

import hashlib
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, Response

from app.analytics import build_insights, build_rollups
from app.config import Settings
from app.dashboard import DASHBOARD_HTML
from app.poller import Poller, create_owlet_poller
from app.store import ReadingStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_app(
    store: ReadingStore | None = None,
    settings: Settings | None = None,
    start_poller: bool = True,
) -> FastAPI:
    settings = settings or Settings()
    store = store or ReadingStore(settings.database_path)
    state: dict[str, object] = {"store": store}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await store.init()
        poller: Poller | None = None
        client = None
        if start_poller:
            if settings.has_owlet_credentials:
                try:
                    poller, client = await create_owlet_poller(
                        store=store,
                        email=settings.owlet_email or "",
                        password=settings.owlet_password or "",
                        region=settings.owlet_region,
                        interval_seconds=settings.poll_interval_seconds,
                    )
                    poller.start()
                    state["poller"] = poller
                    state["client"] = client
                except Exception:
                    logger.exception("Could not start Owlet poller")
            else:
                logger.warning("OWLET_EMAIL/OWLET_PASSWORD not set; dashboard will show stored data only")
        try:
            yield
        finally:
            if poller:
                await poller.stop()
            if client:
                await client.close()

    app = FastAPI(title="Owlet History Server", lifespan=lifespan)
    app.state.owlet_state = state

    @app.middleware("http")
    async def require_basic_auth(request: Request, call_next):
        if not settings.basic_auth_enabled:
            return await call_next(request)

        expected_username = settings.owlet_basic_auth_username or ""
        expected_password = settings.owlet_basic_auth_password or ""
        expected_cookie = _basic_auth_cookie_value(expected_username, expected_password)
        cookie_authenticated = secrets.compare_digest(
            request.cookies.get("owlet_auth", ""),
            expected_cookie,
        )
        if cookie_authenticated:
            return await call_next(request)

        username, password = _parse_basic_auth(request.headers.get("authorization"))
        authenticated = secrets.compare_digest(username, expected_username) and secrets.compare_digest(
            password,
            expected_password,
        )
        if not authenticated:
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Owlet History"'},
            )
        response = await call_next(request)
        response.set_cookie(
            "owlet_auth",
            expected_cookie,
            httponly=True,
            samesite="lax",
        )
        return response

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> str:
        return DASHBOARD_HTML

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return {
            "ok": True,
            "collecting": "poller" in state,
            "has_credentials": settings.has_owlet_credentials,
            "database_path": str(settings.database_path),
        }

    @app.get("/api/readings")
    async def readings(
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=5000, ge=1, le=100_000),
        include_raw: bool = Query(default=False),
    ):
        rows = await store.get_readings(hours=hours, limit=limit)
        exclude = None if include_raw else {"raw"}
        return [row.model_dump(mode="json", exclude=exclude) for row in rows]

    @app.get("/api/summary")
    async def summary(hours: int | None = Query(default=None, ge=1, le=24 * 365)):
        return await store.get_summary(hours=hours)

    @app.get("/api/insights")
    async def insights(hours: int | None = Query(default=None, ge=1, le=24 * 365)):
        rows = await store.get_readings(hours=hours, limit=100_000)
        return build_insights(rows)

    @app.get("/api/rollups")
    async def rollups(
        bucket: Literal["hour", "day"] = Query(default="hour"),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
    ):
        rows = await store.get_readings(hours=hours, limit=100_000)
        return {"bucket": bucket, "rollups": build_rollups(rows, bucket=bucket)}

    return app


app = create_app()


def _parse_basic_auth(header: str | None) -> tuple[str, str]:
    if not header or not header.lower().startswith("basic "):
        return "", ""
    import base64
    import binascii

    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return "", ""
    username, separator, password = decoded.partition(":")
    if not separator:
        return "", ""
    return username, password


def _basic_auth_cookie_value(username: str, password: str) -> str:
    return hashlib.sha256(f"{username}:{password}".encode()).hexdigest()
