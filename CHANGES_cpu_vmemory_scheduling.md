# Changes: CPU Scheduling, Virtual-Memory Metrics & CPU/IO Pressure Monitoring

**Branch:** `feature/cpu-vmemory-scheduling-metrics`
**Author:** (add your name here)
**Date:** (add date here)

## Why this branch exists

Our rubric (`CSE_308_OS_Sessional_Final_Project_Evaluation_Rubric.pdf`), under
**Criterion 2 — "Operating System Concepts: Relevance, Correctness & Technical
Depth" (20 marks)**, requires four to five OS concepts to be integrated
*meaningfully and correctly*, not just mentioned. Before this branch, the
project genuinely demonstrated only:

- **Memory management / pressure** — `/proc/pressure/memory`, cgroup v2
  `memory.current` / `memory.max` / `memory.events`
- **Resource control** — cgroup v2 memory controller
- **Process control** — `SIGTERM` / `SIGSTOP`

That is 2–3 concepts, and all process-level data was read through `psutil`
(a high-level wrapper) rather than directly from the kernel-exported `/proc`
files, which also touches **Criterion 3 — "Linux / System-Level Integration"
(10 marks)**, which explicitly rewards direct use of `/proc`, `/sys`, and
kernel-facing mechanisms over library abstractions.

This branch adds two more OS pillars with real depth:

1. **CPU scheduling** (cgroup v2 `cpu.weight` / `cpu.max`) — previously
   completely absent.
2. **Virtual memory** (RSS, swap, minor/major page faults) and further
   **process/scheduling** detail (voluntary/involuntary context switches) —
   read directly from `/proc/[pid]/status` and `/proc/[pid]/stat`, not via
   `psutil`.

It also extends the existing PSI-based pressure detection from memory-only
to **CPU and I/O pressure** (`/proc/pressure/cpu`, `/proc/pressure/io`),
which strengthens the "resource management" story used throughout
Criteria 2, 3, and 5 (Experimentation & Evaluation).

## What was added, file by file

| File | Type | What it does |
|---|---|---|
| `exam_manager/system_metrics.py` | New | `read_cpu_psi()` / `read_io_psi()` — parse `/proc/pressure/cpu` and `/proc/pressure/io` directly, same style as the existing memory PSI parser. |
| `exam_manager/proc_reader.py` | New | `read_process_detail(pid)` — parses `/proc/[pid]/status` (VmRSS, VmSwap, voluntary/nonvoluntary context switches) and `/proc/[pid]/stat` (minflt/majflt) **without psutil**, returning a `ProcessDetail` dataclass. |
| `exam_manager/cpu_io_monitor.py` | New | `CpuIoMonitor` samples CPU/IO PSI each loop into a `CpuIoSnapshot`, mirroring `MemoryMonitor`'s design. |
| `exam_manager/cgroup_manager.py` | Modified (additive) | New `CgroupManager.apply_cpu()` writes `cpu.weight` (scheduler share) and `cpu.max` (hard CPU quota, in `quota_us period_us` form) into the restricted/protected cgroups for `THROTTLE`/`PROTECT` decisions — real CPU scheduling control, independent of the existing memory `apply()`. New `cpu_controller` key in `status()`. **The original `apply()` and its behavior are unchanged.** |
| `exam_manager/action_manager.py` | Modified (additive) | `execute()` now also calls `apply_cpu()` as a best-effort step after the existing memory `apply()`. Overall `success`/`attempted` are still governed by the memory-cgroup result, exactly as before — CPU control is reported in the message but never breaks the existing contract. |
| `exam_manager/event_logger.py` | Modified (additive) | New nullable columns (`vm_rss_kb`, `vm_swap_kb`, `voluntary_ctxt_switches`, `nonvoluntary_ctxt_switches`, `minor_faults`, `major_faults` on `events`; `cpu_psi_some_avg10`, `cpu_psi_avg60`, `io_psi_some_avg10`, `io_psi_full_avg10` on `samples`), added via the same `ALTER TABLE` migration pattern already used for `detection_latency_ms`. `record()` and `record_sample()` gained new **optional, trailing** parameters, so old call sites keep working unmodified. `summary()` gained two new peak-CPU/IO-pressure keys. |
| `exam_manager/service.py` | Modified (additive) | Wires `CpuIoMonitor` and `read_process_detail()` into the monitoring loop and `status()` dashboard payload. `/proc` reads only happen for a process at the moment an event is actually logged, not on every process every loop, to keep the loop-time budget (Criterion 5's "Experimentation, Evaluation & Results") unaffected. |
| `tests/test_system_metrics.py` | New | Unit tests for CPU/IO PSI parsing. |
| `tests/test_proc_reader.py` | New | Unit tests for `/proc/[pid]` parsing (uses the test process's own PID; skipped on non-Linux). |
| `tests/test_cpu_io_monitor.py` | New | Unit test for `CpuIoMonitor.sample()`. |
| `tests/test_cgroup_manager_cpu.py` | New | Unit tests for `apply_cpu()` (throttle weight/quota, protect weight, missing-controller handling, critical-PID refusal). |
| `exam_manager/templates/dashboard.html` | Modified (additive only) | Added one new section, **"CPU scheduling & virtual memory"**, showing live CPU PSI (some avg10/avg60), I/O PSI (some avg10/full avg10), and whether the cgroup v2 `cpu` controller is available — the same card style already used by "Phase 5 · Memory monitoring" etc. Inserted between the existing "Phase 8 · Evaluation" section and the `status.error` banner. **No existing line, id, class, or the `<script>` chart block was touched, removed, or reordered** — verified with a line-by-line `diff` against the pre-change file, which showed only this one 11-line addition. |

**No existing test file was modified**, and the full original test suite
(28 tests) plus the 9 new tests all pass — 37/37. The dashboard was also
exercised end-to-end (started exam mode, waited for a live monitoring
loop, re-rendered the page) to confirm it renders with zero errors both
before and after `Start Exam` is pressed.

## How this maps to the rubric

- **Criterion 2 (OS Concepts Depth, 20 marks):** raises the concept count
  from 2–3 to 4–5 — memory management, resource control, process control,
  **CPU scheduling**, and **virtual memory** — each backed by real kernel
  interfaces, not slide-only mentions.
- **Criterion 3 (Linux/System-Level Integration, 10 marks):** adds direct
  `/proc/[pid]/status` and `/proc/[pid]/stat` parsing (bypassing `psutil`),
  plus a second cgroup v2 controller (`cpu`) alongside `memory`.
- **Criterion 5 (Experimentation & Evaluation, 10 marks):** new CPU/IO PSI
  and VM/scheduling fields are persisted to SQLite (`samples`/`events`
  tables) so they can be exported and plotted the same way the existing
  `EVALUATION.md` experiments already do for memory.
- **Criterion 8 (Innovation & Problem Solving, 5 marks):** the `apply_cpu()`
  design deliberately keeps CPU control **independent and best-effort**
  from the existing memory-cgroup result, so a host without the `cpu`
  controller degrades gracefully instead of breaking enforcement — a
  concrete "engineering decision" worth mentioning in the report/demo.

## How to demo this live

1. Show `/proc/pressure/cpu` and `/proc/pressure/io` alongside the existing
   memory PSI file, to prove CPU/IO pressure is now being read the same way.
2. Point at the dashboard's new **"CPU scheduling & virtual memory"**
   section (below "Phase 8 · Evaluation") to show these same PSI values
   updating live in the UI, and whether the cgroup v2 `cpu` controller is
   available on the host.
3. Trigger a `THROTTLE` decision (e.g. run a CPU-heavy disallowed process)
   and `cat` the resulting `cpu.weight` and `cpu.max` files under the
   managed cgroup's `restricted/` directory to show the real kernel-side
   scheduling limit being applied.
4. Point at `/proc/[pid]/status` for a monitored process and show that the
   dashboard's logged `vm_rss_kb`/`vm_swap_kb`/`minor_faults`/`major_faults`
   match it exactly — proving the values come from the kernel, not from an
   estimate.

## Follow-ups not included in this branch (possible next steps)

- Adding CPU/IO pressure levels into `decision_engine.py`'s decision logic
  (currently only memory pressure drives THROTTLE/PROTECT decisions; CPU/IO
  pressure is monitored, logged, and shown on the dashboard, but not yet a
  decision input).
- Extending `config/policy.json` / `policy.py` to let `cpu.weight` /
  `cpu.max` percentages be tuned via policy instead of the hardcoded
  defaults in `CgroupManager`.
- Adding a second chart line (alongside the existing memory/risk-score
  chart) to plot CPU/IO PSI history over time, rather than just the
  current-value cards added in this branch.
