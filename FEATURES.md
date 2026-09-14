# Project Features

## Purpose

Predictive Exam-Aware Resource Manager is a Linux service for controlled computer-based exams. It combines application policy enforcement with memory-pressure monitoring so important exam workloads can be protected while prohibited or low-priority workloads are handled safely.

## Core features

- **Exam sessions:** Start and stop a named exam session from the local teacher dashboard.
- **Policy configuration:** Configure allowed, blocked, protected, and prioritized applications in `config/policy.json`.
- **Process discovery:** Collect process name, PID, executable, creation time, CPU usage, memory usage, and status through `psutil`.
- **Blocked-application detection:** Detect blocked applications launched during an exam and detect blocked or unknown applications already present when the session starts.
- **Memory monitoring:** Read system or cgroup memory usage, rolling memory growth, memory events, and Linux PSI memory pressure.
- **CPU scheduling control:** Use cgroup v2 `cpu.weight` and `cpu.max` for best-effort throttle/protect enforcement when the host exposes the CPU controller.
- **Virtual-memory/process detail:** Read `/proc/[pid]/status` and `/proc/[pid]/stat` for RSS, swap, page faults, and voluntary/involuntary context switches at event time.
- **CPU/I/O pressure:** Sample `/proc/pressure/cpu` and `/proc/pressure/io`, persist the readings, and expose them on the live dashboard.
- **Explainable prediction:** Classify pressure as Normal, Elevated, High, or Critical with hysteresis, risk score, signals, and a human-readable explanation.
- **Priority-aware decisions:** Protect critical and high-priority exam workloads and select lower-priority workloads for resource intervention.
- **Safe operating modes:** `detect_only` records the action that would be taken; `enforce` permits configured process and cgroup actions.
- **Process actions:** Warn, log, terminate, pause, throttle, and protect are represented in the policy and decision model. Termination uses a graceful `SIGTERM` period and escalates to `SIGKILL` when required.
- **cgroups v2 controls:** Create restricted and protected groups with configurable memory limits where the Linux environment permits it.
- **Action restoration:** Best-effort restoration returns moved processes to their original cgroup when an exam stops.
- **SQLite audit history:** Store policy events, prediction samples, action outcomes, latency, service overhead, and session metrics.
- **Teacher dashboard:** Display session state, process inventory, memory and PSI signals, predictions, cgroup readiness, events, and evaluation metrics.
- **Evidence exports:** Download event CSV, sample CSV, and JSON session reports for evaluation.
- **Automated tests:** Unit tests cover policy parsing, prediction, decisions, memory monitoring, cgroup operations, logging, and web routes.

## High-level workflow

```text
Load policy
    -> sample processes and memory
    -> classify applications and pressure
    -> choose a policy-aware action
    -> apply or simulate the action
    -> record the evidence
    -> show the result on the dashboard
```

## Safety defaults

- `detect_only` is the default mode.
- PID creation time is rechecked before enforcement.
- PID 0, PID 1, the monitor, and its parent are protected.
- Critical workloads are protected from destructive actions.
- cgroup roots must resolve below the cgroup v2 hierarchy root.
- Enforcement should only be tested with harmless processes in a disposable Linux VM.
