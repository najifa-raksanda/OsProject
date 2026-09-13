"""Direct /proc/[pid] readers for virtual-memory and scheduling metrics.

These readers deliberately bypass psutil and parse the raw kernel-exported
text files, to demonstrate genuine system-level interaction (VmRSS/VmSwap,
context-switch counters, and page-fault counters) rather than relying only
on a high-level wrapper library for everything.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ProcessDetail:
    pid: int
    vm_rss_kb: int
    vm_swap_kb: int
    voluntary_ctxt_switches: int
    nonvoluntary_ctxt_switches: int
    minor_faults: int
    major_faults: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_STATUS_FIELDS = {
    "VmRSS:": "vm_rss_kb",
    "VmSwap:": "vm_swap_kb",
    "voluntary_ctxt_switches:": "voluntary_ctxt_switches",
    "nonvoluntary_ctxt_switches:": "nonvoluntary_ctxt_switches",
}


def _read_status(pid: int) -> dict[str, int] | None:
    path = Path(f"/proc/{pid}/status")
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
        return None
    values = dict.fromkeys(_STATUS_FIELDS.values(), 0)
    for line in text.splitlines():
        for prefix, field in _STATUS_FIELDS.items():
            if line.startswith(prefix):
                digits = "".join(char for char in line if char.isdigit())
                values[field] = int(digits) if digits else 0
    return values


def _read_stat_faults(pid: int) -> tuple[int, int]:
    """Return (minor_faults, major_faults) parsed from /proc/[pid]/stat.

    Field 2 (comm) is parenthesised and may itself contain spaces or
    closing parens, so we split on the *last* ')' before re-splitting the
    remaining whitespace-separated fields. After the comm field, minflt is
    field index 7 and majflt is field index 9 (0-indexed from 'state').
    """
    path = Path(f"/proc/{pid}/stat")
    try:
        raw = path.read_text(encoding="utf-8")
        after_comm = raw.rsplit(")", 1)[-1].split()
        return int(after_comm[7]), int(after_comm[9])
    except (FileNotFoundError, PermissionError, OSError, IndexError, ValueError):
        return 0, 0


def read_process_detail(pid: int) -> ProcessDetail | None:
    """Read VM and scheduling detail for one PID directly from /proc.

    Returns None if the process no longer exists or /proc is unavailable
    (e.g. non-Linux platforms), so callers can degrade gracefully.
    """
    status = _read_status(pid)
    if status is None:
        return None
    minor_faults, major_faults = _read_stat_faults(pid)
    return ProcessDetail(
        pid=pid,
        vm_rss_kb=status["vm_rss_kb"],
        vm_swap_kb=status["vm_swap_kb"],
        voluntary_ctxt_switches=status["voluntary_ctxt_switches"],
        nonvoluntary_ctxt_switches=status["nonvoluntary_ctxt_switches"],
        minor_faults=minor_faults,
        major_faults=major_faults,
    )