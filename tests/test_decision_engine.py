import json

from exam_manager.decision_engine import decide
from exam_manager.models import Action, PressureLevel, ProcessSnapshot
from exam_manager.policy import Policy


def process(name):
    return ProcessSnapshot(1234, name, None, 1.0, 0, 0, 0, "running")


def policy(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({
        "mode": "detect_only", "allowed": ["code", "student"], "blocked": ["firefox"],
        "protected": ["systemd"], "priorities": {"code": "high", "student": "low"}
    }), encoding="utf-8")
    return Policy.load(path)


def test_blocked_process_is_terminated(tmp_path):
    assert decide(process("firefox"), policy(tmp_path), PressureLevel.NORMAL).action is Action.TERMINATE


def test_unknown_process_is_logged(tmp_path):
    assert decide(process("mystery"), policy(tmp_path), PressureLevel.NORMAL).action is Action.LOG


def test_low_priority_allowed_process_is_throttled_under_pressure(tmp_path):
    assert decide(process("student"), policy(tmp_path), PressureLevel.HIGH).action is Action.THROTTLE


def test_high_priority_allowed_process_is_protected_under_pressure(tmp_path):
    assert decide(process("code"), policy(tmp_path), PressureLevel.HIGH).action is Action.PROTECT
