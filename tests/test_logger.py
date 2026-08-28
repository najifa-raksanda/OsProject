from exam_manager.action_manager import ActionResult
from exam_manager.event_logger import EventLogger
from exam_manager.models import (
    Action, Classification, Decision, MemorySnapshot, PressureLevel, ProcessSnapshot,
)


def test_event_round_trip(tmp_path):
    logger = EventLogger(tmp_path / "events.db")
    process = ProcessSnapshot(4, "firefox", None, 1, 2, 3, 4, "running")
    memory = MemorySnapshot(1, 100, 50, 50, 0, 0, 0)
    decision = Decision(Action.TERMINATE, "blocked", Classification.BLOCKED, "low", PressureLevel.NORMAL)
    event_id = logger.record("session", process, memory, decision, ActionResult(False, True, "detect-only"))
    events = logger.recent()
    assert event_id == 1
    assert events[0]["process_name"] == "firefox"
    assert events[0]["decision"] == "terminate"

