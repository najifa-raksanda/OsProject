import pytest

from exam_manager.cgroup_manager import CgroupManager
from exam_manager.models import Action


def fake_hierarchy(tmp_path):
    hierarchy = tmp_path / "cgroup"
    hierarchy.mkdir()
    (hierarchy / "cgroup.controllers").write_text("cpu io memory", encoding="utf-8")
    (hierarchy / "cgroup.subtree_control").write_text("", encoding="utf-8")
    return hierarchy


def test_rejects_root_outside_cgroup_hierarchy(tmp_path):
    hierarchy = fake_hierarchy(tmp_path)
    with pytest.raises(ValueError, match="must be below"):
        CgroupManager(tmp_path / "outside", hierarchy_root=hierarchy)


def test_throttle_creates_restricted_group_and_limits(tmp_path):
    hierarchy = fake_hierarchy(tmp_path)
    manager = CgroupManager(
        hierarchy / "exam",
        {"restricted_memory_high_percent": 50, "restricted_memory_max_percent": 80},
        hierarchy,
    )
    result = manager.apply(Action.THROTTLE, 4321, 1000)
    restricted = hierarchy / "exam" / "restricted"
    assert result.success
    assert (restricted / "memory.high").read_text(encoding="utf-8") == "500"
    assert (restricted / "memory.max").read_text(encoding="utf-8") == "800"
    assert (restricted / "cgroup.procs").read_text(encoding="utf-8") == "4321"


def test_protect_creates_memory_reservation(tmp_path):
    hierarchy = fake_hierarchy(tmp_path)
    manager = CgroupManager(
        hierarchy / "exam",
        {"protected_memory_low_percent": 25},
        hierarchy,
    )
    result = manager.apply(Action.PROTECT, 4321, 1000)
    protected = hierarchy / "exam" / "protected"
    assert result.success
    assert (protected / "memory.low").read_text(encoding="utf-8") == "250"
    assert manager.status()["prepared"] is True


def test_refuses_critical_pid(tmp_path):
    hierarchy = fake_hierarchy(tmp_path)
    manager = CgroupManager(hierarchy / "exam", hierarchy_root=hierarchy)
    result = manager.apply(Action.THROTTLE, 1, 1000)
    assert not result.success

