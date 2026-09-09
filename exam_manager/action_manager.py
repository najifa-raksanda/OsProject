from __future__ import annotations

import os
import signal
from dataclasses import dataclass

import psutil

from .cgroup_manager import CgroupManager
from .models import Action, Decision, MemorySnapshot, ProcessSnapshot


@dataclass(frozen=True, slots=True)
class ActionResult:
    attempted: bool
    success: bool
    message: str


class ActionManager:
    def __init__(self, mode: str, cgroup_manager: CgroupManager | None = None) -> None:
        self.mode = mode
        self.cgroup_manager = cgroup_manager

    def execute(
        self,
        process: ProcessSnapshot,
        decision: Decision,
        memory: MemorySnapshot | None = None,
    ) -> ActionResult:
        if decision.action not in {Action.TERMINATE, Action.PAUSE, Action.THROTTLE, Action.PROTECT}:
            return ActionResult(False, True, "No enforcement required")
        if self.mode != "enforce":
            return ActionResult(False, True, f"Detect-only: would {decision.action.value} PID {process.pid}")
        if process.pid in {0, 1, os.getpid(), os.getppid()}:
            return ActionResult(False, False, "Safety guard refused a critical or self PID")

        try:
            live = psutil.Process(process.pid)
            if abs(live.create_time() - process.create_time) > 0.01:
                return ActionResult(False, False, "PID was reused; action cancelled")
            if decision.action is Action.TERMINATE:
                live.send_signal(signal.SIGTERM)
                return ActionResult(True, True, "SIGTERM sent")
            if decision.action is Action.PAUSE:
                live.send_signal(signal.SIGSTOP)
                return ActionResult(True, True, "SIGSTOP sent")
            if self.cgroup_manager is None:
                return ActionResult(False, False, "No managed cgroup is configured")
            if memory is None:
                return ActionResult(False, False, "No memory snapshot is available for cgroup limits")
            result = self.cgroup_manager.apply(decision.action, process.pid, memory.total_bytes)
            return ActionResult(True, result.success, result.message)
        except psutil.NoSuchProcess:
            return ActionResult(False, False, "Process exited before action")
        except (psutil.AccessDenied, PermissionError) as exc:
            return ActionResult(True, False, f"Permission denied: {exc}")
