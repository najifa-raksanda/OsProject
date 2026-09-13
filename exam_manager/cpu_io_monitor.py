"""CPU and I/O pressure sampling using Linux PSI (/proc/pressure/*).

Kept separate from MemoryMonitor so the already-tested memory sampling
path is completely untouched; this module is wired in wherever additional
resource-pressure visibility (CPU scheduling contention, I/O stalls) is
wanted, alongside the existing memory pressure signal.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from .system_metrics import read_cpu_psi, read_io_psi


@dataclass(frozen=True, slots=True)
class CpuIoSnapshot:
    timestamp: float
    cpu_psi_some_avg10: float
    cpu_psi_avg60: float
    io_psi_some_avg10: float
    io_psi_full_avg10: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CpuIoMonitor:
    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock

    def sample(self) -> CpuIoSnapshot:
        cpu_some, cpu_avg60 = read_cpu_psi()
        io_some, io_full = read_io_psi()
        return CpuIoSnapshot(
            timestamp=self._clock(),
            cpu_psi_some_avg10=cpu_some,
            cpu_psi_avg60=cpu_avg60,
            io_psi_some_avg10=io_some,
            io_psi_full_avg10=io_full,
        )