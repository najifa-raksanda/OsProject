from pathlib import Path


def _read_psi(path: str | Path) -> dict[str, float]:
    result: dict[str, float] = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, PermissionError, OSError):
        return result
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        kind = parts[0]
        for token in parts[1:]:
            if "=" in token:
                key, value = token.split("=", 1)
                try:
                    result[f"{kind}_{key}"] = float(value)
                except ValueError:
                    pass
    return result


def read_cpu_psi(path: str | Path = "/proc/pressure/cpu") -> tuple[float, float]:
    """Read CPU PSI averages directly from the kernel PSI interface."""
    data = _read_psi(path)
    return data.get("some_avg10", 0.0), data.get("some_avg60", 0.0)


def read_io_psi(path: str | Path = "/proc/pressure/io") -> tuple[float, float]:
    """Read I/O PSI averages directly from the kernel PSI interface."""
    data = _read_psi(path)
    return data.get("some_avg10", 0.0), data.get("full_avg10", 0.0)
