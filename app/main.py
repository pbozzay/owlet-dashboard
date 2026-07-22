from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path as FilePath
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Body, Depends, FastAPI, Form, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

from app import auth_pages
from app.analytics import (
    O2_THRESHOLD_MAX,
    O2_THRESHOLD_MIN,
    build_insights,
    build_rollups,
    resolve_o2_thresholds,
)
from app.auth_routes import current_user, require_user
from app.auth_routes import router as auth_router
from app.auth_store import AuthStore
from app.config import Settings
from app.dashboard import render_dashboard
from app.night_page import render_night_page
from app.now_page import render_now_page
from app.owlet_client import OwletClient
from app.poller import Poller, create_account_poller, create_owlet_poller
from app.pwa import MANIFEST, SERVICE_WORKER_JS
from app.quality import is_offline_reading
from app.ratelimit import RateLimiter
from app.rhythms_page import render_rhythms_page
from app.security import hash_password
from app.store import ReadingStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
STATIC_DIR = FilePath(__file__).parent / "static"
JSON_BODY = Body(default_factory=dict)


def _app_version() -> str:
    """Installed package version, for the health check / UI version badge.

    The container installs the package (``pip install .``), so this reflects the
    running build. In the frozen desktop sidecar the metadata may be absent —
    that's fine, the desktop shell injects its own (authoritative) version.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("owlet-dashboard")
    except PackageNotFoundError:
        return "dev"


def _desktop_config_path(settings: Settings) -> FilePath:
    return FilePath(settings.database_path).parent / "desktop-config.json"


def _read_desktop_config(settings: Settings) -> dict[str, object]:
    try:
        return json.loads(_desktop_config_path(settings).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_desktop_config(settings: Settings, data: dict[str, object]) -> None:
    path = _desktop_config_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


async def _probe_owlet_instance(url: str) -> bool:
    """Confirm a URL is a reachable Owlet Dashboard before we point the window
    at it. Server-side (no browser CORS) via stdlib, off the event loop."""
    import urllib.request

    def _get() -> bool:
        req = urllib.request.Request(
            url.rstrip("/") + "/api/health", headers={"User-Agent": "owlet-desktop"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:  # noqa: S310 - user-entered URL
            return bool(json.loads(resp.read().decode("utf-8")).get("ok"))

    try:
        return await asyncio.to_thread(_get)
    except Exception:
        return False


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
        payload["movement_bucket"] = 0
        payload["oxygen_10_av"] = 0
    return payload


def create_app(
    store: ReadingStore | None = None,
    settings: Settings | None = None,
    start_poller: bool = True,
    auth_store: AuthStore | None = None,
) -> FastAPI:
    settings = settings or Settings()
    store = store or ReadingStore(settings.database_path)
    auth_store = auth_store or AuthStore(settings.database_path)
    state: dict[str, object] = {"store": store}
    rollup_cache: dict[tuple, tuple[float, dict]] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await store.init()
        await auth_store.init()
        if settings.seed_default_admin and await auth_store.get_user_by_email("admin") is None:
            await auth_store.create_user("admin", hash_password("password"))
            logger.warning(
                "Seeded default login admin/password (SEED_DEFAULT_ADMIN=true). "
                "Do NOT expose this instance publicly with this flag on."
            )
        pollers: list[Poller] = []
        clients: list[OwletClient] = []
        # When the desktop app is pointed at a remote server it's a pure viewer —
        # a local collector here would just fight the remote for the Owlet token.
        remote_mode = bool(settings.desktop_mode and _read_desktop_config(settings).get("backend"))
        if start_poller and not remote_mode:
            accounts = await store.list_accounts()
            token_accounts = [
                account
                for account in accounts
                if (account.get("refresh_token") and account.get("status") == "active")
                or account.get("owlet_password")
            ]
            if token_accounts:
                for account in token_accounts:
                    try:
                        poller, client = await create_account_poller(
                            store=store,
                            account=account,
                            interval_seconds=int(
                                account.get("poll_interval_seconds") or settings.poll_interval_seconds
                            ),
                            password=account.get("owlet_password"),
                        )
                        poller.start()
                        pollers.append(poller)
                        clients.append(client)
                    except Exception:
                        logger.exception("Could not start Owlet poller for account_id=%s", account.get("id"))
                        await store.update_account_status(int(account["id"]), "needs_reauth")
            elif settings.has_owlet_credentials:
                try:
                    accounts_list = await store.list_accounts()
                    default_account_id = (
                        int(accounts_list[0]["id"])
                        if accounts_list
                        else int((await store.create_account(email=settings.owlet_email or ""))["id"])
                    )
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
    app.state.settings = settings
    app.state.auth_store = auth_store
    app.state.rate_limiter = RateLimiter()
    app.include_router(auth_router)

    @app.middleware("http")
    async def share_guard(request: Request, call_next):
        if request.url.path.startswith("/share/"):
            if _share_path_is_authorized(request.url.path, settings.owlet_share_token):
                return await call_next(request)
            return Response(status_code=404)
        return await call_next(request)

    @app.get("/")
    async def home(request: Request):
        if settings.desktop_mode:
            cfg = _read_desktop_config(settings)
            if cfg.get("backend"):
                return HTMLResponse(auth_pages.desktop_redirect_page(str(cfg["backend"])))
            if cfg.get("mode") != "local":  # first run — offer the launcher
                return HTMLResponse(auth_pages.desktop_launcher_page())
        user = await current_user(request)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        accounts = await store.list_accounts(user_id=user["id"])
        # A logged-out ("disconnected") account keeps its data but doesn't count
        # as linked — fall through to onboarding so the user can sign back in.
        if not any(a.get("status") != "disconnected" for a in accounts):
            return HTMLResponse(auth_pages.onboarding_page(desktop_mode=settings.desktop_mode))
        return HTMLResponse(render_now_page())

    @app.get("/desktop")
    async def desktop_launcher(request: Request):
        if not settings.desktop_mode:
            return RedirectResponse("/", status_code=303)
        cfg = _read_desktop_config(settings)
        backend = cfg.get("backend")
        return HTMLResponse(
            auth_pages.desktop_launcher_page(current_backend=str(backend) if backend else None)
        )

    @app.post("/desktop/use-local")
    async def desktop_use_local():
        if not settings.desktop_mode:
            raise HTTPException(status_code=404, detail="Not found")
        _write_desktop_config(settings, {"mode": "local"})
        return RedirectResponse("/", status_code=303)

    @app.post("/desktop/reset")
    async def desktop_reset():
        """Clear the local/remote choice so the app returns to the launcher —
        used on logout, so signing out lands on the 'how do you want to use
        this app?' chooser rather than straight back on the local link page."""
        if not settings.desktop_mode:
            raise HTTPException(status_code=404, detail="Not found")
        _write_desktop_config(settings, {})
        return {"ok": True}

    @app.post("/desktop/connect")
    async def desktop_connect(payload: dict[str, object] = JSON_BODY):
        if not settings.desktop_mode:
            raise HTTPException(status_code=404, detail="Not found")
        url = str(payload.get("url") or "").strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Enter a full http:// or https:// address")
        if not await _probe_owlet_instance(url):
            raise HTTPException(
                status_code=400, detail="Couldn't reach an Owlet Dashboard at that address"
            )
        _write_desktop_config(settings, {"mode": "remote", "backend": url})
        return {"ok": True, "url": url}

    @app.get("/data")
    async def data_workbench(request: Request):
        user = await current_user(request)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        accounts = await store.list_accounts(user_id=user["id"])
        if not any(a.get("status") != "disconnected" for a in accounts):
            return RedirectResponse("/", status_code=303)
        return HTMLResponse(render_dashboard())

    @app.get("/night")
    async def night_report(request: Request):
        user = await current_user(request)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        return HTMLResponse(render_night_page())

    @app.get("/rhythms")
    async def rhythms_report(request: Request):
        user = await current_user(request)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        return HTMLResponse(render_rhythms_page())

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
    async def icon(size: Literal["32", "180", "192", "512"]) -> FileResponse:
        return FileResponse(
            STATIC_DIR / f"icon-{size}.png",
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/favicon.ico")
    async def favicon() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "favicon.ico",
            media_type="image/x-icon",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/theme.css")
    async def theme_css() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "theme.css",
            media_type="text/css",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/insights.js")
    async def insights_js() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "insights.js",
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/logo.svg")
    async def logo() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "logo.svg",
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/preview-today.png")
    async def preview_today() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "preview-today.png",
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
            "desktop_mode": settings.desktop_mode,
            "database_path": str(settings.database_path),
            "version": _app_version(),
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

    @app.get("/api/me")
    async def me(user: dict = Depends(require_user)):
        return {"email": user["email"]}

    @app.get("/api/accounts")
    async def accounts(user: dict = Depends(require_user)):
        # Logged-out accounts stay in the DB (so re-linking reactivates them)
        # but are hidden from the picker — they're not connected.
        return {
            "accounts": [
                _public_account(account)
                for account in await store.list_accounts(user_id=user["id"])
                if account.get("status") != "disconnected"
            ]
        }

    @app.patch("/api/accounts/{account_id}")
    async def update_account(
        account_id: int = Path(ge=1),
        payload: dict[str, object] = JSON_BODY,
        user: dict = Depends(require_user),
    ):
        display_name = payload.get("display_name")
        dashboard_preferences = _public_dashboard_preferences_patch(payload.get("dashboard_preferences"))
        interval_raw = payload.get("poll_interval_seconds")
        poll_interval = (
            int(interval_raw)
            if isinstance(interval_raw, int | str) and str(interval_raw) in {"5", "10", "30", "60", "300"}
            else None
        )
        try:
            await store.get_account(account_id, user_id=user["id"])  # ownership check -> KeyError
            account = await store.update_account_preferences(
                account_id,
                display_name=str(display_name).strip() if isinstance(display_name, str) else None,
                dashboard_preferences=dashboard_preferences,
                poll_interval_seconds=poll_interval,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Account not found") from exc
        if poll_interval is not None:
            for poller in state.get("pollers", []):  # type: ignore[union-attr]
                if getattr(poller, "account_id", None) == account_id:
                    poller.interval_seconds = poll_interval
        return {"account": _public_account(account)}

    async def _scope(user: dict, account: int | None) -> list[int]:
        owned = [int(a["id"]) for a in await store.list_accounts(user_id=user["id"])]
        if account is None:
            return owned
        if account not in owned:
            raise HTTPException(status_code=404, detail="Not found")
        return [account]

    async def _link_owlet_account(payload: dict[str, object], user: dict) -> dict:
        if not app.state.rate_limiter.allow(
            f"owlet-link:{user['id']}", max_hits=5, window_seconds=3600
        ):
            raise HTTPException(status_code=429, detail="Too many link attempts; try again later")
        email = str(payload.get("email") or "").strip()
        password = str(payload.get("password") or "")
        region = str(payload.get("region") or "world").strip() or "world"
        display_name = str(payload.get("display_name") or email or "Owlet account").strip()
        if not email or not password:
            raise HTTPException(status_code=400, detail="Owlet email and password are required")
        client: OwletClient | None = None
        try:
            client = OwletClient(email=email, password=password, region=region)
            await client.connect()
            client.discard_password()
            # Re-linking the same Owlet login must refresh the existing account,
            # not spawn a duplicate that double-polls the same sock.
            existing = next(
                (
                    a
                    for a in await store.list_accounts(user_id=user["id"])
                    if str(a.get("email") or "").strip().lower() == email.lower()
                ),
                None,
            )
            if existing is not None:
                account_id = int(existing["id"])
                await store.update_account_tokens(
                    account_id,
                    api_token=client.tokens.get("api_token"),
                    api_token_expiry=client.tokens.get("expiry"),
                    refresh_token=client.tokens.get("refresh"),
                    status="active",
                )
                account = await store.get_account(account_id)
            else:
                account = await store.create_account(
                    email=email,
                    region=region,
                    display_name=display_name,
                    api_token=client.tokens.get("api_token"),
                    api_token_expiry=client.tokens.get("expiry"),
                    refresh_token=client.tokens.get("refresh"),
                    status="active",
                    user_id=user["id"],
                    # Desktop installs keep the Owlet login locally so a dead refresh
                    # token (e.g. after weeks powered off) never strands collection.
                    owlet_password=password if settings.desktop_mode else None,
                )
            account_id = int(account["id"])
            if start_poller:
                # Exactly one poller per account: stop any already running for
                # this account (e.g. started on boot) before attaching the new client.
                live = state.setdefault("pollers", [])  # type: ignore[union-attr]
                for stale in [p for p in live if getattr(p, "account_id", None) == account_id]:
                    await stale.stop()
                    live.remove(stale)
                client_for_poller = client
                poller = Poller(
                    store=store,
                    read_once=client_for_poller.read_once,
                    interval_seconds=settings.poll_interval_seconds,
                    account_id=account_id,
                    token_snapshot=lambda client=client_for_poller: client.tokens,
                )
                poller.start()
                live.append(poller)
                state.setdefault("clients", []).append(client)  # type: ignore[union-attr]
                client = None
            return account
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Could not validate Owlet account") from exc
        finally:
            if client is not None:
                await client.close()

    @app.post("/api/accounts")
    async def create_account(
        payload: dict[str, object] = JSON_BODY, user: dict = Depends(require_user)
    ):
        account = await _link_owlet_account(payload, user)
        return {"account": _public_account(account)}

    @app.delete("/api/accounts/{account_id}")
    async def unlink_account(
        account_id: int = Path(ge=1), user: dict = Depends(require_user)
    ):
        """Unlink an Owlet account: stop its collector and delete it with all
        of its stored history. Irreversible — the UI gates it behind a
        typed confirmation."""
        await _scope(user, account_id)  # 404s unless the user owns it
        live = state.setdefault("pollers", [])  # type: ignore[union-attr]
        for poller in [p for p in live if getattr(p, "account_id", None) == account_id]:
            await poller.stop()
            live.remove(poller)
        deleted = await store.delete_account(account_id, user_id=user["id"])
        if not deleted:
            raise HTTPException(status_code=404, detail="Not found")
        return {"ok": True}

    @app.post("/api/accounts/{account_id}/disconnect")
    async def disconnect_account(
        account_id: int = Path(ge=1), user: dict = Depends(require_user)
    ):
        """Log an Owlet account out: stop its collector and clear the stored
        login, but keep all collected history. Non-destructive — re-linking the
        same login reactivates this account with its data intact."""
        await _scope(user, account_id)  # 404s unless the user owns it
        live = state.setdefault("pollers", [])  # type: ignore[union-attr]
        for poller in [p for p in live if getattr(p, "account_id", None) == account_id]:
            await poller.stop()
            live.remove(poller)
        updated = await store.disconnect_account(account_id, user_id=user["id"])
        if not updated:
            raise HTTPException(status_code=404, detail="Not found")
        return {"ok": True}

    @app.post("/onboarding/link")
    async def onboarding_link(
        email: str = Form(),
        password: str = Form(),
        region: str = Form(default="world"),
        user: dict = Depends(require_user),
    ):
        try:
            await _link_owlet_account({"email": email, "password": password, "region": region}, user)
        except HTTPException as exc:
            if exc.status_code == 429:
                raise
            return HTMLResponse(
                auth_pages.onboarding_page(
                    error="Owlet rejected that login - check email/password/region",
                    desktop_mode=settings.desktop_mode,
                ),
                status_code=400,
            )
        return RedirectResponse("/", status_code=303)

    @app.get("/api/devices")
    async def devices(
        account: int | None = Query(default=None, ge=1),
        user: dict = Depends(require_user),
    ):
        return {"devices": await store.list_devices(account_ids=await _scope(user, account))}

    @app.get("/share/{token}/api/devices")
    async def shared_devices(token: str = Path(min_length=20)):
        _require_share_token(token, settings)
        return {"devices": await store.list_devices()}

    @app.get("/api/device-info")
    async def device_info(
        account: int | None = Query(default=None, ge=1),
        device: str | None = Query(default=None),
        user: dict = Depends(require_user),
    ):
        """Static device facts from the latest snapshot: firmware, hardware,
        radio MACs — the once-per-change copy of the Ayla payload."""
        snapshot = await store.get_device_snapshot(
            account_ids=await _scope(user, account), device_serial=device
        )
        if snapshot is None:
            return {"info": None}
        payload = snapshot["payload"]

        def prop(name: str) -> object | None:
            value = payload.get(name)
            return value.get("value") if isinstance(value, dict) else value

        def config(field: str) -> object | None:
            raw_cfg = prop("CONFIG_STATUS")
            if isinstance(raw_cfg, str):
                try:
                    return json.loads(raw_cfg).get(field)
                except ValueError:
                    return None
            if isinstance(raw_cfg, dict):
                return raw_cfg.get(field)
            return None

        return {
            "info": {
                "device_serial": snapshot["device_serial"],
                "captured_at": snapshot["updated_at"],
                "sock_firmware": prop("oem_sock_version"),
                "base_firmware": prop("oem_base_version"),
                "flash_firmware": prop("oem_flash_version"),
                "hardware_version": prop("hardware_version"),
                "sock_mac": config("smac"),
                "base_mac": config("bmac"),
            }
        }

    @app.get("/api/readings")
    async def readings(
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=5000, ge=1, le=100_000),
        include_raw: bool = Query(default=False),
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
        user: dict = Depends(require_user),
    ):
        ids = await _scope(user, account)
        rows = (
            await store.get_readings(hours=hours, limit=limit, device_serial=device, account_ids=ids)
            if include_raw
            else await store.get_analysis_readings(hours=hours, limit=limit, device_serial=device, account_ids=ids)
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
        user: dict = Depends(require_user),
    ):
        return await store.get_summary(
            hours=hours, device_serial=device, account_ids=await _scope(user, account)
        )

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
        user: dict = Depends(require_user),
    ):
        ids = await _scope(user, account)
        rows = await store.get_analysis_readings(hours=hours, limit=100_000, device_serial=device, account_ids=ids)
        rows = await store.exclude_challenge_readings(rows, account_ids=ids)
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

    async def _o2_thresholds_for(user: dict, ids: list[int]) -> tuple[int, int]:
        """The account's oxygen tiers, so rollup counters match what the pages
        paint. Falls back to the shipped defaults when nothing is configured."""
        accounts = await store.list_accounts(user_id=user["id"])
        scoped = set(ids)
        prefs = next(
            (a.get("dashboard_preferences") for a in accounts if int(a["id"]) in scoped),
            None,
        )
        return resolve_o2_thresholds(prefs)

    @app.get("/api/rollups")
    async def rollups(
        bucket: Literal["5m", "15m", "30m", "hour", "6h", "12h", "day"] = Query(default="hour"),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
        user: dict = Depends(require_user),
    ):
        ids = await _scope(user, account)
        o2_warn, o2_critical = await _o2_thresholds_for(user, ids)
        # History is immutable; only the newest bucket moves. A short server-side
        # cache turns repeat loads (every page needs rollups) into instant hits.
        # Thresholds are part of the key so retuning them re-counts immediately.
        key = (tuple(ids), bucket, hours, device, o2_warn, o2_critical)
        cached = rollup_cache.get(key)
        now_monotonic = time.monotonic()
        if cached and now_monotonic - cached[0] < 45:
            payload = cached[1]
        else:
            # 300k covers a gapless 14-day window at the 5s poll cadence — the
            # Rhythms pages ask for 336h and must not lose their oldest days.
            rows = await store.get_analysis_readings(
                hours=hours, limit=300_000, device_serial=device, account_ids=ids
            )
            rows = await store.exclude_challenge_readings(rows, account_ids=ids)
            payload = {
                "bucket": bucket,
                "rollups": build_rollups(
                    rows, bucket=bucket, o2_warn=o2_warn, o2_critical=o2_critical
                ),
            }
            rollup_cache[key] = (now_monotonic, payload)
            while len(rollup_cache) > 64:
                rollup_cache.pop(next(iter(rollup_cache)))
        return JSONResponse(payload, headers={"Cache-Control": "private, max-age=30"})

    @app.get("/share/{token}/api/rollups")
    async def shared_rollups(
        token: str = Path(min_length=20),
        bucket: Literal["5m", "15m", "30m", "hour", "6h", "12h", "day"] = Query(default="hour"),
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        device: str | None = Query(default=None),
    ):
        _require_share_token(token, settings)
        rows = await store.get_analysis_readings(hours=hours, limit=300_000, device_serial=device)
        rows = await store.exclude_challenge_readings(rows)
        return {"bucket": bucket, "rollups": build_rollups(rows, bucket=bucket)}


    @app.get("/api/notifications")
    async def notifications(
        hours: int | None = Query(default=None, ge=1, le=24 * 365),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
        user: dict = Depends(require_user),
    ):
        return await store.get_notifications(
            hours=hours,
            limit=limit,
            offset=offset,
            device_serial=device,
            account_ids=await _scope(user, account),
        )

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
        user: dict = Depends(require_user),
    ):
        return await store.get_oxygen_challenges(
            hours=hours,
            limit=limit,
            offset=offset,
            device_serial=device,
            account_ids=await _scope(user, account),
        )

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
    async def create_oxygen_challenge(
        payload: dict[str, object] = JSON_BODY,
        user: dict = Depends(require_user),
    ):
        start_time = payload.get("start_time")
        if not isinstance(start_time, str):
            raise HTTPException(status_code=400, detail="start_time is required")
        end_time = payload.get("end_time")
        account_id = payload.get("account_id")
        requested = (
            int(account_id)
            if isinstance(account_id, int | str) and str(account_id).isdigit()
            else None
        )
        ids = await _scope(user, requested)
        if not ids:
            raise HTTPException(status_code=400, detail="Link an Owlet account first")
        target_account_id = ids[0]
        return await store.create_oxygen_challenge(
            start_time=start_time,
            end_time=end_time if isinstance(end_time, str) else None,
            label=str(payload.get("label") or "Oxygen challenge"),
            notes=str(payload.get("notes") or ""),
            account_id=target_account_id,
        )

    @app.get("/api/oxygen-challenges/{challenge_id}")
    async def oxygen_challenge(
        challenge_id: int = Path(ge=1),
        user: dict = Depends(require_user),
    ):
        try:
            return await store.get_oxygen_challenge(
                challenge_id, account_ids=await _scope(user, None)
            )
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
        user: dict = Depends(require_user),
    ):
        start_value = payload.get("start_time")
        end_value = payload.get("end_time")
        start_time = start_value if isinstance(start_value, str) else None
        end_time = end_value if isinstance(end_value, str) else None
        clear_end_time = "end_time" in payload and not end_time
        try:
            await store.get_oxygen_challenge(  # ownership check -> KeyError
                challenge_id, account_ids=await _scope(user, None)
            )
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
    async def delete_oxygen_challenge(
        challenge_id: int = Path(ge=1),
        user: dict = Depends(require_user),
    ):
        deleted = await store.delete_oxygen_challenge(
            challenge_id, account_ids=await _scope(user, None)
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Challenge not found")
        return {"ok": True}

    @app.get("/api/readings/window")
    async def readings_window(
        around: str = Query(min_length=10),
        span: int = Query(default=45, ge=5, le=24 * 60),
        account: int | None = Query(default=None, ge=1),
        user: dict = Depends(require_user),
    ):
        """A precise slice around a moment — feeds the focus modal without
        dragging the whole history over the wire."""
        try:
            center = datetime.fromisoformat(around.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid timestamp") from exc
        if center.tzinfo is None:
            center = center.replace(tzinfo=timezone.utc)
        half = timedelta(minutes=span / 2)
        rows = await store.get_readings_window(
            start=center - half,
            end=center + half,
            account_ids=await _scope(user, account),
        )
        return [_reading_response(row) for row in rows]

    @app.post("/api/notifications/read")
    async def mark_notifications_read(user: dict = Depends(require_user)):
        marked = await store.mark_notifications_read(account_ids=await _scope(user, None))
        return {"ok": True, "marked": marked}

    @app.get("/api/events")
    async def care_events(
        hours: int | None = Query(default=48, ge=1, le=24 * 365),
        limit: int = Query(default=500, ge=1, le=2000),
        account: int | None = Query(default=None, ge=1),
        user: dict = Depends(require_user),
    ):
        events = await store.get_care_events(
            hours=hours, limit=limit, account_ids=await _scope(user, account)
        )
        return {"events": events}

    @app.post("/api/events")
    async def create_care_event(
        payload: dict[str, object] = JSON_BODY,
        user: dict = Depends(require_user),
    ):
        kind = str(payload.get("kind") or "").strip()
        if not kind or len(kind) > 60:
            raise HTTPException(status_code=400, detail="kind is required (max 60 chars)")
        at = payload.get("at")
        note = str(payload.get("note") or "")[:500]
        method = str(payload.get("method") or "").strip()
        if method not in ("", "bottle", "nursing", "solids"):
            method = ""
        amount_ml = payload.get("amount_ml")
        amount_ml = (
            round(float(amount_ml), 1)
            if isinstance(amount_ml, (int, float)) and 0 < float(amount_ml) <= 500
            else None
        )
        duration_min = payload.get("duration_min")
        duration_min = (
            round(float(duration_min), 1)
            if isinstance(duration_min, (int, float)) and 0 < float(duration_min) <= 180
            else None
        )
        account_id = payload.get("account_id")
        requested = (
            int(account_id)
            if isinstance(account_id, int | str) and str(account_id).isdigit()
            else None
        )
        ids = await _scope(user, requested)
        if not ids:
            raise HTTPException(status_code=400, detail="Link an Owlet account first")
        try:
            event = await store.create_care_event(
                account_id=ids[0],
                at=at if isinstance(at, str) and at else datetime.now(timezone.utc),
                kind=kind,
                note=note,
                method=method,
                amount_ml=amount_ml,
                duration_min=duration_min,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid timestamp") from exc
        return {"event": event}

    @app.delete("/api/events/{event_id}")
    async def delete_care_event(
        event_id: int = Path(ge=1),
        user: dict = Depends(require_user),
    ):
        deleted = await store.delete_care_event(event_id, account_ids=await _scope(user, None))
        if not deleted:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"ok": True}

    @app.get("/api/widget")
    async def widget(
        hours: int = Query(default=24, ge=1, le=24 * 30),
        device: str | None = Query(default=None),
        account: int | None = Query(default=None, ge=1),
        user: dict = Depends(require_user),
    ):
        return await _widget_payload(
            store, hours=hours, device=device, account_ids=await _scope(user, account)
        )

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
    account_ids: list[int] | None = None,
) -> dict[str, object]:
    readings = await store.get_analysis_readings(hours=hours, limit=100_000, device_serial=device, account_ids=account_ids)
    summary = await store.get_summary(hours=hours, device_serial=device, account_ids=account_ids)
    insights = build_insights(await store.exclude_challenge_readings(readings, account_ids=account_ids))
    # Fixed week-wide window: the unread badge and toast source must not
    # shrink with the caller's vitals window (the shell polls with hours=1).
    notifications = await store.get_notifications(
        hours=24 * 7,
        limit=1,
        offset=0,
        device_serial=device,
        account_ids=account_ids,
    )
    latest_reading = readings[-1].model_dump(mode="json", exclude={"raw"}) if readings else {}
    latest = latest_reading or insights.get("latest") or {}
    breathing = insights.get("breathing") or {}
    latest_notification = notifications["items"][0] if notifications["items"] else None
    return {
        "updated_at": latest.get("recorded_at") if isinstance(latest, dict) else None,
        "sock_reporting": bool(readings) and not is_offline_reading(readings[-1]),
        "window": summary["window"],
        "oxygen_now": latest.get("oxygen_saturation") if isinstance(latest, dict) else None,
        "oxygen_avg": summary["oxygen_saturation"]["avg"],
        "heart_rate": latest.get("heart_rate") if isinstance(latest, dict) else None,
        "trend": breathing.get("direction"),
        "trend_sentence": breathing.get("plain_language"),
        "battery": latest.get("battery") if isinstance(latest, dict) else None,
        "battery_minutes": latest.get("battery_minutes") if isinstance(latest, dict) else None,
        "charging": bool(latest.get("charging")) if isinstance(latest, dict) else False,
        "signal_strength": latest.get("signal_strength") if isinstance(latest, dict) else None,
        "notification_count": notifications["total"],
        "unread_notifications": notifications.get("unread_total", 0),
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
            if str(key) in {"heartRate", "oxygen", "movement", "skinTemperature", "notifications", "o2Trailing30", "o2Baseline4h", "o2TrendSignal"}
            and isinstance(setting, bool)
        }
    chart_settings = value.get("chart_settings")
    if isinstance(chart_settings, dict):
        safe_settings: dict[str, object] = {}
        window_value = chart_settings.get("window")
        if str(window_value) in {"6", "12", "24", "72", "168", "720", "all"}:
            safe_settings["window"] = str(window_value)
        smoothing = chart_settings.get("smoothing")
        if str(smoothing) in {"raw", "5", "15", "30", "60", "240"}:
            safe_settings["smoothing"] = str(smoothing)
        layout_value = chart_settings.get("layout")
        if str(layout_value) in {"combined", "split"}:
            safe_settings["layout"] = str(layout_value)
        for key in ("challenge_bands", "sleep_highlight", "sleep_ballpark"):
            if isinstance(chart_settings.get(key), bool):
                safe_settings[key] = bool(chart_settings[key])
        allowed["chart_settings"] = safe_settings
    theme_value = value.get("theme")
    if str(theme_value) in {"auto", "light", "dark"}:
        allowed["theme"] = str(theme_value)
    if str(value.get("movement_source")) in {"raw", "bucket"}:
        allowed["movement_source"] = str(value.get("movement_source"))
    if str(value.get("o2_display")) in {"raw", "smoothed"}:
        allowed["o2_display"] = str(value.get("o2_display"))
    if isinstance(value.get("feed_tracking"), bool):
        allowed["feed_tracking"] = bool(value.get("feed_tracking"))
    baby_name = value.get("baby_name")
    if isinstance(baby_name, str):
        allowed["baby_name"] = baby_name.strip()[:40]
    if "birth_date" in value:
        raw_birth = value.get("birth_date")
        if raw_birth in (None, ""):
            allowed["birth_date"] = None
        else:
            birth = _valid_birth_date(raw_birth)
            if birth is not None:
                allowed["birth_date"] = birth
    if "o2_alert_threshold" in value:
        raw_threshold = value.get("o2_alert_threshold")
        if raw_threshold in (None, 0, "", "0"):
            allowed["o2_alert_threshold"] = None
        elif isinstance(raw_threshold, (int, float)) and 80 <= int(raw_threshold) <= 95:
            allowed["o2_alert_threshold"] = int(raw_threshold)
    # Two-tier oxygen colouring. Each bound is validated on its own; the
    # ordering rule (critical strictly below warn) is applied when the pair is
    # resolved, so saving one half of the pair can never wedge the other.
    for key in ("o2_warn_threshold", "o2_critical_threshold"):
        if key in value:
            raw_bound = value.get(key)
            if raw_bound in (None, ""):
                allowed[key] = None
            elif (
                isinstance(raw_bound, (int, float))
                and O2_THRESHOLD_MIN <= int(raw_bound) <= O2_THRESHOLD_MAX
            ):
                allowed[key] = int(raw_bound)
    for key in ("night_start", "night_end"):
        if key in value:
            clock = _valid_clock(value.get(key))
            if clock is not None:
                allowed[key] = clock
    if "readiness_report_time" in value:
        raw_time = value.get("readiness_report_time")
        if raw_time in (None, ""):
            allowed["readiness_report_time"] = None
        else:
            clock = _valid_clock(raw_time)
            if clock is not None:
                allowed["readiness_report_time"] = clock
    if "tz_offset_minutes" in value:
        raw_offset = value.get("tz_offset_minutes")
        if isinstance(raw_offset, (int, float)) and -840 <= int(raw_offset) <= 840:
            allowed["tz_offset_minutes"] = int(raw_offset)
    if "timezone" in value:
        raw_tz = value.get("timezone")
        if raw_tz in (None, "", "auto"):
            allowed["timezone"] = None
        elif isinstance(raw_tz, str) and len(raw_tz) <= 64:
            try:
                ZoneInfo(raw_tz)
            except (KeyError, ValueError, ZoneInfoNotFoundError):
                pass
            else:
                allowed["timezone"] = raw_tz
    return allowed


def _valid_clock(value: object) -> str | None:
    """Accept 'HH:MM' 24-hour strings and nothing else."""
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        return None
    try:
        hour, minute = int(value[:2]), int(value[3:])
    except ValueError:
        return None
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return None


def _valid_birth_date(value: object) -> str | None:
    """Accept an ISO 'YYYY-MM-DD' date that isn't in the future or absurdly old."""
    if not isinstance(value, str):
        return None
    try:
        birth = date.fromisoformat(value)
    except ValueError:
        return None
    today = datetime.now(timezone.utc).date()
    if birth > today or birth < today - timedelta(days=366 * 6):
        return None
    return birth.isoformat()


def _public_account(account: dict[str, object]) -> dict[str, object]:
    return {
        "id": account.get("id"),
        "email": account.get("email"),
        "region": account.get("region"),
        "display_name": account.get("display_name"),
        "status": account.get("status"),
        "poll_interval_seconds": account.get("poll_interval_seconds"),
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
