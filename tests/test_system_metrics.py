from exam_manager.system_metrics import read_cpu_psi, read_io_psi


def test_read_cpu_psi_parses_some_line(tmp_path):
    path = tmp_path / "cpu_pressure"
    path.write_text("some avg10=5.00 avg60=2.00 avg300=1.00 total=123\n", encoding="utf-8")
    assert read_cpu_psi(path) == (5.0, 2.0)


def test_read_io_psi_parses_some_and_full(tmp_path):
    path = tmp_path / "io_pressure"
    path.write_text(
        "some avg10=3.50 avg60=1.00 avg300=0.50 total=10\n"
        "full avg10=1.25 avg60=0.40 avg300=0.10 total=5\n",
        encoding="utf-8",
    )
    assert read_io_psi(path) == (3.5, 1.25)


def test_missing_file_returns_zeroes(tmp_path):
    assert read_cpu_psi(tmp_path / "missing") == (0.0, 0.0)
    assert read_io_psi(tmp_path / "missing") == (0.0, 0.0)