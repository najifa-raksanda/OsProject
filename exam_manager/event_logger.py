from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .action_manager import ActionResult
from .models import Decision, MemorySnapshot, PredictionResult, ProcessSnapshot


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
    detection_latency_ms REAL,
    details_json TEXT NOT NULL
)
"""

SAMPLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    memory_used_percent REAL NOT NULL,
    growth_mb_s REAL NOT NULL,
    psi_some_avg10 REAL NOT NULL,
    psi_full_avg10 REAL NOT NULL,
    stable_level TEXT NOT NULL,
    raw_level TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    loop_duration_ms REAL NOT NULL,
    monitor_cpu_percent REAL NOT NULL,
    monitor_memory_bytes INTEGER NOT NULL,
    process_count INTEGER NOT NULL
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
            connection.execute(SAMPLES_SCHEMA)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(events)")}
            if "detection_latency_ms" not in columns:
                connection.execute("ALTER TABLE events ADD COLUMN detection_latency_ms REAL")
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
        detection_latency_ms: float | None = None,
    ) -> int:
        details = {"process": process.to_dict(), "memory": memory.to_dict()}
        event_time = datetime.now(UTC)
        values = (
            event_time.isoformat(), session_id, process.pid, process.name, process.cpu_percent,
            process.memory_bytes, decision.pressure.value, decision.classification.value, decision.priority,
            decision.action.value, decision.reason, int(result.attempted), int(result.success), result.message,
            round(detection_latency_ms, 3) if detection_latency_ms is not None else None,
            json.dumps(details, sort_keys=True),
        )
        with self._lock:
            connection = self._connect()
            try:
                cursor = connection.execute(
                    """INSERT INTO events (
                        timestamp, session_id, pid, process_name, cpu_percent, memory_bytes,
                        pressure_level, classification, priority, decision, reason, attempted,
                        success, result_message, detection_latency_ms, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    values,
                )
                connection.commit()
                return int(cursor.lastrowid or 0)
            finally:
                connection.close()

    def record_sample(
        self,
        session_id: str,
        memory: MemorySnapshot,
        prediction: PredictionResult,
        loop_duration_ms: float,
        monitor_cpu_percent: float,
        monitor_memory_bytes: int,
        process_count: int,
    ) -> int:
        values = (
            datetime.now(UTC).isoformat(), session_id, memory.used_percent, memory.growth_mb_s,
            memory.psi_some_avg10, memory.psi_full_avg10, prediction.level.value,
            prediction.raw_level.value, prediction.score, round(loop_duration_ms, 3),
            round(monitor_cpu_percent, 3), monitor_memory_bytes, process_count,
        )
        with self._lock:
            connection = self._connect()
            try:
                cursor = connection.execute(
                    """INSERT INTO samples (
                        timestamp, session_id, memory_used_percent, growth_mb_s, psi_some_avg10,
                        psi_full_avg10, stable_level, raw_level, risk_score, loop_duration_ms,
                        monitor_cpu_percent, monitor_memory_bytes, process_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    values,
                )
                connection.commit()
                return int(cursor.lastrowid or 0)
            finally:
                connection.close()

    def recent(self, limit: int = 100, session_id: str | None = None) -> list[dict[str, Any]]:
        safe_limit = min(max(int(limit), 1), 500)
        with self._lock:
            connection = self._connect()
            try:
                if session_id:
                    rows = connection.execute(
                        "SELECT * FROM events WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                        (session_id, safe_limit),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        "SELECT * FROM events ORDER BY id DESC LIMIT ?", (safe_limit,)
                    ).fetchall()
            finally:
                connection.close()
        return [dict(row) for row in rows]

    def recent_samples(self, session_id: str, limit: int = 120) -> list[dict[str, Any]]:
        safe_limit = min(max(int(limit), 1), 2000)
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    "SELECT * FROM samples WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                    (session_id, safe_limit),
                ).fetchall()
            finally:
                connection.close()
        return [dict(row) for row in rows]

    def session_events(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    "SELECT * FROM events WHERE session_id = ? ORDER BY id", (session_id,)
                ).fetchall()
            finally:
                connection.close()
        return [dict(row) for row in rows]

    def summary(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            connection = self._connect()
            try:
                samples = connection.execute(
                    """SELECT COUNT(*) AS sample_count,
                              COALESCE(MAX(memory_used_percent), 0) AS peak_memory_percent,
                              COALESCE(MAX(growth_mb_s), 0) AS peak_growth_mb_s,
                              COALESCE(MAX(psi_some_avg10), 0) AS peak_psi_some,
                              COALESCE(MAX(risk_score), 0) AS peak_risk_score,
                              COALESCE(AVG(loop_duration_ms), 0) AS avg_loop_ms,
                              COALESCE(MAX(loop_duration_ms), 0) AS max_loop_ms,
                              COALESCE(AVG(monitor_cpu_percent), 0) AS avg_monitor_cpu,
                              COALESCE(MAX(monitor_memory_bytes), 0) AS peak_monitor_memory_bytes
                       FROM samples WHERE session_id = ?""",
                    (session_id,),
                ).fetchone()
                events = connection.execute(
                    """SELECT COUNT(*) AS event_count,
                              COALESCE(SUM(classification = 'blocked'), 0) AS blocked_count,
                              COALESCE(SUM(classification = 'unknown'), 0) AS unknown_count,
                              COALESCE(SUM(attempted), 0) AS attempted_count,
                              COALESCE(SUM(CASE WHEN attempted = 1 AND success = 1 THEN 1 ELSE 0 END), 0) AS successful_actions,
                              COALESCE(AVG(detection_latency_ms), 0) AS avg_detection_latency_ms
                       FROM events WHERE session_id = ?""",
                    (session_id,),
                ).fetchone()
                pressure_rows = connection.execute(
                    "SELECT stable_level, COUNT(*) AS count FROM samples WHERE session_id = ? GROUP BY stable_level",
                    (session_id,),
                ).fetchall()
            finally:
                connection.close()

        result = dict(samples or {}) | dict(events or {})
        attempted = int(result.get("attempted_count", 0))
        successful = int(result.get("successful_actions", 0))
        result["action_success_percent"] = round(successful / attempted * 100, 2) if attempted else 0.0
        result["pressure_distribution"] = {row["stable_level"]: row["count"] for row in pressure_rows}
        for key, value in list(result.items()):
            if isinstance(value, float):
                result[key] = round(value, 3)
        return result
