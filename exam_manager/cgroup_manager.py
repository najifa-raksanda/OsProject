from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from .models import Action


@dataclass(frozen=True, slots=True)
class CgroupResult:
    success: bool
    message: str


class CgroupManager:
    """Guarded cgroup v2 resource controller for managed exam workloads."""

    def __init__(
        self,
        root: str | Path,
        controls: dict[str, float] | None = None,
        hierarchy_root: str | Path = "/sys/fs/cgroup",
    ) -> None:
        self.hierarchy_root = Path(os.path.realpath(hierarchy_root))
        self.root = Path(os.path.realpath(root))
        self.controls = {
            "restricted_memory_high_percent": 60.0,
            "restricted_memory_max_percent": 90.0,
            "protected_memory_low_percent": 20.0,
            "restricted_cpu_weight": 100,
            "protected_cpu_weight": 1000,
            "restricted_cpu_quota_percent": 50,
            "cpu_period_us": 100000,
        } | (controls or {})
        try:
            inside = os.path.commonpath((str(self.hierarchy_root), str(self.root))) == str(self.hierarchy_root)
        except ValueError:
            inside = False
        if self.root == self.hierarchy_root or not inside:
            raise ValueError(f"Managed cgroup must be below {self.hierarchy_root}")
        self._original_cgroups: dict[tuple[int, float], Path] = {}

    def status(self) -> dict[str, object]:
        controllers_path = self.hierarchy_root / "cgroup.controllers"
        try:
            controllers = controllers_path.read_text(encoding="utf-8").split()
        except (FileNotFoundError, PermissionError, OSError):
            controllers = []
        return {
            "configured": True,
            "root": str(self.root),
            "cgroup_v2": controllers_path.exists(),
            "memory_controller": "memory" in controllers,
            "cpu_controller": "cpu" in controllers,
            "prepared": (self.root / "restricted").is_dir() and (self.root / "protected").is_dir(),
        }

    @staticmethod
    def _write(path: Path, value: str | int) -> None:
        path.write_text(str(value), encoding="utf-8")

    def _remember_original(self, pid: int, create_time: float | None = None) -> None:
        if create_time is None:
            return
        key = (pid, create_time)
        if key in self._original_cgroups:
            return
        try:
            lines = Path(f"/proc/{pid}/cgroup").read_text(encoding="utf-8").splitlines()
            unified = next((line.split(":", 2)[2] for line in lines if line.startswith("0::")), None)
            if unified is not None:
                original = self.hierarchy_root / unified.lstrip("/")
                if original.is_dir():
                    self._original_cgroups[key] = original
        except (FileNotFoundError, PermissionError, OSError):
            return

    def restore_all(self) -> list[str]:
        restored: list[str] = []
        for (pid, create_time), original in list(self._original_cgroups.items()):
            try:
                import psutil

                process = psutil.Process(pid)
                if abs(process.create_time() - create_time) > 0.01:
                    continue
                target = original / "cgroup.procs"
                if target.exists():
                    self._write(target, pid)
                    restored.append(str(pid))
            except (FileNotFoundError, PermissionError, OSError, psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        self._original_cgroups.clear()
        return restored

    def _enable_memory(self, parent: Path) -> None:
        control = parent / "cgroup.subtree_control"
        try:
            enabled = control.read_text(encoding="utf-8").split()
        except FileNotFoundError:
            enabled = []
        if "memory" not in enabled:
            self._write(control, "+memory")

    def _enable_cpu(self, parent: Path) -> None:
        control = parent / "cgroup.subtree_control"
        try:
            enabled = control.read_text(encoding="utf-8").split()
        except (FileNotFoundError, PermissionError, OSError):
            enabled = []
        if "cpu" not in enabled:
            self._write(control, "+cpu")

    def apply_cpu(self, action: Action, pid: int, create_time: float | None = None) -> CgroupResult:
        if action not in {Action.THROTTLE, Action.PROTECT}:
            return CgroupResult(False, f"Action {action.value} is not a CPU cgroup operation")
        if pid <= 1:
            return CgroupResult(False, "Refused to move a critical PID into a managed cgroup")
        controllers_path = self.hierarchy_root / "cgroup.controllers"
        try:
            if "cpu" not in controllers_path.read_text(encoding="utf-8").split():
                return CgroupResult(False, "cgroup v2 CPU controller is unavailable")
            self._enable_cpu(self.hierarchy_root)
            self.root.mkdir(parents=False, exist_ok=True)
            self._enable_cpu(self.root)
            restricted, protected = self.root / "restricted", self.root / "protected"
            restricted.mkdir(exist_ok=True); protected.mkdir(exist_ok=True)
            target = restricted if action is Action.THROTTLE else protected
            weight = self.controls["restricted_cpu_weight"] if action is Action.THROTTLE else self.controls["protected_cpu_weight"]
            self._write(target / "cpu.weight", int(weight))
            if action is Action.THROTTLE:
                period = int(self.controls["cpu_period_us"])
                quota = int(period * self.controls["restricted_cpu_quota_percent"] / 100)
                self._write(target / "cpu.max", f"{quota} {period}")
            self._remember_original(pid, create_time)
            self._write(target / "cgroup.procs", pid)
            return CgroupResult(True, f"CPU scheduling applied: weight={int(weight)}")
        except (FileNotFoundError, PermissionError, OSError) as exc:
            return CgroupResult(False, f"CPU cgroup operation failed: {exc}")

    def prepare(self) -> None:
        controllers_path = self.hierarchy_root / "cgroup.controllers"
        if not controllers_path.exists():
            raise RuntimeError("cgroup v2 is not mounted")
        controllers = controllers_path.read_text(encoding="utf-8").split()
        if "memory" not in controllers:
            raise RuntimeError("cgroup v2 memory controller is unavailable")

        self._enable_memory(self.hierarchy_root)
        self.root.mkdir(parents=False, exist_ok=True)
        self._enable_memory(self.root)
        (self.root / "restricted").mkdir(exist_ok=True)
        (self.root / "protected").mkdir(exist_ok=True)

    def apply(
        self,
        action: Action,
        pid: int,
        effective_total_bytes: int,
        create_time: float | None = None,
    ) -> CgroupResult:
        if action not in {Action.THROTTLE, Action.PROTECT}:
            return CgroupResult(False, f"Action {action.value} is not a cgroup operation")
        if pid <= 1:
            return CgroupResult(False, "Refused to move a critical PID into a managed cgroup")
        if effective_total_bytes <= 0:
            return CgroupResult(False, "Cannot calculate cgroup limits without a memory total")

        try:
            self.prepare()
            self._remember_original(pid, create_time)
            if action is Action.THROTTLE:
                target = self.root / "restricted"
                high = int(effective_total_bytes * self.controls["restricted_memory_high_percent"] / 100)
                maximum = int(effective_total_bytes * self.controls["restricted_memory_max_percent"] / 100)
                self._write(target / "memory.high", high)
                self._write(target / "memory.max", maximum)
                self._write(target / "cgroup.procs", pid)
                return CgroupResult(True, f"PID {pid} moved to restricted cgroup; memory.high={high}")

            target = self.root / "protected"
            low = int(effective_total_bytes * self.controls["protected_memory_low_percent"] / 100)
            self._write(target / "memory.low", low)
            self._write(target / "cgroup.procs", pid)
            return CgroupResult(True, f"PID {pid} moved to protected cgroup; memory.low={low}")
        except (FileNotFoundError, PermissionError, OSError) as exc:
            return CgroupResult(False, f"Cgroup operation failed: {exc}")
