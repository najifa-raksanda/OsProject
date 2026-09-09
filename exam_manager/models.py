from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Classification(StrEnum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"
    PROTECTED = "protected"


class PressureLevel(StrEnum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class Action(StrEnum):
    ALLOW = "allow"
    LOG = "log"
    WARN = "warn"
    TERMINATE = "terminate"
    THROTTLE = "throttle"
    PROTECT = "protect"
    PAUSE = "pause"


@dataclass(frozen=True, slots=True)
class ProcessSnapshot:
    pid: int
    name: str
    executable: str | None
    create_time: float
    cpu_percent: float
    memory_bytes: int
    memory_percent: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemorySnapshot:
    timestamp: float
    total_bytes: int
    available_bytes: int
    used_percent: float
    growth_mb_s: float
    psi_some_avg10: float
    psi_full_avg10: float
    source: str = "system"
    current_bytes: int | None = None
    limit_bytes: int | None = None
    events: dict[str, int] = field(default_factory=dict)
    oom_kill_delta: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PredictionResult:
    level: PressureLevel
    raw_level: PressureLevel
    score: int
    confidence: float
    reason: str
    signals: tuple[str, ...]
    samples_at_raw_level: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["level"] = self.level.value
        data["raw_level"] = self.raw_level.value
        data["signals"] = list(self.signals)
        return data


@dataclass(frozen=True, slots=True)
class Decision:
    action: Action
    reason: str
    classification: Classification
    priority: str
    pressure: PressureLevel

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {key: value.value if isinstance(value, StrEnum) else value for key, value in data.items()}
