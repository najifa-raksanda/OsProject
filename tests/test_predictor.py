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

