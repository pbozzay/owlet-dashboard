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
from app.owlet_client import OwletClient
from app.poller import Poller, create_account_poller, create_owlet_poller
from app.pwa import MANIFEST, SERVICE_WORKER_JS
from app.quality import is_offline_reading
from app.store import ReadingStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
STATIC_DIR = FilePath(__file__).parent / "static"
JSON_BODY = Body(default_factory=dict)


def _reading_response(row, *, include_raw: bool = False) -> dict[str, object]:
    """Serialize a reading for dashboard use, zeroing stale no-signal vitals.

    Owlet can hold the last HR/O₂ values while explicitly reporting sock disconnect/off.
    Keep the raw payload unchanged for debugging, but make graph/table points read as zero
    so the no-signal segment does not look like valid physiological data.
    """

    payload = row.model_dump(mode="json", exclude=None if include_raw else {"raw"})
    if is_offline_reading(row):
        payload["heart_rate"] = 0
        payload["oxygen_saturation"] = 0
        payload["movement"] = 0
    return payload


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
        pollers: list[Poller] = []
        clients: list[OwletClient] = []
        if start_poller:
            accounts = await store.list_accounts()
            token_accounts = [account for account in accounts if account.get("refresh_token") and account.get("status") == "active"]
            if token_accounts:
                for account in token_accounts:
                    try:
                        poller, client = await create_account_poller(
                            store=store,
                            account=account,
                            interval_seconds=settings.poll_interval_seconds,
                        )
                        poller.start()
                        pollers.append(poller)
                        clients.append(client)
                    except Exception:
                        logger.exception("Could not start Owlet poller for account_id=%s", account.get("id"))
                        await store.update_account_status(int(account["id"]), "needs_reauth")
            elif settings.has_owlet_credentials:
                try:
                    default_account_id = await store.default_account_id()
                    await store.update_account_profile(
                        default_account_id,
                        email=settings.owlet_email or "",
                        region=settings.owlet_region,
                        display_name=settings.owlet_email or "Owlet account",
                    )
                    poller, client = await create_owlet_poller(
                        store=store,
                        email=settings.owlet_email or "",
                        password=settings.owlet_password or "",
                        region=settings.owlet_region,
                        interval_seconds=settings.poll_interval_seconds,
                        account_id=default_account_id,
                    )
                    poller.start()
                    pollers.append(poller)
                    clients.append(client)
                except Exception:
                    logger.exception("Could not start Owlet poller")
            else:
                logger.warning("No Owlet token account or OWLET_EMAIL/OWLET_PASSWORD set; dashboard will show stored data only")
            if pollers:
                state["pollers"] = pollers
                state["clients"] = clients
        try:
            yield
        finally:
            for poller in pollers:
                await poller.stop()
            for client in clients:
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
            "collecting": bool(state.get("pollers")),
            "has_credentials": settings.has_owlet_credentials,
            "database_path": str(settings.database_path),
        }

    @app.get("/share/{token}/api/health")
    async def shared_health(token: str = Path(min_length=20)) -> dict[str, object]:
        _require_share_token(token, settings)
        return {
            "ok": True,
            "collecting": bool(state.get("pollers")),
            "has_credentials": False,
            "database_path": "shared read-only view",
        }

    @app.get("/api/accounts")
    async def accounts():
        return {"accounts": [_public_account(account) for account in await store.list_accounts()]}

    @app.patch("/api/accounts/{account_id}")
    async def update_account(account_id: int = Path(ge=1), payload: dict[str, object] = JSON_BODY):
        display_name = payload.get("display_name")
        show_crypto = payload.get("show_crypto")
        dashboard_preferences = _public_dashboard_preferences_patch(payload.get("dashboard_preferences"))
        try:
            account = await store.update_account_preferences(
                account_id,
                display_name=str(display_name).strip() if isinstance(display_name, str) else None,
                show_crypto=bool(show_crypto) if isinstance(show_crypto, bool) else None,
                dashboard_preferences=dashboard_preferences,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Account not found") from exc
        return {"account": _public_account(account)}

    @app.post("/api/accounts")
    async def create_account(payload: dict[str, object] = JSON_BODY):
        email = str(payload.get("email") or "").strip()
        password = str(payload.get("password") or "")
        region = str(payload.get("region") or settings.owlet_region or "world").strip() or "world"
        display_name = str(payload.get("display_name") or email or "Owlet account").strip()
        if not email or not password:
            raise HTTPException(status_code=400, detail="Owlet email and password are required")
        client: OwletClient | None = None
        try:
            client = OwletClient(email=email, password=password, region=region)
            await client.connect()
            client.discard_password()
            assert client is not None
            account = await store.create_account(
                email=email,
                region=region,
                display_name=display_name,
                api_token=client.tokens.get("api_token"),
                api_token_expiry=client.tokens.get("expiry"),
                refresh_token=client.tokens.get("refresh"),
                status="active",
            )
            if start_poller:
                client_for_poller = client
                poller = Poller(
                    store=store,
                    read_once=client_for_poller.read_once,
                    interval_seconds=settings.poll_interval_seconds,
                    account_id=int(account["id"]),
                    token_snapshot=lambda client=client_for_poller: client.tokens,
                )
                poller.start()
                state.setdefault("pollers", []).append(poller)  # type: ignore[union-attr]
                state.setdefault("clients", []).append(client)  # type: ignore[union-attr]
                client = None
            return {"account": _public_account(account)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Could not validate Owlet account") from exc
        finally:
            if client is not None:
                await client.close()

    @app.get("/api/devices")
    async def devices(account: int | None = Query(default=None, ge=1)):
        return {"devices": await store.list_devices(account_id=account)}

    @app.get("/share/{token}/api/devices")
    async def shared_devices(token: str = Path(min_length=20)):
        _require_share_token(token, settings)
        return {"devices": await store.list_devices()}

    @app.get("/api/readings")
    async def readings(
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=5000, ge=1, le=100_000),
        include_raw: bool = Query(default=False),
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
    ):
        rows = (
            await store.get_readings(hours=hours, limit=limit, device_serial=device, account_id=account)
            if include_raw
            else await store.get_analysis_readings(hours=hours, limit=limit, device_serial=device, account_id=account)
        )
        return [_reading_response(row, include_raw=include_raw) for row in rows]

    @app.get("/share/{token}/api/readings")
    async def shared_readings(
        token: str = Path(min_length=20),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=5000, ge=1, le=100_000),
        device: str | None = Query(default=None),
    ):
        _require_share_token(token, settings)
        rows = await store.get_analysis_readings(hours=hours, limit=limit, device_serial=device)
        return [_reading_response(row) for row in rows]

    @app.get("/api/summary")
    async def summary(
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
    ):
        return await store.get_summary(hours=hours, device_serial=device, account_id=account)

    @app.get("/share/{token}/api/summary")
    async def shared_summary(
        token: str = Path(min_length=20),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        device: str | None = Query(default=None),
    ):
        _require_share_token(token, settings)
        return await store.get_summary(hours=hours, device_serial=device)

    @app.get("/api/insights")
    async def insights(
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
    ):
        rows = await store.get_analysis_readings(hours=hours, limit=100_000, device_serial=device, account_id=account)
        rows = await store.exclude_challenge_readings(rows, account_id=account)
        return build_insights(rows)

    @app.get("/share/{token}/api/insights")
    async def shared_insights(
        token: str = Path(min_length=20),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        device: str | None = Query(default=None),
    ):
        _require_share_token(token, settings)
        rows = await store.get_analysis_readings(hours=hours, limit=100_000, device_serial=device)
        rows = await store.exclude_challenge_readings(rows)
        return build_insights(rows)

    @app.get("/api/rollups")
    async def rollups(
        bucket: Literal["5m", "15m", "30m", "hour", "6h", "12h", "day"] = Query(default="hour"),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
    ):
        rows = await store.get_analysis_readings(hours=hours, limit=100_000, device_serial=device, account_id=account)
        rows = await store.exclude_challenge_readings(rows, account_id=account)
        return {"bucket": bucket, "rollups": build_rollups(rows, bucket=bucket)}

    @app.get("/share/{token}/api/rollups")
    async def shared_rollups(
        token: str = Path(min_length=20),
        bucket: Literal["5m", "15m", "30m", "hour", "6h", "12h", "day"] = Query(default="hour"),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        device: str | None = Query(default=None),
    ):
        _require_share_token(token, settings)
        rows = await store.get_analysis_readings(hours=hours, limit=100_000, device_serial=device)
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
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
    ):
        return await store.get_notifications(hours=hours, limit=limit, offset=offset, device_serial=device, account_id=account)

    @app.get("/share/{token}/api/notifications")
    async def shared_notifications(
        token: str = Path(min_length=20),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        device: str | None = Query(default=None),
    ):
        _require_share_token(token, settings)
        return await store.get_notifications(hours=hours, limit=limit, offset=offset, device_serial=device)

    @app.get("/api/oxygen-challenges")
    async def oxygen_challenges(
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
    ):
        return await store.get_oxygen_challenges(hours=hours, limit=limit, offset=offset, device_serial=device, account_id=account)

    @app.get("/share/{token}/api/oxygen-challenges")
    async def shared_oxygen_challenges(
        token: str = Path(min_length=20),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        device: str | None = Query(default=None),
    ):
        _require_share_token(token, settings)
        return await store.get_oxygen_challenges(hours=hours, limit=limit, offset=offset, device_serial=device)

    @app.post("/api/oxygen-challenges")
    async def create_oxygen_challenge(payload: dict[str, object] = JSON_BODY):
        start_time = payload.get("start_time")
        if not isinstance(start_time, str):
            raise HTTPException(status_code=400, detail="start_time is required")
        end_time = payload.get("end_time")
        account_id = payload.get("account_id")
        return await store.create_oxygen_challenge(
            start_time=start_time,
            end_time=end_time if isinstance(end_time, str) else None,
            label=str(payload.get("label") or "Oxygen challenge"),
            notes=str(payload.get("notes") or ""),
            account_id=int(account_id) if isinstance(account_id, int | str) and str(account_id).isdigit() else None,
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
    async def widget(
        hours: int = Query(default=24, ge=1, le=24 * 30),
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
    ):
        return await _widget_payload(store, hours=hours, device=device, account_id=account)

    @app.get("/share/{token}/api/widget")
    async def shared_widget(
        token: str = Path(min_length=20),
        hours: int = Query(default=24, ge=1, le=24 * 30),
        device: str | None = Query(default=None),
    ):
        _require_share_token(token, settings)
        return await _widget_payload(store, hours=hours, device=device)

    return app


async def _widget_payload(
    store: ReadingStore,
    hours: int = 24,
    device: str | None = None,
    account_id: int | None = None,
) -> dict[str, object]:
    readings = await store.get_readings(hours=hours, limit=100_000, device_serial=device, account_id=account_id)
    summary = await store.get_summary(hours=hours, device_serial=device, account_id=account_id)
    insights = build_insights(await store.exclude_challenge_readings(readings, account_id=account_id))
    notifications = await store.get_notifications(
        hours=hours,
        limit=1,
        offset=0,
        device_serial=device,
        account_id=account_id,
    )
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


def _public_dashboard_preferences_patch(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    allowed: dict[str, object] = {}
    chart_visibility = value.get("chart_visibility")
    if isinstance(chart_visibility, dict):
        allowed["chart_visibility"] = {
            str(key): bool(setting)
            for key, setting in chart_visibility.items()
            if str(key) in {"heartRate", "oxygen", "movement", "skinTemperature", "btcPrice", "notifications", "o2Trailing30", "o2Baseline4h", "o2TrendSignal"}
            and isinstance(setting, bool)
        }
    chart_settings = value.get("chart_settings")
    if isinstance(chart_settings, dict):
        safe_settings: dict[str, object] = {}
        window_value = chart_settings.get("window")
        if str(window_value) in {"6", "12", "24", "72", "168", "720", "all"}:
            safe_settings["window"] = str(window_value)
        smoothing = chart_settings.get("smoothing")
        if str(smoothing) in {"raw", "5", "15", "30", "60"}:
            safe_settings["smoothing"] = str(smoothing)
        for key in ("challenge_bands", "sleep_highlight", "sleep_ballpark"):
            if isinstance(chart_settings.get(key), bool):
                safe_settings[key] = bool(chart_settings[key])
        allowed["chart_settings"] = safe_settings
    return allowed


def _public_account(account: dict[str, object]) -> dict[str, object]:
    return {
        "id": account.get("id"),
        "email": account.get("email"),
        "region": account.get("region"),
        "display_name": account.get("display_name"),
        "status": account.get("status"),
        "show_crypto": bool(account.get("show_crypto")),
        "dashboard_preferences": account.get("dashboard_preferences") if isinstance(account.get("dashboard_preferences"), dict) else {},
        "last_validated_at": account.get("last_validated_at"),
        "created_at": account.get("created_at"),
        "updated_at": account.get("updated_at"),
        "has_refresh_token": bool(account.get("refresh_token")),
        "has_api_token": bool(account.get("api_token")),
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
