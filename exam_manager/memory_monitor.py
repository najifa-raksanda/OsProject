from __future__ import annotations

import time
from pathlib import Path

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


class MemoryMonitor:
    def __init__(self) -> None:
        self._last_timestamp: float | None = None
        self._last_used_bytes: int | None = None

    def sample(self) -> MemorySnapshot:
        now = time.time()
        memory = psutil.virtual_memory()
        used = int(memory.total - memory.available)
        growth = 0.0
        if self._last_timestamp is not None and self._last_used_bytes is not None:
            elapsed = max(now - self._last_timestamp, 0.001)
            growth = (used - self._last_used_bytes) / (1024 * 1024) / elapsed
        self._last_timestamp = now
        self._last_used_bytes = used
        psi_some, psi_full = read_memory_psi()
        return MemorySnapshot(
            timestamp=now,
            total_bytes=int(memory.total),
            available_bytes=int(memory.available),
            used_percent=float(memory.percent),
            growth_mb_s=round(growth, 3),
            psi_some_avg10=psi_some,
            psi_full_avg10=psi_full,
        )

