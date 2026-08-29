## Why

The existing HA manager is an SSH one-click version that coordinates both hosts from one panel, which is too coupled for operators who want each machine to execute only its own local role changes. A local simplified version is needed so each host can be controlled independently, with explicit step-by-step guidance during risky switch operations.

## What Changes

- Add a new plugin named `ha_manager_local` that coexists with `ha_manager_ssh` and uses its own plugin directory, runtime directory, metadata, assets, state files, and UI entrypoints.
- Provide local-only online/offline operations that affect only the current machine.
- Provide local role switching so the current machine can be manually switched to master or standby without contacting or validating a peer host.
- Keep local status and quality-check views, including service, scheduled-task, rsync, OpenResty, and role-consistency checks.
- Replace the two-host switch wizard with an operator-guided step runner where each switch step can be executed, retried, skipped when allowed, and inspected independently.
- Add a standalone "close external service" action that quickly blocks incoming service traffic, at minimum by stopping OpenResty.
- Add per-step failure guidance and repair actions for known recoverable states.
- Remove SSH peer binding and two-host orchestration from the local plugin flow.

## Capabilities

### New Capabilities
- `ha-manager-local-control`: Local-only HA manager plugin behavior, including local online/offline control, guided local role switching, health checks, external service shutdown, and repair guidance.

### Modified Capabilities
- None.

## Impact

- Adds a new plugin under `/www/server/jh-panel/plugins/ha_manager_local`.
- Adds a new runtime directory under `/www/server/ha_manager_local`.
- Reuses proven local health-check and switch-script concepts from `ha_manager_ssh`, while removing peer SSH execution, peer binding, and cloud-monitor orchestration from the local plugin UI and backend paths.
- May add or adapt local backend functions for step execution, step state persistence, external service shutdown, repair actions, and status reporting.
- No breaking change to `ha_manager_ssh`; both plugins must remain installable independently.
