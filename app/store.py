from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from app.models import OwletReading
from app.notifications import NotificationEvent, extract_notifications
from app.oxygen_challenges import challenge_analysis, parse_time, reading_in_any_period
from app.quality import is_offline_reading


class ReadingStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_serial TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    heart_rate REAL,
                    oxygen_saturation REAL,
                    battery REAL,
                    movement REAL,
                    sleep_state TEXT,
                    skin_temperature REAL,
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(device_serial, recorded_at)
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
                    UNIQUE(device_serial, recorded_at, event_type)
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
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            await self._ensure_notification_backfill(db)
            await db.commit()

    async def insert_reading(self, reading: OwletReading) -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO readings (
                    device_serial, recorded_at, heart_rate, oxygen_saturation, battery,
                    movement, sleep_state, skin_temperature, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_serial, recorded_at) DO UPDATE SET
                    heart_rate=excluded.heart_rate,
                    oxygen_saturation=excluded.oxygen_saturation,
                    battery=excluded.battery,
                    movement=excluded.movement,
                    sleep_state=excluded.sleep_state,
                    skin_temperature=excluded.skin_temperature,
                    raw_json=excluded.raw_json
                """,
                (
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
            await self._insert_notification_rows(db, reading)
            await db.commit()

    async def _latest_timestamp(self) -> str | None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT MAX(recorded_at) FROM readings")
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def get_readings(self, hours: int | None = 24, limit: int = 5000) -> list[OwletReading]:
        await self.init()
        latest = await self._latest_timestamp()
        where = ""
        params: list[Any] = []
        if latest and hours is not None:
            latest_dt = datetime.fromisoformat(latest)
            cutoff = latest_dt - timedelta(hours=int(hours))
            where = "WHERE recorded_at >= ?"
            params.append(cutoff.isoformat())
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
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

    async def get_summary(self, hours: int | None = 24) -> dict[str, Any]:
        readings = await self.get_readings(hours=hours)
        analysis_readings = await self.exclude_challenge_readings(readings)
        valid_readings = [reading for reading in analysis_readings if not is_offline_reading(reading)]
        first_recorded_at = readings[0].recorded_at.isoformat() if readings else None
        last_recorded_at = readings[-1].recorded_at.isoformat() if readings else None
        return {
            "hours": hours,
            "window": "all" if hours is None else f"{hours}h",
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
        }

    async def create_oxygen_challenge(
        self,
        start_time: str | datetime,
        end_time: str | datetime | None = None,
        label: str = "Oxygen challenge",
        notes: str = "",
    ) -> dict[str, Any]:
        await self.init()
        start = parse_time(start_time).isoformat()
        end = parse_time(end_time).isoformat() if end_time else None
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO oxygen_challenges (start_time, end_time, label, notes, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (start, end, label or "Oxygen challenge", notes or ""),
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
        start = parse_time(start_time).isoformat() if start_time else current[1]
        end = None if clear_end_time else (parse_time(end_time).isoformat() if end_time else current[2])
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE oxygen_challenges
                SET start_time = ?, end_time = ?, label = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    start,
                    end,
                    label if label is not None else current[3],
                    notes if notes is not None else current[4],
                    challenge_id,
                ),
            )
            await db.commit()
        return await self.get_oxygen_challenge(challenge_id)

    async def delete_oxygen_challenge(self, challenge_id: int) -> None:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM oxygen_challenges WHERE id = ?", (challenge_id,))
            await db.commit()

    async def get_oxygen_challenges(
        self,
        hours: int | None = 24,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        await self.init()
        rows, total = await self._oxygen_challenge_rows(hours=hours, limit=limit, offset=offset)
        readings = await self.get_readings(hours=None, limit=100_000)
        latest = readings[-1].recorded_at if readings else None
        items = [challenge_analysis(self._row_to_challenge(row), readings, latest) for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def get_oxygen_challenge(self, challenge_id: int) -> dict[str, Any]:
        await self.init()
        row = await self._get_oxygen_challenge_row(challenge_id)
        if not row:
            raise KeyError(challenge_id)
        readings = await self.get_readings(hours=None, limit=100_000)
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

    async def exclude_challenge_readings(self, readings: list[OwletReading]) -> list[OwletReading]:
        intervals = await self.get_oxygen_challenge_intervals()
        if not intervals:
            return readings
        return [reading for reading in readings if not reading_in_any_period(reading, intervals)]

    async def get_oxygen_challenge_intervals(self) -> list[tuple[datetime, datetime]]:
        await self.init()
        latest = await self._latest_timestamp()
        fallback_end = parse_time(latest) if latest else datetime.now()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT start_time, end_time FROM oxygen_challenges ORDER BY start_time ASC")
            rows = await cursor.fetchall()
        return [(parse_time(row[0]), parse_time(row[1]) if row[1] else fallback_end) for row in rows]

    async def _oxygen_challenge_rows(
        self,
        hours: int | None = 24,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[tuple[Any, ...]], int]:
        latest = await self._latest_timestamp()
        where = ""
        params: list[Any] = []
        if latest and hours is not None:
            cutoff = parse_time(latest) - timedelta(hours=int(hours))
            where = "WHERE (end_time IS NULL OR end_time >= ?)"
            params.append(cutoff.isoformat())
        async with aiosqlite.connect(self.db_path) as db:
            count_cursor = await db.execute(f"SELECT COUNT(*) FROM oxygen_challenges {where}", params)
            count_row = await count_cursor.fetchone()
            cursor = await db.execute(
                f"""
                SELECT id, start_time, end_time, label, notes, created_at, updated_at
                FROM oxygen_challenges
                {where}
                ORDER BY start_time DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
            rows = await cursor.fetchall()
        return rows, int(count_row[0] or 0)

    async def _get_oxygen_challenge_row(self, challenge_id: int) -> tuple[Any, ...] | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, start_time, end_time, label, notes, created_at, updated_at
                FROM oxygen_challenges
                WHERE id = ?
                """,
                (challenge_id,),
            )
            return await cursor.fetchone()

    async def get_notifications(
        self,
        hours: int | None = 24,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        await self.init()
        latest = await self._latest_timestamp()
        where = ""
        params: list[Any] = []
        if latest and hours is not None:
            latest_dt = datetime.fromisoformat(latest)
            cutoff = latest_dt - timedelta(hours=int(hours))
            where = "WHERE recorded_at >= ?"
            params.append(cutoff.isoformat())

        async with aiosqlite.connect(self.db_path) as db:
            count_cursor = await db.execute(f"SELECT COUNT(*) FROM notifications {where}", params)
            count_row = await count_cursor.fetchone()
            total = int(count_row[0] or 0)
            cursor = await db.execute(
                f"""
                SELECT device_serial, recorded_at, event_type, severity, title, message,
                       heart_rate, oxygen_saturation, battery, sleep_state, details_json
                FROM notifications
                {where}
                ORDER BY recorded_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
            rows = await cursor.fetchall()

        items = [self._row_to_notification(row).model_dump(mode="json") for row in rows]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def _ensure_notification_backfill(self, db: aiosqlite.Connection) -> None:
        cursor = await db.execute("SELECT value FROM metadata WHERE key = 'notifications_schema_version'")
        row = await cursor.fetchone()
        if row and row[0] == "2":
            return
        await db.execute("DELETE FROM notifications")
        await self._backfill_notifications(db)
        await db.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('notifications_schema_version', '2')"
        )

    async def _backfill_notifications(self, db: aiosqlite.Connection) -> None:
        cursor = await db.execute(
            """
            SELECT device_serial, recorded_at, heart_rate, oxygen_saturation, battery,
                   movement, sleep_state, skin_temperature, raw_json
            FROM readings
            ORDER BY recorded_at ASC
            """
        )
        rows = await cursor.fetchall()
        active_types: set[str] = set()
        for row in rows:
            reading = self._row_to_reading(row)
            events = extract_notifications(reading)
            current_types = {event.event_type for event in events}
            for event in events:
                if event.event_type not in active_types:
                    await self._insert_notification_event(db, event)
            active_types = current_types

    async def _insert_notification_rows(
        self,
        db: aiosqlite.Connection,
        reading: OwletReading,
    ) -> None:
        current_events = extract_notifications(reading)
        if not current_events:
            return
        previous = await self._previous_reading(db, reading)
        previous_types = {event.event_type for event in extract_notifications(previous)} if previous else set()
        for event in current_events:
            if event.event_type not in previous_types:
                await self._insert_notification_event(db, event)

    async def _previous_reading(
        self,
        db: aiosqlite.Connection,
        reading: OwletReading,
    ) -> OwletReading | None:
        cursor = await db.execute(
            """
            SELECT device_serial, recorded_at, heart_rate, oxygen_saturation, battery,
                   movement, sleep_state, skin_temperature, raw_json
            FROM readings
            WHERE device_serial = ? AND recorded_at < ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (reading.device_serial, reading.recorded_at.isoformat()),
        )
        row = await cursor.fetchone()
        return self._row_to_reading(row) if row else None

    async def _insert_notification_event(
        self,
        db: aiosqlite.Connection,
        event: NotificationEvent,
    ) -> None:
        await db.execute(
            """
            INSERT INTO notifications (
                device_serial, recorded_at, event_type, severity, title, message,
                heart_rate, oxygen_saturation, battery, sleep_state, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_serial, recorded_at, event_type) DO UPDATE SET
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

    def _row_to_reading(self, row: tuple[Any, ...]) -> OwletReading:
        raw = json.loads(row[8]) if row[8] else {}
        return OwletReading(
            device_serial=row[0],
            recorded_at=row[1],
            heart_rate=row[2],
            oxygen_saturation=row[3],
            battery=row[4],
            movement=row[5],
            sleep_state=row[6],
            skin_temperature=row[7],
            raw=raw,
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
            "start_time": row[1],
            "end_time": row[2],
            "label": row[3],
            "notes": row[4],
            "created_at": row[5],
            "updated_at": row[6],
        }


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
