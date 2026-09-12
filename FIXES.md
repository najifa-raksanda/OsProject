# Verified Fixes and Readiness Updates

This document records changes that are present in the `fix/evaluation-readiness` branch. It distinguishes implemented behavior from experiments and future work so presentation and report claims remain accurate.

## New fixes in this branch

- System metrics remain selected when `memory_cgroup` is unset; the cgroup enforcement root is not silently used as a metric source.
- Historical cgroup OOM counters are baselined, and changing metric source resets growth and event history.
- Detection latency is captured before enforcement, while action duration is stored separately in `details_json`.
- SIGKILL outcomes are confirmed with a wait; a process that remains alive is reported as an unsuccessful action.
- Sample CSV export now returns every retained sample in the selected session instead of stopping at 2,000 rows.
- The dashboard label `Confidence` is now `Signal persistence`. The value describes how long the current signal has persisted; it is not a statistical forecast-confidence measurement.
- The systemd Gunicorn configuration now uses one worker and four threads. One worker ensures all dashboard requests share the same in-memory exam session.
- `run.py` and `wsgi.py` accept an `EXAM_POLICY` environment variable, allowing the safe demo policy to be selected without editing the default policy.
- `config/demo_policy.json` provides harmless named demo workloads. The dashboard browser is not blocked by this policy.
- `.gitattributes` preserves Linux LF line endings for shell scripts and project text files.
- A logger regression test verifies complete chronological session-sample retrieval.

## Fixes inherited from additional improvements

- Policy values and process priorities are validated when an exam starts.
- Blocked and unknown policy actions are connected to the decision and action pipeline.
- Termination begins with `SIGTERM` and can escalate to `SIGKILL` after a configurable grace period.
- PID creation time is checked before enforcement to reduce PID-reuse risk.
- Existing processes are sampled when Exam Mode starts instead of all being treated as new allowed launches.
- cgroup paths are resolved and checked to remain under the configured Linux cgroup hierarchy.
- Best-effort restoration returns moved processes to their original cgroup when Exam Mode stops.
- SQLite uses WAL mode, indexes, and age-based retention.
- The dashboard refreshes process, event, and prediction tables and provides process search and policy filters.
- GitHub Actions runs compilation and pytest checks.

## Evidence still required

The following are evaluation tasks, not completed feature claims:

- Final Kali or VirtualBox rehearsal
- Normal baseline measurements
- Controlled blocked-process detection results
- Controlled memory-growth results
- Priority-decision results under sustained pressure
- Bounded real-cgroup enforcement evidence on a disposable Linux VM
- Tables or plots comparing expected and observed results

## Not implemented

- A verified guarantee that the project prevents OOM failures
- Measured forecast accuracy across labeled workloads
- Comparative performance against another resource manager
- UNIX-domain IPC for a privileged helper
- CPU scheduler controls
- Proactive memory reclaim
- Optimized process-victim selection

These items are future work unless they were explicitly promised in the approved proposal.
