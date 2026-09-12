from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass

import psutil

from .cgroup_manager import CgroupManager
from .models import Action, Decision, MemorySnapshot, ProcessSnapshot


@dataclass(frozen=True, slots=True)
class ActionResult:
    attempted: bool
    success: bool
    message: str
    duration_ms: float = 0.0


class ActionManager:
    def __init__(
        self,
        mode: str,
        cgroup_manager: CgroupManager | None = None,
        terminate_grace_seconds: float = 2.0,
    ) -> None:
        self.mode = mode
        self.cgroup_manager = cgroup_manager
        self.terminate_grace_seconds = max(0.0, min(30.0, float(terminate_grace_seconds)))

    def execute(
        self,
        process: ProcessSnapshot,
        decision: Decision,
        memory: MemorySnapshot | None = None,
    ) -> ActionResult:
        started = time.monotonic()

        def result(attempted: bool, success: bool, message: str) -> ActionResult:
            return ActionResult(attempted, success, message, (time.monotonic() - started) * 1000)

        if decision.action not in {Action.TERMINATE, Action.PAUSE, Action.THROTTLE, Action.PROTECT}:
            return result(False, True, "No enforcement required")
        if self.mode != "enforce":
            return result(False, True, f"Detect-only: would {decision.action.value} PID {process.pid}")
        if process.pid in {0, 1, os.getpid(), os.getppid()}:
            return result(False, False, "Safety guard refused a critical or self PID")

        try:
            live = psutil.Process(process.pid)
            if abs(live.create_time() - process.create_time) > 0.01:
                return result(False, False, "PID was reused; action cancelled")
            if decision.action is Action.TERMINATE:
                live.send_signal(signal.SIGTERM)
                deadline = time.monotonic() + self.terminate_grace_seconds
                while time.monotonic() < deadline:
                    if not live.is_running():
                        return result(True, True, "SIGTERM sent; process exited")
                    time.sleep(0.05)
                if live.is_running():
                    live.send_signal(signal.SIGKILL)
                    try:
                        live.wait(timeout=2)
                    except psutil.TimeoutExpired:
                        return result(True, False, "SIGKILL sent; process did not exit")
                    return result(True, True, "SIGTERM timed out; SIGKILL sent; process exited")
                return result(True, True, "SIGTERM sent; process exited")
            if decision.action is Action.PAUSE:
                live.send_signal(signal.SIGSTOP)
                return result(True, True, "SIGSTOP sent")
            if self.cgroup_manager is None:
                return result(False, False, "No managed cgroup is configured")
            if memory is None:
                return result(False, False, "No memory snapshot is available for cgroup limits")
            result = self.cgroup_manager.apply(
                decision.action,
                process.pid,
                memory.total_bytes,
                process.create_time,
            )
            return ActionResult(True, result.success, result.message, (time.monotonic() - started) * 1000)
        except psutil.NoSuchProcess:
            return result(False, False, "Process exited before action")
        except (psutil.AccessDenied, PermissionError) as exc:
            return result(True, False, f"Permission denied: {exc}")
