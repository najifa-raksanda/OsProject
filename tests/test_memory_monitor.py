from types import SimpleNamespace

from exam_manager.memory_monitor import MemoryMonitor, read_flat_key_values, read_memory_psi


def write_cgroup(tmp_path, current_mb=50, oom_kill=0):
    (tmp_path / "memory.current").write_text(str(current_mb * 1024 * 1024), encoding="utf-8")
    (tmp_path / "memory.max").write_text(str(100 * 1024 * 1024), encoding="utf-8")
    (tmp_path / "memory.events").write_text(
        f"low 0\nhigh 2\nmax 0\noom 0\noom_kill {oom_kill}\n", encoding="utf-8"
    )
    (tmp_path / "memory.pressure").write_text(
        "some avg10=1.25 avg60=0.50 avg300=0.10 total=10\n"
        "full avg10=0.25 avg60=0.10 avg300=0.01 total=2\n",
        encoding="utf-8",
    )


def test_psi_and_event_parsers(tmp_path):
    write_cgroup(tmp_path)
    assert read_memory_psi(tmp_path / "memory.pressure") == (1.25, 0.25)
    assert read_flat_key_values(tmp_path / "memory.events")["high"] == 2


def test_cgroup_sample_tracks_growth_and_oom_delta(tmp_path):
    write_cgroup(tmp_path, current_mb=50)
    times = iter([100.0, 102.0])
    vm = lambda: SimpleNamespace(total=1000 * 1024 * 1024, available=500 * 1024 * 1024, percent=50)
    monitor = MemoryMonitor(tmp_path, clock=lambda: next(times), virtual_memory=vm)

    first = monitor.sample()
    assert first.source.startswith("cgroup:")
    assert first.used_percent == 50
    assert first.growth_mb_s == 0
    assert first.events["high"] == 2

    write_cgroup(tmp_path, current_mb=70, oom_kill=1)
    second = monitor.sample()
    assert second.used_percent == 70
    assert second.growth_mb_s == 10
    assert second.oom_kill_delta == 1


def test_missing_cgroup_falls_back_to_system(tmp_path):
    vm = lambda: SimpleNamespace(total=1000, available=400, percent=60)
    monitor = MemoryMonitor(tmp_path / "missing", clock=lambda: 1.0, virtual_memory=vm)
    result = monitor.sample()
    assert result.source == "system"
    assert result.current_bytes == 600
    assert result.used_percent == 60


def test_historical_oom_count_is_baselined(tmp_path):
    write_cgroup(tmp_path, oom_kill=7)
    monitor = MemoryMonitor(tmp_path, clock=lambda: 1.0)
    first = monitor.sample()
    assert first.oom_kill_delta == 0

    write_cgroup(tmp_path, oom_kill=8)
    second = monitor.sample()
    assert second.oom_kill_delta == 1


def test_source_change_resets_growth_history(tmp_path):
    write_cgroup(tmp_path, current_mb=50)
    clock_values = iter([1.0, 2.0, 3.0])
    vm = lambda: SimpleNamespace(total=1000 * 1024 * 1024, available=500 * 1024 * 1024, percent=50)
    monitor = MemoryMonitor(tmp_path, clock=lambda: next(clock_values), virtual_memory=vm)
    monitor.sample()
    write_cgroup(tmp_path, current_mb=70)
    monitor.sample()
    # Replace the cgroup reader with system metrics to simulate a source change.
    monitor.cgroup = None
    changed = monitor.sample()
    assert changed.source == "system"
    assert changed.growth_mb_s == 0

