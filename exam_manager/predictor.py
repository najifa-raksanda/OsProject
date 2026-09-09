from __future__ import annotations

from .models import MemorySnapshot, PredictionResult, PressureLevel


DEFAULTS = {
    "elevated_memory_percent": 70.0,
    "high_memory_percent": 82.0,
    "critical_memory_percent": 92.0,
    "elevated_growth_mb_s": 20.0,
    "high_growth_mb_s": 60.0,
    "critical_growth_mb_s": 120.0,
    "high_psi_avg10": 2.0,
    "critical_psi_avg10": 10.0,
    "escalation_samples": 2.0,
    "recovery_samples": 3.0,
}


SEVERITY = {
    PressureLevel.NORMAL: 0,
    PressureLevel.ELEVATED: 1,
    PressureLevel.HIGH: 2,
    PressureLevel.CRITICAL: 3,
}
BY_SEVERITY = {value: key for key, value in SEVERITY.items()}


class PressurePredictor:
    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self.thresholds = DEFAULTS | (thresholds or {})
        self.level = PressureLevel.NORMAL
        self._candidate = PressureLevel.NORMAL
        self._candidate_count = 0
        self._recovery_count = 0

    def _raw_classification(self, sample: MemorySnapshot) -> PressureLevel:
        """Classify one measurement without temporal smoothing."""
        t = self.thresholds
        psi = max(sample.psi_some_avg10, sample.psi_full_avg10)
        growth = max(0.0, sample.growth_mb_s)

        if sample.oom_kill_delta > 0 or (
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

    def _signals(self, sample: MemorySnapshot) -> tuple[str, ...]:
        t = self.thresholds
        psi = max(sample.psi_some_avg10, sample.psi_full_avg10)
        signals: list[str] = []
        if sample.oom_kill_delta:
            signals.append(f"{sample.oom_kill_delta} new OOM kill event(s)")
        if sample.used_percent >= t["critical_memory_percent"]:
            signals.append(f"memory {sample.used_percent:.1f}% is critical")
        elif sample.used_percent >= t["high_memory_percent"]:
            signals.append(f"memory {sample.used_percent:.1f}% is high")
        elif sample.used_percent >= t["elevated_memory_percent"]:
            signals.append(f"memory {sample.used_percent:.1f}% is elevated")
        if sample.growth_mb_s >= t["critical_growth_mb_s"]:
            signals.append(f"growth {sample.growth_mb_s:.1f} MB/s is critical")
        elif sample.growth_mb_s >= t["high_growth_mb_s"]:
            signals.append(f"growth {sample.growth_mb_s:.1f} MB/s is high")
        elif sample.growth_mb_s >= t["elevated_growth_mb_s"]:
            signals.append(f"growth {sample.growth_mb_s:.1f} MB/s is elevated")
        if psi >= t["critical_psi_avg10"]:
            signals.append(f"PSI avg10 {psi:.2f}% is critical")
        elif psi >= t["high_psi_avg10"]:
            signals.append(f"PSI avg10 {psi:.2f}% is high")
        return tuple(signals) or ("memory, growth, and PSI are below warning thresholds",)

    def _score(self, sample: MemorySnapshot) -> int:
        """Return an explainable 0-100 risk score; level decisions still use thresholds."""
        t = self.thresholds
        psi = max(sample.psi_some_avg10, sample.psi_full_avg10)
        memory_ratio = sample.used_percent / max(t["critical_memory_percent"], 1)
        growth_ratio = max(0.0, sample.growth_mb_s) / max(t["critical_growth_mb_s"], 1)
        psi_ratio = psi / max(t["critical_psi_avg10"], 0.01)
        score = 45 * min(memory_ratio, 1.25) + 30 * min(growth_ratio, 1.25) + 25 * min(psi_ratio, 1.25)
        if sample.oom_kill_delta:
            score = 100
        return min(100, max(0, round(score)))

    def predict(self, sample: MemorySnapshot) -> PredictionResult:
        raw = self._raw_classification(sample)
        escalation_samples = max(1, int(self.thresholds["escalation_samples"]))
        recovery_samples = max(1, int(self.thresholds["recovery_samples"]))

        if raw == self._candidate:
            self._candidate_count += 1
        else:
            self._candidate = raw
            self._candidate_count = 1

        if SEVERITY[raw] > SEVERITY[self.level]:
            self._recovery_count = 0
            immediate_critical = raw is PressureLevel.CRITICAL and sample.oom_kill_delta > 0
            if immediate_critical or self._candidate_count >= escalation_samples:
                self.level = raw
        elif SEVERITY[raw] < SEVERITY[self.level]:
            self._recovery_count += 1
            if self._recovery_count >= recovery_samples:
                self.level = BY_SEVERITY[max(SEVERITY[self.level] - 1, SEVERITY[raw])]
                self._recovery_count = 0
        else:
            self._recovery_count = 0

        if raw == self.level:
            confidence = 1.0
        else:
            confidence_target = escalation_samples if SEVERITY[raw] > SEVERITY[self.level] else recovery_samples
            confidence = min(1.0, self._candidate_count / max(confidence_target, 1))
        signals = self._signals(sample)
        if self.level == raw:
            reason = f"Stable {self.level.value}: " + "; ".join(signals)
        else:
            reason = (
                f"Holding {self.level.value}; observed {raw.value} for "
                f"{self._candidate_count} sample(s): " + "; ".join(signals)
            )
        return PredictionResult(
            level=self.level,
            raw_level=raw,
            score=self._score(sample),
            confidence=round(confidence, 2),
            reason=reason,
            signals=signals,
            samples_at_raw_level=self._candidate_count,
        )

    def classify(self, sample: MemorySnapshot) -> PressureLevel:
        """Backward-compatible instantaneous classification for callers and tests."""
        return self._raw_classification(sample)
