from dataclasses import dataclass, asdict
import time
from .system_metrics import read_cpu_psi, read_io_psi


@dataclass(frozen=True, slots=True)
class CpuIoSnapshot:
    timestamp: float
    cpu_psi_some_avg10: float = 0.0
    cpu_psi_some_avg60: float = 0.0
    io_psi_some_avg10: float = 0.0
    io_psi_full_avg10: float = 0.0

    def to_dict(self):
        return asdict(self)


class CpuIoMonitor:
    def sample(self) -> CpuIoSnapshot:
        cpu_some10, cpu_some60 = read_cpu_psi()
        io_some10, io_full10 = read_io_psi()
        return CpuIoSnapshot(time.time(), cpu_some10, cpu_some60, io_some10, io_full10)
