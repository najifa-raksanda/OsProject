"""Direct /proc-based system pressure metrics (CPU and I/O).

This module intentionally mirrors the parsing style already used for
memory PSI in ``memory_monitor.read_memory_psi`` so CPU/IO PSI can be
added without touching the already-tested memory sampling code path.
"""
from __future__ import annotations

from pathlib import Path


def _parse_psi_file(path: str | Path) -> dict[str, dict[str, float]]:
    psi_path = Path(path)
    if not psi_path.exists():
        return {}
    parsed: dict[str, dict[str, float]] = {}
    try:
        for line in psi_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if not parts:
                continue
            category = parts[0]
            metrics = dict(item.split("=", 1) for item in parts[1:])
            parsed[category] = {
                key: float(value) for key, value in metrics.items() if key != "total"
            }
    except (OSError, ValueError):
        return {}
    return parsed


def read_cpu_psi(path: str | Path = "/proc/pressure/cpu") -> tuple[float, float]:
    """Return (avg10, avg60) for CPU pressure's 'some' line.

    The kernel does not expose a 'full' line for CPU PSI (a thread can
    always make progress on another CPU while one is stalled), so only
    'some' is meaningful here.
    """
    values = _parse_psi_file(path)
    some = values.get("some", {})
    return some.get("avg10", 0.0), some.get("avg60", 0.0)


def read_io_psi(path: str | Path = "/proc/pressure/io") -> tuple[float, float]:
    """Return (some_avg10, full_avg10) for I/O pressure, matching the
    (some, full) tuple shape already used by memory PSI in this project."""
    values = _parse_psi_file(path)
    return values.get("some", {}).get("avg10", 0.0), values.get("full", {}).get("avg10", 0.0)