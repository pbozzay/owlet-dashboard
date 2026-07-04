from __future__ import annotations

import hashlib
import json
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path as FilePath
from typing import Literal

from fastapi import Body, FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from app.analytics import build_insights, build_rollups
from app.config import Settings
from app.crypto import get_crypto_prices
from app.dashboard import render_dashboard
from app.poller import Poller, create_owlet_poller
from app.pwa import MANIFEST, SERVICE_WORKER_JS
from app.store import ReadingStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
STATIC_DIR = FilePath(__file__).parent / "static"
JSON_BODY = Body(default_factory=dict)


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
        if request.url.path.startswith("/share/"):
            if _share_path_is_authorized(request.url.path, settings.owlet_share_token):
                return await call_next(request)
            return Response(status_code=404)

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
        return render_dashboard()

    @app.get("/manifest.webmanifest")
    async def manifest() -> Response:
        return Response(
            json.dumps(MANIFEST),
            media_type="application/manifest+json",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.get("/sw.js")
    async def service_worker() -> Response:
        return Response(
            SERVICE_WORKER_JS,
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/icon-{size}.png")
    async def icon(size: Literal["192", "512"]) -> FileResponse:
        return FileResponse(
            STATIC_DIR / f"icon-{size}.png",
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/share/{token}", response_class=HTMLResponse)
    async def shared_dashboard(token: str = Path(min_length=20)) -> str:
        _require_share_token(token, settings)
        return render_dashboard(api_base=f"/share/{token}", share_mode=True)

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return {
            "ok": True,
            "collecting": "poller" in state,
            "has_credentials": settings.has_owlet_credentials,
            "database_path": str(settings.database_path),
        }

    @app.get("/share/{token}/api/health")
    async def shared_health(token: str = Path(min_length=20)) -> dict[str, object]:
        _require_share_token(token, settings)
        return {
            "ok": True,
            "collecting": "poller" in state,
            "has_credentials": False,
            "database_path": "shared read-only view",
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

    @app.get("/share/{token}/api/readings")
    async def shared_readings(
        token: str = Path(min_length=20),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=5000, ge=1, le=100_000),
    ):
        _require_share_token(token, settings)
        rows = await store.get_readings(hours=hours, limit=limit)
        return [row.model_dump(mode="json", exclude={"raw"}) for row in rows]

    @app.get("/api/summary")
    async def summary(hours: int | None = Query(default=None, ge=1, le=24 * 365)):
        return await store.get_summary(hours=hours)

    @app.get("/share/{token}/api/summary")
    async def shared_summary(
        token: str = Path(min_length=20),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
    ):
        _require_share_token(token, settings)
        return await store.get_summary(hours=hours)

    @app.get("/api/insights")
    async def insights(hours: int | None = Query(default=None, ge=1, le=24 * 365)):
        rows = await store.get_readings(hours=hours, limit=100_000)
        rows = await store.exclude_challenge_readings(rows)
        return build_insights(rows)

    @app.get("/share/{token}/api/insights")
    async def shared_insights(
        token: str = Path(min_length=20),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
    ):
        _require_share_token(token, settings)
        rows = await store.get_readings(hours=hours, limit=100_000)
        rows = await store.exclude_challenge_readings(rows)
        return build_insights(rows)

    @app.get("/api/rollups")
    async def rollups(
        bucket: Literal["5m", "15m", "30m", "hour", "6h", "12h", "day"] = Query(default="hour"),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
    ):
        rows = await store.get_readings(hours=hours, limit=100_000)
        rows = await store.exclude_challenge_readings(rows)
        return {"bucket": bucket, "rollups": build_rollups(rows, bucket=bucket)}

    @app.get("/share/{token}/api/rollups")
    async def shared_rollups(
        token: str = Path(min_length=20),
        bucket: Literal["5m", "15m", "30m", "hour", "6h", "12h", "day"] = Query(default="hour"),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
    ):
        _require_share_token(token, settings)
        rows = await store.get_readings(hours=hours, limit=100_000)
        rows = await store.exclude_challenge_readings(rows)
        return {"bucket": bucket, "rollups": build_rollups(rows, bucket=bucket)}

    @app.get("/api/crypto")
    async def crypto(hours: int = Query(default=24, ge=1, le=24 * 30)):
        return await get_crypto_prices(hours=hours)

    @app.get("/share/{token}/api/crypto")
    async def shared_crypto(
        token: str = Path(min_length=20),
        hours: int = Query(default=24, ge=1, le=24 * 30),
    ):
        _require_share_token(token, settings)
        return await get_crypto_prices(hours=hours)

    @app.get("/api/notifications")
    async def notifications(
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ):
        return await store.get_notifications(hours=hours, limit=limit, offset=offset)

    @app.get("/share/{token}/api/notifications")
    async def shared_notifications(
        token: str = Path(min_length=20),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ):
        _require_share_token(token, settings)
        return await store.get_notifications(hours=hours, limit=limit, offset=offset)

    @app.get("/api/oxygen-challenges")
    async def oxygen_challenges(
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ):
        return await store.get_oxygen_challenges(hours=hours, limit=limit, offset=offset)

    @app.get("/share/{token}/api/oxygen-challenges")
    async def shared_oxygen_challenges(
        token: str = Path(min_length=20),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ):
        _require_share_token(token, settings)
        return await store.get_oxygen_challenges(hours=hours, limit=limit, offset=offset)

    @app.post("/api/oxygen-challenges")
    async def create_oxygen_challenge(payload: dict[str, object] = JSON_BODY):
        start_time = payload.get("start_time")
        if not isinstance(start_time, str):
            raise HTTPException(status_code=400, detail="start_time is required")
        end_time = payload.get("end_time")
        return await store.create_oxygen_challenge(
            start_time=start_time,
            end_time=end_time if isinstance(end_time, str) else None,
            label=str(payload.get("label") or "Oxygen challenge"),
            notes=str(payload.get("notes") or ""),
        )

    @app.get("/api/oxygen-challenges/{challenge_id}")
    async def oxygen_challenge(challenge_id: int = Path(ge=1)):
        try:
            return await store.get_oxygen_challenge(challenge_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Challenge not found") from exc

    @app.get("/share/{token}/api/oxygen-challenges/{challenge_id}")
    async def shared_oxygen_challenge(
        token: str = Path(min_length=20),
        challenge_id: int = Path(ge=1),
    ):
        _require_share_token(token, settings)
        try:
            return await store.get_oxygen_challenge(challenge_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Challenge not found") from exc

    @app.patch("/api/oxygen-challenges/{challenge_id}")
    async def update_oxygen_challenge(
        challenge_id: int = Path(ge=1),
        payload: dict[str, object] = JSON_BODY,
    ):
        start_value = payload.get("start_time")
        end_value = payload.get("end_time")
        start_time = start_value if isinstance(start_value, str) else None
        end_time = end_value if isinstance(end_value, str) else None
        clear_end_time = "end_time" in payload and not end_time
        try:
            return await store.update_oxygen_challenge(
                challenge_id,
                start_time=start_time,
                end_time=end_time,
                label=str(payload["label"]) if "label" in payload else None,
                notes=str(payload["notes"]) if "notes" in payload else None,
                clear_end_time=clear_end_time,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Challenge not found") from exc

    @app.delete("/api/oxygen-challenges/{challenge_id}")
    async def delete_oxygen_challenge(challenge_id: int = Path(ge=1)):
        await store.delete_oxygen_challenge(challenge_id)
        return {"ok": True}

    @app.get("/api/widget")
    async def widget(hours: int = Query(default=24, ge=1, le=24 * 30)):
        return await _widget_payload(store, hours=hours)

    @app.get("/share/{token}/api/widget")
    async def shared_widget(
        token: str = Path(min_length=20),
        hours: int = Query(default=24, ge=1, le=24 * 30),
    ):
        _require_share_token(token, settings)
        return await _widget_payload(store, hours=hours)

    return app


async def _widget_payload(store: ReadingStore, hours: int = 24) -> dict[str, object]:
    readings = await store.get_readings(hours=hours, limit=100_000)
    summary = await store.get_summary(hours=hours)
    insights = build_insights(await store.exclude_challenge_readings(readings))
    notifications = await store.get_notifications(hours=hours, limit=1, offset=0)
    latest_reading = readings[-1].model_dump(mode="json", exclude={"raw"}) if readings else {}
    latest = latest_reading or insights.get("latest") or {}
    breathing = insights.get("breathing") or {}
    latest_notification = notifications["items"][0] if notifications["items"] else None
    return {
        "updated_at": latest.get("recorded_at") if isinstance(latest, dict) else None,
        "window": summary["window"],
        "oxygen_now": latest.get("oxygen_saturation") if isinstance(latest, dict) else None,
        "oxygen_avg": summary["oxygen_saturation"]["avg"],
        "heart_rate": latest.get("heart_rate") if isinstance(latest, dict) else None,
        "trend": breathing.get("direction"),
        "trend_sentence": breathing.get("plain_language"),
        "battery": latest.get("battery") if isinstance(latest, dict) else None,
        "notification_count": notifications["total"],
        "latest_notification": latest_notification,
    }


def _require_share_token(token: str, settings: Settings) -> None:
    expected = settings.owlet_share_token or ""
    if not expected or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=404)


def _share_path_is_authorized(path: str, token: str | None) -> bool:
    if not token or not path.startswith("/share/"):
        return False
    candidate = path.removeprefix("/share/").split("/", 1)[0]
    return bool(candidate) and secrets.compare_digest(candidate, token)


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
