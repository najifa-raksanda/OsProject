from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .action_manager import ActionManager
from .decision_engine import decide
from .event_logger import EventLogger
from .memory_monitor import MemoryMonitor
from .models import Action, Classification, PressureLevel
from .policy import Policy
from .predictor import PressurePredictor
from .process_monitor import ProcessMonitor


class ExamService:
    def __init__(self, policy_path: str | Path, database_path: str | Path) -> None:
        self.policy_path = Path(policy_path)
        self.policy = Policy.load(self.policy_path)
        self.logger = EventLogger(database_path)
        self.monitor = ProcessMonitor()
        self.memory_monitor = MemoryMonitor(self.policy.memory_cgroup)
        self.predictor = PressurePredictor(self.policy.pressure_thresholds)
        self.action_manager = ActionManager(self.policy.mode)
        self.session_id = uuid.uuid4().hex[:12]
        self._active = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._latest_processes: list[dict[str, Any]] = []
        self._latest_memory: dict[str, Any] = {}
        self._pressure = PressureLevel.NORMAL
        self._error: str | None = None

    def start(self) -> bool:
        with self._lock:
            if self._active:
                return False
            self.policy = Policy.load(self.policy_path)
            self.predictor = PressurePredictor(self.policy.pressure_thresholds)
            self.action_manager = ActionManager(self.policy.mode)
            self.memory_monitor = MemoryMonitor(self.policy.memory_cgroup)
            self.session_id = uuid.uuid4().hex[:12]
            self._active = True
            self._error = None
            self._thread = threading.Thread(target=self._run, name="exam-monitor", daemon=True)
            self._thread.start()
            return True

    def stop(self) -> bool:
        with self._lock:
            was_active = self._active
            self._active = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.policy.sample_interval_seconds + 1)
        return was_active

    def _run(self) -> None:
        while self._active:
            started = time.monotonic()
            try:
                processes = self.monitor.snapshot()
                new_processes = self.monitor.new_processes(processes)
                memory = self.memory_monitor.sample()
                pressure = self.predictor.classify(memory)

                with self._lock:
                    self._latest_processes = [item.to_dict() for item in processes]
                    self._latest_memory = memory.to_dict()
                    self._pressure = pressure

                for process in new_processes:
                    if self.monitor.is_self(process):
                        continue
                    decision = decide(process, self.policy, pressure)
                    if decision.classification is Classification.ALLOWED and decision.action is Action.ALLOW:
                        continue
                    result = self.action_manager.execute(process, decision)
                    self.logger.record(self.session_id, process, memory, decision, result)
            except Exception as exc:  # keep the monitor alive and expose the failure to the dashboard
                with self._lock:
                    self._error = f"{type(exc).__name__}: {exc}"
            elapsed = time.monotonic() - started
            time.sleep(max(0.1, self.policy.sample_interval_seconds - elapsed))

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "exam_name": self.policy.exam_name,
                "mode": self.policy.mode,
                "session_id": self.session_id,
                "pressure": self._pressure.value,
                "memory": dict(self._latest_memory),
                "process_count": len(self._latest_processes),
                "error": self._error,
            }

    def processes(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._latest_processes)
