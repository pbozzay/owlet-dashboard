from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from app.models import OwletReading


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
        first_recorded_at = readings[0].recorded_at.isoformat() if readings else None
        last_recorded_at = readings[-1].recorded_at.isoformat() if readings else None
        return {
            "hours": hours,
            "window": "all" if hours is None else f"{hours}h",
            "count": len(readings),
            "first_recorded_at": first_recorded_at,
            "last_recorded_at": last_recorded_at,
            "heart_rate": _metric_summary([r.heart_rate for r in readings]),
            "oxygen_saturation": _metric_summary([r.oxygen_saturation for r in readings]),
            "battery": _metric_summary([r.battery for r in readings]),
            "movement": _metric_summary([r.movement for r in readings]),
        }

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
