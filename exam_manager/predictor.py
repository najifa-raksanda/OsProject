from __future__ import annotations

from .models import MemorySnapshot, PressureLevel


DEFAULTS = {
    "elevated_memory_percent": 70.0,
    "high_memory_percent": 82.0,
    "critical_memory_percent": 92.0,
    "elevated_growth_mb_s": 20.0,
    "high_growth_mb_s": 60.0,
    "critical_growth_mb_s": 120.0,
    "high_psi_avg10": 2.0,
    "critical_psi_avg10": 10.0,
}


class PressurePredictor:
    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self.thresholds = DEFAULTS | (thresholds or {})

    def classify(self, sample: MemorySnapshot) -> PressureLevel:
        t = self.thresholds
        psi = max(sample.psi_some_avg10, sample.psi_full_avg10)
        growth = max(0.0, sample.growth_mb_s)

        if (
            sample.used_percent >= t["critical_memory_percent"]
            or growth >= t["critical_growth_mb_s"]
            or psi >= t["critical_psi_avg10"]
        ):
            return PressureLevel.CRITICAL
        if (
            sample.used_percent >= t["high_memory_percent"]
            or growth >= t["high_growth_mb_s"]
            or psi >= t["high_psi_avg10"]
        ):
            return PressureLevel.HIGH
        if sample.used_percent >= t["elevated_memory_percent"] or growth >= t["elevated_growth_mb_s"]:
            return PressureLevel.ELEVATED
        return PressureLevel.NORMAL

