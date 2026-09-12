# Final Technical Report Outline

The report must contain more technical detail than the slides. LaTeX is recommended for the final PDF.

1. **Title page:** course, project title, team name, members, IDs, section, and submission date.
2. **Abstract:** problem, method, implemented system, main measured result, and limitation.
3. **Introduction:** exam environment and resource-management context.
4. **Problem statement and motivation:** why application policy and memory pressure must be handled together.
5. **Approved objectives:** exact original commitments and completion status.
6. **OS background:** processes, signals, memory pressure, PSI, cgroups v2, protection, and synchronization.
7. **Related systems:** relevant Linux mechanisms or existing approaches, with references.
8. **Architecture and methodology:** components, data flow, state ownership, safety boundary, and failure handling.
9. **Implementation:** process monitor, policy loader, predictor, decision engine, action manager, cgroup manager, logger, API, and dashboard.
10. **Experimental design:** machine/VM configuration, workload, baseline, variables, metrics, repetitions, and expected results.
11. **Results:** labeled tables and plots from exported CSV/JSON evidence.
12. **Discussion:** interpretation, anomalies, overhead, and what the results do and do not prove.
13. **Challenges and engineering decisions:** cgroup permissions, PID reuse, graceful termination, hysteresis, cleanup, and shared web state.
14. **Individual contributions:** member, task, code/docs/experiment evidence, and understanding.
15. **Limitations:** controlled VM, rule-based predictor, local dashboard, privileges, and unmeasured claims.
16. **Conclusion and future work:** verified outcome followed by clearly separated future improvements.
17. **Reproducibility:** repository branch, exact installation commands, policy, test commands, and evidence filenames.
18. **References:** Linux kernel documentation, Python and library documentation, and acknowledged external code.

## Results table template

| Experiment | Expected | Observed | Key metrics | Evidence file | Interpretation |
|---|---|---|---|---|---|
| Normal baseline | Mostly Normal; low overhead | Fill after experiment | Memory, PSI, loop time, CPU, RAM | Fill filename | Fill interpretation |
| Blocked workload | One blocked detect-only event | Fill after experiment | Detection latency, count | Fill filename | Fill interpretation |
| Memory growth | Growth and risk increase | Fill after experiment | Peak memory, growth, PSI, risk | Fill filename | Fill interpretation |
| Priority decision | Low workload throttle; high workload protect | Fill after experiment | Actions and persistence | Fill filename | Fill interpretation |
| Bounded enforcement | Correct cgroup membership and cleanup | Fill after experiment | Limits, events, result | Fill filename | Fill interpretation |

Never replace missing measurements with estimated values. State `not measured` and explain why when an experiment cannot be completed.
