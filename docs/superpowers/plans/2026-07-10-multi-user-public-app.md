# Multi-User App (Slim v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Multi-user Owlet dashboard: email+password login, per-user tenancy, onboarding page for linking a sock, shipped as one Docker container for Unraid behind nginx.

**Architecture:** One FastAPI process (unchanged runtime model: in-process pollers + SQLite). New `AuthStore` (users + sessions) beside `ReadingStore`. Session = random 256-bit cookie token, SHA-256-hashed in DB. No email sending, no encryption-at-rest, no share links in v1 (see spec's scope-reduction note).

**Tech Stack:** FastAPI, aiosqlite, argon2-cffi, python-multipart, pytest.

**Branch:** all work on `multi-user`.

**Conventions:** tests run with `.venv/Scripts/python -m pytest -q` (Windows venv). Timestamps are `datetime.now(UTC).isoformat()` strings. Commit after each task.

---

### Task 1: Security helpers + AuthStore

**Files:**
- Modify: `pyproject.toml`
- Create: `app/security.py`, `app/auth_store.py`
- Test: `tests/test_auth_store.py`

- [ ] **Step 1: Add dependencies**

In `pyproject.toml` `dependencies`, append:

```toml
  "argon2-cffi>=23.1.0",
  "python-multipart>=0.0.9",
```

Run: `.venv/Scripts/python -m pip install -e ".[dev]" --quiet`

- [ ] **Step 2: Write the failing test**

Create `tests/test_auth_store.py`:

```python
import pytest

from app.auth_store import AuthStore
from app.security import hash_password, hash_token, new_token, verify_password
from app.store import ReadingStore


def test_password_and_token_helpers():
    hashed = hash_password("correct horse")
    assert hashed != "correct horse"
    assert verify_password(hashed, "correct horse") is True
    assert verify_password(hashed, "wrong") is False
    assert verify_password("not-a-hash", "x") is False
    a, b = new_token(), new_token()
    assert a != b and len(a) >= 40
    assert hash_token(a) == hash_token(a) != hash_token(b)


@pytest.mark.asyncio
async def test_user_crud_and_email_normalization(tmp_path):
    auth = AuthStore(tmp_path / "owlet.sqlite3")
    user = await auth.create_user("Parent@Example.COM", hash_password("hunter22"))
    assert user["email"] == "parent@example.com"
    assert (await auth.get_user_by_email("PARENT@example.com"))["id"] == user["id"]
    with pytest.raises(ValueError):
        await auth.create_user("parent@example.com", hash_password("other"))


@pytest.mark.asyncio
async def test_sessions_create_expire_revoke(tmp_path):
    auth = AuthStore(tmp_path / "owlet.sqlite3")
    user = await auth.create_user("a@b.c", hash_password("hunter22"))
    token = new_token()
    await auth.create_session(user["id"], hash_token(token))
    assert (await auth.get_session_user(hash_token(token)))["id"] == user["id"]
    assert await auth.get_session_user(hash_token("nope")) is None
    expired = new_token()
    await auth.create_session(user["id"], hash_token(expired), ttl_days=-1)
    assert await auth.get_session_user(hash_token(expired)) is None
    await auth.delete_session(hash_token(token))
    assert await auth.get_session_user(hash_token(token)) is None


@pytest.mark.asyncio
async def test_first_user_adopts_orphan_accounts(tmp_path):
    db = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db)
    await store.init()
    orphan = await store.create_account(email="sock@example.com")
    auth = AuthStore(db)
    first = await auth.create_user("first@example.com", hash_password("hunter22"))
    second = await auth.create_user("second@example.com", hash_password("hunter22"))
    assert {a["id"] for a in await store.list_accounts(user_id=first["id"])} == {orphan["id"]}
    assert await store.list_accounts(user_id=second["id"]) == []
```

The last test needs Task 2's `list_accounts(user_id=...)`; comment it out with `# enabled in Task 2` and re-enable it there.

- [ ] **Step 3: Run to verify failure**

Run: `.venv/Scripts/python -m pytest tests/test_auth_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.auth_store'`

- [ ] **Step 4: Implement `app/security.py`**

```python
from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def new_token() -> str:
    """256-bit URL-safe token for session cookies."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

- [ ] **Step 5: Implement `app/auth_store.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite


def _now() -> datetime:
    return datetime.now(UTC)


class AuthStore:
    """Users and sessions. Shares the SQLite file with ReadingStore."""

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
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
            await db.commit()

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
            await self._adopt_orphan_accounts(db, user_id)
            await db.commit()
        return await self.get_user(user_id)

    async def _adopt_orphan_accounts(self, db: aiosqlite.Connection, user_id: int) -> None:
        """The very first user inherits accounts created before multi-user existed."""
        cursor = await db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='accounts'"
        )
        row = await cursor.fetchone()
        if not row or not row[0]:
            return
        columns = [r[1] for r in await (await db.execute("PRAGMA table_info(accounts)")).fetchall()]
        if "user_id" not in columns:
            return
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        count_row = await cursor.fetchone()
        if int(count_row[0]) == 1:
            await db.execute("UPDATE accounts SET user_id = ? WHERE user_id IS NULL", (user_id,))

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, email, password_hash, created_at, updated_at FROM users WHERE id = ?",
                (user_id,),
            )
            return _row_to_user(await cursor.fetchone())

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, email, password_hash, created_at, updated_at FROM users WHERE email = ?",
                (email.strip().lower(),),
            )
            return _row_to_user(await cursor.fetchone())

    async def create_session(
        self, user_id: int, token_hash: str, *, ttl_days: int = 30, user_agent: str = ""
    ) -> None:
        await self.init()
        expires = (_now() + timedelta(days=ttl_days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at, user_agent) VALUES (?, ?, ?, ?)",
                (token_hash, user_id, expires, user_agent[:200]),
            )
            await db.commit()

    async def get_session_user(self, token_hash: str) -> dict[str, Any] | None:
        await self.init()
        now = _now()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT u.id, u.email, u.password_hash, u.created_at, u.updated_at,
                       s.expires_at, s.last_seen_at
                FROM sessions s JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ?
                """,
                (token_hash,),
            )
            row = await cursor.fetchone()
            if not row or datetime.fromisoformat(row[5]) < now:
                return None
            if (now - datetime.fromisoformat(row[6])) > timedelta(hours=1):  # rolling expiry
                await db.execute(
                    "UPDATE sessions SET last_seen_at = ?, expires_at = ? WHERE token_hash = ?",
                    (now.isoformat(), (now + timedelta(days=30)).isoformat(), token_hash),
                )
                await db.commit()
            return _row_to_user(row[:5])

    async def delete_session(self, token_hash: str) -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            await db.commit()


def _row_to_user(row: tuple[Any, ...] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": int(row[0]),
        "email": row[1],
        "password_hash": row[2],
        "created_at": row[3],
        "updated_at": row[4],
    }
```

- [ ] **Step 6: Run to verify pass**

Run: `.venv/Scripts/python -m pytest tests/test_auth_store.py -v`
Expected: 3 PASS (adoption test commented out)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml app/security.py app/auth_store.py tests/test_auth_store.py
git commit -m "feat: password hashing, session tokens, and AuthStore"
```

---

### Task 2: Account ownership + scoped queries (`app/store.py`)

**Files:**
- Modify: `app/store.py`, `app/poller.py`, `app/main.py`
- Test: `tests/test_store.py` (append), `tests/test_auth_store.py` (re-enable adoption test)

- [ ] **Step 1: Failing tests**

Re-enable `test_first_user_adopts_orphan_accounts`. Append to `tests/test_store.py`:

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
async def test_challenge_ownership_scoping(tmp_path):
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    await store.init()
    acc = await store.create_account(email="a@x.y", user_id=1)
    challenge = await store.create_oxygen_challenge("2026-07-02T00:00:00Z", account_id=acc["id"])
    assert (await store.get_oxygen_challenge(challenge["id"], account_ids=[acc["id"]]))["id"] == challenge["id"]
    with pytest.raises(KeyError):
        await store.get_oxygen_challenge(challenge["id"], account_ids=[999])
    assert await store.delete_oxygen_challenge(challenge["id"], account_ids=[999]) == 0
    assert await store.delete_oxygen_challenge(challenge["id"], account_ids=[acc["id"]]) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest tests/test_store.py tests/test_auth_store.py -v`
Expected: new tests FAIL (unexpected kwargs)

- [ ] **Step 3: Implement in `app/store.py`**

**(a) Schema:** in `init()`'s accounts CREATE TABLE add `user_id INTEGER,` after `id`. In `_ensure_account_preference_schema` add:

```python
        if "user_id" not in columns:
            await db.execute("ALTER TABLE accounts ADD COLUMN user_id INTEGER")
```

**(b) No auto default account on fresh DBs.** Replace `_ensure_account_schema`'s first line (`default_account_id = await self._ensure_default_account(db)`) with a call placed AFTER `_ensure_account_preference_schema`, using a new helper, and delete `_ensure_default_account` and the public `default_account_id()`:

```python
    async def _ensure_account_schema(self, db: aiosqlite.Connection) -> None:
        await self._ensure_account_preference_schema(db)
        default_account_id = await self._legacy_default_account_id(db)
        await self._ensure_readings_account_schema(db, default_account_id)
        await self._ensure_notifications_account_schema(db, default_account_id)
        await self._ensure_challenges_account_schema(db, default_account_id)
        # existing CREATE INDEX statements stay unchanged below

    async def _legacy_default_account_id(self, db: aiosqlite.Connection) -> int:
        """Existing first account, or create one ONLY if legacy rows need an owner."""
        cursor = await db.execute("SELECT id FROM accounts ORDER BY id ASC LIMIT 1")
        row = await cursor.fetchone()
        if row:
            return int(row[0])
        for table in ("readings", "notifications", "oxygen_challenges"):
            cursor = await db.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)
            )
            exists_row = await cursor.fetchone()
            if exists_row and exists_row[0]:
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                count_row = await cursor.fetchone()
                if count_row and int(count_row[0]) > 0:
                    insert = await db.execute(
                        "INSERT INTO accounts (email, region, display_name, status, updated_at) "
                        "VALUES ('', 'world', 'Default account', 'active', CURRENT_TIMESTAMP)"
                    )
                    return int(insert.lastrowid)
        return 0  # fresh database: no account rows created
```

`insert_reading` and `create_oxygen_challenge` now require the account:

```python
    async def insert_reading(self, reading: OwletReading, account_id: int) -> None:
        await self.init()
        if not account_id:
            raise ValueError("account_id is required")
        # rest unchanged
```

(same guard in `create_oxygen_challenge`, dropping its `account_id or await self.default_account_id()` line.)

**(c) `user_id` on accounts.** `create_account` gains `user_id: int | None = None` keyword: add `user_id` to the INSERT columns/values. `list_accounts` gains `user_id: int | None = None`: add `user_id` to the SELECT column list and `WHERE user_id = ?` when set. `get_account` gains `user_id: int | None = None`: `WHERE id = ?` plus `AND user_id = ?` when set (still `raise KeyError(account_id)` when no row). Add `user_id` as the last column in both SELECTs and in `_row_to_account`:

```python
            "user_id": int(row[13]) if row[13] is not None else None,
```

**(d) `account_ids` filters.** Add keyword `account_ids: list[int] | None = None` to `_latest_timestamp`, `get_readings`, `get_analysis_readings`, `get_summary`, `list_devices`, `get_notifications`, `get_oxygen_challenges`, `_oxygen_challenge_rows`, `get_oxygen_challenge_intervals`, and `exclude_challenge_readings` (which passes it to `get_oxygen_challenge_intervals`). Pattern for each:

```python
        if account_ids is not None and not account_ids:
            return []  # or the empty dict shape for notifications/challenges/summary
```

Empty shapes: `get_notifications`/`get_oxygen_challenges` → `{"items": [], "total": 0, "limit": limit, "offset": offset}`; `get_summary` → build via its normal path with `readings = []` (skip queries; simplest is to short-circuit `get_analysis_readings` which `get_summary` calls — returning `[]` there makes `get_summary` produce the correct empty summary naturally, so only `get_analysis_readings`, `get_readings`, `list_devices`, `_latest_timestamp`, `get_notifications`, and the challenge helpers need the explicit guard). WHERE clause pattern:

```python
        if account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where_parts.append(f"account_id IN ({placeholders})")
            params.extend(account_ids)
```

(`get_summary`, `get_oxygen_challenges`, `exclude_challenge_readings` just pass `account_ids=` through to the helpers they call. In `list_devices` the column is `r.account_id`. Keep the existing single `account_id` params working alongside — pollers and the widget still use them.)

**(e) Challenge ownership.** `_get_oxygen_challenge_row` and `get_oxygen_challenge` gain `account_ids: list[int] | None = None` → `AND account_id IN (...)` (empty list → no row → `KeyError`). `delete_oxygen_challenge` gains `account_ids` and returns the deleted rowcount:

```python
    async def delete_oxygen_challenge(self, challenge_id: int, account_ids: list[int] | None = None) -> int:
        await self.init()
        where = "WHERE id = ?"
        params: list[Any] = [challenge_id]
        if account_ids is not None:
            if not account_ids:
                return 0
            placeholders = ",".join("?" for _ in account_ids)
            where += f" AND account_id IN ({placeholders})"
            params.extend(account_ids)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(f"DELETE FROM oxygen_challenges {where}", params)
            await db.commit()
            return cursor.rowcount or 0
```

**(f) Callers of removed `default_account_id()`:**
- `app/poller.py` `create_owlet_poller`: parameter becomes `account_id: int` (required); delete the `or await store.default_account_id()` fallback.
- `app/main.py` lifespan `elif settings.has_owlet_credentials:` branch: replace `default_account_id = await store.default_account_id()` with:

```python
                    accounts_list = await store.list_accounts()
                    default_account_id = (
                        int(accounts_list[0]["id"])
                        if accounts_list
                        else int((await store.create_account(email=settings.owlet_email or ""))["id"])
                    )
```

- `app/main.py` `create_oxygen_challenge` route: it currently passes `account_id=... else None`. Interim fix (Task 4 replaces it): resolve `accounts_list = await store.list_accounts()`; if the payload has no valid account id, use `accounts_list[0]["id"]` or raise `HTTPException(status_code=400, detail="account_id is required")` when there are no accounts.

**(g) Existing tests.** In `tests/test_api.py` and `tests/test_store.py`, seeds relying on the auto default account must create one explicitly. Add to each file's helpers:

```python
async def _default_account_id(store):
    accounts = await store.list_accounts()
    if accounts:
        return accounts[0]["id"]
    return (await store.create_account(email="seed@example.test"))["id"]
```

and in `_seed_reading`: `account_id = account_id or await _default_account_id(store)`. Any test doing `(await store.list_accounts())[0]` right after `init()` must `create_account` first. Run the suite and fix all such sites mechanically.

- [ ] **Step 4: Full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/store.py app/poller.py app/main.py tests/
git commit -m "feat: account ownership (user_id) and account_ids scoping in store"
```

---

### Task 3: Login/signup/onboarding pages, sessions, gated routes

**Files:**
- Create: `app/auth_pages.py`, `app/auth_routes.py`, `app/ratelimit.py`, `tests/conftest.py`
- Modify: `app/main.py`, `app/dashboard.py`
- Test: `tests/test_auth.py`, adapt `tests/test_api.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient

from app.auth_store import AuthStore
from app.config import Settings
from app.main import create_app
from app.security import hash_password, hash_token, new_token
from app.store import ReadingStore


def test_settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)  # type: ignore[call-arg]


@pytest.fixture
def app_bundle(tmp_path):
    """(app, store, auth_store) wired against a tmp SQLite file."""
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    auth_store = AuthStore(tmp_path / "owlet.sqlite3")
    app = create_app(store=store, settings=test_settings(), start_poller=False, auth_store=auth_store)
    return app, store, auth_store


async def make_user(auth_store: AuthStore, email: str) -> tuple[dict, str]:
    """Create a user + session directly; returns (user, raw_session_token)."""
    user = await auth_store.create_user(email, hash_password("hunter22"))
    raw = new_token()
    await auth_store.create_session(user["id"], hash_token(raw))
    return user, raw


def client_for(app, session_token: str | None = None) -> TestClient:
    client = TestClient(app)
    if session_token:
        client.cookies.set("owlet_session", session_token)
    return client
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_auth.py`:

```python
from app.ratelimit import RateLimiter
from tests.conftest import client_for


def test_rate_limiter_sliding_window():
    clock = {"now": 0.0}
    limiter = RateLimiter(clock=lambda: clock["now"])
    assert all(limiter.allow("k", max_hits=3, window_seconds=60) for _ in range(3))
    assert limiter.allow("k", max_hits=3, window_seconds=60) is False
    assert limiter.allow("other", max_hits=3, window_seconds=60) is True
    clock["now"] = 61.0
    assert limiter.allow("k", max_hits=3, window_seconds=60) is True


def test_signup_login_logout_flow(app_bundle):
    app, _store, _auth = app_bundle
    with client_for(app) as client:
        landing = client.get("/", follow_redirects=False)
        assert landing.status_code == 303 and landing.headers["location"] == "/login"
        assert client.get("/login").status_code == 200
        assert client.get("/api/readings").status_code == 401

        response = client.post(
            "/auth/signup",
            data={"email": "parent@example.com", "password": "hunter22"},
            follow_redirects=False,
        )
        assert response.status_code == 303 and response.headers["location"] == "/"
        # no linked accounts yet -> onboarding page instead of the dashboard
        assert "link your owlet sock" in client.get("/").text.lower()
        assert client.get("/api/readings").status_code == 200

        assert client.post("/auth/logout", follow_redirects=False).status_code == 303
        assert client.get("/api/readings").status_code == 401

        # log back in
        response = client.post(
            "/auth/login",
            data={"email": "parent@example.com", "password": "hunter22"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert client.get("/api/readings").status_code == 200


def test_signup_validation_and_login_failures(app_bundle):
    app, *_ = app_bundle
    with client_for(app) as client:
        short = client.post(
            "/auth/signup", data={"email": "a@b.c", "password": "short"}, follow_redirects=False
        )
        assert "error" in short.headers["location"]
        client.post("/auth/signup", data={"email": "a@b.c", "password": "hunter22"})
        duplicate = client.post(
            "/auth/signup", data={"email": "a@b.c", "password": "hunter22"}, follow_redirects=False
        )
        assert "error" in duplicate.headers["location"]
        wrong = client.post(
            "/auth/login", data={"email": "a@b.c", "password": "nope"}, follow_redirects=False
        )
        assert "error" in wrong.headers["location"]


def test_login_rate_limited(app_bundle):
    app, *_ = app_bundle
    with client_for(app) as client:
        for _ in range(10):
            client.post("/auth/login", data={"email": "x@y.z", "password": "wrong"})
        response = client.post(
            "/auth/login", data={"email": "x@y.z", "password": "wrong"}, follow_redirects=False
        )
        assert response.status_code == 429
```

- [ ] **Step 3: Run to verify failure**

Run: `.venv/Scripts/python -m pytest tests/test_auth.py -v`
Expected: FAIL — no `app.ratelimit`, then 404s on `/auth/*`

- [ ] **Step 4: Implement `app/ratelimit.py`**

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

- [ ] **Step 5: Implement `app/auth_pages.py`**

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
    .notice {{ background:#fef2f2; color:#991b1b; border-radius:10px; padding:10px 12px; font-size:13px; margin-bottom:8px; }}
    footer {{ margin-top:20px; font-size:11px; color:var(--muted); text-align:center; }}
  </style>
</head>
<body>
  <div class="card">
    {body}
    <footer>Retrospective trend viewing only — not a medical monitor or alert replacement.</footer>
  </div>
</body>
</html>"""


def _page(title: str, body: str) -> str:
    return _BASE.format(title=html.escape(title), body=body)


def _error(error: str | None) -> str:
    return f'<div class="notice">{html.escape(error)}</div>' if error else ""


def login_page(error: str | None = None) -> str:
    return _page(
        "Sign in",
        f"""<h1>Owlet Dashboard</h1>
    <p class="sub">Private history for your Owlet sock data.</p>
    {_error(error)}
    <form method="post" action="/auth/login">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required autocomplete="email" />
      <label for="password">Password</label>
      <input id="password" name="password" type="password" required autocomplete="current-password" />
      <button type="submit">Sign in</button>
    </form>
    <div class="links"><a href="/signup">Create an account</a><span></span></div>""",
    )


def signup_page(error: str | None = None) -> str:
    return _page(
        "Create account",
        f"""<h1>Create your account</h1>
    <p class="sub">Then link your Owlet sock to start collecting history.</p>
    {_error(error)}
    <form method="post" action="/auth/signup">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required autocomplete="email" />
      <label for="password">Password (8+ characters)</label>
      <input id="password" name="password" type="password" required minlength="8" maxlength="128"
             autocomplete="new-password" />
      <button type="submit">Create account</button>
    </form>
    <div class="links"><a href="/login">Back to sign in</a><span></span></div>""",
    )


def onboarding_page(error: str | None = None) -> str:
    return _page(
        "Link your Owlet sock",
        f"""<h1>Link your Owlet sock</h1>
    <p class="sub">Enter the login you use in the Owlet app. We verify it with Owlet once and
    <strong>never store your Owlet password</strong> — only a revocable access token.</p>
    {_error(error)}
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

- [ ] **Step 6: Implement `app/auth_routes.py`**

```python
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
    return auth_pages.login_page(error=error)


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
```

- [ ] **Step 7: Wire into `app/main.py`**

Imports to add:

```python
from fastapi import Depends, Form
from fastapi.responses import RedirectResponse

from app import auth_pages
from app.auth_store import AuthStore
from app.auth_routes import current_user, require_user, router as auth_router
from app.ratelimit import RateLimiter
```

`create_app` signature and setup:

```python
def create_app(
    store: ReadingStore | None = None,
    settings: Settings | None = None,
    start_poller: bool = True,
    auth_store: AuthStore | None = None,
) -> FastAPI:
    settings = settings or Settings()
    store = store or ReadingStore(settings.database_path)
    auth_store = auth_store or AuthStore(settings.database_path)
```

After `app = FastAPI(...)`:

```python
    app.state.auth_store = auth_store
    app.state.rate_limiter = RateLimiter()
    app.include_router(auth_router)
```

In lifespan, after `await store.init()`: `await auth_store.init()`.

**Dashboard gate** — replace the `dashboard` route:

```python
    @app.get("/")
    async def dashboard(request: Request):
        user = await current_user(request)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        accounts = await store.list_accounts(user_id=user["id"])
        if not accounts:
            return HTMLResponse(auth_pages.onboarding_page())
        return HTMLResponse(render_dashboard())
```

**Gate the API** — add `user: dict = Depends(require_user)` to every data endpoint: `accounts`, `update_account`, `create_account`, `devices`, `readings`, `summary`, `insights`, `rollups`, `crypto`, `notifications`, all `oxygen_challenges` routes, and `widget`. (`/api/health`, PWA/static routes, and `/share/*` stay as they are.)

**Owlet link refactor** — extract the body of the JSON `create_account` route into a helper both routes use (defined inside `create_app`, above the routes):

```python
    async def _link_owlet_account(request: Request, payload: dict[str, object], user: dict) -> dict:
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
            account = await store.create_account(
                email=email,
                region=region,
                display_name=display_name,
                api_token=client.tokens.get("api_token"),
                api_token_expiry=client.tokens.get("expiry"),
                refresh_token=client.tokens.get("refresh"),
                status="active",
                user_id=user["id"],
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
            return account
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Could not validate Owlet account") from exc
        finally:
            if client is not None:
                await client.close()
```

The JSON route body becomes:

```python
    @app.post("/api/accounts")
    async def create_account(
        request: Request, payload: dict[str, object] = JSON_BODY, user: dict = Depends(require_user)
    ):
        account = await _link_owlet_account(request, payload, user)
        return {"account": _public_account(account)}
```

And the onboarding form route:

```python
    @app.post("/onboarding/link")
    async def onboarding_link(
        request: Request,
        email: str = Form(),
        password: str = Form(),
        region: str = Form(default="world"),
        user: dict = Depends(require_user),
    ):
        try:
            await _link_owlet_account(request, {"email": email, "password": password, "region": region}, user)
        except HTTPException as exc:
            if exc.status_code == 429:
                raise
            return HTMLResponse(
                auth_pages.onboarding_page(error="Owlet rejected that login - check email/password/region"),
                status_code=400,
            )
        return RedirectResponse("/", status_code=303)
```

**Note:** the old basic-auth middleware (`require_basic_auth`) stays for now ONLY in its `/share/` branch role; simplify it by deleting the basic-auth section (everything after the share block) so it returns `await call_next(request)` for non-share paths, and delete `_parse_basic_auth` / `_basic_auth_cookie_value` and the `hashlib`/`base64` usage. Share links remain env-token-based and default-off (`OWLET_SHARE_TOKEN` unset → all `/share/*` 404).

- [ ] **Step 8: Logout link in the dashboard (`app/dashboard.py`)**

Directly after the line `el('addAccount')?.addEventListener('click', addAccountFromPrompt);` (~line 3131), insert:

```javascript
    (function injectSignOut() {
      if (SHARE_MODE) return;
      const wrap = el('profileMenuWrap');
      if (!wrap) return;
      const nav = document.createElement('form');
      nav.method = 'post';
      nav.action = '/auth/logout';
      nav.style.cssText = 'margin:0;padding:6px 12px;text-align:right';
      nav.innerHTML = '<button type="submit" style="all:unset;cursor:pointer;color:inherit;'
        + 'font-size:12px;text-decoration:underline">Sign out</button>';
      wrap.appendChild(nav);
    })();
```

- [ ] **Step 9: Adapt `tests/test_api.py`**

Replace its local `_test_settings` definition with `from tests.conftest import client_for, make_user, test_settings as _test_settings  # noqa: E402`. For every test that makes HTTP calls: construct `auth = AuthStore(db_path)` (import it), `user, session = await make_user(auth, "owner@example.test")`, pass `user_id=user["id"]` to every `store.create_account(...)` call, pass `auth_store=auth` to `create_app(...)`, and use `client_for(app, session)` instead of `TestClient(app)`. Delete the now-unused `TestClient` import if nothing else uses it.

- [ ] **Step 10: Full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

- [ ] **Step 11: Commit**

```bash
git add app/ tests/
git commit -m "feat: user/pass auth with sessions, login/onboarding pages, gated routes"
```

---

### Task 4: Tenancy enforcement on every data endpoint

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
    bob, _bob_session = await make_user(auth, "bob@example.test")
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
    return app, alice_session, alice_acc, bob_acc, challenge


@pytest.mark.asyncio
async def test_data_endpoints_scoped_to_session_user(two_tenants):
    app, alice_session, alice_acc, bob_acc, _challenge = two_tenants
    with client_for(app, alice_session) as client:
        assert [a["id"] for a in client.get("/api/accounts").json()["accounts"]] == [alice_acc["id"]]
        assert {r["heart_rate"] for r in client.get("/api/readings").json()} == {110}
        assert {d["account_id"] for d in client.get("/api/devices").json()["devices"]} == {alice_acc["id"]}
        assert client.get("/api/summary").json()["count"] == 1
        for path in ("readings", "devices", "summary", "insights", "rollups",
                     "notifications", "oxygen-challenges", "widget"):
            assert client.get(f"/api/{path}?account={bob_acc['id']}").status_code == 404, path


@pytest.mark.asyncio
async def test_mutations_on_foreign_resources_return_404(two_tenants):
    app, alice_session, _alice_acc, bob_acc, challenge = two_tenants
    with client_for(app, alice_session) as client:
        assert client.patch(f"/api/accounts/{bob_acc['id']}", json={"display_name": "hi"}).status_code == 404
        assert client.get(f"/api/oxygen-challenges/{challenge['id']}").status_code == 404
        assert client.patch(f"/api/oxygen-challenges/{challenge['id']}", json={"label": "x"}).status_code == 404
        assert client.delete(f"/api/oxygen-challenges/{challenge['id']}").status_code == 404
        assert client.post(
            "/api/oxygen-challenges",
            json={"start_time": "2026-07-02T02:00:00Z", "account_id": bob_acc["id"]},
        ).status_code == 404
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest tests/test_tenancy.py -v`
Expected: FAIL — cross-tenant reads currently return 200

- [ ] **Step 3: Implement in `app/main.py`**

Scoping helper inside `create_app`:

```python
    async def _scope(user: dict, account: int | None) -> list[int]:
        owned = [int(a["id"]) for a in await store.list_accounts(user_id=user["id"])]
        if account is None:
            return owned
        if account not in owned:
            raise HTTPException(status_code=404, detail="Not found")
        return [account]
```

Endpoint changes (each already has `user` from Task 3):

- `accounts`: list only the user's — `await store.list_accounts(user_id=user["id"])`.
- `update_account`: first line inside the `try`: `await store.get_account(account_id, user_id=user["id"])` (its `KeyError` joins the existing 404 handling).
- `devices`: `ids = await _scope(user, account)` → `store.list_devices(account_ids=ids)`.
- `readings`: `ids = await _scope(user, account)` → pass `account_ids=ids` to `get_readings`/`get_analysis_readings`; drop `account_id=account`.
- `summary`, `insights`, `rollups`, `notifications`: same — `account_ids=ids` on the store calls (including `exclude_challenge_readings(rows, account_ids=ids)`).
- `oxygen_challenges` list: `ids = await _scope(user, account)` → `get_oxygen_challenges(..., account_ids=ids)`.
- `create_oxygen_challenge`: if the payload carries `account_id`, `ids = await _scope(user, int(account_id))`; else `ids = await _scope(user, None)` and `raise HTTPException(400, "Link an Owlet account first")` if empty; call the store with `account_id=ids[0]`.
- `oxygen_challenge` GET: `ids = await _scope(user, None)` → `store.get_oxygen_challenge(challenge_id, account_ids=ids)` (KeyError → existing 404).
- `update_oxygen_challenge` PATCH: same ownership pre-check via `store.get_oxygen_challenge(challenge_id, account_ids=ids)` before calling `update_oxygen_challenge`.
- `delete_oxygen_challenge` DELETE: `deleted = await store.delete_oxygen_challenge(challenge_id, account_ids=await _scope(user, None))`; `raise HTTPException(status_code=404)` when `deleted == 0`.
- `widget`: change `_widget_payload`'s `account_id` parameter to `account_ids: list[int] | None = None`, thread it into its four store calls, and call it with `account_ids=await _scope(user, account)`.
- `crypto`: session-gated only (Task 3); no scoping — public market data.

- [ ] **Step 4: Full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_tenancy.py
git commit -m "feat: enforce per-user tenancy with 404 semantics on all data endpoints"
```

---

### Task 5: Docker, GHCR workflow, docs

**Files:**
- Create: `Dockerfile`, `.dockerignore`, `.github/workflows/docker.yml`
- Modify: `README.md`, `docs/deployment.md`

- [ ] **Step 1: `Dockerfile`**

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

- [ ] **Step 2: `.dockerignore`**

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

- [ ] **Step 3: `.github/workflows/docker.yml`**

```yaml
name: docker

on:
  push:
    branches: [main, multi-user]

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
    if: github.ref == 'refs/heads/main'
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

- [ ] **Step 4: Local Docker smoke test (if Docker available; otherwise rely on CI)**

```bash
docker build -t owlet-dashboard:dev .
docker run --rm -d --name owlet-smoke -p 8899:8888 owlet-dashboard:dev
curl -s http://127.0.0.1:8899/api/health          # expect {"ok":true,...}
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8899/   # expect 303
docker rm -f owlet-smoke
```

- [ ] **Step 5: Update `README.md`**

Replace the `## Setup` and `## Run` sections with:

```markdown
## Run with Docker (recommended)

    docker run -d --name owlet-dashboard \
      -p 8888:8888 \
      -v /path/to/appdata/owlet-dashboard:/data \
      ghcr.io/pbozzay/owlet-dashboard:latest

Put your reverse proxy (nginx, Nginx Proxy Manager, ...) in front of port 8888 with
HTTPS; the app trusts `X-Forwarded-*` headers. On Unraid: add a container using the
GHCR image, map `/data` to an appdata share, map the port.

Open the site, create an account (first signup adopts any data from a pre-multi-user
database), and link your Owlet login on the onboarding page. Owlet passwords are
verified once and never stored — only access tokens.

## Local development

    python -m venv .venv
    .venv/Scripts/python -m pip install -e ".[dev]"   # .venv/bin/... on mac/linux
    .venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8888
```

Delete the stale `OWLET_EMAIL`/`OWLET_PASSWORD` setup instructions and the Mac-specific paths; keep the feature list and safety note. In the `## Internet access` section, replace the Cloudflare recommendation with one line: "Any HTTPS reverse proxy works; sign-in is required on every page."

- [ ] **Step 6: Update `docs/deployment.md`**

Replace contents with the Unraid runbook:

```markdown
# Deployment (Unraid + nginx)

Image: `ghcr.io/pbozzay/owlet-dashboard:latest` (published by GitHub Actions on main).

## Unraid container

- Repository: `ghcr.io/pbozzay/owlet-dashboard:latest`
- Volume: `/mnt/user/appdata/owlet-dashboard` -> `/data`
- Port: `8888` -> host port of your choice
- Env (all optional): `POLL_INTERVAL_SECONDS` (default 30)

## nginx reverse proxy

    location / {
        proxy_pass http://UNRAID_IP:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $remote_addr;
    }

The container runs uvicorn with `--proxy-headers`, so session cookies get the
`Secure` flag when the request arrives as https.

## Updates

Push to `main` -> Actions builds and publishes -> Unraid "check for update" pulls.

## Data

Everything lives in the `/data` volume (`owlet.sqlite3`). Back that folder up with
your normal appdata backup; stop the container first for a guaranteed-consistent copy.
```

- [ ] **Step 7: Full suite + commit**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS

```bash
git add Dockerfile .dockerignore .github/ README.md docs/deployment.md
git commit -m "feat: Docker packaging, GHCR publish workflow, Unraid deployment docs"
```

---

## Final Verification

1. `.venv/Scripts/python -m pytest -q` — green.
2. Boot locally, walk the golden path in a browser: `/` redirects to `/login` → sign up → onboarding page appears → (optionally link a real Owlet account) → dashboard renders → Sign out works → log back in.
3. Anonymous `/api/readings` returns 401 JSON; a second user cannot see the first user's data (covered by tests, spot-check manually if desired).

## Deferred (documented in the spec's scope-reduction note)

Email verification/reset, encryption at rest, per-user share links, settings/deletion,
adaptive polling/heartbeat, retention, snapshots, CSRF middleware, security headers,
legal pages — all designed in the spec, none in v1.
