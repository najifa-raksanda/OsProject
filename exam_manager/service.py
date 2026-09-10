from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Any

import psutil

from .action_manager import ActionManager
from .cgroup_manager import CgroupManager
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
        self._self_process = psutil.Process()
        self._self_process.cpu_percent(None)
        self.monitor = ProcessMonitor()
        self.cgroup_manager = self._make_cgroup_manager()
        self.memory_monitor = MemoryMonitor(self.policy.memory_cgroup or self.policy.cgroup_root)
        self.predictor = PressurePredictor(self.policy.pressure_thresholds)
        self.action_manager = ActionManager(self.policy.mode, self.cgroup_manager)
        self.session_id = uuid.uuid4().hex[:12]
        self._active = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._latest_processes: list[dict[str, Any]] = []
        self._latest_memory: dict[str, Any] = {}
        self._pressure = PressureLevel.NORMAL
        self._latest_prediction: dict[str, Any] = {}
        self._prediction_history: list[dict[str, Any]] = []
        self._baseline_ready = False
        self._last_actions: dict[tuple[int, float, str], float] = {}
        self._error: str | None = None

    def start(self) -> bool:
        with self._lock:
            if self._active:
                return False
            self.policy = Policy.load(self.policy_path)
            self.predictor = PressurePredictor(self.policy.pressure_thresholds)
            self.cgroup_manager = self._make_cgroup_manager()
            self.action_manager = ActionManager(self.policy.mode, self.cgroup_manager)
            self.memory_monitor = MemoryMonitor(self.policy.memory_cgroup or self.policy.cgroup_root)
            self.session_id = uuid.uuid4().hex[:12]
            self._latest_prediction = {}
            self._prediction_history = []
            self._baseline_ready = False
            self._last_actions = {}
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
                observed_new = self.monitor.new_processes(processes)
                new_processes = observed_new if self._baseline_ready else []
                self._baseline_ready = True
                memory = self.memory_monitor.sample()
                prediction = self.predictor.predict(memory)
                pressure = prediction.level
                prediction_data = {"timestamp": memory.timestamp, **prediction.to_dict()}

                with self._lock:
                    self._latest_processes = [item.to_dict() for item in processes]
                    self._latest_memory = memory.to_dict()
                    self._pressure = pressure
                    self._latest_prediction = prediction_data
                    self._prediction_history.append(prediction_data)
                    self._prediction_history = self._prediction_history[-60:]

                new_identities = {(item.pid, item.create_time) for item in new_processes}
                candidates = list(new_processes)
                if pressure in {PressureLevel.HIGH, PressureLevel.CRITICAL}:
                    candidates.extend(
                        item for item in processes if (item.pid, item.create_time) not in new_identities
                    )

                now = time.monotonic()
                live_identities = {(item.pid, item.create_time) for item in processes}
                self._last_actions = {
                    key: value for key, value in self._last_actions.items()
                    if (key[0], key[1]) in live_identities
                }
                for process in candidates:
                    if self.monitor.is_self(process):
                        continue
                    decision = decide(process, self.policy, pressure)
                    if decision.classification is Classification.ALLOWED and decision.action is Action.ALLOW:
                        continue
                    is_new = (process.pid, process.create_time) in new_identities
                    if not is_new and decision.action not in {Action.THROTTLE, Action.PROTECT}:
                        continue
                    action_key = (process.pid, process.create_time, decision.action.value)
                    if now - self._last_actions.get(action_key, float("-inf")) < 30:
                        continue
                    result = self.action_manager.execute(process, decision, memory)
                    detection_latency_ms = (
                        max(0.0, (time.time() - process.create_time) * 1000) if is_new else None
                    )
                    self.logger.record(
                        self.session_id, process, memory, decision, result, detection_latency_ms
                    )
                    self._last_actions[action_key] = now

                loop_duration_ms = (time.monotonic() - started) * 1000
                try:
                    monitor_cpu = self._self_process.cpu_percent(None)
                    monitor_memory = self._self_process.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    monitor_cpu = 0.0
                    monitor_memory = 0
                self.logger.record_sample(
                    self.session_id,
                    memory,
                    prediction,
                    loop_duration_ms,
                    monitor_cpu,
                    monitor_memory,
                    len(processes),
                )
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
                "prediction": dict(self._latest_prediction),
                "cgroup": self.cgroup_manager.status() if self.cgroup_manager else {"configured": False},
                "memory": dict(self._latest_memory),
                "process_count": len(self._latest_processes),
                "evaluation": self.logger.summary(self.session_id),
                "error": self._error,
            }

    def processes(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._latest_processes)

    def predictions(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(reversed(self._prediction_history))

    def samples(self, limit: int = 120) -> list[dict[str, Any]]:
        return self.logger.recent_samples(self.session_id, limit)

    def _make_cgroup_manager(self) -> CgroupManager | None:
        if not self.policy.cgroup_root:
            return None
        return CgroupManager(self.policy.cgroup_root, self.policy.resource_controls)
