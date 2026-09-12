from __future__ import annotations

from .models import Action, Classification, Decision, PressureLevel, ProcessSnapshot
from .policy import Policy


def decide(process: ProcessSnapshot, policy: Policy, pressure: PressureLevel) -> Decision:
    classification = policy.classify(process.name)
    priority = policy.priority_for(process.name)

    if classification is Classification.PROTECTED or priority == "critical":
        return Decision(Action.PROTECT, "Protected or critical exam workload", classification, priority, pressure)
    if classification is Classification.BLOCKED:
        action = Action(policy.blocked_action)
        return Decision(action, "Application is blocked by the exam policy", classification, priority, pressure)
    if classification is Classification.UNKNOWN:
        return Decision(
            Action(policy.unknown_action),
            "Unknown application requires teacher review",
            classification,
            priority,
            pressure,
        )
    if pressure in {PressureLevel.HIGH, PressureLevel.CRITICAL} and priority == "high":
        return Decision(Action.PROTECT, "High-priority workload protected during memory pressure", classification, priority, pressure)
    if pressure in {PressureLevel.HIGH, PressureLevel.CRITICAL} and priority == "low":
        return Decision(Action.THROTTLE, "Low-priority workload under memory pressure", classification, priority, pressure)
    return Decision(Action.ALLOW, "Application is allowed by the exam policy", classification, priority, pressure)
