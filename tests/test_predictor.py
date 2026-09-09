from exam_manager.models import MemorySnapshot, PressureLevel
from exam_manager.predictor import PressurePredictor


def sample(memory=40, growth=0, psi=0):
    return MemorySnapshot(0, 100, 60, memory, growth, psi, 0)


def test_pressure_levels():
    predictor = PressurePredictor()
    assert predictor.classify(sample()) is PressureLevel.NORMAL
    assert predictor.classify(sample(memory=72)) is PressureLevel.ELEVATED
    assert predictor.classify(sample(growth=70)) is PressureLevel.HIGH
    assert predictor.classify(sample(psi=12)) is PressureLevel.CRITICAL


def test_negative_growth_does_not_raise_pressure():
    assert PressurePredictor().classify(sample(growth=-500)) is PressureLevel.NORMAL


def test_sustained_samples_are_required_to_escalate():
    predictor = PressurePredictor({"escalation_samples": 2})
    first = predictor.predict(sample(memory=85))
    second = predictor.predict(sample(memory=85))
    assert first.raw_level is PressureLevel.HIGH
    assert first.level is PressureLevel.NORMAL
    assert "Holding normal" in first.reason
    assert second.level is PressureLevel.HIGH


def test_recovery_uses_hysteresis_and_drops_one_level_at_a_time():
    predictor = PressurePredictor({"escalation_samples": 1, "recovery_samples": 2})
    assert predictor.predict(sample(memory=85)).level is PressureLevel.HIGH
    assert predictor.predict(sample()).level is PressureLevel.HIGH
    assert predictor.predict(sample()).level is PressureLevel.ELEVATED
    assert predictor.predict(sample()).level is PressureLevel.ELEVATED
    assert predictor.predict(sample()).level is PressureLevel.NORMAL


def test_oom_kill_is_immediately_critical():
    memory = MemorySnapshot(0, 100, 60, 40, 0, 0, 0, oom_kill_delta=1)
    result = PressurePredictor({"escalation_samples": 5}).predict(memory)
    assert result.level is PressureLevel.CRITICAL
    assert result.score == 100
    assert "OOM kill" in result.reason


def test_prediction_is_explainable():
    result = PressurePredictor({"escalation_samples": 1}).predict(sample(memory=75, growth=25))
    assert result.level is PressureLevel.ELEVATED
    assert result.signals
    assert 0 <= result.score <= 100
