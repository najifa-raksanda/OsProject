from exam_manager.cpu_io_monitor import CpuIoMonitor


def test_cpu_io_monitor_sample_shape():
    monitor = CpuIoMonitor(clock=lambda: 42.0)
    snapshot = monitor.sample()
    assert snapshot.timestamp == 42.0
    assert snapshot.cpu_psi_some_avg10 >= 0
    assert snapshot.io_psi_some_avg10 >= 0
    data = snapshot.to_dict()
    assert set(data) == {
        "timestamp", "cpu_psi_some_avg10", "cpu_psi_avg60",
        "io_psi_some_avg10", "io_psi_full_avg10",
    }