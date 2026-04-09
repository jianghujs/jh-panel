## 1. Alert State Persistence

- [ ] 1.1 Add helper logic in `class/core/mw.py` to load and save persisted active monitor-alert state from a dedicated JSON file.
- [ ] 1.2 Make the state helper tolerate missing, empty, or invalid JSON content by falling back to an empty active-state set and rewriting valid data.

## 2. Monitor Alert Deduplication

- [ ] 2.1 Refactor `mw.generateMonitorReportAndNotify(...)` to collect monitor problems as stable `problem_key + message` entries instead of a plain message list.
- [ ] 2.2 Compare current problem keys against persisted active state to compute newly active, recovered, and continued problems.
- [ ] 2.3 Send notifications only for newly active problems and update persisted state so recovered problems are cleared and reoccurrences can notify again.
- [ ] 2.4 Remove dependence on the shared `trigger_time=600` throttle for `stype='面板监控'` so unrelated new problems are not suppressed by earlier alerts.

## 3. Verification

- [ ] 3.1 Verify that a sustained abnormal condition produces only one notification across multiple monitor cycles.
- [ ] 3.2 Verify that after a problem clears and later reappears, the same problem key produces a fresh notification.
- [ ] 3.3 Verify that when one problem remains active and a different problem appears later, only the newly active problem is sent in the later notification.
