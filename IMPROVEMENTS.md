# Combined Improvements

This file records the code-level and systems-level improvements applied on the `combined-improvements-ui` branch, along with the remaining work that should be treated as future hardening.

## Implemented in this branch

### Correctness

1. `unknown_action` and `blocked_action` are now validated and used by the decision engine. Unknown applications can be configured to log, warn, pause, or terminate.
2. Applications already running when Exam Mode starts are no longer silently absorbed into the baseline when they are blocked or unknown. The first monitoring cycle evaluates them.
3. `terminate_grace_seconds` is configurable. Termination sends `SIGTERM`, waits for the configured grace period, and escalates to `SIGKILL` if the process remains alive.
4. The cgroup manager records original cgroup membership where it can be read and attempts to restore moved processes when the exam stops.
5. The cgroup containment check uses resolved real paths and `commonpath`, reducing symlink and path-prefix ambiguity.

### Documentation and UI

6. `FEATURES.md` documents the product features, workflow, and safety defaults.
7. The README now links to the feature and improvement documents and explains the new configurable action behavior.
8. The dashboard has a refreshed visual system with clearer status hierarchy, responsive layout, stronger table readability, and improved action and evaluation presentation.

## Remaining hardening work

These items require additional product decisions, a real Linux test environment, or user/account integration and are intentionally documented rather than simulated:

- Add teacher authentication, CSRF protection, and authorization for control, API, and export endpoints.
- Verify applications by executable path, ownership, hash, or signature instead of process name alone.
- Add policy checksums, read-only policy locking, and a watchdog for monitor tampering or unexpected service termination.
- Split privileged cgroup operations into a minimal helper over a protected Unix socket.
- Run the dashboard and monitor as separate supervised services using systemd and a production WSGI server.
- Add session lifecycle states, database WAL mode, retention, archival, and backup policies.
- Calibrate thresholds per machine and include swap, CPU, and I/O pressure in prediction.
- Add service-level, end-to-end, failure-mode, Linux integration, and performance tests.
- Add GitHub Actions for tests, linting, type checking, and security checks.
- Extend the current status-card API polling to process, event, and prediction tables; Server-Sent Events or WebSockets can remove polling later.
- Add student warnings, teacher-approved exceptions, accessible status indicators, and clearer operator guidance.

## Validation notes

The new behavior should be tested first in `detect_only` mode. Enforcement requires cgroups v2 and suitable Linux permissions. A live Linux VM is required to validate signals, cgroup movement, PSI readings, and restoration behavior.
