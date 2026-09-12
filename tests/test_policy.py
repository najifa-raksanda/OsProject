import json

import pytest

from exam_manager.models import Classification
from exam_manager.policy import Policy, normalize_process_name


def write_policy(tmp_path, **overrides):
    values = {
        "exam_name": "Test",
        "mode": "detect_only",
        "allowed": ["code"],
        "blocked": ["firefox"],
        "priorities": {"code": "high"},
    } | overrides
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def test_policy_classifies_and_normalizes(tmp_path):
    policy = Policy.load(write_policy(tmp_path))
    assert policy.classify("/usr/bin/Firefox") is Classification.BLOCKED
    assert policy.classify("CODE.exe") is Classification.ALLOWED
    assert policy.classify("notes") is Classification.UNKNOWN
    assert policy.priority_for("CODE") == "high"
    assert normalize_process_name("C:/Apps/Chrome.exe") == "chrome"


def test_policy_rejects_overlap(tmp_path):
    with pytest.raises(ValueError, match="both allowed and blocked"):
        Policy.load(write_policy(tmp_path, allowed=["firefox"], blocked=["firefox"]))


def test_policy_rejects_invalid_mode(tmp_path):
    with pytest.raises(ValueError, match="mode"):
        Policy.load(write_policy(tmp_path, mode="dangerous"))


def test_policy_validates_and_loads_configured_actions(tmp_path):
    policy = Policy.load(write_policy(
        tmp_path,
        unknown_action="warn",
        blocked_action="pause",
        terminate_grace_seconds=4,
    ))

    assert policy.unknown_action == "warn"
    assert policy.blocked_action == "pause"
    assert policy.terminate_grace_seconds == 4


def test_policy_rejects_unknown_action(tmp_path):
    with pytest.raises(ValueError, match="unknown_action"):
        Policy.load(write_policy(tmp_path, unknown_action="explode"))

