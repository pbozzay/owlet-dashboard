from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from app.models import OwletReading, raw_alert_mask_has, raw_flag_active
from app.notifications import NotificationEvent, extract_notifications
from app.oxygen_challenges import challenge_analysis, parse_time, reading_in_any_period
from app.quality import is_offline_reading


class ReadingStore:
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
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    email TEXT NOT NULL DEFAULT '',
                    region TEXT NOT NULL DEFAULT 'world',
                    display_name TEXT NOT NULL DEFAULT 'Default account',
                    api_token TEXT,
                    api_token_expiry REAL,
                    refresh_token TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    dashboard_preferences TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_validated_at TEXT
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    device_serial TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    heart_rate REAL,
                    oxygen_saturation REAL,
                    battery REAL,
                    movement REAL,
                    sleep_state TEXT,
                    skin_temperature REAL,
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_readings_recorded_at ON readings(recorded_at)"
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    device_serial TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    heart_rate REAL,
                    oxygen_saturation REAL,
                    battery REAL,
                    sleep_state TEXT,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    read_at TEXT
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_notifications_recorded_at ON notifications(recorded_at)"
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS oxygen_challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    label TEXT NOT NULL DEFAULT 'Oxygen challenge',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_oxygen_challenges_start ON oxygen_challenges(start_time)"
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS care_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_care_events_account_at ON care_events(account_id, at)"
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            await self._ensure_account_schema(db)
            await self._ensure_notification_backfill(db)
            await db.commit()
        self._schema_ready = True

    async def _ensure_account_schema(self, db: aiosqlite.Connection) -> None:
        await self._ensure_account_preference_schema(db)
        default_account_id = await self._legacy_default_account_id(db)
        await self._ensure_readings_account_schema(db, default_account_id)
        await self._ensure_notifications_account_schema(db, default_account_id)
        await self._ensure_challenges_account_schema(db, default_account_id)
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_readings_account_device_time_unique "
            "ON readings(account_id, device_serial, recorded_at)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_readings_account_recorded_at "
            "ON readings(account_id, recorded_at)"
        )
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_account_device_event_unique "
            "ON notifications(account_id, device_serial, recorded_at, event_type)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_account_recorded_at "
            "ON notifications(account_id, recorded_at)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_oxygen_challenges_account_start "
            "ON oxygen_challenges(account_id, start_time)"
        )

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

    async def _ensure_account_preference_schema(self, db: aiosqlite.Connection) -> None:
        columns = await self._table_columns(db, "accounts")
        if "dashboard_preferences" not in columns:
            await db.execute("ALTER TABLE accounts ADD COLUMN dashboard_preferences TEXT NOT NULL DEFAULT '{}'")
        if "user_id" not in columns:
            await db.execute("ALTER TABLE accounts ADD COLUMN user_id INTEGER")
        if "poll_interval_seconds" not in columns:
            await db.execute("ALTER TABLE accounts ADD COLUMN poll_interval_seconds INTEGER")
        if "owlet_password" not in columns:
            # Only populated in desktop mode, so a dead refresh token never
            # strands a single-user local install. Never exposed via the API.
            await db.execute("ALTER TABLE accounts ADD COLUMN owlet_password TEXT")

    async def _table_columns(self, db: aiosqlite.Connection, table: str) -> list[str]:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        return [str(row[1]) for row in rows]

    async def _table_sql(self, db: aiosqlite.Connection, table: str) -> str:
        cursor = await db.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,))
        row = await cursor.fetchone()
        return str(row[0] or "") if row else ""

    async def _ensure_readings_account_schema(self, db: aiosqlite.Connection, default_account_id: int) -> None:
        columns = await self._table_columns(db, "readings")
        table_sql = await self._table_sql(db, "readings")
        needs_rebuild = "account_id" not in columns or "UNIQUE(device_serial, recorded_at)" in table_sql
        if not needs_rebuild:
            await db.execute("UPDATE readings SET account_id = ? WHERE account_id IS NULL", (default_account_id,))
            return
        await db.execute("ALTER TABLE readings RENAME TO readings_legacy_accounts_migration")
        await db.execute(
            """
            CREATE TABLE readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                device_serial TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                heart_rate REAL,
                oxygen_saturation REAL,
                battery REAL,
                movement REAL,
                sleep_state TEXT,
                skin_temperature REAL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        legacy_columns = await self._table_columns(db, "readings_legacy_accounts_migration")
        account_expr = "account_id" if "account_id" in legacy_columns else str(default_account_id)
        await db.execute(
            f"""
            INSERT INTO readings (
                id, account_id, device_serial, recorded_at, heart_rate, oxygen_saturation,
                battery, movement, sleep_state, skin_temperature, raw_json, created_at
            )
            SELECT id, {account_expr}, device_serial, recorded_at, heart_rate, oxygen_saturation,
                   battery, movement, sleep_state, skin_temperature, raw_json, created_at
            FROM readings_legacy_accounts_migration
            """
        )
        await db.execute("DROP TABLE readings_legacy_accounts_migration")

    async def _ensure_notifications_account_schema(self, db: aiosqlite.Connection, default_account_id: int) -> None:
        columns = await self._table_columns(db, "notifications")
        if "read_at" not in columns:
            await db.execute("ALTER TABLE notifications ADD COLUMN read_at TEXT")
        table_sql = await self._table_sql(db, "notifications")
        needs_rebuild = "account_id" not in columns or "UNIQUE(device_serial, recorded_at, event_type)" in table_sql
        if not needs_rebuild:
            await db.execute("UPDATE notifications SET account_id = ? WHERE account_id IS NULL", (default_account_id,))
            return
        await db.execute("ALTER TABLE notifications RENAME TO notifications_legacy_accounts_migration")
        await db.execute(
            """
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                device_serial TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                heart_rate REAL,
                oxygen_saturation REAL,
                battery REAL,
                sleep_state TEXT,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                read_at TEXT
            )
            """
        )
        legacy_columns = await self._table_columns(db, "notifications_legacy_accounts_migration")
        account_expr = "account_id" if "account_id" in legacy_columns else str(default_account_id)
        await db.execute(
            f"""
            INSERT INTO notifications (
                id, account_id, device_serial, recorded_at, event_type, severity, title, message,
                heart_rate, oxygen_saturation, battery, sleep_state, details_json, created_at
            )
            SELECT id, {account_expr}, device_serial, recorded_at, event_type, severity, title, message,
                   heart_rate, oxygen_saturation, battery, sleep_state, details_json, created_at
            FROM notifications_legacy_accounts_migration
            """
        )
        await db.execute("DROP TABLE notifications_legacy_accounts_migration")

    async def _ensure_challenges_account_schema(self, db: aiosqlite.Connection, default_account_id: int) -> None:
        columns = await self._table_columns(db, "oxygen_challenges")
        if "account_id" in columns:
            await db.execute("UPDATE oxygen_challenges SET account_id = ? WHERE account_id IS NULL", (default_account_id,))
            return
        await db.execute("ALTER TABLE oxygen_challenges ADD COLUMN account_id INTEGER")
        await db.execute("UPDATE oxygen_challenges SET account_id = ? WHERE account_id IS NULL", (default_account_id,))

    async def list_accounts(self, user_id: int | None = None) -> list[dict[str, Any]]:
        await self.init()
        where = "WHERE user_id = ?" if user_id is not None else ""
        params: list[Any] = [user_id] if user_id is not None else []
        async with self._connect() as db:
            cursor = await db.execute(
                f"""
                SELECT id, email, region, display_name, api_token, api_token_expiry,
                       refresh_token, status, dashboard_preferences,
                       created_at, updated_at, last_validated_at, user_id, poll_interval_seconds,
                       owlet_password
                FROM accounts
                {where}
                ORDER BY id ASC
                """,
                params,
            )
            rows = await cursor.fetchall()
        return [self._row_to_account(row) for row in rows]

    async def create_account(
        self,
        *,
        email: str,
        user_id: int | None = None,
        region: str = "world",
        display_name: str | None = None,
        api_token: str | None = None,
        api_token_expiry: float | None = None,
        refresh_token: str | None = None,
        status: str = "active",
        owlet_password: str | None = None,
    ) -> dict[str, Any]:
        await self.init()
        async with self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO accounts (
                    user_id, email, region, display_name, api_token, api_token_expiry,
                    refresh_token, status, owlet_password, updated_at, last_validated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    user_id,
                    email,
                    region or "world",
                    display_name or email or "Owlet account",
                    api_token,
                    api_token_expiry,
                    refresh_token,
                    status,
                    owlet_password,
                ),
            )
            await db.commit()
            account_id = int(cursor.lastrowid)
        return await self.get_account(account_id)

    async def get_account(self, account_id: int, user_id: int | None = None) -> dict[str, Any]:
        await self.init()
        where = "WHERE id = ?"
        params: list[Any] = [account_id]
        if user_id is not None:
            where += " AND user_id = ?"
            params.append(user_id)
        async with self._connect() as db:
            cursor = await db.execute(
                f"""
                SELECT id, email, region, display_name, api_token, api_token_expiry,
                       refresh_token, status, dashboard_preferences,
                       created_at, updated_at, last_validated_at, user_id, poll_interval_seconds,
                       owlet_password
                FROM accounts
                {where}
                """,
                params,
            )
            row = await cursor.fetchone()
        if not row:
            raise KeyError(account_id)
        return self._row_to_account(row)

    async def update_account_profile(
        self,
        account_id: int,
        *,
        email: str,
        region: str = "world",
        display_name: str | None = None,
    ) -> None:
        await self.init()
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE accounts
                SET email = ?, region = ?, display_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (email, region or "world", display_name or email or "Owlet account", account_id),
            )
            await db.commit()

    async def update_account_preferences(
        self,
        account_id: int,
        *,
        display_name: str | None = None,
        dashboard_preferences: dict[str, Any] | None = None,
        poll_interval_seconds: int | None = None,
    ) -> dict[str, Any]:
        await self.init()
        current = await self.get_account(account_id)
        assignments: list[str] = []
        values: list[Any] = []
        if display_name is not None:
            cleaned = display_name.strip()
            if cleaned:
                assignments.append("display_name = ?")
                values.append(cleaned)
        if poll_interval_seconds is not None:
            assignments.append("poll_interval_seconds = ?")
            values.append(int(poll_interval_seconds))
        if dashboard_preferences is not None:
            merged_preferences = _deep_merge_preferences(
                dict(current.get("dashboard_preferences") or {}),
                dashboard_preferences,
            )
            assignments.append("dashboard_preferences = ?")
            values.append(json.dumps(merged_preferences, sort_keys=True))
        if not assignments:
            return current
        assignments.append("updated_at = CURRENT_TIMESTAMP")
        values.append(account_id)
        async with self._connect() as db:
            await db.execute(
                f"UPDATE accounts SET {', '.join(assignments)} WHERE id = ?",
                values,
            )
            await db.commit()
        return await self.get_account(account_id)

    async def update_account_tokens(
        self,
        account_id: int,
        *,
        api_token: str | None,
        api_token_expiry: float | None,
        refresh_token: str | None,
        status: str = "active",
    ) -> None:
        await self.init()
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE accounts
                SET api_token = ?, api_token_expiry = ?, refresh_token = ?, status = ?,
                    updated_at = CURRENT_TIMESTAMP, last_validated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (api_token, api_token_expiry, refresh_token, status, account_id),
            )
            await db.commit()

    async def update_account_status(self, account_id: int, status: str) -> None:
        await self.init()
        async with self._connect() as db:
            await db.execute(
                "UPDATE accounts SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, account_id),
            )
            await db.commit()

    async def insert_reading(self, reading: OwletReading, account_id: int) -> None:
        await self.init()
        if not account_id:
            raise ValueError("account_id is required")
        async with self._connect() as db:
            await db.execute(
                """
                INSERT INTO readings (
                    account_id, device_serial, recorded_at, heart_rate, oxygen_saturation, battery,
                    movement, sleep_state, skin_temperature, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, device_serial, recorded_at) DO UPDATE SET
                    heart_rate=excluded.heart_rate,
                    oxygen_saturation=excluded.oxygen_saturation,
                    battery=excluded.battery,
                    movement=excluded.movement,
                    sleep_state=excluded.sleep_state,
                    skin_temperature=excluded.skin_temperature,
                    raw_json=excluded.raw_json
                """,
                (
                    account_id,
                    reading.device_serial,
                    reading.recorded_at.isoformat(),
                    reading.heart_rate,
                    reading.oxygen_saturation,
                    reading.battery,
                    reading.movement,
                    reading.sleep_state,
                    reading.skin_temperature,
                    json.dumps(reading.raw, default=str),
                ),
            )
            await self._insert_notification_rows(db, reading, account_id=account_id)
            await db.commit()

    async def _latest_timestamp(
        self,
        device_serial: str | None = None,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> str | None:
        await self.init()
        if account_ids is not None and not account_ids:
            return None
        where_parts: list[str] = []
        params: list[Any] = []
        if account_id is not None:
            where_parts.append("account_id = ?")
            params.append(account_id)
        elif account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where_parts.append(f"account_id IN ({placeholders})")
            params.extend(account_ids)
        if device_serial:
            where_parts.append("device_serial = ?")
            params.append(device_serial)
        where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        async with self._connect() as db:
            cursor = await db.execute(f"SELECT MAX(recorded_at) FROM readings {where}", params)
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def get_readings(
        self,
        hours: int | None = 24,
        limit: int = 5000,
        device_serial: str | None = None,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> list[OwletReading]:
        await self.init()
        if account_ids is not None and not account_ids:
            return []
        latest = await self._latest_timestamp(
            device_serial=device_serial, account_id=account_id, account_ids=account_ids
        )
        where_parts: list[str] = []
        params: list[Any] = []
        if account_id is not None:
            where_parts.append("account_id = ?")
            params.append(account_id)
        elif account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where_parts.append(f"account_id IN ({placeholders})")
            params.extend(account_ids)
        if device_serial:
            where_parts.append("device_serial = ?")
            params.append(device_serial)
        if latest and hours is not None:
            latest_dt = datetime.fromisoformat(latest)
            cutoff = latest_dt - timedelta(hours=int(hours))
            where_parts.append("recorded_at >= ?")
            params.append(cutoff.isoformat())
        where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        params.append(limit)

        async with self._connect() as db:
            cursor = await db.execute(
                f"""
                SELECT device_serial, recorded_at, heart_rate, oxygen_saturation, battery,
                       movement, sleep_state, skin_temperature, raw_json
                FROM readings
                {where}
                ORDER BY recorded_at ASC
                LIMIT ?
                """,
                params,
            )
            rows = await cursor.fetchall()

        return [self._row_to_reading(row) for row in rows]

    async def get_analysis_readings(
        self,
        hours: int | None = 24,
        limit: int = 100_000,
        device_serial: str | None = None,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> list[OwletReading]:
        """Return readings for summaries without materializing large raw payloads."""

        await self.init()
        if account_ids is not None and not account_ids:
            return []
        latest = await self._latest_timestamp(
            device_serial=device_serial, account_id=account_id, account_ids=account_ids
        )
        where_parts: list[str] = []
        params: list[Any] = []
        if account_id is not None:
            where_parts.append("account_id = ?")
            params.append(account_id)
        elif account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where_parts.append(f"account_id IN ({placeholders})")
            params.extend(account_ids)
        if device_serial:
            where_parts.append("device_serial = ?")
            params.append(device_serial)
        if latest and hours is not None:
            latest_dt = datetime.fromisoformat(latest)
            cutoff = latest_dt - timedelta(hours=int(hours))
            where_parts.append("recorded_at >= ?")
            params.append(cutoff.isoformat())
        where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        params.append(limit)

        async with self._connect() as db:
            cursor = await db.execute(
                f"""
                SELECT device_serial, recorded_at, heart_rate, oxygen_saturation, battery,
                       movement, sleep_state, skin_temperature,
                       json_extract(raw_json, '$.sock_disconnected'),
                       json_extract(raw_json, '$.SOCK_DISCON_ALRT.value'),
                       json_extract(raw_json, '$.sock_off'),
                       json_extract(raw_json, '$.SOCK_OFF.value'),
                       json_extract(raw_json, '$.alerts_mask')
                FROM readings
                {where}
                ORDER BY recorded_at ASC
                LIMIT ?
                """,
                params,
            )
            rows = await cursor.fetchall()

        return [self._row_to_analysis_reading(row) for row in rows]

    async def get_summary(
        self,
        hours: int | None = 24,
        device_serial: str | None = None,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        readings = await self.get_analysis_readings(
            hours=hours, device_serial=device_serial, account_id=account_id, account_ids=account_ids
        )
        analysis_readings = await self.exclude_challenge_readings(
            readings, account_id=account_id, account_ids=account_ids
        )
        valid_readings = [reading for reading in analysis_readings if not is_offline_reading(reading)]
        first_recorded_at = readings[0].recorded_at.isoformat() if readings else None
        last_recorded_at = readings[-1].recorded_at.isoformat() if readings else None
        return {
            "hours": hours,
            "window": "all" if hours is None else f"{hours}h",
            "device_serial": device_serial,
            "account_id": account_id,
            "count": len(analysis_readings),
            "total_count": len(readings),
            "valid_count": len(valid_readings),
            "offline_count": len(analysis_readings) - len(valid_readings),
            "challenge_count": len(readings) - len(analysis_readings),
            "first_recorded_at": first_recorded_at,
            "last_recorded_at": last_recorded_at,
            "heart_rate": _metric_summary([r.heart_rate for r in valid_readings]),
            "oxygen_saturation": _metric_summary([r.oxygen_saturation for r in valid_readings]),
            "battery": _metric_summary([r.battery for r in readings]),
            "movement": _metric_summary([r.movement for r in valid_readings]),
            "skin_temperature": _metric_summary([
                r.skin_temperature if r.skin_temperature is not None and r.skin_temperature > 0 else None
                for r in valid_readings
            ]),
        }

    async def list_devices(
        self,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        await self.init()
        if account_ids is not None and not account_ids:
            return []
        where = ""
        params: list[Any] = []
        if account_id is not None:
            where = "WHERE r.account_id = ?"
            params = [account_id]
        elif account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where = f"WHERE r.account_id IN ({placeholders})"
            params = list(account_ids)
        async with self._connect() as db:
            cursor = await db.execute(
                f"""
                SELECT r.account_id, r.device_serial, COUNT(*) AS reading_count,
                       MIN(r.recorded_at), MAX(r.recorded_at), a.display_name, a.email
                FROM readings r
                JOIN accounts a ON a.id = r.account_id
                {where}
                GROUP BY r.account_id, r.device_serial
                ORDER BY MAX(r.recorded_at) DESC
                """,
                params,
            )
            rows = await cursor.fetchall()
        return [
            {
                "account_id": int(row[0]),
                "serial": row[1],
                "name": _device_display_name(row[1]),
                "baby_name": _device_baby_name(row[1]),
                "account_name": row[5],
                "account_email": row[6],
                "reading_count": int(row[2] or 0),
                "first_recorded_at": row[3],
                "last_recorded_at": row[4],
            }
            for row in rows
        ]

    async def create_oxygen_challenge(
        self,
        start_time: str | datetime,
        end_time: str | datetime | None = None,
        label: str = "Oxygen challenge",
        notes: str = "",
        account_id: int | None = None,
    ) -> dict[str, Any]:
        await self.init()
        if not account_id:
            raise ValueError("account_id is required")
        start = parse_time(start_time).isoformat()
        end = parse_time(end_time).isoformat() if end_time else None
        async with self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO oxygen_challenges (account_id, start_time, end_time, label, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (account_id, start, end, label or "Oxygen challenge", notes or ""),
            )
            await db.commit()
            challenge_id = int(cursor.lastrowid)
        return await self.get_oxygen_challenge(challenge_id)

    async def update_oxygen_challenge(
        self,
        challenge_id: int,
        *,
        start_time: str | datetime | None = None,
        end_time: str | datetime | None = None,
        label: str | None = None,
        notes: str | None = None,
        clear_end_time: bool = False,
    ) -> dict[str, Any]:
        await self.init()
        current = await self._get_oxygen_challenge_row(challenge_id)
        if not current:
            raise KeyError(challenge_id)
        start = parse_time(start_time).isoformat() if start_time else current[2]
        end = None if clear_end_time else (parse_time(end_time).isoformat() if end_time else current[3])
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE oxygen_challenges
                SET start_time = ?, end_time = ?, label = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    start,
                    end,
                    label if label is not None else current[4],
                    notes if notes is not None else current[5],
                    challenge_id,
                ),
            )
            await db.commit()
        return await self.get_oxygen_challenge(challenge_id)

    async def delete_oxygen_challenge(
        self,
        challenge_id: int,
        account_ids: list[int] | None = None,
    ) -> int:
        await self.init()
        where = "WHERE id = ?"
        params: list[Any] = [challenge_id]
        if account_ids is not None:
            if not account_ids:
                return 0
            placeholders = ",".join("?" for _ in account_ids)
            where += f" AND account_id IN ({placeholders})"
            params.extend(account_ids)
        async with self._connect() as db:
            cursor = await db.execute(f"DELETE FROM oxygen_challenges {where}", params)
            await db.commit()
            return cursor.rowcount or 0

    async def create_care_event(
        self,
        *,
        account_id: int,
        at: str | datetime,
        kind: str,
        note: str = "",
    ) -> dict[str, Any]:
        await self.init()
        moment = parse_time(at)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        async with self._connect() as db:
            cursor = await db.execute(
                "INSERT INTO care_events (account_id, at, kind, note) VALUES (?, ?, ?, ?)",
                (account_id, moment.astimezone(timezone.utc).isoformat(), kind, note or ""),
            )
            await db.commit()
            event_id = int(cursor.lastrowid)
            cursor = await db.execute(
                "SELECT id, account_id, at, kind, note, created_at FROM care_events WHERE id = ?",
                (event_id,),
            )
            row = await cursor.fetchone()
        return self._row_to_care_event(row)

    async def get_care_events(
        self,
        hours: int | None = 24,
        limit: int = 500,
        account_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        await self.init()
        if account_ids is not None and not account_ids:
            return []
        where: list[str] = []
        params: list[Any] = []
        if hours is not None:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=int(hours))).isoformat()
            where.append("at >= ?")
            params.append(cutoff)
        if account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where.append(f"account_id IN ({placeholders})")
            params.extend(account_ids)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params.append(int(limit))
        async with self._connect() as db:
            cursor = await db.execute(
                f"""
                SELECT id, account_id, at, kind, note, created_at FROM care_events
                {clause} ORDER BY at DESC LIMIT ?
                """,
                params,
            )
            rows = await cursor.fetchall()
        return [self._row_to_care_event(row) for row in rows]

    async def delete_care_event(
        self,
        event_id: int,
        account_ids: list[int] | None = None,
    ) -> int:
        await self.init()
        where = "WHERE id = ?"
        params: list[Any] = [event_id]
        if account_ids is not None:
            if not account_ids:
                return 0
            placeholders = ",".join("?" for _ in account_ids)
            where += f" AND account_id IN ({placeholders})"
            params.extend(account_ids)
        async with self._connect() as db:
            cursor = await db.execute(f"DELETE FROM care_events {where}", params)
            await db.commit()
            return cursor.rowcount or 0

    def _row_to_care_event(self, row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": int(row[0]),
            "account_id": int(row[1]),
            "at": row[2],
            "kind": row[3],
            "note": row[4],
            "created_at": row[5],
        }

    async def get_oxygen_challenges(
        self,
        hours: int | None = 24,
        limit: int = 100,
        offset: int = 0,
        device_serial: str | None = None,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        await self.init()
        if account_ids is not None and not account_ids:
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        rows, total = await self._oxygen_challenge_rows(
            hours=hours, limit=limit, offset=offset, account_id=account_id, account_ids=account_ids
        )
        analysis_hours = None if hours is None else min(24 * 365, max(int(hours) * 2, int(hours) + 24))
        readings = await self.get_analysis_readings(
            hours=analysis_hours,
            limit=100_000,
            device_serial=device_serial,
            account_id=account_id,
            account_ids=account_ids,
        )
        latest = readings[-1].recorded_at if readings else None
        items = [challenge_analysis(self._row_to_challenge(row), readings, latest) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def get_oxygen_challenge(
        self,
        challenge_id: int,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        await self.init()
        row = await self._get_oxygen_challenge_row(
            challenge_id, account_id=account_id, account_ids=account_ids
        )
        if not row:
            raise KeyError(challenge_id)
        challenge_account_id = int(row[1])
        readings = await self.get_readings(hours=None, limit=100_000, account_id=challenge_account_id)
        latest = readings[-1].recorded_at if readings else None
        payload = challenge_analysis(self._row_to_challenge(row), readings, latest)
        start = parse_time(payload["start_time"])
        end = parse_time(payload["effective_end_time"])
        duration = end - start
        prior_start = start - duration
        payload["readings"] = [
            reading.model_dump(mode="json", exclude={"raw"})
            for reading in readings
            if start <= reading.recorded_at <= end
        ]
        payload["prior_readings"] = [
            reading.model_dump(mode="json", exclude={"raw"})
            for reading in readings
            if prior_start <= reading.recorded_at <= start
        ]
        return payload

    async def exclude_challenge_readings(
        self,
        readings: list[OwletReading],
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> list[OwletReading]:
        intervals = await self.get_oxygen_challenge_intervals(
            account_id=account_id, account_ids=account_ids
        )
        if not intervals:
            return readings
        return [reading for reading in readings if not reading_in_any_period(reading, intervals)]

    async def get_oxygen_challenge_intervals(
        self,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> list[tuple[datetime, datetime]]:
        await self.init()
        if account_ids is not None and not account_ids:
            return []
        latest = await self._latest_timestamp(account_id=account_id, account_ids=account_ids)
        fallback_end = parse_time(latest) if latest else datetime.now()
        where = ""
        params: list[Any] = []
        if account_id is not None:
            where = "WHERE account_id = ?"
            params = [account_id]
        elif account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where = f"WHERE account_id IN ({placeholders})"
            params = list(account_ids)
        async with self._connect() as db:
            cursor = await db.execute(
                f"SELECT start_time, end_time FROM oxygen_challenges {where} ORDER BY start_time ASC",
                params,
            )
            rows = await cursor.fetchall()
        return [(parse_time(row[0]), parse_time(row[1]) if row[1] else fallback_end) for row in rows]

    async def _oxygen_challenge_rows(
        self,
        hours: int | None = 24,
        limit: int = 100,
        offset: int = 0,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> tuple[list[tuple[Any, ...]], int]:
        if account_ids is not None and not account_ids:
            return [], 0
        latest = await self._latest_timestamp(account_id=account_id, account_ids=account_ids)
        where_parts: list[str] = []
        params: list[Any] = []
        if account_id is not None:
            where_parts.append("account_id = ?")
            params.append(account_id)
        elif account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where_parts.append(f"account_id IN ({placeholders})")
            params.extend(account_ids)
        if latest and hours is not None:
            cutoff = parse_time(latest) - timedelta(hours=int(hours))
            where_parts.append("(end_time IS NULL OR end_time >= ?)")
            params.append(cutoff.isoformat())
        where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        async with self._connect() as db:
            count_cursor = await db.execute(f"SELECT COUNT(*) FROM oxygen_challenges {where}", params)
            count_row = await count_cursor.fetchone()
            cursor = await db.execute(
                f"""
                SELECT id, account_id, start_time, end_time, label, notes, created_at, updated_at
                FROM oxygen_challenges
                {where}
                ORDER BY start_time DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
            rows = await cursor.fetchall()
        return rows, int(count_row[0] or 0)

    async def _get_oxygen_challenge_row(
        self,
        challenge_id: int,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> tuple[Any, ...] | None:
        if account_ids is not None and not account_ids:
            return None
        where = "WHERE id = ?"
        params: list[Any] = [challenge_id]
        if account_id is not None:
            where += " AND account_id = ?"
            params.append(account_id)
        elif account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where += f" AND account_id IN ({placeholders})"
            params.extend(account_ids)
        async with self._connect() as db:
            cursor = await db.execute(
                f"""
                SELECT id, account_id, start_time, end_time, label, notes, created_at, updated_at
                FROM oxygen_challenges
                {where}
                """,
                params,
            )
            return await cursor.fetchone()

    async def get_notifications(
        self,
        hours: int | None = 24,
        limit: int = 50,
        offset: int = 0,
        device_serial: str | None = None,
        account_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        await self.init()
        if account_ids is not None and not account_ids:
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        latest = await self._latest_timestamp(
            device_serial=device_serial, account_id=account_id, account_ids=account_ids
        )
        where_parts: list[str] = []
        params: list[Any] = []
        if account_id is not None:
            where_parts.append("account_id = ?")
            params.append(account_id)
        elif account_ids is not None:
            placeholders = ",".join("?" for _ in account_ids)
            where_parts.append(f"account_id IN ({placeholders})")
            params.extend(account_ids)
        if device_serial:
            where_parts.append("device_serial = ?")
            params.append(device_serial)
        if latest and hours is not None:
            latest_dt = datetime.fromisoformat(latest)
            cutoff = latest_dt - timedelta(hours=int(hours))
            where_parts.append("recorded_at >= ?")
            params.append(cutoff.isoformat())
        where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        async with self._connect() as db:
            count_cursor = await db.execute(f"SELECT COUNT(*) FROM notifications {where}", params)
            count_row = await count_cursor.fetchone()
            total = int(count_row[0] or 0)
            unread_where = f"{where} AND read_at IS NULL" if where else "WHERE read_at IS NULL"
            unread_cursor = await db.execute(
                f"SELECT COUNT(*) FROM notifications {unread_where}", params
            )
            unread_row = await unread_cursor.fetchone()
            unread_total = int(unread_row[0] or 0)
            cursor = await db.execute(
                f"""
                SELECT device_serial, recorded_at, event_type, severity, title, message,
                       heart_rate, oxygen_saturation, battery, sleep_state, details_json,
                       id, read_at
                FROM notifications
                {where}
                ORDER BY recorded_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
            rows = await cursor.fetchall()

        items = [
            {
                **self._row_to_notification(row[:11]).model_dump(mode="json"),
                "id": int(row[11]),
                "read_at": row[12],
            }
            for row in rows
        ]
        return {
            "items": items,
            "total": total,
            "unread_total": unread_total,
            "limit": limit,
            "offset": offset,
        }

    async def mark_notifications_read(self, account_ids: list[int] | None = None) -> int:
        await self.init()
        where = "WHERE read_at IS NULL"
        params: list[Any] = []
        if account_ids is not None:
            if not account_ids:
                return 0
            placeholders = ",".join("?" for _ in account_ids)
            where += f" AND account_id IN ({placeholders})"
            params.extend(account_ids)
        async with self._connect() as db:
            cursor = await db.execute(
                f"UPDATE notifications SET read_at = CURRENT_TIMESTAMP {where}", params
            )
            await db.commit()
            return cursor.rowcount or 0

    async def _ensure_notification_backfill(self, db: aiosqlite.Connection) -> None:
        cursor = await db.execute("SELECT value FROM metadata WHERE key = 'notifications_schema_version'")
        row = await cursor.fetchone()
        if row and row[0] == "5":
            return
        await db.execute("DELETE FROM notifications")
        await self._backfill_notifications(db)
        await db.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('notifications_schema_version', '5')"
        )

    async def _backfill_notifications(self, db: aiosqlite.Connection) -> None:
        cursor = await db.execute(
            """
            SELECT account_id, device_serial, recorded_at, heart_rate, oxygen_saturation, battery,
                   movement, sleep_state, skin_temperature, raw_json
            FROM readings
            ORDER BY account_id ASC, device_serial ASC, recorded_at ASC
            """
        )
        rows = await cursor.fetchall()
        active_types_by_key: dict[tuple[int, str], set[str]] = {}
        for row in rows:
            account_id = int(row[0])
            reading = self._row_to_reading(row[1:])
            key = (account_id, reading.device_serial)
            events = extract_notifications(reading)
            current_types = {event.event_type for event in events}
            active_types = active_types_by_key.get(key, set())
            for event in events:
                if event.event_type not in active_types:
                    await self._insert_notification_event(db, event, account_id=account_id)
            active_types_by_key[key] = current_types

    async def _insert_notification_rows(
        self,
        db: aiosqlite.Connection,
        reading: OwletReading,
        *,
        account_id: int,
    ) -> None:
        current_events = extract_notifications(reading)
        if not current_events:
            return
        previous = await self._previous_reading(db, reading, account_id=account_id)
        previous_types = {event.event_type for event in extract_notifications(previous)} if previous else set()
        for event in current_events:
            if event.event_type not in previous_types:
                await self._insert_notification_event(db, event, account_id=account_id)

    async def _previous_reading(
        self,
        db: aiosqlite.Connection,
        reading: OwletReading,
        *,
        account_id: int,
    ) -> OwletReading | None:
        cursor = await db.execute(
            """
            SELECT device_serial, recorded_at, heart_rate, oxygen_saturation, battery,
                   movement, sleep_state, skin_temperature, raw_json
            FROM readings
            WHERE account_id = ? AND device_serial = ? AND recorded_at < ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (account_id, reading.device_serial, reading.recorded_at.isoformat()),
        )
        row = await cursor.fetchone()
        return self._row_to_reading(row) if row else None

    async def _insert_notification_event(
        self,
        db: aiosqlite.Connection,
        event: NotificationEvent,
        *,
        account_id: int,
    ) -> None:
        await db.execute(
            """
            INSERT INTO notifications (
                account_id, device_serial, recorded_at, event_type, severity, title, message,
                heart_rate, oxygen_saturation, battery, sleep_state, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, device_serial, recorded_at, event_type) DO UPDATE SET
                severity=excluded.severity,
                title=excluded.title,
                message=excluded.message,
                heart_rate=excluded.heart_rate,
                oxygen_saturation=excluded.oxygen_saturation,
                battery=excluded.battery,
                sleep_state=excluded.sleep_state,
                details_json=excluded.details_json
            """,
            (
                account_id,
                event.device_serial,
                event.recorded_at,
                event.event_type,
                event.severity,
                event.title,
                event.message,
                event.heart_rate,
                event.oxygen_saturation,
                event.battery,
                event.sleep_state,
                json.dumps(event.details, default=str),
            ),
        )

    def _row_to_account(self, row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": int(row[0]),
            "email": row[1],
            "region": row[2],
            "display_name": row[3],
            "api_token": row[4],
            "api_token_expiry": row[5],
            "refresh_token": row[6],
            "status": row[7],
            "dashboard_preferences": _sqlite_json_object(row[8]),
            "created_at": row[9],
            "updated_at": row[10],
            "last_validated_at": row[11],
            "user_id": int(row[12]) if len(row) > 12 and row[12] is not None else None,
            "poll_interval_seconds": int(row[13]) if len(row) > 13 and row[13] is not None else None,
            "owlet_password": row[14] if len(row) > 14 else None,
        }

    def _row_to_reading(self, row: tuple[Any, ...]) -> OwletReading:
        raw = json.loads(row[8]) if row[8] else {}
        return OwletReading(
            device_serial=row[0],
            recorded_at=row[1],
            heart_rate=row[2],
            oxygen_saturation=row[3],
            battery=row[4],
            battery_minutes=_raw_metric(raw, "battery_minutes", "btt", "BATTERY_MINUTES"),
            movement=row[5],
            sleep_state=row[6],
            sock_disconnected=raw_flag_active(raw, "sock_disconnected", "SOCK_DISCON_ALRT") or raw_alert_mask_has(raw, 16),
            sock_off=raw_flag_active(raw, "sock_off", "SOCK_OFF") or raw_alert_mask_has(raw, 64),
            skin_temperature=row[7],
            raw=raw,
        )

    def _row_to_analysis_reading(self, row: tuple[Any, ...]) -> OwletReading:
        alerts_mask = _sqlite_float(row[12])
        # model_construct skips validation: these rows were validated on insert,
        # and this path materializes ~100k rows for analytics queries.
        return OwletReading.model_construct(
            device_serial=row[0],
            recorded_at=datetime.fromisoformat(row[1]),
            heart_rate=row[2],
            oxygen_saturation=row[3],
            battery=row[4],
            movement=row[5],
            sleep_state=row[6],
            sock_disconnected=_sqlite_bool(row[8]) or _sqlite_bool(row[9]) or _mask_has(alerts_mask, 16),
            sock_off=_sqlite_bool(row[10]) or _sqlite_bool(row[11]) or _mask_has(alerts_mask, 64),
            skin_temperature=row[7],
            battery_minutes=None,
            raw={},
        )

    def _row_to_notification(self, row: tuple[Any, ...]) -> NotificationEvent:
        return NotificationEvent(
            device_serial=row[0],
            recorded_at=row[1],
            event_type=row[2],
            severity=row[3],
            title=row[4],
            message=row[5],
            heart_rate=row[6],
            oxygen_saturation=row[7],
            battery=row[8],
            sleep_state=row[9],
            details=json.loads(row[10]) if row[10] else {},
        )

    def _row_to_challenge(self, row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": row[0],
            "account_id": row[1],
            "start_time": row[2],
            "end_time": row[3],
            "label": row[4],
            "notes": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }


def _deep_merge_preferences(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_preferences(dict(merged[key]), value)
        elif value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged


def _sqlite_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value in (None, ""):
        return {}
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _sqlite_bool(value: Any) -> bool:
    if value in (None, ""):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    return str(value).strip().lower() not in {"", "0", "false", "none", "null", "off"}


def _sqlite_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mask_has(mask: float | None, bit: int) -> bool:
    return mask is not None and bool(int(mask) & bit)


def _metric_summary(values: list[float | None]) -> dict[str, float | str | None]:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return {"min": None, "max": None, "avg": None, "latest": None, "trend": "unknown"}

    avg = sum(clean) / len(clean)
    midpoint = max(1, len(clean) // 2)
    first_avg = sum(clean[:midpoint]) / len(clean[:midpoint])
    second_avg = sum(clean[midpoint:]) / len(clean[midpoint:]) if clean[midpoint:] else first_avg
    delta = second_avg - first_avg
    if abs(delta) < 0.25:
        trend = "flat"
    elif delta > 0:
        trend = "up"
    else:
        trend = "down"

    return {
        "min": min(clean),
        "max": max(clean),
        "avg": round(avg, 2),
        "latest": clean[-1],
        "trend": trend,
    }


def _device_display_name(serial: str | None) -> str:
    if not serial:
        return "Owlet sock"
    return f"Owlet sock {str(serial)[-4:]}"


def _device_baby_name(serial: str | None) -> str:
    # Owlet's raw history rows in this dataset do not carry the child profile name.
    # Keep a short stable label in the UI until a real device/baby name is available.
    return _device_display_name(serial)


def _raw_metric(raw: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, dict) and "value" in value:
            value = value.get("value")
        if isinstance(value, dict):
            continue
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


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
