from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

import psutil

from .models import MemorySnapshot


def read_memory_psi(path: str | Path = "/proc/pressure/memory") -> tuple[float, float]:
    psi_path = Path(path)
    if not psi_path.exists():
        return 0.0, 0.0
    values: dict[str, float] = {}
    try:
        for line in psi_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            category = parts[0]
            metrics = dict(item.split("=", 1) for item in parts[1:])
            values[category] = float(metrics.get("avg10", 0))
    except (OSError, ValueError):
        return 0.0, 0.0
    return values.get("some", 0.0), values.get("full", 0.0)


def read_flat_key_values(path: str | Path) -> dict[str, int]:
    """Read Linux files such as cgroup v2 memory.events."""
    values: dict[str, int] = {}
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            key, value = line.split(maxsplit=1)
            values[key] = int(value)
    except (FileNotFoundError, PermissionError, OSError, ValueError):
        return {}
    return values


class CgroupMemoryReader:
    """Read memory controller metrics from one cgroup v2 directory."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @property
    def available(self) -> bool:
        return (self.path / "cgroup.controllers").exists() or (self.path / "memory.current").exists()

    def _read_limit(self) -> int | None:
        try:
            value = (self.path / "memory.max").read_text(encoding="utf-8").strip()
            return None if value == "max" else int(value)
        except (FileNotFoundError, PermissionError, OSError, ValueError):
            return None

    def read(self) -> dict[str, Any] | None:
        try:
            current = int((self.path / "memory.current").read_text(encoding="utf-8").strip())
        except (FileNotFoundError, PermissionError, OSError, ValueError):
            return None
        psi_some, psi_full = read_memory_psi(self.path / "memory.pressure")
        return {
            "current_bytes": current,
            "limit_bytes": self._read_limit(),
            "events": read_flat_key_values(self.path / "memory.events"),
            "psi_some_avg10": psi_some,
            "psi_full_avg10": psi_full,
        }


class MemoryMonitor:
    def __init__(
        self,
        cgroup_path: str | Path | None = None,
        trend_window_seconds: float = 10.0,
        clock: Callable[[], float] = time.time,
        virtual_memory: Callable[[], Any] = psutil.virtual_memory,
    ) -> None:
        self.cgroup = CgroupMemoryReader(cgroup_path) if cgroup_path else None
        self.trend_window_seconds = max(2.0, float(trend_window_seconds))
        self._clock = clock
        self._virtual_memory = virtual_memory
        self._history: deque[tuple[float, int]] = deque()
        self._last_events: dict[str, int] = {}

    def _growth_rate(self, timestamp: float, used_bytes: int) -> float:
        self._history.append((timestamp, used_bytes))
        cutoff = timestamp - self.trend_window_seconds
        while len(self._history) > 2 and self._history[1][0] <= cutoff:
            self._history.popleft()
        if len(self._history) < 2:
            return 0.0
        first_time, first_bytes = self._history[0]
        elapsed = max(timestamp - first_time, 0.001)
        return (used_bytes - first_bytes) / (1024 * 1024) / elapsed

    def sample(self) -> MemorySnapshot:
        now = self._clock()
        memory = self._virtual_memory()
        cgroup_data = self.cgroup.read() if self.cgroup else None

        if cgroup_data:
            current = int(cgroup_data["current_bytes"])
            limit = cgroup_data["limit_bytes"]
            effective_total = int(limit or memory.total)
            available = max(effective_total - current, 0)
            used_percent = min(100.0, current / effective_total * 100) if effective_total else 0.0
            psi_some = float(cgroup_data["psi_some_avg10"])
            psi_full = float(cgroup_data["psi_full_avg10"])
            events = dict(cgroup_data["events"])
            source = f"cgroup:{self.cgroup.path}"
            used = current
        else:
            effective_total = int(memory.total)
            available = int(memory.available)
            used = int(memory.total - memory.available)
            used_percent = float(memory.percent)
            psi_some, psi_full = read_memory_psi()
            events = {}
            limit = None
            source = "system"

        growth = self._growth_rate(now, used)
        oom_kill_delta = max(0, events.get("oom_kill", 0) - self._last_events.get("oom_kill", 0))
        self._last_events = events
        return MemorySnapshot(
            timestamp=now,
            total_bytes=effective_total,
            available_bytes=available,
            used_percent=round(used_percent, 3),
            growth_mb_s=round(growth, 3),
            psi_some_avg10=psi_some,
            psi_full_avg10=psi_full,
            source=source,
            current_bytes=used,
            limit_bytes=limit,
            events=events,
            oom_kill_delta=oom_kill_delta,
        )
