# Predictive Exam-Aware Resource Manager

A lightweight Linux service that monitors processes during an exam, applies an application policy, measures memory and PSI pressure, makes explainable decisions, safely enforces selected actions, and records events for a teacher dashboard.

## Five-day MVP status

Implemented:

- Process discovery and resource snapshots with `psutil`
- JSON policy validation and allowed/blocked/unknown classification
- Detect-only mode by default
- Safe `SIGTERM` enforcement with PID creation-time validation
- Linux PSI and memory-growth monitoring
- Rule-based pressure classification
- Explainable decision engine
- SQLite event history
- Flask teacher dashboard and JSON APIs
- Automated tests

Phase-two item: cgroup throttling is represented by the decision engine but is deliberately not enforced yet.

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

