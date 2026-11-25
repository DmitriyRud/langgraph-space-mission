import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventStore:
    """SQLite persistence for mission metadata and technical execution events (Replay & SSE reconnect)."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def startup(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS missions (
                mission_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'en',
                status TEXT NOT NULL,
                max_iterations INTEGER NOT NULL,
                parent_mission_id TEXT,
                parent_checkpoint_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS execution_events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                mission_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                node_id TEXT,
                task_id TEXT,
                iteration INTEGER,
                checkpoint_id TEXT,
                payload_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_events_mission_seq
                ON execution_events(mission_id, seq);
            """
        )
        await self._conn.commit()
        # Safe lightweight migration for existing SQLite databases created before i18n
        try:
            await self._conn.execute("ALTER TABLE missions ADD COLUMN language TEXT NOT NULL DEFAULT 'en'")
            await self._conn.commit()
        except Exception:
            pass

    async def shutdown(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def create_mission(
        self,
        *,
        mission_id: str,
        thread_id: str,
        scenario_id: str,
        mode: str,
        max_iterations: int,
        language: str = "en",
        status: str = "created",
        parent_mission_id: str | None = None,
        parent_checkpoint_id: str | None = None,
    ) -> dict[str, Any]:
        assert self._conn is not None
        now = _utc_now()
        await self._conn.execute(
            """
            INSERT INTO missions (
                mission_id, thread_id, scenario_id, mode, language, status, max_iterations,
                parent_mission_id, parent_checkpoint_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mission_id,
                thread_id,
                scenario_id,
                mode,
                language,
                status,
                max_iterations,
                parent_mission_id,
                parent_checkpoint_id,
                now,
                now,
            ),
        )
        await self._conn.commit()
        return await self.get_mission(mission_id)  # type: ignore[return-value]

    async def update_mission_status(self, mission_id: str, status: str) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "UPDATE missions SET status = ?, updated_at = ? WHERE mission_id = ?",
            (status, _utc_now(), mission_id),
        )
        await self._conn.commit()

    async def update_mission_mode(self, mission_id: str, mode: str) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "UPDATE missions SET mode = ?, updated_at = ? WHERE mission_id = ?",
            (mode, _utc_now(), mission_id),
        )
        await self._conn.commit()

    async def get_mission(self, mission_id: str) -> dict[str, Any] | None:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT * FROM missions WHERE mission_id = ?", (mission_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def list_missions(self, limit: int = 50) -> list[dict[str, Any]]:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        assert self._conn is not None
        payload_json = json.dumps(event.get("payload", {}), default=str)
        cur = await self._conn.execute(
            """
            INSERT INTO execution_events (
                event_id, mission_id, thread_id, event_type, timestamp,
                node_id, task_id, iteration, checkpoint_id, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["event_id"],
                event["mission_id"],
                event["thread_id"],
                event["event_type"],
                event["timestamp"],
                event.get("node_id"),
                event.get("task_id"),
                event.get("iteration"),
                event.get("checkpoint_id"),
                payload_json,
            ),
        )
        await self._conn.commit()
        return {**event, "seq": cur.lastrowid}

    async def list_events(
        self,
        mission_id: str,
        after_event_id: str | None = None,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        after_seq = 0
        if after_event_id:
            async with self._conn.execute(
                "SELECT seq FROM execution_events WHERE mission_id = ? AND event_id = ?",
                (mission_id, after_event_id),
            ) as cur:
                row = await cur.fetchone()
                if row:
                    after_seq = int(row["seq"])

        async with self._conn.execute(
            """
            SELECT * FROM execution_events
            WHERE mission_id = ? AND seq > ?
            ORDER BY seq ASC
            """,
            (mission_id, after_seq),
        ) as cur:
            rows = await cur.fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "seq": row["seq"],
                    "event_id": row["event_id"],
                    "mission_id": row["mission_id"],
                    "thread_id": row["thread_id"],
                    "event_type": row["event_type"],
                    "timestamp": row["timestamp"],
                    "node_id": row["node_id"],
                    "task_id": row["task_id"],
                    "iteration": row["iteration"],
                    "checkpoint_id": row["checkpoint_id"],
                    "payload": json.loads(row["payload_json"]),
                }
            )
        return result
