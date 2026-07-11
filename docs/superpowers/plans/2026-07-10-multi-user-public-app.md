# Multi-User Public App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single-family Owlet dashboard into a public multi-user app: email+password auth, per-user tenancy, encrypted Owlet tokens, adaptive polling, retention/backups, shipped as one Docker container for Unraid behind the owner's nginx.

**Architecture:** One FastAPI process serves session-gated web/API routes and runs per-account asyncio pollers; SQLite (WAL) on a `/data` volume; new `AuthStore` (users/sessions/auth_tokens) beside the existing `ReadingStore`; Resend for verification/reset email. Spec: `docs/superpowers/specs/2026-07-10-multi-user-public-app-design.md`.

**Tech Stack:** FastAPI, aiosqlite, argon2-cffi, cryptography (Fernet), httpx (Resend API), python-multipart (form posts), pytest + httpx TestClient, Docker + GitHub Actions → GHCR.

**Conventions for every task:**
- Run tests with: `.venv/Scripts/python -m pytest <file>::<test> -v` (Windows venv in repo root). Full suite: `.venv/Scripts/python -m pytest -q`.
- `pyproject.toml` sets `asyncio_mode = "auto"` — async tests need no decorator (existing files use explicit `@pytest.mark.asyncio`; both work).
- All timestamps are `datetime.now(UTC).isoformat()` strings, matching existing store code.
- Commit after each task with the message given in its final step.

---

## File Map (who owns what)

| File | Status | Responsibility |
|---|---|---|
| `app/security.py` | create | Password hashing, token generate/hash, Fernet `TokenCipher` |
| `app/auth_store.py` | create | `AuthStore`: users, sessions, auth_tokens, share tokens, orphan-account adoption |
| `app/emailer.py` | create | `Emailer` (Resend via httpx) with console fallback capturing sent mail |
| `app/ratelimit.py` | create | In-memory sliding-window `RateLimiter` |
| `app/auth_pages.py` | create | HTML for login/signup/forgot/reset/verify-gate/onboarding/settings/terms/privacy |
| `app/auth_routes.py` | create | Auth router + `current_user`/`require_verified_user` dependencies + cookie helpers |
| `app/settings_routes.py` | create | Settings router: password change, logout-all, share token, delete account |
| `app/maintenance.py` | create | Daily task: raw-payload trim, downsample, DB snapshot rotation |
| `app/config.py` | modify | New env surface; legacy Owlet/basic-auth/share env removed at the end |
| `app/store.py` | modify | `user_id` on accounts, `account_ids` scoping, token encryption, metadata helpers, cascade delete, retention SQL |
| `app/main.py` | modify | Session/CSRF middleware, route gating, tenancy scoping, share-token resolution, maintenance task |
| `app/poller.py` | modify | Adaptive interval, jitter, backoff, heartbeat |
| `app/dashboard.py` | modify | Logout/settings in profile menu area, collector-offline banner (JS-injected) |
| `Dockerfile`, `.dockerignore`, `.github/workflows/docker.yml` | create | Packaging + GHCR publish |
| `tests/conftest.py` | create | App/auth fixtures shared by all API tests |
| `tests/test_security.py`, `test_auth_store.py`, `test_auth.py`, `test_tenancy.py`, `test_poller.py`, `test_maintenance.py` | create | New coverage |
| `tests/test_api.py`, `tests/test_store.py` | modify | Adapt to auth + explicit account ids |
| `README.md`, `docs/deployment.md`, `.env.example` | modify | New setup story |

---

### Task 1: Security primitives (`app/security.py`)

**Files:**
- Modify: `pyproject.toml` (dependencies)
- Create: `app/security.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: Add dependencies**

In `pyproject.toml`, change the `dependencies` list to:

```toml
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic-settings>=2.4.0",
  "aiosqlite>=0.20.0",
  "pyowletapi>=2025.4.10",
  "argon2-cffi>=23.1.0",
  "cryptography>=43.0.0",
  "httpx>=0.27.0",
  "python-multipart>=0.0.9",
]
```

(`httpx` moves from dev-only to runtime; leave the `dev` extra as is.)

Run: `.venv/Scripts/python -m pip install -e ".[dev]" --quiet`

- [ ] **Step 2: Write the failing test**

Create `tests/test_security.py`:

```python
from cryptography.fernet import Fernet

from app.security import TokenCipher, hash_password, hash_token, new_token, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse")
    assert hashed != "correct horse"
    assert verify_password(hashed, "correct horse") is True
    assert verify_password(hashed, "wrong") is False
    assert verify_password("not-a-hash", "anything") is False


def test_tokens_are_random_and_hash_deterministically():
    a, b = new_token(), new_token()
    assert a != b and len(a) >= 40
    assert hash_token(a) == hash_token(a)
    assert hash_token(a) != hash_token(b)


def test_cipher_roundtrip_and_plaintext_passthrough():
    cipher = TokenCipher(Fernet.generate_key().decode())
    secret = "owlet-refresh-token"
    encrypted = cipher.encrypt(secret)
    assert encrypted != secret
    assert cipher.decrypt(encrypted) == secret
    assert cipher.is_encrypted(encrypted) is True
    # Legacy plaintext rows must read through unchanged.
    assert cipher.decrypt("plain-legacy-token") == "plain-legacy-token"
    assert cipher.is_encrypted("plain-legacy-token") is False
    assert cipher.encrypt(None) is None
    assert cipher.decrypt(None) is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_security.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.security'`

- [ ] **Step 4: Implement `app/security.py`**

```python
from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def new_token() -> str:
    """256-bit URL-safe token for sessions, email links, and share URLs."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TokenCipher:
    """Fernet wrapper for Owlet api/refresh tokens at rest.

    decrypt() passes unrecognized values through unchanged so rows written
    before encryption keep working until the startup migration re-writes them.
    """

    def __init__(self, key: str):
        self._fernet = Fernet(key.encode("utf-8") if isinstance(key, str) else key)

    def encrypt(self, value: str | None) -> str | None:
        if value in (None, ""):
            return value
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str | None) -> str | None:
        if value in (None, ""):
            return value
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            return value

    def is_encrypted(self, value: str | None) -> bool:
        if value in (None, ""):
            return False
        try:
            self._fernet.decrypt(str(value).encode("utf-8"))
            return True
        except (InvalidToken, ValueError):
            return False
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_security.py -v`
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml app/security.py tests/test_security.py
git commit -m "feat: add password hashing, token, and Fernet cipher primitives"
```

---

### Task 2: Config surface (`app/config.py`)

**Files:**
- Modify: `app/config.py`
- Modify: `.env.example`
- Test: `tests/test_security.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_security.py`:

```python
def test_settings_new_fields_have_safe_defaults():
    from app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.secret_key is None
    assert settings.token_encryption_key is None
    assert settings.resend_api_key is None
    assert settings.app_base_url == "http://127.0.0.1:8888"
    assert settings.cookie_secure is True
    assert settings.poll_idle_seconds == 300
    assert settings.retention_raw_days == 7
    assert settings.retention_full_days == 180
    assert settings.auth_ready is False
    assert Settings(_env_file=None, secret_key="x", token_encryption_key="y").auth_ready is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_security.py::test_settings_new_fields_have_safe_defaults -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'secret_key'`

- [ ] **Step 3: Implement**

In `app/config.py`, add these fields to `Settings` (after `owlet_share_token`, before `model_config`):

```python
    secret_key: str | None = Field(default=None, alias="SECRET_KEY")
    token_encryption_key: str | None = Field(default=None, alias="TOKEN_ENCRYPTION_KEY")
    resend_api_key: str | None = Field(default=None, alias="RESEND_API_KEY")
    email_from: str = Field(default="Owlet Dashboard <onboarding@resend.dev>", alias="EMAIL_FROM")
    app_base_url: str = Field(default="http://127.0.0.1:8888", alias="APP_BASE_URL")
    cookie_secure: bool = Field(default=True, alias="COOKIE_SECURE")
    poll_idle_seconds: int = Field(default=300, alias="POLL_IDLE_SECONDS")
    retention_raw_days: int = Field(default=7, alias="RETENTION_RAW_DAYS")
    retention_full_days: int = Field(default=180, alias="RETENTION_FULL_DAYS")
```

And add this property next to `has_owlet_credentials`:

```python
    @property
    def auth_ready(self) -> bool:
        return bool(self.secret_key and self.token_encryption_key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_security.py -v`
Expected: all PASS

- [ ] **Step 5: Update `.env.example`**

Replace the full contents of `.env.example` with:

```bash
# --- Required for multi-user auth ---
# Generate each with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SECRET_KEY=
TOKEN_ENCRYPTION_KEY=

# --- Email (verification + password reset) ---
# Leave RESEND_API_KEY empty in development: emails are logged to the console instead.
RESEND_API_KEY=
EMAIL_FROM=Owlet Dashboard <onboarding@resend.dev>
APP_BASE_URL=http://127.0.0.1:8888

# --- Server ---
DATABASE_PATH=data/owlet.sqlite3
HOST=127.0.0.1
PORT=8888
COOKIE_SECURE=true

# --- Polling / retention ---
POLL_INTERVAL_SECONDS=30
POLL_IDLE_SECONDS=300
RETENTION_RAW_DAYS=7
RETENTION_FULL_DAYS=180
```

Then update the developer's local `.env`: keep existing values, append generated `SECRET_KEY` and `TOKEN_ENCRYPTION_KEY` (run the generator command twice), and add `COOKIE_SECURE=false` for local http.

- [ ] **Step 6: Commit**

```bash
git add app/config.py .env.example tests/test_security.py
git commit -m "feat: add auth/email/retention settings to config surface"
```

---

### Task 3: `AuthStore` (`app/auth_store.py`)

**Files:**
- Create: `app/auth_store.py`
- Test: `tests/test_auth_store.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_auth_store.py`:

```python
import pytest

from app.auth_store import AuthStore
from app.security import hash_password, hash_token, new_token
from app.store import ReadingStore


@pytest.mark.asyncio
async def test_user_crud_and_email_normalization(tmp_path):
    auth = AuthStore(tmp_path / "owlet.sqlite3")
    user = await auth.create_user("Parent@Example.COM", hash_password("hunter22"))
    assert user["email"] == "parent@example.com"
    assert user["email_verified_at"] is None
    assert await auth.get_user_by_email("PARENT@example.com") == user
    with pytest.raises(ValueError):
        await auth.create_user("parent@example.com", hash_password("other"))
    await auth.mark_email_verified(user["id"])
    assert (await auth.get_user(user["id"]))["email_verified_at"] is not None


@pytest.mark.asyncio
async def test_sessions_expire_and_revoke(tmp_path):
    auth = AuthStore(tmp_path / "owlet.sqlite3")
    user = await auth.create_user("a@b.c", hash_password("hunter22"))
    token = new_token()
    await auth.create_session(user["id"], hash_token(token), ttl_days=30)
    assert (await auth.get_session_user(hash_token(token)))["id"] == user["id"]
    assert await auth.get_session_user(hash_token("nope")) is None
    expired = new_token()
    await auth.create_session(user["id"], hash_token(expired), ttl_days=-1)
    assert await auth.get_session_user(hash_token(expired)) is None
    await auth.delete_user_sessions(user["id"])
    assert await auth.get_session_user(hash_token(token)) is None


@pytest.mark.asyncio
async def test_auth_tokens_single_use_purpose_and_expiry(tmp_path):
    auth = AuthStore(tmp_path / "owlet.sqlite3")
    user = await auth.create_user("a@b.c", hash_password("hunter22"))
    raw = new_token()
    await auth.create_auth_token(user["id"], hash_token(raw), purpose="verify", ttl_minutes=15)
    assert await auth.consume_auth_token(hash_token(raw), purpose="password_reset") is None
    assert await auth.consume_auth_token(hash_token(raw), purpose="verify") == user["id"]
    assert await auth.consume_auth_token(hash_token(raw), purpose="verify") is None  # single use
    stale = new_token()
    await auth.create_auth_token(user["id"], hash_token(stale), purpose="verify", ttl_minutes=-1)
    assert await auth.consume_auth_token(hash_token(stale), purpose="verify") is None


@pytest.mark.asyncio
async def test_share_tokens(tmp_path):
    auth = AuthStore(tmp_path / "owlet.sqlite3")
    user = await auth.create_user("a@b.c", hash_password("hunter22"))
    raw = new_token()
    await auth.set_share_token(user["id"], hash_token(raw))
    assert (await auth.get_user_by_share_token(hash_token(raw)))["id"] == user["id"]
    await auth.set_share_token(user["id"], None)
    assert await auth.get_user_by_share_token(hash_token(raw)) is None


@pytest.mark.asyncio
async def test_first_user_adopts_orphan_accounts(tmp_path):
    db = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db)
    await store.init()  # creates legacy 'Default account' style rows without user_id
    orphan = await store.create_account(email="sock@example.com")
    auth = AuthStore(db)
    first = await auth.create_user("first@example.com", hash_password("hunter22"))
    second = await auth.create_user("second@example.com", hash_password("hunter22"))
    owned_first = await store.list_accounts(user_id=first["id"])
    owned_second = await store.list_accounts(user_id=second["id"])
    assert {a["id"] for a in owned_first} >= {orphan["id"]}
    assert owned_second == []
```

Note: `list_accounts(user_id=...)` does not exist yet — Task 4 adds it. To keep this task self-contained, comment out ONLY the final test (`test_first_user_adopts_orphan_accounts`) with a `# enabled in Task 4` marker, and re-enable it during Task 4 Step 1.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_auth_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.auth_store'`

- [ ] **Step 3: Implement `app/auth_store.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite


def _now() -> datetime:
    return datetime.now(UTC)


class AuthStore:
    """Users, sessions, and one-time auth tokens. Shares the SQLite file with ReadingStore."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    email_verified_at TEXT,
                    share_token_hash TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT NOT NULL,
                    user_agent TEXT NOT NULL DEFAULT ''
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    purpose TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used_at TEXT
                )
                """
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
            await db.commit()

    # -- users ---------------------------------------------------------------

    async def create_user(self, email: str, password_hash: str) -> dict[str, Any]:
        await self.init()
        normalized = email.strip().lower()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(
                    "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                    (normalized, password_hash),
                )
            except aiosqlite.IntegrityError as exc:
                raise ValueError("email already registered") from exc
            user_id = int(cursor.lastrowid)
            # First user adopts any accounts created before multi-user existed.
            await self._adopt_orphan_accounts(db, user_id)
            await db.commit()
        return await self.get_user(user_id)

    async def _adopt_orphan_accounts(self, db: aiosqlite.Connection, user_id: int) -> None:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='accounts'"
        )
        if not (row := await cursor.fetchone()) or not row[0]:
            return
        columns = [r[1] for r in await (await db.execute("PRAGMA table_info(accounts)")).fetchall()]
        if "user_id" not in columns:
            return
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        count_row = await cursor.fetchone()
        if int(count_row[0]) == 1:  # the user we just inserted is the first
            await db.execute("UPDATE accounts SET user_id = ? WHERE user_id IS NULL", (user_id,))

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, email, password_hash, email_verified_at, share_token_hash, created_at, updated_at "
                "FROM users WHERE id = ?",
                (user_id,),
            )
            return _row_to_user(await cursor.fetchone())

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, email, password_hash, email_verified_at, share_token_hash, created_at, updated_at "
                "FROM users WHERE email = ?",
                (email.strip().lower(),),
            )
            return _row_to_user(await cursor.fetchone())

    async def mark_email_verified(self, user_id: int) -> None:
        await self._execute(
            "UPDATE users SET email_verified_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (_now().isoformat(), user_id),
        )

    async def set_password(self, user_id: int, password_hash: str) -> None:
        await self._execute(
            "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (password_hash, user_id),
        )

    async def delete_user(self, user_id: int) -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM auth_tokens WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            await db.commit()

    # -- sessions ------------------------------------------------------------

    async def create_session(
        self, user_id: int, token_hash: str, *, ttl_days: int = 30, user_agent: str = ""
    ) -> None:
        expires = (_now() + timedelta(days=ttl_days)).isoformat()
        await self._execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at, user_agent) VALUES (?, ?, ?, ?)",
            (token_hash, user_id, expires, user_agent[:200]),
        )

    async def get_session_user(self, token_hash: str) -> dict[str, Any] | None:
        await self.init()
        now = _now()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT u.id, u.email, u.password_hash, u.email_verified_at, u.share_token_hash,
                       u.created_at, u.updated_at, s.expires_at, s.last_seen_at
                FROM sessions s JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ?
                """,
                (token_hash,),
            )
            row = await cursor.fetchone()
            if not row or datetime.fromisoformat(row[7]) < now:
                return None
            last_seen = datetime.fromisoformat(row[8])
            if (now - last_seen) > timedelta(hours=1):  # rolling expiry, throttled writes
                await db.execute(
                    "UPDATE sessions SET last_seen_at = ?, expires_at = ? WHERE token_hash = ?",
                    (now.isoformat(), (now + timedelta(days=30)).isoformat(), token_hash),
                )
                await db.commit()
            return _row_to_user(row[:7])

    async def delete_session(self, token_hash: str) -> None:
        await self._execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    async def delete_user_sessions(self, user_id: int) -> None:
        await self._execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    # -- one-time tokens -------------------------------------------------------

    async def create_auth_token(
        self, user_id: int, token_hash: str, *, purpose: str, ttl_minutes: int = 15
    ) -> None:
        expires = (_now() + timedelta(minutes=ttl_minutes)).isoformat()
        await self._execute(
            "INSERT OR REPLACE INTO auth_tokens (token_hash, user_id, purpose, expires_at, used_at) "
            "VALUES (?, ?, ?, ?, NULL)",
            (token_hash, user_id, purpose, expires),
        )

    async def consume_auth_token(self, token_hash: str, *, purpose: str) -> int | None:
        await self.init()
        now = _now()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, purpose, expires_at, used_at FROM auth_tokens WHERE token_hash = ?",
                (token_hash,),
            )
            row = await cursor.fetchone()
            if (
                not row
                or row[1] != purpose
                or row[3] is not None
                or datetime.fromisoformat(row[2]) < now
            ):
                return None
            await db.execute(
                "UPDATE auth_tokens SET used_at = ? WHERE token_hash = ?",
                (now.isoformat(), token_hash),
            )
            await db.commit()
            return int(row[0])

    # -- share tokens ----------------------------------------------------------

    async def set_share_token(self, user_id: int, token_hash: str | None) -> None:
        await self._execute(
            "UPDATE users SET share_token_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (token_hash, user_id),
        )

    async def get_user_by_share_token(self, token_hash: str) -> dict[str, Any] | None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, email, password_hash, email_verified_at, share_token_hash, created_at, updated_at "
                "FROM users WHERE share_token_hash = ?",
                (token_hash,),
            )
            return _row_to_user(await cursor.fetchone())

    async def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, params)
            await db.commit()


def _row_to_user(row: tuple[Any, ...] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": int(row[0]),
        "email": row[1],
        "password_hash": row[2],
        "email_verified_at": row[3],
        "share_token_hash": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_auth_store.py -v`
Expected: 4 PASS (adoption test still commented out)

- [ ] **Step 5: Commit**

```bash
git add app/auth_store.py tests/test_auth_store.py
git commit -m "feat: add AuthStore for users, sessions, and one-time tokens"
```

---

### Task 4: Account ownership + scoped queries (`app/store.py`)

**Files:**
- Modify: `app/store.py`
- Test: `tests/test_auth_store.py` (re-enable last test), `tests/test_store.py` (append)

- [ ] **Step 1: Re-enable and extend failing tests**

Re-enable `test_first_user_adopts_orphan_accounts` in `tests/test_auth_store.py`. Append to `tests/test_store.py`:

```python
import pytest

from app.models import normalize_reading
from app.store import ReadingStore


@pytest.mark.asyncio
async def test_account_ids_scope_readings_and_devices(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    a = await store.create_account(email="a@x.y", user_id=1)
    b = await store.create_account(email="b@x.y", user_id=2)
    for account, hr in ((a, 100), (b, 150)):
        await store.insert_reading(
            normalize_reading(
                {"heart_rate": hr, "oxygen_saturation": 95, "last_updated": "2026-07-02T01:00:00Z"},
                f"S{account['id']}",
            ),
            account_id=account["id"],
        )
    only_a = await store.get_readings(hours=None, account_ids=[a["id"]])
    both = await store.get_readings(hours=None, account_ids=[a["id"], b["id"]])
    none = await store.get_readings(hours=None, account_ids=[])
    assert [r.heart_rate for r in only_a] == [100]
    assert len(both) == 2
    assert none == []
    assert [d["account_id"] for d in await store.list_devices(account_ids=[b["id"]])] == [b["id"]]
    assert (await store.get_summary(hours=None, account_ids=[a["id"]]))["count"] == 1
    assert (await store.get_notifications(account_ids=[]))["items"] == []
    assert (await store.get_oxygen_challenges(account_ids=[]))["items"] == []


@pytest.mark.asyncio
async def test_list_accounts_filters_by_user_and_get_account_enforces_owner(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    mine = await store.create_account(email="mine@x.y", user_id=7)
    await store.create_account(email="theirs@x.y", user_id=8)
    assert [a["id"] for a in await store.list_accounts(user_id=7)] == [mine["id"]]
    assert (await store.get_account(mine["id"], user_id=7))["id"] == mine["id"]
    with pytest.raises(KeyError):
        await store.get_account(mine["id"], user_id=8)


@pytest.mark.asyncio
async def test_fresh_db_creates_no_default_account(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    assert await store.list_accounts() == []


@pytest.mark.asyncio
async def test_delete_accounts_for_user_cascades(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    acc = await store.create_account(email="a@x.y", user_id=3)
    await store.insert_reading(
        normalize_reading(
            {"heart_rate": 120, "oxygen_saturation": 95, "last_updated": "2026-07-02T01:00:00Z"}, "S1"
        ),
        account_id=acc["id"],
    )
    await store.create_oxygen_challenge("2026-07-02T00:00:00Z", account_id=acc["id"])
    await store.delete_accounts_for_user(3)
    assert await store.list_accounts(user_id=3) == []
    assert await store.get_readings(hours=None, account_ids=[acc["id"]]) == []
    assert (await store.get_oxygen_challenges(account_ids=[acc["id"]]))["items"] == []
```

**Important compatibility note:** `test_fresh_db_creates_no_default_account` changes existing behavior — `init()` currently always creates a "Default account" row, and several existing tests in `tests/test_api.py` / `tests/test_store.py` rely on it (`(await store.list_accounts())[0]`, seeds with `account_id=None`). Those call sites are updated in this task (Step 3d) and Task 8.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_store.py tests/test_auth_store.py -v`
Expected: new tests FAIL (`unexpected keyword argument 'account_ids'` / `'user_id'`)

- [ ] **Step 3: Implement in `app/store.py`**

**(a) Schema.** In `init()`'s `CREATE TABLE IF NOT EXISTS accounts`, add `user_id INTEGER,` after `id`. In `_ensure_account_preference_schema`, add:

```python
        if "user_id" not in columns:
            await db.execute("ALTER TABLE accounts ADD COLUMN user_id INTEGER")
```

**(b) No auto default account on fresh DBs.** Replace `_ensure_account_schema`'s first line and `_ensure_default_account` usage:

```python
    async def _ensure_account_schema(self, db: aiosqlite.Connection) -> None:
        await self._ensure_account_preference_schema(db)
        default_account_id = await self._legacy_default_account_id(db)
        await self._ensure_readings_account_schema(db, default_account_id)
        await self._ensure_notifications_account_schema(db, default_account_id)
        await self._ensure_challenges_account_schema(db, default_account_id)
        # ... (existing index creation stays unchanged)

    async def _legacy_default_account_id(self, db: aiosqlite.Connection) -> int:
        """Existing first account, or create one ONLY if legacy rows need an owner."""
        cursor = await db.execute("SELECT id FROM accounts ORDER BY id ASC LIMIT 1")
        row = await cursor.fetchone()
        if row:
            return int(row[0])
        needs_owner = False
        for table in ("readings", "notifications", "oxygen_challenges"):
            cursor = await db.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)
            )
            exists_row = await cursor.fetchone()
            if exists_row and exists_row[0]:
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                count_row = await cursor.fetchone()
                if count_row and int(count_row[0]) > 0:
                    needs_owner = True
                    break
        if not needs_owner:
            return 0  # fresh database: no account rows at all
        cursor = await db.execute(
            "INSERT INTO accounts (email, region, display_name, status, updated_at) "
            "VALUES ('', 'world', 'Default account', 'active', CURRENT_TIMESTAMP)"
        )
        return int(cursor.lastrowid)
```

Delete the old `_ensure_default_account` and the `default_account_id()` public method. `insert_reading` and `create_oxygen_challenge` now REQUIRE an account id:

```python
    async def insert_reading(self, reading: OwletReading, account_id: int) -> None:
        await self.init()
        if not account_id:
            raise ValueError("account_id is required")
        # ... rest unchanged
```

(same `if not account_id: raise ValueError(...)` guard in `create_oxygen_challenge`, whose signature becomes `account_id: int` — `main.py`'s `create_oxygen_challenge` route currently passes `None` when absent; change the route to reject missing account: covered properly in Task 8, but to keep the app importable now, have the route return HTTP 400 when `account_id` is falsy).

**(c) `user_id` on accounts API.** Update signatures and SQL:

```python
    async def create_account(self, *, email: str, user_id: int | None = None, region: str = "world", ...):
        # INSERT adds user_id column and value
```

```python
    async def list_accounts(self, user_id: int | None = None) -> list[dict[str, Any]]:
        # SELECT adds user_id to the column list;
        # WHERE user_id = ? when user_id is not None
```

```python
    async def get_account(self, account_id: int, user_id: int | None = None) -> dict[str, Any]:
        # WHERE id = ? [AND user_id = ?]; raise KeyError when no row
```

`_row_to_account` gains `"user_id": int(row[...])` if not None (append `user_id` as the last selected column in all three SELECTs and map it).

**(d) `account_ids` filters.** For `_latest_timestamp`, `get_readings`, `get_analysis_readings`, `get_notifications`, `list_devices`, `_oxygen_challenge_rows`, `get_oxygen_challenge_intervals`, `get_summary`, `get_oxygen_challenges`, `exclude_challenge_readings`: add keyword `account_ids: list[int] | None = None` and apply this pattern at the top of each:

```python
        if account_ids is not None and not account_ids:
            return []  # (or the empty-shaped dict for get_notifications/get_oxygen_challenges/get_summary)
```

and in WHERE-building:

```python
        if account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where_parts.append(f"account_id IN ({placeholders})")
            params.extend(account_ids)
```

Keep the existing single `account_id` parameter working (it's used by pollers and the widget): where both are provided, `account_id` wins. For `get_summary` the empty shape is the existing dict with all counts 0 and `_metric_summary([])` values; for `get_notifications`/`get_oxygen_challenges` it is `{"items": [], "total": 0, "limit": limit, "offset": offset}`; for `list_devices` `[]`. In `list_devices` the filter column is `r.account_id`.

**(e) Cascade delete:**

```python
    async def delete_accounts_for_user(self, user_id: int) -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM accounts WHERE user_id = ?", (user_id,))
            ids = [int(row[0]) for row in await cursor.fetchall()]
            if not ids:
                return
            placeholders = ",".join("?" for _ in ids)
            for table in ("readings", "notifications", "oxygen_challenges"):
                await db.execute(f"DELETE FROM {table} WHERE account_id IN ({placeholders})", ids)
            await db.execute(f"DELETE FROM accounts WHERE id IN ({placeholders})", ids)
            await db.commit()
```

**(f) Fix immediate breakage in `app/main.py`** (full tenancy comes in Task 8; this keeps the app running single-user): in the lifespan, `store.default_account_id()` no longer exists — replace the `elif settings.has_owlet_credentials:` block's account resolution with:

```python
                    accounts_list = await store.list_accounts()
                    default_account_id = (
                        int(accounts_list[0]["id"])
                        if accounts_list
                        else int((await store.create_account(email=settings.owlet_email or ""))["id"])
                    )
```

and in `create_owlet_poller` (`app/poller.py`), replace `account_id or await store.default_account_id()` with a required `account_id: int` parameter (its only caller now always passes one). In `main.py`'s `create_oxygen_challenge` route, when the payload has no valid `account_id`, fall back to the first account: `accounts_list = await store.list_accounts()`, 400 if empty.

**(g) Existing tests.** In `tests/test_store.py` and `tests/test_api.py`, any `_seed_reading(..., account_id=None)` path must create an account first. Update the shared helper in each file:

```python
async def _default_account_id(store):
    accounts = await store.list_accounts()
    if accounts:
        return accounts[0]["id"]
    return (await store.create_account(email="seed@example.test"))["id"]
```

and inside `_seed_reading`: `account_id = account_id or await _default_account_id(store)`. Any test asserting on the auto-created "Default account" row should create its account explicitly instead. Run the full suite and mechanically fix remaining `default_account_id()` / seed call sites the same way.

- [ ] **Step 4: Run full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/store.py app/poller.py app/main.py tests/
git commit -m "feat: account ownership (user_id) and account_ids scoping in store"
```

---

### Task 5: Owlet token encryption at rest

**Files:**
- Modify: `app/store.py`, `app/main.py`
- Test: `tests/test_store.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_store.py`:

```python
@pytest.mark.asyncio
async def test_tokens_encrypted_at_rest_and_legacy_rows_migrate(tmp_path):
    import aiosqlite
    from cryptography.fernet import Fernet

    from app.security import TokenCipher

    db_path = tmp_path / "owlet.sqlite3"
    plain_store = ReadingStore(db_path)
    await plain_store.init()
    legacy = await plain_store.create_account(
        email="legacy@x.y", user_id=1, api_token="plain-api", refresh_token="plain-refresh"
    )

    cipher = TokenCipher(Fernet.generate_key().decode())
    store = ReadingStore(db_path, cipher=cipher)
    encrypted_count = await store.encrypt_plaintext_tokens()
    assert encrypted_count == 1

    acc = await store.create_account(
        email="new@x.y", user_id=1, api_token="api-2", refresh_token="refresh-2"
    )
    assert (await store.get_account(acc["id"]))["refresh_token"] == "refresh-2"  # decrypted read
    assert (await store.get_account(legacy["id"]))["api_token"] == "plain-api"

    async with aiosqlite.connect(db_path) as db:  # raw rows must NOT contain plaintext
        rows = await (await db.execute("SELECT api_token, refresh_token FROM accounts")).fetchall()
    flat = [v for row in rows for v in row if v]
    assert flat and all(cipher.is_encrypted(v) for v in flat)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_store.py::test_tokens_encrypted_at_rest_and_legacy_rows_migrate -v`
Expected: FAIL — `__init__() got an unexpected keyword argument 'cipher'`

- [ ] **Step 3: Implement**

In `app/store.py`:

```python
    def __init__(self, db_path: str | Path, cipher: "TokenCipher | None" = None):
        self.db_path = Path(db_path)
        self.cipher = cipher

    def _enc(self, value: str | None) -> str | None:
        return self.cipher.encrypt(value) if self.cipher else value

    def _dec(self, value: str | None) -> str | None:
        return self.cipher.decrypt(value) if self.cipher else value
```

(import `TokenCipher` under `from app.security import TokenCipher` — plain import, quotes unnecessary.) Apply `self._enc(...)` to `api_token` and `refresh_token` values in `create_account` and `update_account_tokens` INSERT/UPDATE params; apply `self._dec(...)` to `"api_token"` and `"refresh_token"` in `_row_to_account`. Add the migration method:

```python
    async def encrypt_plaintext_tokens(self) -> int:
        """One-time startup migration: encrypt any plaintext api/refresh tokens."""
        if not self.cipher:
            return 0
        await self.init()
        changed = 0
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id, api_token, refresh_token FROM accounts")
            for row in await cursor.fetchall():
                api_token, refresh_token = row[1], row[2]
                needs = any(
                    value and not self.cipher.is_encrypted(value)
                    for value in (api_token, refresh_token)
                )
                if not needs:
                    continue
                await db.execute(
                    "UPDATE accounts SET api_token = ?, refresh_token = ? WHERE id = ?",
                    (
                        self.cipher.encrypt(api_token) if api_token else api_token,
                        self.cipher.encrypt(refresh_token) if refresh_token else refresh_token,
                        int(row[0]),
                    ),
                )
                changed += 1
            await db.commit()
        return changed
```

In `app/main.py` `create_app`, construct the cipher and pass it, and run the migration in lifespan:

```python
def create_app(store=None, settings=None, start_poller=True, auth_store=None, emailer=None) -> FastAPI:
    settings = settings or Settings()
    cipher = TokenCipher(settings.token_encryption_key) if settings.token_encryption_key else None
    store = store or ReadingStore(settings.database_path, cipher=cipher)
```

(`auth_store`/`emailer` params are wired fully in Task 7 — for now accept and ignore them.) In lifespan, immediately after `await store.init()`:

```python
        await store.encrypt_plaintext_tokens()
```

- [ ] **Step 4: Run full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/store.py app/main.py tests/test_store.py
git commit -m "feat: encrypt Owlet tokens at rest with startup migration"
```

---

### Task 6: Emailer + rate limiter

**Files:**
- Create: `app/emailer.py`, `app/ratelimit.py`
- Test: `tests/test_auth.py` (new file, first tests)

- [ ] **Step 1: Write the failing test**

Create `tests/test_auth.py`:

```python
import pytest

from app.emailer import Emailer
from app.ratelimit import RateLimiter


@pytest.mark.asyncio
async def test_console_emailer_captures_messages():
    emailer = Emailer(api_key=None, from_address="Owlet <x@y.z>")
    await emailer.send("parent@example.com", "Verify your email", "click: http://x/verify?token=abc")
    assert emailer.sent == [
        {
            "to": "parent@example.com",
            "subject": "Verify your email",
            "text": "click: http://x/verify?token=abc",
        }
    ]


def test_rate_limiter_sliding_window():
    clock = {"now": 0.0}
    limiter = RateLimiter(clock=lambda: clock["now"])
    assert all(limiter.allow("k", max_hits=3, window_seconds=60) for _ in range(3))
    assert limiter.allow("k", max_hits=3, window_seconds=60) is False
    assert limiter.allow("other", max_hits=3, window_seconds=60) is True
    clock["now"] = 61.0
    assert limiter.allow("k", max_hits=3, window_seconds=60) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.emailer'`

- [ ] **Step 3: Implement**

`app/emailer.py`:

```python
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


class Emailer:
    """Sends via Resend when an API key is set; otherwise logs and records (dev/test mode)."""

    def __init__(self, api_key: str | None, from_address: str):
        self.api_key = api_key
        self.from_address = from_address
        self.sent: list[dict[str, str]] = []

    async def send(self, to: str, subject: str, text: str) -> None:
        if not self.api_key:
            logger.info("EMAIL (console mode) to=%s subject=%r\n%s", to, subject, text)
            self.sent.append({"to": to, "subject": subject, "text": text})
            return
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"from": self.from_address, "to": [to], "subject": subject, "text": text},
            )
        response.raise_for_status()
```

`app/ratelimit.py`:

```python
from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable


class RateLimiter:
    """In-memory sliding window. Single-process by design (one container)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, *, max_hits: int, window_seconds: float) -> bool:
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= window_seconds:
            hits.popleft()
        if len(hits) >= max_hits:
            return False
        hits.append(now)
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_auth.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add app/emailer.py app/ratelimit.py tests/test_auth.py
git commit -m "feat: add Resend emailer with console fallback and rate limiter"
```

---

### Task 7: Auth pages, routes, and session gating

This is the largest task: it introduces sessions, replaces the basic-auth middleware, and gates the dashboard. After it, **every existing API route requires a session** (fine-grained tenancy lands in Task 8).

**Files:**
- Create: `app/auth_pages.py`, `app/auth_routes.py`, `tests/conftest.py`
- Modify: `app/main.py`
- Test: `tests/test_auth.py` (append), `tests/test_api.py` (fixture adoption)

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.auth_store import AuthStore
from app.config import Settings
from app.emailer import Emailer
from app.main import create_app
from app.security import hash_password, hash_token, new_token
from app.store import ReadingStore

TEST_FERNET_KEY = Fernet.generate_key().decode()


def test_settings(**kwargs) -> Settings:
    defaults = {
        "secret_key": "test-secret",
        "token_encryption_key": TEST_FERNET_KEY,
        "cookie_secure": False,
        "app_base_url": "http://testserver",
    }
    defaults.update(kwargs)
    return Settings(_env_file=None, **defaults)  # type: ignore[call-arg]


@pytest.fixture
def app_bundle(tmp_path):
    """(app, store, auth_store, emailer, settings) wired against a tmp SQLite file."""
    settings = test_settings()
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    auth_store = AuthStore(tmp_path / "owlet.sqlite3")
    emailer = Emailer(api_key=None, from_address="Owlet <test@example.test>")
    app = create_app(
        store=store, settings=settings, start_poller=False, auth_store=auth_store, emailer=emailer
    )
    return app, store, auth_store, emailer, settings


async def make_user(auth_store: AuthStore, email: str, *, verified: bool = True) -> tuple[dict, str]:
    """Create a user + session directly; returns (user, raw_session_token)."""
    user = await auth_store.create_user(email, hash_password("hunter22"))
    if verified:
        await auth_store.mark_email_verified(user["id"])
    raw = new_token()
    await auth_store.create_session(user["id"], hash_token(raw))
    return await auth_store.get_user(user["id"]), raw


def client_for(app, session_token: str | None = None) -> TestClient:
    client = TestClient(app)
    if session_token:
        client.cookies.set("owlet_session", session_token)
    return client
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_auth.py`:

```python
from tests.conftest import client_for, make_user, test_settings  # noqa: E402


def _extract_link(text: str) -> str:
    return next(word for word in text.split() if word.startswith("http"))


def test_full_signup_verify_login_logout_flow(app_bundle):
    app, _store, _auth, emailer, _settings = app_bundle
    with client_for(app) as client:
        # anonymous dashboard -> login redirect
        landing = client.get("/", follow_redirects=False)
        assert landing.status_code == 303 and landing.headers["location"] == "/login"
        assert client.get("/login").status_code == 200

        response = client.post(
            "/auth/signup", data={"email": "parent@example.com", "password": "hunter22"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert len(emailer.sent) == 1 and "/verify?token=" in emailer.sent[0]["text"]

        # logged in but unverified -> verify gate, APIs blocked
        response = client.post(
            "/auth/login", data={"email": "parent@example.com", "password": "hunter22"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "verify" in client.get("/").text.lower()
        assert client.get("/api/readings").status_code == 403

        verify_link = _extract_link(emailer.sent[0]["text"])
        assert client.get(verify_link, follow_redirects=False).status_code == 303
        assert client.get("/api/readings").status_code == 200

        assert client.post("/auth/logout", follow_redirects=False).status_code == 303
        assert client.get("/api/readings").status_code == 401


def test_bad_login_and_rate_limit(app_bundle):
    app, *_ = app_bundle
    with client_for(app) as client:
        for _ in range(10):
            response = client.post(
                "/auth/login", data={"email": "x@y.z", "password": "wrong"}, follow_redirects=False
            )
            assert response.status_code == 303 and "error" in response.headers["location"]
        response = client.post(
            "/auth/login", data={"email": "x@y.z", "password": "wrong"}, follow_redirects=False
        )
        assert response.status_code == 429


def test_password_reset_flow_invalidates_sessions(app_bundle):
    app, _store, auth, emailer, _settings = app_bundle
    import asyncio

    user, session = asyncio.get_event_loop().run_until_complete(
        make_user(auth, "parent@example.com")
    )
    with client_for(app) as client:
        response = client.post("/auth/forgot", data={"email": "parent@example.com"}, follow_redirects=False)
        assert response.status_code == 303
        link = _extract_link(emailer.sent[-1]["text"])
        token = link.split("token=")[1]
        assert client.get(f"/reset?token={token}").status_code == 200
        response = client.post(
            "/auth/reset", data={"token": token, "password": "new-password-9"}, follow_redirects=False
        )
        assert response.status_code == 303
        # old session is dead
        assert client_for(app, session).get("/api/readings").status_code == 401
        # unknown email: same generic redirect, no email sent
        before = len(emailer.sent)
        client.post("/auth/forgot", data={"email": "ghost@example.com"}, follow_redirects=False)
        assert len(emailer.sent) == before


def test_csrf_origin_mismatch_rejected(app_bundle):
    app, _store, auth, _emailer, _settings = app_bundle
    import asyncio

    _user, session = asyncio.get_event_loop().run_until_complete(make_user(auth, "a@b.c"))
    with client_for(app, session) as client:
        response = client.post("/auth/logout", headers={"origin": "https://evil.example"})
        assert response.status_code == 403
```

Note on async fixtures: `asyncio.get_event_loop().run_until_complete(...)` inside sync tests works because these tests are sync and no loop is running; if the installed pytest-asyncio version complains, switch those tests to `async def` with `@pytest.mark.asyncio` and call `await make_user(...)` directly, using `client_for(...)` unchanged.

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_auth.py -v`
Expected: new tests FAIL (no `/auth/signup` route, no redirect on `/`)

- [ ] **Step 4: Implement `app/auth_pages.py`**

```python
from __future__ import annotations

import html

_BASE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} · Owlet Dashboard</title>
  <link rel="icon" href="/favicon.ico" sizes="any" />
  <style>
    :root {{ --bg:#f5f7fb; --panel:#fff; --text:#122033; --muted:#5b6b80; --purple:#6d28d9; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
           background:var(--bg); color:var(--text); display:flex; min-height:100vh;
           align-items:center; justify-content:center; padding:24px; }}
    .card {{ background:var(--panel); border-radius:16px; box-shadow:0 8px 30px rgba(18,32,51,.08);
            padding:32px; width:100%; max-width:420px; }}
    h1 {{ margin:0 0 4px; font-size:24px; }}
    p.sub {{ margin:0 0 20px; color:var(--muted); font-size:14px; }}
    label {{ display:block; font-size:13px; font-weight:600; margin:14px 0 4px; }}
    input, select {{ width:100%; padding:10px 12px; border:1px solid #d6dee9; border-radius:10px; font-size:15px; }}
    button {{ margin-top:18px; width:100%; padding:11px; border:0; border-radius:10px;
             background:var(--purple); color:#fff; font-size:15px; font-weight:600; cursor:pointer; }}
    .links {{ margin-top:16px; font-size:13px; color:var(--muted); display:flex; justify-content:space-between; }}
    .links a {{ color:var(--purple); text-decoration:none; }}
    .notice {{ background:#eef2ff; border-radius:10px; padding:10px 12px; font-size:13px; margin-bottom:8px; }}
    .error {{ background:#fef2f2; color:#991b1b; }}
    footer {{ margin-top:20px; font-size:11px; color:var(--muted); text-align:center; }}
    footer a {{ color:var(--muted); }}
  </style>
</head>
<body>
  <div class="card">
    {body}
    <footer>Retrospective trend viewing only — not a medical monitor or alert replacement.<br/>
      <a href="/terms">Terms</a> · <a href="/privacy">Privacy</a></footer>
  </div>
</body>
</html>"""


def _page(title: str, body: str) -> str:
    return _BASE.format(title=html.escape(title), body=body)


def _notice(message: str | None, error: str | None) -> str:
    parts = []
    if message:
        parts.append(f'<div class="notice">{html.escape(message)}</div>')
    if error:
        parts.append(f'<div class="notice error">{html.escape(error)}</div>')
    return "".join(parts)


def login_page(message: str | None = None, error: str | None = None) -> str:
    return _page(
        "Sign in",
        f"""<h1>Owlet Dashboard</h1>
    <p class="sub">Private history for your Owlet sock data.</p>
    {_notice(message, error)}
    <form method="post" action="/auth/login">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required autocomplete="email" />
      <label for="password">Password</label>
      <input id="password" name="password" type="password" required autocomplete="current-password" />
      <button type="submit">Sign in</button>
    </form>
    <div class="links"><a href="/signup">Create an account</a><a href="/forgot">Forgot password?</a></div>""",
    )


def signup_page(error: str | None = None) -> str:
    return _page(
        "Create account",
        f"""<h1>Create your account</h1>
    <p class="sub">Then link your Owlet sock to start collecting history.</p>
    {_notice(None, error)}
    <form method="post" action="/auth/signup">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required autocomplete="email" />
      <label for="password">Password (8+ characters)</label>
      <input id="password" name="password" type="password" required minlength="8" maxlength="128"
             autocomplete="new-password" />
      <button type="submit">Create account</button>
    </form>
    <div class="links"><a href="/login">Back to sign in</a></div>""",
    )


def forgot_page() -> str:
    return _page(
        "Reset password",
        """<h1>Reset your password</h1>
    <p class="sub">We'll email you a reset link if this address has an account.</p>
    <form method="post" action="/auth/forgot">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required autocomplete="email" />
      <button type="submit">Email me a reset link</button>
    </form>
    <div class="links"><a href="/login">Back to sign in</a></div>""",
    )


def reset_page(token: str, error: str | None = None) -> str:
    return _page(
        "Choose a new password",
        f"""<h1>Choose a new password</h1>
    {_notice(None, error)}
    <form method="post" action="/auth/reset">
      <input type="hidden" name="token" value="{html.escape(token)}" />
      <label for="password">New password (8+ characters)</label>
      <input id="password" name="password" type="password" required minlength="8" maxlength="128"
             autocomplete="new-password" />
      <button type="submit">Set password</button>
    </form>""",
    )


def verify_gate_page(email: str) -> str:
    return _page(
        "Verify your email",
        f"""<h1>Check your inbox</h1>
    <p class="sub">We sent a verification link to <strong>{html.escape(email)}</strong>.
    Click it to unlock your dashboard.</p>
    <form method="post" action="/auth/resend-verification"><button type="submit">Resend email</button></form>
    <form method="post" action="/auth/logout"><button type="submit"
      style="background:#e2e8f0;color:#122033">Sign out</button></form>""",
    )


def onboarding_page(error: str | None = None) -> str:
    return _page(
        "Link your Owlet sock",
        f"""<h1>Link your Owlet sock</h1>
    <p class="sub">Enter the login you use in the Owlet app. We verify it with Owlet once and
    <strong>never store your Owlet password</strong> — only a revocable access token.</p>
    {_notice(None, error)}
    <form method="post" action="/onboarding/link">
      <label for="owlet_email">Owlet account email</label>
      <input id="owlet_email" name="email" type="email" required />
      <label for="owlet_password">Owlet account password</label>
      <input id="owlet_password" name="password" type="password" required autocomplete="off" />
      <label for="region">Region</label>
      <select id="region" name="region">
        <option value="world" selected>World (US and most countries)</option>
        <option value="europe">Europe</option>
      </select>
      <button type="submit">Link sock and start collecting</button>
    </form>
    <div class="links"><span></span><form method="post" action="/auth/logout" style="margin:0">
      <button type="submit" style="background:none;color:#5b6b80;margin:0;padding:0;width:auto;font-size:13px">
        Sign out</button></form></div>""",
    )
```

(`settings_page`, `terms_page`, `privacy_page` are added in Tasks 9 and 12.)

- [ ] **Step 5: Implement `app/auth_routes.py`**

```python
from __future__ import annotations

import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app import auth_pages
from app.security import hash_password, hash_token, new_token, verify_password

logger = logging.getLogger(__name__)
router = APIRouter()

SESSION_COOKIE = "owlet_session"
MIN_PASSWORD, MAX_PASSWORD = 8, 128


# -- helpers -------------------------------------------------------------------

def _auth(request: Request):
    return request.app.state.auth_store


def _emailer(request: Request):
    return request.app.state.emailer


def _settings(request: Request):
    return request.app.state.settings


def _limiter(request: Request):
    return request.app.state.rate_limiter


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def set_session_cookie(response: Response, request: Request, raw_token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        httponly=True,
        samesite="lax",
        secure=_settings(request).cookie_secure,
        max_age=30 * 24 * 3600,
        path="/",
    )


async def current_user(request: Request) -> dict | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    return await _auth(request).get_session_user(hash_token(raw))


async def require_verified_user(request: Request) -> dict:
    user = await current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    if not user["email_verified_at"]:
        raise HTTPException(status_code=403, detail="Email verification required")
    return user


async def send_verification_email(request: Request, user: dict) -> None:
    raw = new_token()
    await _auth(request).create_auth_token(user["id"], hash_token(raw), purpose="verify")
    base = _settings(request).app_base_url.rstrip("/")
    await _emailer(request).send(
        user["email"],
        "Verify your Owlet Dashboard email",
        f"Welcome! Confirm your email to unlock your dashboard:\n\n{base}/verify?token={raw}\n\n"
        "This link expires in 15 minutes.",
    )


def same_origin(request: Request, base_url: str) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True  # non-browser clients; SameSite=Lax cookies are the primary defense
    parsed, base = urlparse(origin), urlparse(base_url)
    if (parsed.scheme, parsed.netloc) == (base.scheme, base.netloc):
        return True
    return parsed.netloc == request.headers.get("host", "")


# -- pages ---------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, message: str | None = None, error: str | None = None):
    if await current_user(request):
        return RedirectResponse("/", status_code=303)
    return auth_pages.login_page(message=message, error=error)


@router.get("/signup", response_class=HTMLResponse)
async def signup_form(error: str | None = None):
    return auth_pages.signup_page(error=error)


@router.get("/forgot", response_class=HTMLResponse)
async def forgot_form():
    return auth_pages.forgot_page()


@router.get("/reset", response_class=HTMLResponse)
async def reset_form(token: str = Query(min_length=20)):
    return auth_pages.reset_page(token)


# -- actions -------------------------------------------------------------------

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
    await send_verification_email(request, user)
    raw = new_token()
    await _auth(request).create_session(
        user["id"], hash_token(raw), user_agent=request.headers.get("user-agent", "")
    )
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, request, raw)
    return response


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
    raw = new_token()
    await _auth(request).create_session(
        user["id"], hash_token(raw), user_agent=request.headers.get("user-agent", "")
    )
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, request, raw)
    return response


@router.post("/auth/logout")
async def logout(request: Request):
    raw = request.cookies.get(SESSION_COOKIE)
    if raw:
        await _auth(request).delete_session(hash_token(raw))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.post("/auth/resend-verification")
async def resend_verification(request: Request):
    user = await current_user(request)
    if user and not user["email_verified_at"]:
        if not _limiter(request).allow(f"verify:{user['id']}", max_hits=3, window_seconds=900):
            raise HTTPException(status_code=429, detail="Too many emails; wait 15 minutes")
        await send_verification_email(request, user)
    return RedirectResponse("/", status_code=303)


@router.get("/verify")
async def verify_email(request: Request, token: str = Query(min_length=20)):
    user_id = await _auth(request).consume_auth_token(hash_token(token), purpose="verify")
    if user_id is None:
        return RedirectResponse("/login?error=That+link+is+expired+or+used", status_code=303)
    await _auth(request).mark_email_verified(user_id)
    return RedirectResponse("/", status_code=303)


@router.post("/auth/forgot")
async def forgot(request: Request, email: str = Form()):
    normalized = email.strip().lower()
    if _limiter(request).allow(f"forgot:{normalized}", max_hits=3, window_seconds=900):
        user = await _auth(request).get_user_by_email(normalized)
        if user:
            raw = new_token()
            await _auth(request).create_auth_token(user["id"], hash_token(raw), purpose="password_reset")
            base = _settings(request).app_base_url.rstrip("/")
            await _emailer(request).send(
                user["email"],
                "Reset your Owlet Dashboard password",
                f"Someone asked to reset your password. If that was you:\n\n{base}/reset?token={raw}\n\n"
                "This link expires in 15 minutes. Otherwise you can ignore this email.",
            )
    return RedirectResponse("/login?message=If+that+account+exists,+a+reset+link+is+on+its+way", status_code=303)


@router.post("/auth/reset")
async def reset(request: Request, token: str = Form(), password: str = Form()):
    if not (MIN_PASSWORD <= len(password) <= MAX_PASSWORD):
        return RedirectResponse(f"/reset?token={token}", status_code=303)
    user_id = await _auth(request).consume_auth_token(hash_token(token), purpose="password_reset")
    if user_id is None:
        return RedirectResponse("/login?error=That+link+is+expired+or+used", status_code=303)
    await _auth(request).set_password(user_id, hash_password(password))
    await _auth(request).delete_user_sessions(user_id)
    return RedirectResponse("/login?message=Password+updated.+Sign+in+with+your+new+password", status_code=303)
```

- [ ] **Step 6: Wire into `app/main.py`**

In `create_app` (building on Task 5's signature):

```python
def create_app(store=None, settings=None, start_poller=True, auth_store=None, emailer=None) -> FastAPI:
    settings = settings or Settings()
    cipher = TokenCipher(settings.token_encryption_key) if settings.token_encryption_key else None
    store = store or ReadingStore(settings.database_path, cipher=cipher)
    auth_store = auth_store or AuthStore(settings.database_path)
    emailer = emailer or Emailer(api_key=settings.resend_api_key, from_address=settings.email_from)
```

Add imports: `from app.auth_store import AuthStore`, `from app.emailer import Emailer`, `from app.ratelimit import RateLimiter`, `from app.security import TokenCipher`, `from app import auth_pages`, `from app.auth_routes import SESSION_COOKIE, current_user, require_verified_user, router as auth_router, same_origin` and `from fastapi import Depends`.

After `app = FastAPI(...)` set state and include the router:

```python
    app.state.settings = settings
    app.state.auth_store = auth_store
    app.state.emailer = emailer
    app.state.rate_limiter = RateLimiter()
    app.include_router(auth_router)
```

In lifespan, first lines become:

```python
        await store.init()
        await auth_store.init()
        await store.encrypt_plaintext_tokens()
        if start_poller and not settings.auth_ready:
            logger.warning(
                "SECRET_KEY / TOKEN_ENCRYPTION_KEY missing - set them before exposing this app publicly"
            )
```

**Replace the `require_basic_auth` middleware entirely** with a CSRF-origin middleware (share-token handling moves to Task 9; until then keep the share branch delegating to the old env check so share tests keep passing):

```python
    @app.middleware("http")
    async def csrf_and_share_guard(request: Request, call_next):
        if request.url.path.startswith("/share/"):
            if _share_path_is_authorized(request.url.path, settings.owlet_share_token):
                return await call_next(request)
            return Response(status_code=404)
        if request.method in {"POST", "PATCH", "PUT", "DELETE"} and not same_origin(
            request, settings.app_base_url
        ):
            return Response(status_code=403)
        return await call_next(request)
```

Delete `_parse_basic_auth` and `_basic_auth_cookie_value` and the `hashlib` import if now unused.

**Gate the dashboard route:**

```python
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> Response:
        user = await current_user(request)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        if not user["email_verified_at"]:
            return HTMLResponse(auth_pages.verify_gate_page(user["email"]))
        accounts = await store.list_accounts(user_id=user["id"])
        if not accounts:
            return HTMLResponse(auth_pages.onboarding_page())
        return HTMLResponse(render_dashboard())
```

**Gate every `/api/*` route** by adding a dependency parameter. For THIS task, add to each existing data endpoint (`accounts`, `update_account`, `create_account`, `devices`, `readings`, `summary`, `insights`, `rollups`, `crypto`, `notifications`, `oxygen_challenges` CRUD, `widget`, `health` stays public):

```python
        user: dict = Depends(require_verified_user),
```

(Tenancy filtering with the user's account ids is Task 8; here the dependency only requires a verified session. `/api/health` remains unauthenticated.)

**Onboarding link endpoint** (form-post version of the JSON link flow):

```python
    @app.post("/onboarding/link")
    async def onboarding_link(
        request: Request,
        email: str = Form(),
        password: str = Form(),
        region: str = Form(default="world"),
        user: dict = Depends(require_verified_user),
    ):
        payload = {"email": email, "password": password, "region": region}
        try:
            await _link_owlet_account(payload, user)
        except HTTPException:
            return HTMLResponse(
                auth_pages.onboarding_page(error="Owlet rejected that login - check email/password/region"),
                status_code=400,
            )
        return RedirectResponse("/", status_code=303)
```

Refactor the body of the existing `create_account` route into an internal `async def _link_owlet_account(payload: dict, user: dict) -> dict` that both the JSON route and this form route call; the JSON route keeps its signature plus the `user` dependency. `store.create_account(...)` inside it gains `user_id=user["id"]`, and it is rate-limited: at the top of `_link_owlet_account` (pass `request` in, or perform the limit check in both callers):

```python
        if not app.state.rate_limiter.allow(f"owlet-link:{user['id']}", max_hits=5, window_seconds=3600):
            raise HTTPException(status_code=429, detail="Too many link attempts; try again later")
```

`Form` import comes from fastapi.

- [ ] **Step 7: Adapt existing `tests/test_api.py`**

Replace its private `_test_settings` with `from tests.conftest import client_for, make_user, test_settings as _test_settings`, and for each test that calls endpoints: build the app with `auth_store=AuthStore(db_path)` (same tmp db path), create a verified user + session via `make_user`, pass `user_id=user["id"]` when the test creates accounts, and use `client_for(app, session)` instead of `TestClient(app)`. Example rewrite of the first test's setup:

```python
@pytest.mark.asyncio
async def test_account_api_is_public_metadata_only_and_scopes_data(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    auth = AuthStore(db_path)
    user, session = await make_user(auth, "owner@example.test")
    first = await store.create_account(email="first@example.test", user_id=user["id"])
    second = await store.create_account(
        email="second@example.test", region="world", display_name="Second baby",
        api_token="secret-api-token", api_token_expiry=12345,
        refresh_token="secret-refresh-token", user_id=user["id"],
    )
    ...
    app = create_app(store=store, settings=_test_settings(), start_poller=False, auth_store=auth)
    with client_for(app, session) as client:
        ...
```

Apply the same mechanical pattern to every test in the file (the seeded "first account" comes from an explicit `create_account` now — `(await store.list_accounts())[0]` no longer returns an auto-created row).

- [ ] **Step 8: Run full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add app/ tests/
git commit -m "feat: email+password auth, sessions, login/onboarding pages, gated routes"
```

---

### Task 8: Tenancy enforcement on every data endpoint

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_tenancy.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tenancy.py`:

```python
import pytest

from app.auth_store import AuthStore
from app.main import create_app
from app.models import normalize_reading
from app.store import ReadingStore
from tests.conftest import client_for, make_user, test_settings


@pytest.fixture
async def two_tenants(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    auth = AuthStore(db_path)
    alice, alice_session = await make_user(auth, "alice@example.test")
    bob, bob_session = await make_user(auth, "bob@example.test")
    alice_acc = await store.create_account(email="alice-sock@x.y", user_id=alice["id"])
    bob_acc = await store.create_account(email="bob-sock@x.y", user_id=bob["id"])
    for acc, hr in ((alice_acc, 110), (bob_acc, 155)):
        await store.insert_reading(
            normalize_reading(
                {"heart_rate": hr, "oxygen_saturation": 95, "last_updated": "2026-07-02T01:00:00Z"},
                f"SOCK{acc['id']}",
            ),
            account_id=acc["id"],
        )
    challenge = await store.create_oxygen_challenge(
        "2026-07-02T00:00:00Z", end_time="2026-07-02T00:30:00Z", account_id=bob_acc["id"]
    )
    app = create_app(store=store, settings=test_settings(), start_poller=False, auth_store=auth)
    return app, alice_session, bob_session, alice_acc, bob_acc, challenge


@pytest.mark.asyncio
async def test_data_endpoints_are_scoped_to_session_user(two_tenants):
    app, alice_session, _bob_session, alice_acc, bob_acc, _challenge = two_tenants
    with client_for(app, alice_session) as client:
        accounts = client.get("/api/accounts").json()["accounts"]
        assert [a["id"] for a in accounts] == [alice_acc["id"]]
        readings = client.get("/api/readings").json()
        assert {r["heart_rate"] for r in readings} == {110}
        devices = client.get("/api/devices").json()["devices"]
        assert {d["account_id"] for d in devices} == {alice_acc["id"]}
        assert client.get("/api/summary").json()["count"] == 1
        assert client.get(f"/api/readings?account={bob_acc['id']}").status_code == 404
        assert client.get(f"/api/devices?account={bob_acc['id']}").status_code == 404
        assert client.get(f"/api/summary?account={bob_acc['id']}").status_code == 404
        assert client.get(f"/api/insights?account={bob_acc['id']}").status_code == 404
        assert client.get(f"/api/rollups?account={bob_acc['id']}").status_code == 404
        assert client.get(f"/api/notifications?account={bob_acc['id']}").status_code == 404
        assert client.get(f"/api/oxygen-challenges?account={bob_acc['id']}").status_code == 404
        assert client.get(f"/api/widget?account={bob_acc['id']}").status_code == 404


@pytest.mark.asyncio
async def test_mutations_on_foreign_resources_return_404(two_tenants):
    app, alice_session, _bob_session, _alice_acc, bob_acc, challenge = two_tenants
    with client_for(app, alice_session) as client:
        assert client.patch(f"/api/accounts/{bob_acc['id']}", json={"display_name": "hi"}).status_code == 404
        assert client.get(f"/api/oxygen-challenges/{challenge['id']}").status_code == 404
        assert client.patch(f"/api/oxygen-challenges/{challenge['id']}", json={"label": "x"}).status_code == 404
        assert client.delete(f"/api/oxygen-challenges/{challenge['id']}").status_code == 404
        created = client.post(
            "/api/oxygen-challenges",
            json={"start_time": "2026-07-02T02:00:00Z", "account_id": bob_acc["id"]},
        )
        assert created.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_tenancy.py -v`
Expected: FAIL (cross-tenant requests currently return 200)

- [ ] **Step 3: Implement in `app/main.py`**

Add a scoping helper inside `create_app`:

```python
    async def _scope(user: dict, account: int | None) -> list[int]:
        owned = [int(a["id"]) for a in await store.list_accounts(user_id=user["id"])]
        if account is None:
            return owned
        if account not in owned:
            raise HTTPException(status_code=404, detail="Not found")
        return [account]
```

Then update every data endpoint to resolve scope and pass `account_ids`:

- `accounts`: `return {"accounts": [_public_account(a) for a in await store.list_accounts(user_id=user["id"])]}`
- `update_account`: before updating, `await _scope(user, account_id)` (raises 404 for foreign ids; `get_account(account_id, user_id=user["id"])` inside store also enforces — use the store form: wrap `store.update_account_preferences` call with a preceding `await store.get_account(account_id, user_id=user["id"])` in the `try` so `KeyError` → 404).
- `devices`: `ids = await _scope(user, account); return {"devices": await store.list_devices(account_ids=ids)}` (drop the raw `account_id=` pass-through).
- `readings`: `ids = await _scope(user, account)` then pass `account_ids=ids` to `get_readings`/`get_analysis_readings` (remove `account_id=account`).
- `summary`, `insights`, `rollups`, `notifications`, `oxygen_challenges` (list): same pattern — `account_ids=ids`; for `exclude_challenge_readings` pass `account_ids=ids` too.
- `widget`: `_widget_payload(store, hours=hours, device=device, account_ids=await _scope(user, account))` — change `_widget_payload`'s `account_id` parameter to `account_ids: list[int] | None` and thread it into its store calls.
- `create_oxygen_challenge` (POST): resolve target account: if payload has `account_id`, `ids = await _scope(user, int(account_id))`; else `ids = await _scope(user, None)` and 400 if empty; use `ids[0]`.
- `oxygen_challenge` GET/PATCH/DELETE by id: extend the store instead of post-hoc checks. `store._get_oxygen_challenge_row` and `store.get_oxygen_challenge` gain `account_ids: list[int] | None = None`, adding `AND account_id IN (...)` to the row query (empty list → no row → `KeyError`). Routes compute `ids = await _scope(user, None)` and call `store.get_oxygen_challenge(challenge_id, account_ids=ids)` — `KeyError` already maps to 404. PATCH first calls `get_oxygen_challenge(challenge_id, account_ids=ids)` for the ownership check, then `update_oxygen_challenge`. DELETE: `delete_oxygen_challenge` gains `account_ids` and deletes with `WHERE id = ? AND account_id IN (...)`; the route treats 0 rows deleted as 404 (have the store method return the rowcount).
- `create_account` (JSON link route): already attaches `user_id` (Task 7); nothing more.

- [ ] **Step 4: Run full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS (tenancy + all prior suites)

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_tenancy.py
git commit -m "feat: enforce per-user tenancy with 404 semantics on all data endpoints"
```

---

### Task 9: Settings page, per-user share tokens, account deletion

**Files:**
- Create: `app/settings_routes.py`
- Modify: `app/auth_pages.py`, `app/main.py`, `app/dashboard.py`
- Test: `tests/test_auth.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_auth.py`:

```python
def test_settings_share_token_lifecycle_and_share_routes(app_bundle):
    app, store, auth, _emailer, _settings = app_bundle
    import asyncio

    loop = asyncio.get_event_loop()
    user, session = loop.run_until_complete(make_user(auth, "parent@example.com"))
    acc = loop.run_until_complete(store.create_account(email="sock@x.y", user_id=user["id"]))
    from app.models import normalize_reading

    loop.run_until_complete(
        store.insert_reading(
            normalize_reading(
                {"heart_rate": 120, "oxygen_saturation": 96, "last_updated": "2026-07-02T01:00:00Z"}, "S1"
            ),
            account_id=acc["id"],
        )
    )
    with client_for(app, session) as client:
        assert client.get("/settings").status_code == 200
        page = client.post("/settings/share", data={"action": "enable"})
        assert page.status_code == 200 and "/share/" in page.text
        share_url = page.text.split('data-share-path="')[1].split('"')[0]
        assert client.post("/settings/share", data={"action": "disable"}).status_code == 200

    with client_for(app) as anon:  # disabled token -> 404
        assert anon.get(share_url).status_code == 404

    with client_for(app, session) as client:
        page = client.post("/settings/share", data={"action": "enable"})
        share_url = page.text.split('data-share-path="')[1].split('"')[0]
    with client_for(app) as anon:
        assert anon.get(share_url).status_code == 200
        readings = anon.get(f"{share_url}/api/readings").json()
        assert readings and readings[0]["heart_rate"] == 120
        assert anon.get("/share/not-a-real-token-aaaaaaaaaaaa/api/readings").status_code == 404


def test_change_password_logout_all_and_delete_account(app_bundle):
    app, store, auth, _emailer, _settings = app_bundle
    import asyncio

    loop = asyncio.get_event_loop()
    user, session = loop.run_until_complete(make_user(auth, "parent@example.com"))
    loop.run_until_complete(store.create_account(email="sock@x.y", user_id=user["id"]))
    with client_for(app, session) as client:
        bad = client.post(
            "/settings/password",
            data={"current_password": "wrong", "new_password": "brand-new-pw"},
            follow_redirects=False,
        )
        assert bad.status_code == 303 and "error" in bad.headers["location"]
        good = client.post(
            "/settings/password",
            data={"current_password": "hunter22", "new_password": "brand-new-pw"},
            follow_redirects=False,
        )
        assert good.status_code == 303
        assert client.post("/settings/logout-all", follow_redirects=False).status_code == 303
    assert client_for(app, session).get("/api/readings").status_code == 401

    user2, session2 = loop.run_until_complete(make_user(auth, "second@example.com"))
    loop.run_until_complete(store.create_account(email="sock2@x.y", user_id=user2["id"]))
    with client_for(app, session2) as client:
        gone = client.post("/settings/delete-account", data={"confirm": "DELETE"}, follow_redirects=False)
        assert gone.status_code == 303
    assert loop.run_until_complete(auth.get_user(user2["id"])) is None
    assert loop.run_until_complete(store.list_accounts(user_id=user2["id"])) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_auth.py -v`
Expected: new tests FAIL — 404 on `/settings`

- [ ] **Step 3: Add `settings_page` to `app/auth_pages.py`**

```python
def settings_page(
    email: str,
    share_path: str | None,
    message: str | None = None,
    error: str | None = None,
) -> str:
    if share_path:
        share_section = f"""<div class="notice" data-share-path="{html.escape(share_path)}">
        Read-only share link is <strong>on</strong>: <code>{html.escape(share_path)}</code><br/>
        Anyone with this URL can view (not edit) your dashboard data.</div>
      <form method="post" action="/settings/share"><input type="hidden" name="action" value="disable"/>
        <button type="submit" style="background:#e2e8f0;color:#122033">Disable share link</button></form>"""
    else:
        share_section = """<p class="sub">Share links are off.</p>
      <form method="post" action="/settings/share"><input type="hidden" name="action" value="enable"/>
        <button type="submit">Create read-only share link</button></form>"""
    return _page(
        "Settings",
        f"""<h1>Settings</h1>
    <p class="sub">Signed in as <strong>{html.escape(email)}</strong> · <a href="/">back to dashboard</a></p>
    {_notice(message, error)}
    <h2 style="font-size:16px">Change password</h2>
    <form method="post" action="/settings/password">
      <label>Current password</label><input name="current_password" type="password" required />
      <label>New password (8+ characters)</label>
      <input name="new_password" type="password" required minlength="8" maxlength="128" />
      <button type="submit">Change password</button>
    </form>
    <h2 style="font-size:16px;margin-top:24px">Share link</h2>
    {share_section}
    <h2 style="font-size:16px;margin-top:24px">Sessions</h2>
    <form method="post" action="/settings/logout-all">
      <button type="submit" style="background:#e2e8f0;color:#122033">Log out everywhere</button></form>
    <h2 style="font-size:16px;margin-top:24px;color:#991b1b">Danger zone</h2>
    <p class="sub">Deletes your login, linked Owlet accounts, and every stored reading. Immediate and permanent.</p>
    <form method="post" action="/settings/delete-account"
          onsubmit="return this.confirm.value==='DELETE'">
      <label>Type DELETE to confirm</label><input name="confirm" autocomplete="off" />
      <button type="submit" style="background:#b91c1c">Delete my account and all data</button>
    </form>""",
    )
```

- [ ] **Step 4: Implement `app/settings_routes.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import auth_pages
from app.auth_routes import SESSION_COOKIE, require_verified_user
from app.security import hash_password, hash_token, new_token, verify_password

router = APIRouter()

# Raw share tokens are only known at creation time; keep the active path per user id
# so the settings page can re-display it within this process lifetime.
_share_paths: dict[int, str] = {}


def _auth(request: Request):
    return request.app.state.auth_store


def _store(request: Request):
    return request.app.state.owlet_state["store"]


@router.get("/settings", response_class=HTMLResponse)
async def settings_home(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    user: dict = Depends(require_verified_user),
):
    share_path = _share_paths.get(user["id"]) if user["share_token_hash"] else None
    if user["share_token_hash"] and not share_path:
        share_path = "/share/(created earlier - disable and re-enable to see the URL again)"
    return auth_pages.settings_page(user["email"], share_path, message=message, error=error)


@router.post("/settings/password")
async def change_password(
    request: Request,
    current_password: str = Form(),
    new_password: str = Form(),
    user: dict = Depends(require_verified_user),
):
    if not verify_password(user["password_hash"], current_password):
        return RedirectResponse("/settings?error=Current+password+is+wrong", status_code=303)
    if not (8 <= len(new_password) <= 128):
        return RedirectResponse("/settings?error=New+password+must+be+8-128+characters", status_code=303)
    await _auth(request).set_password(user["id"], hash_password(new_password))
    return RedirectResponse("/settings?message=Password+updated", status_code=303)


@router.post("/settings/share", response_class=HTMLResponse)
async def toggle_share(
    request: Request, action: str = Form(), user: dict = Depends(require_verified_user)
):
    if action == "enable":
        raw = new_token()
        await _auth(request).set_share_token(user["id"], hash_token(raw))
        _share_paths[user["id"]] = f"/share/{raw}"
        return auth_pages.settings_page(
            user["email"], f"/share/{raw}", message="Share link created - copy it now"
        )
    await _auth(request).set_share_token(user["id"], None)
    _share_paths.pop(user["id"], None)
    return auth_pages.settings_page(user["email"], None, message="Share link disabled")


@router.post("/settings/logout-all")
async def logout_all(request: Request, user: dict = Depends(require_verified_user)):
    await _auth(request).delete_user_sessions(user["id"])
    response = RedirectResponse("/login?message=Signed+out+everywhere", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.post("/settings/delete-account")
async def delete_account(
    request: Request, confirm: str = Form(default=""), user: dict = Depends(require_verified_user)
):
    if confirm != "DELETE":
        return RedirectResponse("/settings?error=Type+DELETE+to+confirm", status_code=303)
    await _store(request).delete_accounts_for_user(user["id"])
    await _auth(request).delete_user(user["id"])
    response = RedirectResponse("/login?message=Account+deleted", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
```

- [ ] **Step 5: Share routes resolve per-user tokens (`app/main.py`)**

Include the router: `app.include_router(settings_router)` (`from app.settings_routes import router as settings_router`).

Replace the middleware share branch:

```python
        if request.url.path.startswith("/share/"):
            candidate = request.url.path.removeprefix("/share/").split("/", 1)[0]
            share_user = (
                await auth_store.get_user_by_share_token(hash_token(candidate)) if candidate else None
            )
            if share_user is None:
                return Response(status_code=404)
            request.state.share_user = share_user
            return await call_next(request)
```

(`from app.security import hash_token` already available via imports added earlier — add if missing.)

Every `/share/{token}` endpoint: delete the `_require_share_token(token, settings)` calls and instead scope by the resolved user:

```python
        share_user = request.state.share_user
        ids = [int(a["id"]) for a in await store.list_accounts(user_id=share_user["id"])]
```

then pass `account_ids=ids` to the store calls (add `request: Request` to each shared route's signature). Delete `_require_share_token` and `_share_path_is_authorized`. `shared_dashboard` and `shared_health` keep their responses, scoped the same way (`shared_health` needs no ids).

- [ ] **Step 6: Dashboard links (`app/dashboard.py`)**

In the profile-menu JS near `el('addAccount')?.addEventListener('click', addAccountFromPrompt);` (line ~3131), add on the following line:

```javascript
    (function injectAccountMenuLinks() {
      const wrap = el('profileMenuWrap');
      const menu = wrap ? wrap.querySelector('.profile-menu, [class*="menu"]') : null;
      const host = menu || wrap;
      if (!host || SHARE_MODE) return;
      const nav = document.createElement('div');
      nav.style.cssText = 'display:flex;gap:10px;padding:8px 12px;font-size:12px';
      nav.innerHTML = '<a href="/settings">Settings</a>'
        + '<form method="post" action="/auth/logout" style="margin:0">'
        + '<button type="submit" style="all:unset;cursor:pointer;color:inherit;text-decoration:underline">Sign out</button></form>';
      host.appendChild(nav);
    })();
```

(If `profileMenuWrap` markup differs, append to whatever container `el('profileMenuWrap')` returns — the JS guards nulls either way.)

- [ ] **Step 7: Run full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add app/ tests/
git commit -m "feat: settings page, per-user share links, self-serve account deletion"
```

---

### Task 10: Adaptive poller with jitter, backoff, and heartbeat

**Files:**
- Modify: `app/poller.py`, `app/store.py`, `app/main.py`, `app/dashboard.py`
- Test: `tests/test_poller.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_poller.py`:

```python
import pytest

from app.models import OwletReading
from app.poller import Poller
from app.store import ReadingStore


class FakeSleeper:
    def __init__(self, stop_event, max_sleeps):
        self.delays: list[float] = []
        self._stop_event = stop_event
        self._max = max_sleeps

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)
        if len(self.delays) >= self._max:
            self._stop_event.set()


def _reading(*, offline: bool) -> OwletReading:
    return OwletReading(
        device_serial="S1",
        heart_rate=0 if offline else 120,
        oxygen_saturation=0 if offline else 96,
        sock_off=offline,
    )


@pytest.mark.asyncio
async def test_adaptive_interval_backoff_and_heartbeat(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    account = await store.create_account(email="a@x.y", user_id=1)

    sequence = [_reading(offline=False), _reading(offline=True), RuntimeError("owlet down"),
                RuntimeError("owlet down"), _reading(offline=False)]

    async def read_once():
        item = sequence.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    poller = Poller(
        store=store,
        read_once=read_once,
        interval_seconds=30,
        idle_interval_seconds=300,
        account_id=account["id"],
        jitter_seconds=0.0,
    )
    sleeper = FakeSleeper(poller._stop, max_sleeps=5)
    poller._sleep = sleeper
    await poller._run()

    # initial jitter sleep of 0, then: online 30, offline 300, error 60, error 120, online 30
    assert sleeper.delays[0] == 0.0
    assert sleeper.delays[1:] == [30, 300, 60, 120]
    assert await store.get_metadata("poller_heartbeat_at") is not None


@pytest.mark.asyncio
async def test_persistent_failures_mark_needs_reauth_and_stop(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    account = await store.create_account(email="a@x.y", user_id=1)

    async def always_fails():
        raise RuntimeError("invalid token")

    poller = Poller(
        store=store,
        read_once=always_fails,
        interval_seconds=30,
        account_id=account["id"],
        jitter_seconds=0.0,
        max_consecutive_failures=3,
    )
    sleeper = FakeSleeper(poller._stop, max_sleeps=50)  # loop must stop itself first
    poller._sleep = sleeper
    await poller._run()

    assert len(sleeper.delays) < 50  # stopped by failure threshold, not the sleeper
    assert (await store.get_account(account["id"]))["status"] == "needs_reauth"


@pytest.mark.asyncio
async def test_metadata_helpers(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    assert await store.get_metadata("missing") is None
    await store.set_metadata("k", "v")
    assert await store.get_metadata("k") == "v"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_poller.py -v`
Expected: FAIL — unexpected kwargs / missing `get_metadata`

- [ ] **Step 3: Implement**

`app/store.py` — metadata helpers:

```python
    async def set_metadata(self, key: str, value: str) -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", (key, value))
            await db.commit()

    async def get_metadata(self, key: str) -> str | None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT value FROM metadata WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return str(row[0]) if row else None
```

`app/poller.py` — rewrite `Poller.__init__` and `_run`:

```python
import random
from datetime import UTC, datetime

from app.quality import is_offline_reading

HEARTBEAT_KEY = "poller_heartbeat_at"
MAX_BACKOFF_SECONDS = 480


class Poller:
    def __init__(
        self,
        store: ReadingStore,
        read_once: ReadOnce,
        interval_seconds: int = 30,
        idle_interval_seconds: int = 300,
        account_id: int | None = None,
        token_snapshot: TokenSnapshot | None = None,
        jitter_seconds: float | None = None,
        max_consecutive_failures: int = 10,
    ):
        self.store = store
        self.read_once = read_once
        self.interval_seconds = interval_seconds
        self.idle_interval_seconds = idle_interval_seconds
        self.account_id = account_id
        self.token_snapshot = token_snapshot
        self.jitter_seconds = (
            jitter_seconds if jitter_seconds is not None else random.uniform(0, interval_seconds)
        )
        self.max_consecutive_failures = max_consecutive_failures
        self._sleep = asyncio.sleep
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    # start()/stop() unchanged

    async def _run(self) -> None:
        consecutive_failures = 0
        await self._sleep(self.jitter_seconds)
        while not self._stop.is_set():
            delay: float = self.interval_seconds
            try:
                reading = await self.read_once()
                if self.account_id is not None:
                    await self.store.insert_reading(reading, account_id=self.account_id)
                await self._persist_tokens()
                await self.store.set_metadata(HEARTBEAT_KEY, datetime.now(UTC).isoformat())
                consecutive_failures = 0
                if is_offline_reading(reading):
                    delay = self.idle_interval_seconds
                logger.info(
                    "stored owlet reading serial=%s hr=%s spo2=%s next_poll=%ss",
                    reading.device_serial, reading.heart_rate, reading.oxygen_saturation, delay,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                consecutive_failures += 1
                if consecutive_failures >= self.max_consecutive_failures:
                    logger.exception(
                        "Owlet poll failed %s times; marking account %s needs_reauth and pausing",
                        consecutive_failures, self.account_id,
                    )
                    if self.account_id is not None:
                        await self.store.update_account_status(self.account_id, "needs_reauth")
                    return  # pauses until the user relinks (which starts a fresh poller)
                delay = min(self.interval_seconds * (2 ** consecutive_failures), MAX_BACKOFF_SECONDS)
                logger.exception("Owlet poll failed; retrying in %ss", delay)
            await self._sleep(delay)
```

`create_account_poller` passes through `idle_interval_seconds` (add parameter with default 300); `app/main.py` lifespan passes `idle_interval_seconds=settings.poll_idle_seconds` at both `create_account_poller` call sites and the inline `Poller(...)` in the JSON link flow.

`app/main.py` health endpoint gains the heartbeat:

```python
    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return {
            "ok": True,
            "collecting": bool(state.get("pollers")),
            "poller_heartbeat_at": await store.get_metadata("poller_heartbeat_at"),
            "database_path": str(settings.database_path),
        }
```

(Drop `has_credentials` — nothing consumes it.)

`app/dashboard.py` — collector-offline banner, added right after the Task 9 `injectAccountMenuLinks` block:

```javascript
    async function checkCollectorHealth() {
      try {
        const health = await fetchJson(`${API_BASE}/api/health`);
        let banner = document.getElementById('collectorBanner');
        const stale = health.poller_heartbeat_at
          ? (Date.now() - Date.parse(health.poller_heartbeat_at)) > 3 * 300 * 1000
          : health.collecting === false;
        if (stale && !banner) {
          banner = document.createElement('div');
          banner.id = 'collectorBanner';
          banner.style.cssText = 'background:#fef3c7;color:#92400e;padding:8px 14px;'
            + 'font-size:13px;text-align:center;border-radius:10px;margin:8px 0';
          document.querySelector('main')?.prepend(banner);
        }
        if (banner) {
          banner.textContent = health.poller_heartbeat_at
            ? `Collector offline since ${new Date(health.poller_heartbeat_at).toLocaleString()} - charts may have gaps.`
            : 'Collector is not running - no new readings are being stored.';
          banner.style.display = stale ? '' : 'none';
        }
      } catch (e) { /* health probe is best-effort */ }
    }
    if (!SHARE_MODE) { checkCollectorHealth(); setInterval(checkCollectorHealth, 60000); }
```

- [ ] **Step 4: Run full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/poller.py app/store.py app/main.py app/dashboard.py tests/test_poller.py
git commit -m "feat: adaptive polling with jitter/backoff and collector heartbeat"
```

---

### Task 11: Retention + daily snapshots (`app/maintenance.py`)

**Files:**
- Create: `app/maintenance.py`
- Modify: `app/store.py`, `app/main.py`
- Test: `tests/test_maintenance.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_maintenance.py`:

```python
import json
from datetime import UTC, datetime, timedelta

import aiosqlite
import pytest

from app.maintenance import run_maintenance_once
from app.models import normalize_reading
from app.store import ReadingStore


async def _seed_at(store, account_id, when: datetime, hr=120):
    await store.insert_reading(
        normalize_reading(
            {"heart_rate": hr, "oxygen_saturation": 96, "battery": 90,
             "last_updated": when.isoformat()},
            "S1",
        ),
        account_id=account_id,
    )


@pytest.mark.asyncio
async def test_raw_payload_trim_and_downsample(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    acc = await store.create_account(email="a@x.y", user_id=1)
    now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    await _seed_at(store, acc["id"], now - timedelta(days=1))                      # recent: untouched
    await _seed_at(store, acc["id"], now - timedelta(days=10))                     # raw trimmed
    old_bucket = now - timedelta(days=200)
    for minute, hr in ((0, 100), (2, 110), (4, 120), (7, 130)):                    # two 5-min buckets
        await _seed_at(store, acc["id"], old_bucket + timedelta(minutes=minute), hr=hr)

    trimmed = await store.trim_raw_payloads(older_than_days=7, now=now)
    downsampled = await store.downsample_readings(older_than_days=180, now=now)
    assert trimmed >= 1 and downsampled == 3  # only the 3-row bucket consolidates

    rows = await store.get_readings(hours=None, account_ids=[acc["id"]], limit=100)
    old_rows = [r for r in rows if r.recorded_at < now - timedelta(days=199)]
    assert len(old_rows) == 2                       # 4 rows -> 2 bucket averages
    assert {round(r.heart_rate) for r in old_rows} == {110, 130}

    async with aiosqlite.connect(store.db_path) as db:
        cursor = await db.execute(
            "SELECT raw_json FROM readings WHERE recorded_at < ?",
            ((now - timedelta(days=7)).isoformat(),),
        )
        assert all(json.loads(row[0] or "{}") == {} for row in await cursor.fetchall())


@pytest.mark.asyncio
async def test_snapshot_rotation(tmp_path):
    store = ReadingStore(tmp_path / "data" / "owlet.sqlite3")
    await store.init()
    for day in range(9):
        stamp = datetime(2026, 7, 1 + day, 3, 0, tzinfo=UTC)
        await run_maintenance_once(store, raw_days=7, full_days=180, keep_snapshots=7, now=stamp)
    backups = sorted((store.db_path.parent / "backups").glob("owlet-*.sqlite3"))
    assert len(backups) == 7
    assert backups[0].name == "owlet-20260703.sqlite3"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_maintenance.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.maintenance'`

- [ ] **Step 3: Implement**

`app/store.py` — retention methods:

```python
    async def trim_raw_payloads(self, older_than_days: int, now: datetime | None = None) -> int:
        await self.init()
        cutoff = ((now or datetime.now(UTC)) - timedelta(days=older_than_days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE readings SET raw_json = '{}' WHERE recorded_at < ? AND raw_json != '{}'",
                (cutoff,),
            )
            await db.commit()
            return cursor.rowcount or 0

    async def downsample_readings(
        self, older_than_days: int, bucket_minutes: int = 5, now: datetime | None = None
    ) -> int:
        """Replace readings older than the cutoff with per-bucket averages (idempotent)."""
        await self.init()
        cutoff = ((now or datetime.now(UTC)) - timedelta(days=older_than_days)).isoformat()
        bucket = (
            "strftime('%Y-%m-%dT%H:', recorded_at) || "
            f"printf('%02d:00', (CAST(strftime('%M', recorded_at) AS INTEGER) / {bucket_minutes}) * {bucket_minutes})"
        )
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"""
                SELECT account_id, device_serial, {bucket} AS bucket_start,
                       AVG(heart_rate), AVG(oxygen_saturation), AVG(battery), AVG(movement),
                       MAX(sleep_state), AVG(skin_temperature), COUNT(*), MIN(recorded_at)
                FROM readings
                WHERE recorded_at < ?
                GROUP BY account_id, device_serial, bucket_start
                HAVING COUNT(*) > 1
                """,
                (cutoff,),
            )
            groups = await cursor.fetchall()
            removed = 0
            for row in groups:
                account_id, serial, bucket_start = int(row[0]), row[1], row[2]
                await db.execute(
                    "DELETE FROM readings WHERE account_id = ? AND device_serial = ? "
                    f"AND {bucket} = ? AND recorded_at < ?",
                    (account_id, serial, bucket_start, cutoff),
                )
                await db.execute(
                    """
                    INSERT INTO readings (
                        account_id, device_serial, recorded_at, heart_rate, oxygen_saturation,
                        battery, movement, sleep_state, skin_temperature, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '{}')
                    """,
                    (account_id, serial, row[10], row[3], row[4], row[5], row[6], row[7], row[8]),
                )
                removed += int(row[9])
            await db.commit()
            return removed  # original rows consolidated into bucket averages
```

(Note: the averaged row reuses the group's MIN(recorded_at) so the unique `(account_id, device_serial, recorded_at)` index cannot collide, and re-running finds `COUNT(*) == 1` groups and skips them — idempotent.)

`app/maintenance.py`:

```python
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.store import ReadingStore

logger = logging.getLogger(__name__)

DAY_SECONDS = 24 * 3600


def _snapshot_sync(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(src) as source, sqlite3.connect(dest) as target:
        source.backup(target)


async def run_maintenance_once(
    store: ReadingStore,
    *,
    raw_days: int,
    full_days: int,
    keep_snapshots: int = 7,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(UTC)
    trimmed = await store.trim_raw_payloads(older_than_days=raw_days, now=now)
    downsampled = await store.downsample_readings(older_than_days=full_days, now=now)
    backups_dir = store.db_path.parent / "backups"
    snapshot = backups_dir / f"owlet-{now.strftime('%Y%m%d')}.sqlite3"
    await asyncio.to_thread(_snapshot_sync, store.db_path, snapshot)
    existing = sorted(backups_dir.glob("owlet-*.sqlite3"))
    for stale in existing[:-keep_snapshots] if len(existing) > keep_snapshots else []:
        stale.unlink()
    logger.info(
        "maintenance done: raw_trimmed=%s downsampled=%s snapshot=%s", trimmed, downsampled, snapshot.name
    )


async def maintenance_loop(store: ReadingStore, *, raw_days: int, full_days: int) -> None:
    while True:
        try:
            await run_maintenance_once(store, raw_days=raw_days, full_days=full_days)
        except Exception:
            logger.exception("maintenance run failed; retrying tomorrow")
        await asyncio.sleep(DAY_SECONDS)
```

`app/main.py` lifespan — start/stop the loop when pollers run (test apps with `start_poller=False` skip it):

```python
        maintenance_task: asyncio.Task | None = None
        if start_poller:
            maintenance_task = asyncio.create_task(
                maintenance_loop(
                    store,
                    raw_days=settings.retention_raw_days,
                    full_days=settings.retention_full_days,
                ),
                name="owlet-maintenance",
            )
```

and in the `finally:` block:

```python
            if maintenance_task:
                maintenance_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await maintenance_task
```

(add `import asyncio`, `import contextlib`, `from app.maintenance import maintenance_loop`.)

- [ ] **Step 4: Run full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/maintenance.py app/store.py app/main.py tests/test_maintenance.py
git commit -m "feat: daily retention (raw trim + downsample) and rotating DB snapshots"
```

---

### Task 12: Legacy env removal, security headers, legal pages

**Files:**
- Modify: `app/config.py`, `app/main.py`, `app/auth_pages.py`, `.env` docs
- Test: `tests/test_auth.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_auth.py`:

```python
def test_security_headers_and_legal_pages(app_bundle):
    app, *_ = app_bundle
    with client_for(app) as client:
        response = client.get("/login")
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "same-origin"
        assert "cdn.jsdelivr.net" in response.headers["content-security-policy"]
        assert client.get("/terms").status_code == 200
        assert "not a medical" in client.get("/privacy").text.lower()


def test_legacy_owlet_env_fields_are_gone():
    from app.config import Settings

    settings = Settings(_env_file=None)
    for legacy in ("owlet_email", "owlet_password", "owlet_basic_auth_username", "owlet_share_token"):
        assert not hasattr(settings, legacy)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_auth.py -v`
Expected: the two new tests FAIL

- [ ] **Step 3: Implement**

`app/config.py`: delete `owlet_email`, `owlet_password`, `owlet_region`, `owlet_basic_auth_username`, `owlet_basic_auth_password`, `owlet_share_token`, and the `has_owlet_credentials` / `basic_auth_enabled` / `share_enabled` properties (region is per-account now). `extra="ignore"` in `model_config` means stale `.env` entries are harmless. In `app/main.py`'s `_link_owlet_account`, the region fallback `str(payload.get("region") or settings.owlet_region or "world")` becomes `str(payload.get("region") or "world")`.

`app/main.py`:
- Lifespan: delete the whole `elif settings.has_owlet_credentials:` branch (token-account pollers remain the only startup path) and the `else:` warning becomes:

```python
            else:
                logger.info("No linked Owlet accounts yet; pollers start when users link accounts")
```

- Delete now-unused imports (`create_owlet_poller` if unreferenced).
- Add security headers to the CSRF middleware (set on every response before returning):

```python
        response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'",
        )
        return response
```

(Restructure the middleware so both the share branch and the normal branch flow through the header block.)

- Legal routes:

```python
    @app.get("/terms", response_class=HTMLResponse)
    async def terms() -> str:
        return auth_pages.terms_page()

    @app.get("/privacy", response_class=HTMLResponse)
    async def privacy() -> str:
        return auth_pages.privacy_page()
```

`app/auth_pages.py` — append:

```python
def terms_page() -> str:
    return _page(
        "Terms of use",
        """<h1>Terms of use</h1>
    <p class="sub">The short version, in plain language.</p>
    <p><strong>Not a medical device.</strong> This dashboard shows retrospective trends from Owlet's
    cloud data. It is not a medical monitor, does not alert, and must never replace the Owlet app,
    base station, or your own judgment.</p>
    <p><strong>Unofficial integration.</strong> Owlet has no public API. If Owlet changes their
    service, data collection can stop without notice.</p>
    <p><strong>Best-effort service.</strong> This is a small self-hosted service with no uptime
    guarantee. Gaps in collected history can occur and cannot be backfilled.</p>
    <p><strong>Your data.</strong> You can delete your account and all stored data at any time from
    Settings.</p>
    <div class="links"><a href="/login">Back</a></div>""",
    )


def privacy_page() -> str:
    return _page(
        "Privacy",
        """<h1>Privacy</h1>
    <p class="sub">What we store and why. This is not a medical service.</p>
    <p><strong>Your login:</strong> email and a salted password hash (argon2). Session cookies are
    HttpOnly.</p>
    <p><strong>Your Owlet link:</strong> we validate your Owlet credentials with Owlet once and keep
    only encrypted access/refresh tokens - never your Owlet password.</p>
    <p><strong>Your readings:</strong> vitals history from your linked socks, stored so you can see
    trends. Raw payloads are pruned after ~7 days; old readings are averaged down after ~6 months.</p>
    <p><strong>Sharing:</strong> nothing is visible to anyone else unless you create a share link.</p>
    <p><strong>Deletion:</strong> Settings → Delete account removes your login, tokens, and all
    readings immediately.</p>
    <div class="links"><a href="/login">Back</a></div>""",
    )
```

Update the developer's local `.env`: remove the now-ignored `OWLET_EMAIL`, `OWLET_PASSWORD`, `OWLET_REGION` lines (optional cleanliness; they are ignored either way).

- [ ] **Step 4: Run full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/ tests/ .env.example
git commit -m "feat: remove legacy env credential paths, add security headers and legal pages"
```

---

### Task 13: Docker, GHCR CI, docs

**Files:**
- Create: `Dockerfile`, `.dockerignore`, `.github/workflows/docker.yml`
- Modify: `README.md`, `docs/deployment.md`

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

RUN useradd --create-home --uid 1000 owlet
WORKDIR /srv/owlet

COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

USER owlet
VOLUME /data
ENV DATABASE_PATH=/data/owlet.sqlite3
EXPOSE 8888

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888", \
     "--proxy-headers", "--forwarded-allow-ips=*"]
```

- [ ] **Step 2: Create `.dockerignore`**

```
.git
.venv
data
docs
tests
scripts
.env
.env.*
__pycache__
*.pyc
.pytest_cache
.ruff_cache
*.egg-info
.github
.claude
```

- [ ] **Step 3: Create `.github/workflows/docker.yml`**

```yaml
name: docker

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest -q

  publish:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.sha }}
```

- [ ] **Step 4: Local verification**

If Docker is available locally:

```bash
docker build -t owlet-dashboard:dev .
docker run --rm -p 8899:8888 \
  -e SECRET_KEY=dev-secret -e TOKEN_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
  -e COOKIE_SECURE=false -e APP_BASE_URL=http://127.0.0.1:8899 \
  owlet-dashboard:dev
curl -s http://127.0.0.1:8899/api/health   # expect {"ok":true,...}
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8899/   # expect 303 (login redirect)
```

If Docker is NOT available locally, note it and rely on the CI `test` + `publish` jobs after push.

- [ ] **Step 5: Rewrite `README.md` Setup/Run/Internet sections**

Replace the `## Setup`, `## Run`, and `## Internet access` sections with:

```markdown
## Run with Docker (recommended)

    docker run -d --name owlet-dashboard \
      -p 8888:8888 \
      -v /path/to/appdata/owlet-dashboard:/data \
      -e SECRET_KEY=<generate> \
      -e TOKEN_ENCRYPTION_KEY=<generate> \
      -e RESEND_API_KEY=<your resend key> \
      -e APP_BASE_URL=https://owlet.example.com \
      ghcr.io/pbozzay/owlet-dashboard:latest

Generate each key with:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Put your reverse proxy (nginx, Nginx Proxy Manager, etc.) in front of port 8888 with
HTTPS. The app trusts `X-Forwarded-*` headers.

On Unraid: add a container using the GHCR image, map `/data` to an appdata share, map
the port, set the four env vars above. Sign up in the web UI, verify your email, and
link your Owlet account - the `.env`-credentials workflow from earlier versions is gone.

## Local development

    python -m venv .venv
    .venv/Scripts/python -m pip install -e ".[dev]"   # or .venv/bin/... on mac/linux
    cp .env.example .env                              # fill SECRET_KEY / TOKEN_ENCRYPTION_KEY, COOKIE_SECURE=false
    .venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8888

Without `RESEND_API_KEY`, verification/reset emails are printed to the server log.
```

Keep the feature list; delete stale references to `OWLET_EMAIL/PASSWORD`, basic auth, `OWLET_SHARE_TOKEN` (share links now live in Settings), and the Mac-specific paths.

- [ ] **Step 6: Rewrite `docs/deployment.md`**

Replace contents with the Unraid + nginx runbook: image URL, volume/port mappings, env var table (from the spec's Configuration section), reverse-proxy note (`proxy_pass http://UNRAID_IP:8888; proxy_set_header X-Forwarded-Proto https; proxy_set_header X-Forwarded-For $remote_addr; proxy_set_header Host $host;`), backup note (`/data/backups` holds 7 daily consistent snapshots; back that folder up), and update flow (pull new image in Unraid; GH Actions publishes on every push to main).

- [ ] **Step 7: Full suite + commit**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

```bash
git add Dockerfile .dockerignore .github/ README.md docs/deployment.md
git commit -m "feat: Docker packaging, GHCR publish workflow, deployment docs"
```

---

## Final Verification (after all tasks)

1. `.venv/Scripts/python -m pytest -q` — everything green.
2. Boot locally (`uvicorn app.main:app --port 8888`), then walk the golden path in a browser:
   sign up → console log shows verification link → open it → onboarding page → (optionally link a real Owlet account) → dashboard renders → Settings: enable share link, open it in a private window → log out.
3. Confirm anonymous `http://127.0.0.1:8888/` redirects to `/login` and `/api/readings` returns 401 JSON.
4. Push to GitHub; confirm the `docker` workflow goes green and `ghcr.io/pbozzay/owlet-dashboard:latest` appears.

## Spec-Coverage Checklist (self-review passed)

- Auth (signup/verify/login/reset/sessions/rate limits) — Tasks 3, 6, 7
- Tenancy + 404 semantics on every endpoint incl. widget/share — Tasks 4, 8, 9
- Owlet tokens encrypted at rest + migration — Task 5
- Sign-in/onboarding/settings UX, "never store your Owlet password" copy — Tasks 7, 9
- Per-user share links replacing env token — Task 9
- Adaptive polling, jitter, backoff, heartbeat + offline banner — Task 10
- Retention (raw 7d, downsample 180d) + rotating snapshots — Task 11
- Legacy env removal, security headers, terms/privacy — Task 12
- Single container, proxy headers, GHCR CI, Unraid/nginx docs — Task 13
- Testing: auth flows, tenancy isolation class, poller fake-clock, retention, migration — Tasks 3-11
