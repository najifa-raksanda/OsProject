from exam_manager.cgroup_manager import CgroupManager
from exam_manager.models import Action


def fake_hierarchy_with_cpu(tmp_path):
    hierarchy = tmp_path / "cgroup"
    hierarchy.mkdir()
    (hierarchy / "cgroup.controllers").write_text("cpu io memory", encoding="utf-8")
    (hierarchy / "cgroup.subtree_control").write_text("", encoding="utf-8")
    return hierarchy


def test_apply_cpu_throttle_writes_weight_and_quota(tmp_path):
    hierarchy = fake_hierarchy_with_cpu(tmp_path)
    manager = CgroupManager(
        hierarchy / "exam",
        {"restricted_cpu_weight": 10, "restricted_cpu_max_percent": 25},
        hierarchy,
    )
    result = manager.apply_cpu(Action.THROTTLE, 4321)
    restricted = hierarchy / "exam" / "restricted"
    assert result.success
    assert (restricted / "cpu.weight").read_text(encoding="utf-8") == "10"
    assert (restricted / "cpu.max").read_text(encoding="utf-8") == "25000 100000"
    assert (restricted / "cgroup.procs").read_text(encoding="utf-8") == "4321"


def test_apply_cpu_protect_writes_weight(tmp_path):
    hierarchy = fake_hierarchy_with_cpu(tmp_path)
    manager = CgroupManager(hierarchy / "exam", {"protected_cpu_weight": 500}, hierarchy)
    result = manager.apply_cpu(Action.PROTECT, 4321)
    protected = hierarchy / "exam" / "protected"
    assert result.success
    assert (protected / "cpu.weight").read_text(encoding="utf-8") == "500"
    assert (protected / "cgroup.procs").read_text(encoding="utf-8") == "4321"


def test_apply_cpu_reports_missing_controller(tmp_path):
    hierarchy = tmp_path / "cgroup"
    hierarchy.mkdir()
    (hierarchy / "cgroup.controllers").write_text("memory", encoding="utf-8")
    (hierarchy / "cgroup.subtree_control").write_text("", encoding="utf-8")
    manager = CgroupManager(hierarchy / "exam", hierarchy_root=hierarchy)
    result = manager.apply_cpu(Action.THROTTLE, 4321)
    assert not result.success
    assert "cpu controller is unavailable" in result.message


def test_apply_cpu_refuses_critical_pid(tmp_path):
    hierarchy = fake_hierarchy_with_cpu(tmp_path)
    manager = CgroupManager(hierarchy / "exam", hierarchy_root=hierarchy)
    result = manager.apply_cpu(Action.THROTTLE, 1)
    assert not result.success