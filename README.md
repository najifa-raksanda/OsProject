# Predictive Exam-Aware Resource Manager

A lightweight Linux service that monitors processes during an exam, applies an application policy, measures memory and PSI pressure, makes explainable decisions, safely enforces selected actions, and records events for a teacher dashboard.

## Five-day MVP status

Implemented:

- Process discovery and resource snapshots with `psutil`
- JSON policy validation and allowed/blocked/unknown classification
- Detect-only mode by default
- Safe `SIGTERM` enforcement with PID creation-time validation
- Linux PSI, rolling memory-growth, and cgroup v2 memory monitoring
- Rule-based pressure classification
- Stateful Phase 6 prediction with sustained-sample escalation, hysteresis, risk scoring, and human-readable explanations
- Explainable decision engine
- SQLite event history
- Flask teacher dashboard and JSON APIs
- Automated tests

Phase 5 is complete: the monitor reads system memory and PSI, or—when configured—a cgroup's `memory.current`, `memory.max`, `memory.events`, and `memory.pressure`. Cgroup throttling is represented by the decision engine but is deliberately not enforced yet.

Phase 6 is complete: every memory sample receives an instantaneous classification and a stable prediction. Escalation requires consecutive dangerous samples, recovery requires consecutive healthy samples, OOM kills trigger an immediate critical state, and each result includes a 0-100 risk score and explanation. This remains an explainable rule-based predictor, not machine learning.

Phase 7 is complete in guarded form: the decision engine protects high/critical workloads during pressure and throttles low-priority workloads. The cgroup manager creates isolated `protected` and `restricted` groups, applies `memory.low`, `memory.high`, and `memory.max`, and moves only a revalidated target PID. Detect-only remains the default, so these controls are not written until enforcement is explicitly enabled.

Phase 8 is complete: each monitoring cycle is stored as an evaluation sample, including memory, PSI, prediction, loop time, monitor CPU/RAM overhead, and process count. The dashboard calculates session-specific peaks, detection latency, policy-event counts, action success rate, and pressure distribution. Event CSV, sample CSV, and JSON summary downloads provide evidence for the final report.

## Kali Linux installation

```bash
sudo apt update
sudo apt install -y python3 python3-full python3-venv python3-pip git sqlite3 stress-ng curl
git clone https://github.com/najifa-raksanda/OsProject.git
cd OsProject
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the tests:

```bash
pytest -q
```

Start the dashboard:

```bash
python run.py
```

Open <http://127.0.0.1:5000>, then click **Start Exam**.

## Safe first demonstration

The default configuration is `detect_only`; no process will be killed. To demonstrate a blocked program without using a real browser, add `python3` to the blocked list only after removing it from the allowed list, then start a separate harmless process. For a cleaner named executable, copy the interpreter and use that copy:

```bash
cp "$(command -v python3)" /tmp/exam-blocked-demo
/tmp/exam-blocked-demo tools/blocked_demo.py
```

Add `exam-blocked-demo` to `blocked` in `config/policy.json`, restart Exam Mode, and run the command again. The dashboard should show a blocked event and the detect-only action that would have occurred.

Only after the detect-only demonstration succeeds, change `"mode": "enforce"`, restart Exam Mode, and repeat using `/tmp/exam-blocked-demo`. Never test enforcement against system services, the terminal, or important applications.

## Configuration

Edit `config/policy.json`. Changes are loaded whenever Exam Mode starts. Application names are case-insensitive and `.exe` is removed during matching.

`memory_cgroup` controls the Phase 5 metric source:

- `null`: monitor whole-system RAM and `/proc/pressure/memory`.
- A cgroup v2 path such as `/sys/fs/cgroup/exam-workloads`: monitor that group's usage, limit, events, OOM kills, and pressure. If the path is missing or unreadable, the service safely falls back to system metrics and identifies the source on the dashboard.

The growth value is calculated across a rolling ten-second observation window, which is more stable than comparing only two adjacent samples.

Prediction behavior is also configured under `pressure_thresholds`:

- `escalation_samples`: dangerous samples required before raising the stable level.
- `recovery_samples`: healthier samples required before lowering the stable level by one step.

The dashboard distinguishes the raw observation from the stable prediction. This hysteresis prevents one short spike from repeatedly changing the system state.

## Phase 7 cgroup setup

Creating cgroups requires a one-time privileged setup inside the disposable Kali VM:

```bash
sudo bash tools/setup_cgroup.sh
```

Confirm the directories:

```bash
find /sys/fs/cgroup/exam-resource-manager -maxdepth 2 -type d
```

The application itself should still run as the normal user. In `detect_only` mode, it reports intended `PROTECT`, `THROTTLE`, `PAUSE`, and `TERMINATE` actions without changing a process. Use `enforce` only with the harmless demonstration workload after taking a VM snapshot.

The service establishes the first process sample as a baseline, so starting Exam Mode does not incorrectly report every existing desktop process as newly opened. When pressure becomes HIGH or CRITICAL, it re-evaluates already-running allowed workloads, applies priority decisions, and uses a 30-second per-process/action cooldown to prevent repeated intervention and duplicate logs.

### Controlled Phase 7 demonstration

Create a distinct executable name for the safe workload:

```bash
cp "$(command -v python3)" /tmp/student-memory-demo
```

Start Exam Mode in `detect_only`, then run in another terminal:

```bash
/tmp/student-memory-demo tools/memory_stress.py --total-mb 300 --step-mb 10
```

The workload is explicitly allowed but has `low` priority. Under HIGH/CRITICAL pressure, the decision engine selects THROTTLE while high-priority workloads are selected for PROTECT. Detect-only records both without writing cgroup controls.

Real cgroup movement may require elevated privileges because Linux checks permissions at the processes' common cgroup ancestor. For a controlled VM-only enforcement test, take a snapshot first, run the one-time setup script, switch the policy to `enforce`, and start the local-only service with the virtual environment's interpreter:

```bash
sudo bash tools/setup_cgroup.sh
sudo "$(pwd)/.venv/bin/python" run.py
```

Do not expose the Flask development server beyond `127.0.0.1`, and do not use enforcement against system or important desktop processes. A production design should separate privileged cgroup operations into a minimal helper instead of running the dashboard service with elevated privileges.

## Phase 8 evaluation

During an exam session, the dashboard records and displays:

- Sample and policy-event counts
- Blocked and unknown application counts
- Average process-detection latency
- Average and maximum monitoring-loop duration
- Average monitor CPU and peak monitor RAM overhead
- Peak system memory, growth, PSI, and prediction-risk score
- Stable pressure-level distribution
- Attempted actions and successful-action percentage

Use the dashboard buttons to download `events-<session>.csv`, `samples-<session>.csv`, and `report-<session>.json`. These exports contain only the current session. Follow [EVALUATION.md](EVALUATION.md) for the controlled experiments and final evidence checklist.

Resource-control policy:

- `protected_memory_low_percent`: best-effort memory protection through `memory.low`.
- `restricted_memory_high_percent`: reclaim/throttling boundary through `memory.high`.
- `restricted_memory_max_percent`: hard ceiling through `memory.max`.

Modes:

- `detect_only`: records the intended action but does not change processes.
- `enforce`: permits the action manager to signal blocked test processes.

## Architecture

```text
policy.json ───────────┐
                      v
process monitor -> decision engine -> action manager
                      ^                    |
memory + PSI ----------┘                   v
                                      SQLite logger
                                           |
                                           v
                                    Flask dashboard
```

## Important safety boundaries

- Detect-only is the default.
- PID and creation time are rechecked before sending a signal.
- PID 0, PID 1, the monitor, and its parent are protected.
- Unknown processes are logged rather than terminated.
- Cgroup intervention will be limited to a dedicated test cgroup in phase two.
- Run memory-pressure experiments inside a disposable VM snapshot.
