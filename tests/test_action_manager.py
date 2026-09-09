import subprocess
import sys

import psutil

from exam_manager.action_manager import ActionManager
from exam_manager.cgroup_manager import CgroupManager
from exam_manager.models import (
    Action,
    Classification,
    Decision,
    MemorySnapshot,
    PressureLevel,
    ProcessSnapshot,
)


def decision(action):
    return Decision(action, "test", Classification.ALLOWED, "low", PressureLevel.HIGH)


def memory():
    return MemorySnapshot(0, 1000, 500, 50, 0, 0, 0)


def test_detect_only_never_touches_process_or_cgroup():
    result = ActionManager("detect_only").execute(
        ProcessSnapshot(999999, "student", None, 1, 0, 0, 0, "running"),
        decision(Action.THROTTLE),
        memory(),
    )
    assert result.success
    assert not result.attempted
    assert result.message.startswith("Detect-only")


def test_enforcement_connects_decision_to_cgroup(tmp_path):
    hierarchy = tmp_path / "cgroup"
    hierarchy.mkdir()
    (hierarchy / "cgroup.controllers").write_text("memory", encoding="utf-8")
    (hierarchy / "cgroup.subtree_control").write_text("", encoding="utf-8")
    cgroups = CgroupManager(hierarchy / "exam", hierarchy_root=hierarchy)
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    try:
        live = psutil.Process(child.pid)
        snapshot = ProcessSnapshot(child.pid, "student", None, live.create_time(), 0, 0, 0, "running")
        result = ActionManager("enforce", cgroups).execute(snapshot, decision(Action.THROTTLE), memory())
        assert result.success
        assert result.attempted
        assert (hierarchy / "exam" / "restricted" / "cgroup.procs").read_text() == str(child.pid)
    finally:
        child.terminate()
        child.wait(timeout=5)


def test_enforcement_reports_missing_cgroup():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    try:
        live = psutil.Process(child.pid)
        snapshot = ProcessSnapshot(child.pid, "student", None, live.create_time(), 0, 0, 0, "running")
        result = ActionManager("enforce").execute(snapshot, decision(Action.THROTTLE), memory())
        assert not result.success
        assert "No managed cgroup" in result.message
    finally:
        child.terminate()
        child.wait(timeout=5)
