from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Classification


VALID_MODES = {"detect_only", "enforce"}
VALID_PRIORITIES = {"low", "normal", "high", "critical"}
VALID_POLICY_ACTIONS = {"log", "warn", "pause", "terminate"}


def normalize_process_name(name: str) -> str:
    value = Path(name.strip()).name.casefold()
    return value[:-4] if value.endswith(".exe") else value


@dataclass(frozen=True, slots=True)
class Policy:
    exam_name: str
    mode: str
    sample_interval_seconds: float
    allowed: frozenset[str]
    blocked: frozenset[str]
    priorities: dict[str, str]
    unknown_action: str
    blocked_action: str
    protected: frozenset[str]
    pressure_thresholds: dict[str, float]
    memory_cgroup: str | None
    cgroup_root: str | None
    resource_controls: dict[str, float]
    terminate_grace_seconds: float
    retention_days: int

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        policy_path = Path(path)
        try:
            raw: dict[str, Any] = json.loads(policy_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"Policy file not found: {policy_path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid policy JSON at line {exc.lineno}: {exc.msg}") from exc

        mode = str(raw.get("mode", "detect_only")).casefold()
        if mode not in VALID_MODES:
            raise ValueError("Policy mode must be 'detect_only' or 'enforce'")

        interval = float(raw.get("sample_interval_seconds", 2))
        if not 0.5 <= interval <= 60:
            raise ValueError("sample_interval_seconds must be between 0.5 and 60")

        allowed = frozenset(normalize_process_name(str(item)) for item in raw.get("allowed", []))
        blocked = frozenset(normalize_process_name(str(item)) for item in raw.get("blocked", []))
        overlap = allowed & blocked
        if overlap:
            raise ValueError(f"Applications cannot be both allowed and blocked: {sorted(overlap)}")

        priorities = {
            normalize_process_name(str(name)): str(priority).casefold()
            for name, priority in raw.get("priorities", {}).items()
        }
        invalid = {name: value for name, value in priorities.items() if value not in VALID_PRIORITIES}
        if invalid:
            raise ValueError(f"Invalid process priorities: {invalid}")

        controls = {key: float(value) for key, value in raw.get("resource_controls", {}).items()}
        for key, value in controls.items():
            if not 1 <= value <= 100:
                raise ValueError(f"Resource control percentage {key} must be between 1 and 100")

        unknown_action = str(raw.get("unknown_action", "log")).casefold()
        blocked_action = str(raw.get("blocked_action", "terminate")).casefold()
        for field_name, action in (("unknown_action", unknown_action), ("blocked_action", blocked_action)):
            if action not in VALID_POLICY_ACTIONS:
                raise ValueError(f"{field_name} must be one of {sorted(VALID_POLICY_ACTIONS)}")
        terminate_grace = float(raw.get("terminate_grace_seconds", 2.0))
        if not 0 <= terminate_grace <= 30:
            raise ValueError("terminate_grace_seconds must be between 0 and 30")
        retention_days = int(raw.get("retention_days", 30))
        if not 1 <= retention_days <= 3650:
            raise ValueError("retention_days must be between 1 and 3650")

        return cls(
            exam_name=str(raw.get("exam_name", "Exam Session")),
            mode=mode,
            sample_interval_seconds=interval,
            allowed=allowed,
            blocked=blocked,
            priorities=priorities,
            unknown_action=unknown_action,
            blocked_action=blocked_action,
            protected=frozenset(normalize_process_name(str(item)) for item in raw.get("protected", [])),
            pressure_thresholds={key: float(value) for key, value in raw.get("pressure_thresholds", {}).items()},
            memory_cgroup=str(raw["memory_cgroup"]) if raw.get("memory_cgroup") else None,
            cgroup_root=str(raw["cgroup_root"]) if raw.get("cgroup_root") else None,
            resource_controls=controls,
            terminate_grace_seconds=terminate_grace,
            retention_days=retention_days,
        )

    def classify(self, process_name: str) -> Classification:
        name = normalize_process_name(process_name)
        if name in self.protected:
            return Classification.PROTECTED
        if name in self.blocked:
            return Classification.BLOCKED
        if name in self.allowed:
            return Classification.ALLOWED
        return Classification.UNKNOWN

    def priority_for(self, process_name: str) -> str:
        return self.priorities.get(normalize_process_name(process_name), "low")
