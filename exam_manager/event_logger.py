from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .action_manager import ActionResult
from .models import Decision, MemorySnapshot, ProcessSnapshot


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    pid INTEGER NOT NULL,
    process_name TEXT NOT NULL,
    cpu_percent REAL NOT NULL,
    memory_bytes INTEGER NOT NULL,
    pressure_level TEXT NOT NULL,
    classification TEXT NOT NULL,
    priority TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    attempted INTEGER NOT NULL,
    success INTEGER NOT NULL,
    result_message TEXT NOT NULL,
    details_json TEXT NOT NULL
)
"""


class EventLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        connection = self._connect()
        try:
            connection.execute(SCHEMA)
            connection.commit()
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def record(
        self,
        session_id: str,
        process: ProcessSnapshot,
        memory: MemorySnapshot,
        decision: Decision,
        result: ActionResult,
    ) -> int:
        details = {"process": process.to_dict(), "memory": memory.to_dict()}
        values = (
            datetime.now(UTC).isoformat(), session_id, process.pid, process.name, process.cpu_percent,
            process.memory_bytes, decision.pressure.value, decision.classification.value, decision.priority,
            decision.action.value, decision.reason, int(result.attempted), int(result.success), result.message,
            json.dumps(details, sort_keys=True),
        )
        with self._lock:
            connection = self._connect()
            try:
                cursor = connection.execute(
                    """INSERT INTO events (
                        timestamp, session_id, pid, process_name, cpu_percent, memory_bytes,
                        pressure_level, classification, priority, decision, reason, attempted,
                        success, result_message, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    values,
                )
                connection.commit()
                return int(cursor.lastrowid or 0)
            finally:
                connection.close()

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = min(max(int(limit), 1), 500)
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (safe_limit,)).fetchall()
            finally:
                connection.close()
        return [dict(row) for row in rows]
