# Phase 8 Evaluation Guide

Use a VirtualBox snapshot and keep `mode` set to `detect_only` for the first four experiments. Run one fresh exam session per experiment and download all three exports before stopping the session.

## Metrics and meanings

| Metric | Meaning | Desired result |
|---|---|---|
| Detection latency | Time between process creation and recorded policy event | Near or below the 2-second sampling interval |
| Average loop time | Time required to collect, decide, act, and record one sample | Clearly below the sampling interval |
| Monitor CPU | CPU used by this service | Low and stable during a normal exam |
| Peak monitor RAM | Maximum resident memory used by the service | Small compared with VM RAM |
| Blocked count | Blocked process detections | Matches the controlled launches |
| Action success | Successful attempted actions divided by attempts | Evaluate only in the isolated enforcement test |
| Pressure distribution | Samples classified at each stable level | Mostly Normal in baseline; higher levels during stress |
| Peak risk | Highest explainable 0-100 prediction score | Increases during memory stress |

## Experiment 1: Normal exam baseline

1. Start Exam Mode.
2. Use the terminal, editor, and compiler normally for five minutes.
3. Do not run a stress workload.
4. Confirm there are no blocked violations or unnecessary actions.
5. Download the exports and label them `normal`.

Expected: primarily Normal pressure, low overhead, and no intervention.

## Experiment 2: Unauthorized application

1. Start a fresh Exam Mode session.
2. Launch Firefox once.
3. Wait five seconds, then close Firefox.
4. Confirm `blocked`, `terminate`, and `Detect-only` appear in the event table.
5. Record the detection latency and download the exports.

Expected: one blocked-process event and no actual termination in detect-only mode.

## Experiment 3: Controlled memory growth

From a second terminal in the project directory:

```bash
cp "$(command -v python3)" /tmp/student-memory-demo
/tmp/student-memory-demo tools/memory_stress.py --total-mb 300 --step-mb 10
```

Watch memory growth, raw observation, stable prediction, and risk score. Use `Ctrl+C` to stop early if the VM becomes unresponsive.

Expected: growth and risk rise; sustained dangerous readings change the stable prediction rather than a single spike doing so.

## Experiment 4: Priority decision

Run the low-priority memory demo while keeping a high-priority configured workload available. Under High or Critical pressure, verify that the event history shows `THROTTLE` for the low-priority workload and `PROTECT` for the high-priority workload.

Expected: priority changes the selected intervention; detect-only performs no cgroup write.

## Experiment 5: Isolated enforcement

Only after taking a VM snapshot:

```bash
sudo bash tools/setup_cgroup.sh
```

Use only the harmless named demonstration process. Enable enforcement for this test, perform one controlled action, return to detect-only immediately afterward, and download the evidence.

Expected: the action result reports the target PID and cgroup limit. Verify membership with the relevant `cgroup.procs` file. Do not target system services, the desktop, the terminal, or personal applications.

## Evidence checklist

- Screenshot of the active dashboard
- Screenshot of a blocked-app decision
- Screenshot of rising memory/risk history
- Screenshot of the Phase 7 cgroup status
- Event CSV for each experiment
- Sample CSV for each experiment
- JSON report for each experiment
- `python -m pytest -q` result
- Table comparing expected and observed results
- Honest limitations: single machine, rule-based thresholds, local dashboard, controlled privileges, and no tamper resistance
