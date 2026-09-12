# Final Presentation and Live Demo Guide

## Six-minute presentation

Keep the slides concise and use the report for technical detail.

| Time | Content |
|---|---|
| 0:00-0:35 | Introduction and problem: exam machines need policy enforcement without harming required workloads |
| 0:35-1:10 | Main objectives and approved scope |
| 1:10-2:15 | Architecture and implementation pipeline |
| 2:15-3:25 | Four or five OS concepts and the Linux mechanisms used |
| 3:25-4:20 | Controlled experiments and measured results |
| 4:20-5:05 | Technical challenges, safety decisions, and innovation |
| 5:05-5:35 | Contribution of each member |
| 5:35-6:00 | Limitations, conclusion, and future work |

## Four-minute live demo

Use the safe policy so the Firefox dashboard remains available.

Start the server:

```bash
cd ~/OsProject
source .venv/bin/activate
EXAM_POLICY=config/demo_policy.json python run.py
```

Prepare harmless executable names once:

```bash
cp "$(command -v python3)" /tmp/exam-blocked
cp "$(command -v python3)" /tmp/exam-low
cp "$(command -v python3)" /tmp/exam-high
```

Recommended timeline:

| Time | Demonstration |
|---|---|
| 0:00-0:30 | Open the dashboard, click Start Exam, and show Linux metric source |
| 0:30-1:05 | Run `/tmp/exam-high tools/blocked_demo.py`; search `exam-high` and show allowed, high priority |
| 1:05-1:40 | Run `/tmp/exam-blocked tools/blocked_demo.py`; show blocked, terminate, detect-only |
| 1:40-2:45 | Run `/tmp/exam-low tools/memory_stress.py --total-mb 300 --step-mb 10 --interval 0.5`; show growth, PSI, raw and stable pressure, risk, and low priority |
| 2:45-3:20 | Show cgroup status and relevant `/sys/fs/cgroup` evidence if prepared |
| 3:20-3:45 | Download event CSV, sample CSV, and JSON report |
| 3:45-4:00 | Stop Exam and state the safety boundary and limitation |

Stop each workload with `Ctrl+C`. Keep the policy in detect-only mode during the ordinary classroom demo.

## Viva preparation

Every member should be able to answer:

- Why use creation time as well as PID?
- What is the difference between `SIGTERM` and `SIGKILL`?
- What does Linux PSI measure?
- What do `memory.low`, `memory.high`, and `memory.max` mean?
- Why use hysteresis for pressure prediction?
- Why is detect-only the default?
- How are race conditions between monitoring and dashboard requests reduced?
- What evidence supports the results, and what has not been proven?
