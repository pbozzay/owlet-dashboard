from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app import auth_pages
from app.security import hash_password, hash_token, new_token, verify_password

router = APIRouter()

SESSION_COOKIE = "owlet_session"
MIN_PASSWORD, MAX_PASSWORD = 8, 128


def _auth(request: Request):
    return request.app.state.auth_store


def _limiter(request: Request):
    return request.app.state.rate_limiter


def _settings(request: Request):
    return request.app.state.settings


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def set_session_cookie(response: Response, request: Request, raw_token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",  # real deployments sit behind https nginx
        max_age=30 * 24 * 3600,
        path="/",
    )


async def current_user(request: Request) -> dict | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    return await _auth(request).get_session_user(hash_token(raw))


async def require_user(request: Request) -> dict:
    user = await current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


async def _start_session(request: Request, user_id: int) -> Response:
    raw = new_token()
    await _auth(request).create_session(
        user_id, hash_token(raw), user_agent=request.headers.get("user-agent", "")
    )
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, request, raw)
    return response


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, error: str | None = None):
    if await current_user(request):
        return RedirectResponse("/", status_code=303)
    return auth_pages.login_page(error=error, desktop_mode=_settings(request).desktop_mode)


@router.get("/signup", response_class=HTMLResponse)
async def signup_form(error: str | None = None):
    return auth_pages.signup_page(error=error)


@router.post("/auth/signup")
async def signup(request: Request, email: str = Form(), password: str = Form()):
    if not _limiter(request).allow(f"signup:{_client_ip(request)}", max_hits=5, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Too many signups; try again later")
    if not (MIN_PASSWORD <= len(password) <= MAX_PASSWORD):
        return RedirectResponse("/signup?error=Password+must+be+8-128+characters", status_code=303)
    try:
        user = await _auth(request).create_user(email, hash_password(password))
    except ValueError:
        return RedirectResponse("/signup?error=That+email+is+already+registered", status_code=303)
    return await _start_session(request, user["id"])


@router.post("/auth/login")
async def login(request: Request, email: str = Form(), password: str = Form()):
    limiter = _limiter(request)
    if not limiter.allow(f"login:{_client_ip(request)}", max_hits=10, window_seconds=60) or not limiter.allow(
        f"login:{email.strip().lower()}", max_hits=10, window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many attempts; wait a minute")
    user = await _auth(request).get_user_by_email(email)
    if not user or not verify_password(user["password_hash"], password):
        return RedirectResponse("/login?error=Wrong+email+or+password", status_code=303)
    return await _start_session(request, user["id"])


@router.post("/auth/logout")
async def logout(request: Request):
    raw = request.cookies.get(SESSION_COOKIE)
    if raw:
        await _auth(request).delete_session(hash_token(raw))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


async def _verified_user(request: Request, current_password: str) -> dict:
    """Re-authenticate for account-credential changes: a live session cookie
    alone must never be enough to take over the login."""
    if not _limiter(request).allow(f"credchange:{_client_ip(request)}", max_hits=8, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many attempts; wait a few minutes")
    user = await require_user(request)
    if not verify_password(user["password_hash"], current_password or ""):
        raise HTTPException(status_code=403, detail="Current password is wrong")
    return user


@router.post("/auth/change-email")
async def change_email(request: Request):
    payload = await request.json()
    user = await _verified_user(request, str(payload.get("current_password") or ""))
    email = str(payload.get("email") or "").strip()
    if "@" not in email or len(email) < 6 or len(email) > 254:
        raise HTTPException(status_code=400, detail="That doesn't look like an email address")
    try:
        await _auth(request).update_email(user["id"], email)
    except ValueError:
        raise HTTPException(status_code=409, detail="That email is already registered") from None
    return {"ok": True, "email": email.lower()}


@router.post("/auth/change-password")
async def change_password(request: Request):
    payload = await request.json()
    user = await _verified_user(request, str(payload.get("current_password") or ""))
    new_password = str(payload.get("new_password") or "")
    if not (MIN_PASSWORD <= len(new_password) <= MAX_PASSWORD):
        raise HTTPException(status_code=400, detail="Password must be 8-128 characters")
    auth = _auth(request)
    await auth.update_password(user["id"], hash_password(new_password))
    raw = request.cookies.get(SESSION_COOKIE) or ""
    dropped = await auth.delete_other_sessions(user["id"], hash_token(raw))
    return {"ok": True, "other_sessions_signed_out": dropped}
