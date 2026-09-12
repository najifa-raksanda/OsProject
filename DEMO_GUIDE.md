# Live Demonstration Guide

This guide explains how to show each project feature to a teacher using safe, temporary workloads. Keep `mode` set to `detect_only` for the demonstration. For the four-minute rubric demo, use `config/demo_policy.json`; it blocks only the harmless named workload `exam-blocked`, so the dashboard browser remains usable.

## Before the demonstration

Start the service:

```bash
cd ~/OsProject
source .venv/bin/activate
EXAM_POLICY=config/demo_policy.json python run.py
```

Open `http://127.0.0.1:5000` in Firefox and click **Start Exam**. Keep this terminal open. Run each test in a second terminal.

## Prepare the safe named workloads

Run once in a second terminal:

```bash
cp "$(command -v python3)" /tmp/exam-blocked
cp "$(command -v python3)" /tmp/exam-low
cp "$(command -v python3)" /tmp/exam-high
```

The copied interpreter keeps the test harmless while giving the process a policy-controlled executable name.

## Show an allowed Python process

Run:

```bash
python3 -c "import time; print('Allowed Python process is running'); time.sleep(120)"
```

In the dashboard, search for `python3` in **Running processes**. It should show:

```text
Policy: allowed
Priority: normal
Recommended action: allow
```

Allowed processes do not normally create policy events. Stop the test with `Ctrl+C`.

## Show an allowed GCC process

Run:

```bash
gcc -x c - -o /tmp/demo-program
```

GCC waits for input, which keeps the real compiler process visible. Search for `gcc` in the dashboard. It should show:

```text
Policy: allowed
Priority: high
Recommended action: allow
```

Stop it with `Ctrl+C`. Under High or Critical memory pressure, the recommended action changes to `protect`.

## Show a blocked named workload

Start the harmless blocked workload after Exam Mode is active:

```bash
/tmp/exam-blocked tools/blocked_demo.py
```

Select the **Blocked** process filter. The dashboard should display a red alert and an event similar to:

```text
chrome -> blocked -> terminate -> Detect-only
```

The workload remains open because detect-only mode records the decision without enforcing it. The default policy can still be used separately to demonstrate browser blocking, but it is not the safest four-minute classroom demo because the browser is also the dashboard client.

## Show an unknown process

Run:

```bash
sleep 120
```

Select the **Unknown** filter or check **Recent policy events**. The expected result is:

```text
sleep -> unknown -> log
```

Stop it with `Ctrl+C`.

## Show memory growth and prediction

Create a temporary executable name once:

```bash
cp "$(command -v python3)" /tmp/student-memory-demo
```

This copies the Python interpreter to `/tmp` under the name `student-memory-demo`. It does not modify the project. The policy assigns this name low priority so the decision engine can demonstrate throttling.

Run the controlled workload:

```bash
/tmp/student-memory-demo tools/memory_stress.py --total-mb 300 --step-mb 10 --interval 0.5
```

The options mean:

- `--total-mb 300`: allocate up to 300 MB.
- `--step-mb 10`: add memory in 10 MB steps.
- `--interval 0.5`: wait half a second between steps.

Show the teacher how memory usage, growth, PSI, risk score, raw observation, and stable prediction change. If pressure becomes High or Critical, search for `student-memory-demo`; its recommended action should be `throttle` because it is low priority.

Stop the workload with `Ctrl+C`. Remove the temporary executable after the demonstration:

```bash
rm -f /tmp/student-memory-demo /tmp/demo-program
```

## Show cgroup readiness

Run once in the disposable VM:

```bash
sudo bash tools/setup_cgroup.sh
```

Restart Exam Mode. The dashboard should show **Managed groups: READY**. Detect-only mode still performs no cgroup writes.

## Show reports

Use the dashboard buttons to download:

- Event CSV for application decisions
- Sample CSV for memory and prediction measurements
- JSON report for the session summary

## Recommended presentation order

```text
Start Exam
-> Python allowed
-> GCC allowed and high priority
-> Chrome blocked
-> sleep unknown
-> memory growth and prediction
-> cgroup readiness
-> download evaluation report
```
