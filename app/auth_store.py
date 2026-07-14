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
        self._schema_ready = False

    def _connect(self):
        """WAL + busy-timeout on every connection: long analytic reads must not
        lock out the 5s poller writes (or vice versa)."""
        return _WALConnection(self.db_path)

    async def init(self) -> None:
        if self._schema_ready:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with self._connect() as db:
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
        self._schema_ready = True

    async def create_user(self, email: str, password_hash: str) -> dict[str, Any]:
        await self.init()
        normalized = email.strip().lower()
        async with self._connect() as db:
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
        user = await self.get_user(user_id)
        assert user is not None
        return user

    async def _adopt_orphan_accounts(self, db: aiosqlite.Connection, user_id: int) -> None:
        """The very first user inherits accounts created before multi-user existed."""
        cursor = await db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='accounts'"
        )
        row = await cursor.fetchone()
        if not row or not row[0]:
            return
        columns_cursor = await db.execute("PRAGMA table_info(accounts)")
        columns = [r[1] for r in await columns_cursor.fetchall()]
        if "user_id" not in columns:
            return
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        count_row = await cursor.fetchone()
        if count_row and int(count_row[0]) == 1:
            await db.execute("UPDATE accounts SET user_id = ? WHERE user_id IS NULL", (user_id,))

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        await self.init()
        async with self._connect() as db:
            cursor = await db.execute(
                "SELECT id, email, password_hash, created_at, updated_at FROM users WHERE id = ?",
                (user_id,),
            )
            return _row_to_user(await cursor.fetchone())

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        await self.init()
        async with self._connect() as db:
            cursor = await db.execute(
                "SELECT id, email, password_hash, created_at, updated_at FROM users WHERE email = ?",
                (email.strip().lower(),),
            )
            return _row_to_user(await cursor.fetchone())

    async def update_email(self, user_id: int, email: str) -> None:
        await self.init()
        normalized = email.strip().lower()
        async with self._connect() as db:
            try:
                await db.execute(
                    "UPDATE users SET email = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (normalized, user_id),
                )
            except aiosqlite.IntegrityError as exc:
                raise ValueError("email already registered") from exc
            await db.commit()

    async def update_password(self, user_id: int, password_hash: str) -> None:
        await self.init()
        async with self._connect() as db:
            await db.execute(
                "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (password_hash, user_id),
            )
            await db.commit()

    async def delete_other_sessions(self, user_id: int, keep_token_hash: str) -> int:
        """Sign out every other device — a changed password must orphan any
        session an old credential holder might still have open."""
        await self.init()
        async with self._connect() as db:
            cursor = await db.execute(
                "DELETE FROM sessions WHERE user_id = ? AND token_hash != ?",
                (user_id, keep_token_hash),
            )
            await db.commit()
            return cursor.rowcount or 0

    async def create_session(
        self, user_id: int, token_hash: str, *, ttl_days: int = 30, user_agent: str = ""
    ) -> None:
        await self.init()
        now = _now()
        expires = (now + timedelta(days=ttl_days)).isoformat()
        async with self._connect() as db:
            await db.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at, last_seen_at, user_agent) "
                "VALUES (?, ?, ?, ?, ?)",
                (token_hash, user_id, expires, now.isoformat(), user_agent[:200]),
            )
            await db.commit()

    async def get_session_user(self, token_hash: str) -> dict[str, Any] | None:
        await self.init()
        now = _now()
        async with self._connect() as db:
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
        async with self._connect() as db:
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


class _WALConnection:
    """Async context manager: aiosqlite connection with WAL + busy timeout."""

    def __init__(self, db_path):
        self._db_path = db_path
        self._db = None

    async def __aenter__(self):
        self._db = await aiosqlite.connect(self._db_path, timeout=15)
        await self._db.execute("PRAGMA busy_timeout = 15000")
        await self._db.execute("PRAGMA journal_mode = WAL")
        await self._db.execute("PRAGMA synchronous = NORMAL")
        return self._db

    async def __aexit__(self, exc_type, exc, tb):
        await self._db.close()
        return False
