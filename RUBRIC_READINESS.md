# Evaluation Rubric Readiness

Use this checklist before the final presentation. Core approved objectives take priority over additional features.

## Rubric mapping

| Criterion | Current evidence | Required final action |
|---|---|---|
| Approved objectives and core functionality | Process policy, memory and PSI monitoring, prediction, decisions, dashboard, cgroup support, logging, and exports | Compare this list with the approved proposal and demonstrate every promised objective end to end |
| OS relevance and technical depth | Processes, Linux signals, `/proc` PSI, `/sys/fs/cgroup`, cgroups v2, memory pressure, protection, SQLite synchronization | Explain where, why, and how at least four or five concepts are used; show relevant code and Linux files |
| Linux and system-level integration | Real process inspection, signals, cgroup files, PSI, memory events | Demonstrate actual commands, kernel-facing files, logs, and live behavior on Linux |
| Methodology and architecture | Modular monitor, predictor, decision engine, action manager, logger, and web dashboard | Include an architecture diagram and explain failure handling, safety guards, and design decisions |
| Experimentation and results | Metrics and export support exist | Run controlled experiments and add measured values, baseline, comparison, interpretation, and limitations |
| Live demonstration | Safe named workloads and a demo policy exist | Rehearse the complete flow within four minutes on the final Kali or VirtualBox environment |
| Report and reproducibility | README, feature, improvement, evaluation, and demo guides exist | Produce a detailed PDF report with figures, tables, results, references, contributions, and exact setup steps |
| Innovation and problem solving | Hysteresis, priority-aware control, safe PID validation, cgroup containment, and audit history | Explain the technical problems, attempted approaches, final decisions, and trade-offs |
| Presentation and communication | Required structure documented | Rehearse a concise six-minute presentation and avoid spending time on UI styling |
| Contribution and viva | Repository history can provide supporting evidence | Add a member-contribution table and ensure every member can explain the entire architecture |

## OS concepts to demonstrate

1. **Process management:** discover process identity, PID, creation time, state, CPU, and memory.
2. **Signals:** use `SIGTERM`, `SIGKILL`, and `SIGSTOP` with safety checks.
3. **Memory management:** observe utilization, growth, OOM counters, and pressure.
4. **Kernel interfaces:** read PSI from `/proc/pressure/memory` and cgroup files from `/sys/fs/cgroup`.
5. **Resource control and protection:** use cgroups v2 `memory.low`, `memory.high`, `memory.max`, and `cgroup.procs`.
6. **Concurrency and synchronization:** run the monitor thread while the dashboard reads state protected by locks; use SQLite WAL for concurrent reads.

Only select the strongest four or five concepts for the six-minute presentation. Explain the remaining concepts in the report and viva.

## Required evidence package

- Screenshot of active Exam Mode
- Screenshot of an allowed named workload
- Screenshot and CSV row for a blocked named workload
- Screenshot of rising memory, PSI, risk, and stable prediction
- Screenshot or terminal output showing cgroup readiness and membership
- Event CSV, complete sample CSV, and JSON report for each experiment
- `pytest -q` output from the final Linux environment
- Expected-versus-observed results table
- Architecture diagram
- Member-contribution table
- Exact limitations and future work

## Submission checklist

- [ ] Approved objectives verified against the original proposal
- [ ] Four-minute live demo rehearsed
- [ ] Six-minute presentation rehearsed
- [ ] Five-minute viva preparation completed by every member
- [ ] Final Linux tests and shell syntax checks passed
- [ ] Experimental evidence saved outside temporary directories
- [ ] Detailed report exported to PDF and printed
- [ ] Team name, project title, objectives, and accessible Drive link entered in the course sheet
- [ ] Repository branch committed and pushed after the final rehearsal
