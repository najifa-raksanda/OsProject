from exam_manager.action_manager import ActionResult
from exam_manager.event_logger import EventLogger
from exam_manager.models import (
    Action, Classification, Decision, MemorySnapshot, PredictionResult, PressureLevel, ProcessSnapshot,
)


def test_event_round_trip(tmp_path):
    logger = EventLogger(tmp_path / "events.db")
    process = ProcessSnapshot(4, "firefox", None, 1, 2, 3, 4, "running")
    memory = MemorySnapshot(1, 100, 50, 50, 0, 0, 0)
    decision = Decision(Action.TERMINATE, "blocked", Classification.BLOCKED, "low", PressureLevel.NORMAL)
    event_id = logger.record(
        "session", process, memory, decision, ActionResult(False, True, "detect-only"), 125.5
    )
    events = logger.recent()
    assert event_id == 1
    assert events[0]["process_name"] == "firefox"
    assert events[0]["decision"] == "terminate"
    assert events[0]["detection_latency_ms"] == 125.5


def test_sample_persistence_and_session_summary(tmp_path):
    logger = EventLogger(tmp_path / "events.db")
    memory = MemorySnapshot(1, 100, 20, 80, 12, 3, 1)
    prediction = PredictionResult(
        PressureLevel.HIGH, PressureLevel.HIGH, 75, 1.0, "high pressure", ("memory high",), 2
    )
    logger.record_sample("exam-1", memory, prediction, 14.5, 1.2, 20 * 1024 * 1024, 45)
    logger.record_sample("exam-1", memory, prediction, 10.5, 0.8, 22 * 1024 * 1024, 46)

    samples = logger.recent_samples("exam-1")
    summary = logger.summary("exam-1")
    assert len(samples) == 2
    assert summary["sample_count"] == 2
    assert summary["peak_memory_percent"] == 80
    assert summary["avg_loop_ms"] == 12.5
    assert summary["peak_monitor_memory_bytes"] == 22 * 1024 * 1024
    assert summary["pressure_distribution"] == {"high": 2}


def test_summary_keeps_sessions_separate(tmp_path):
    logger = EventLogger(tmp_path / "events.db")
    memory = MemorySnapshot(1, 100, 50, 50, 0, 0, 0)
    prediction = PredictionResult(
        PressureLevel.NORMAL, PressureLevel.NORMAL, 20, 1.0, "normal", ("normal",), 1
    )
    logger.record_sample("first", memory, prediction, 1, 1, 1, 1)
    logger.record_sample("second", memory, prediction, 1, 1, 1, 1)
    assert logger.summary("first")["sample_count"] == 1
    assert logger.summary("second")["sample_count"] == 1


def test_session_samples_returns_all_samples_in_chronological_order(tmp_path):
    logger = EventLogger(tmp_path / "events.db")
    memory = MemorySnapshot(1, 100, 50, 50, 0, 0, 0)
    prediction = PredictionResult(
        PressureLevel.NORMAL, PressureLevel.NORMAL, 20, 1.0, "normal", ("normal",), 1
    )
    for index in range(3):
        logger.record_sample("exam", memory, prediction, index, 0, 0, 1)

    samples = logger.session_samples("exam")
    assert len(samples) == 3
    assert [sample["loop_duration_ms"] for sample in samples] == [0.0, 1.0, 2.0]
