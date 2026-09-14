from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProcessDetail:
    vm_rss_kb: int = 0
    vm_swap_kb: int = 0
    voluntary_ctxt_switches: int = 0
    nonvoluntary_ctxt_switches: int = 0
    minor_faults: int = 0
    major_faults: int = 0

    def to_dict(self) -> dict[str, int]:
        return {"vm_rss_kb": self.vm_rss_kb, "vm_swap_kb": self.vm_swap_kb,
                "voluntary_ctxt_switches": self.voluntary_ctxt_switches,
                "nonvoluntary_ctxt_switches": self.nonvoluntary_ctxt_switches,
                "minor_faults": self.minor_faults, "major_faults": self.major_faults}


def read_process_detail(pid: int) -> ProcessDetail:
    values: dict[str, int] = {}
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            key, _, raw = line.partition(":")
            if key in {"VmRSS", "VmSwap", "voluntary_ctxt_switches", "nonvoluntary_ctxt_switches"}:
                try:
                    values[key] = int(raw.strip().split()[0])
                except (ValueError, IndexError):
                    values[key] = 0
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        # The comm field may contain spaces; split only after its closing ')'.
        remainder = stat[stat.rfind(")") + 1:].split()
        values["minor_faults"] = int(remainder[7])
        values["major_faults"] = int(remainder[9])
    except (FileNotFoundError, PermissionError, OSError, ValueError, IndexError):
        return ProcessDetail()
    return ProcessDetail(values.get("VmRSS", 0), values.get("VmSwap", 0),
                         values.get("voluntary_ctxt_switches", 0), values.get("nonvoluntary_ctxt_switches", 0),
                         values.get("minor_faults", 0), values.get("major_faults", 0))
