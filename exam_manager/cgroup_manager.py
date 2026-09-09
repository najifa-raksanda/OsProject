from __future__ import annotations

from dataclasses import dataclass
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
        self.hierarchy_root = Path(hierarchy_root).resolve()
        self.root = Path(root).resolve()
        self.controls = {
            "restricted_memory_high_percent": 60.0,
            "restricted_memory_max_percent": 90.0,
            "protected_memory_low_percent": 20.0,
        } | (controls or {})
        if self.root == self.hierarchy_root or not self.root.is_relative_to(self.hierarchy_root):
            raise ValueError(f"Managed cgroup must be below {self.hierarchy_root}")

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
            "prepared": (self.root / "restricted").is_dir() and (self.root / "protected").is_dir(),
        }

    @staticmethod
    def _write(path: Path, value: str | int) -> None:
        path.write_text(str(value), encoding="utf-8")

    def _enable_memory(self, parent: Path) -> None:
        control = parent / "cgroup.subtree_control"
        try:
            enabled = control.read_text(encoding="utf-8").split()
        except FileNotFoundError:
            enabled = []
        if "memory" not in enabled:
            self._write(control, "+memory")

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

    def apply(self, action: Action, pid: int, effective_total_bytes: int) -> CgroupResult:
        if action not in {Action.THROTTLE, Action.PROTECT}:
            return CgroupResult(False, f"Action {action.value} is not a cgroup operation")
        if pid <= 1:
            return CgroupResult(False, "Refused to move a critical PID into a managed cgroup")
        if effective_total_bytes <= 0:
            return CgroupResult(False, "Cannot calculate cgroup limits without a memory total")

        try:
            self.prepare()
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
