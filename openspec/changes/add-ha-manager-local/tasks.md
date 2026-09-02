## 1. Plugin Scaffold

- [x] 1.1 Create the `ha_manager_local` plugin directory and metadata with isolated name, title, runtime path, and asset references.
- [x] 1.2 Create a new local plugin backend entrypoint based on the SSH plugin structure, but remove peer-binding and cloud-monitor dependencies from the primary flow.
- [x] 1.3 Create the local plugin frontend entrypoint and asset wiring with the new plugin name and UI title.

## 2. Local State and Health Model

- [x] 2.1 Add local-only state files and initialization logic for role, desired role, switch status, and step progress.
- [x] 2.2 Reuse or adapt the local health-check logic so the plugin can report service, scheduled-task, rsync, and OpenResty state without peer access.
- [x] 2.3 Ensure the status view renders correctly when no peer host is configured or reachable.

## 3. Step-by-Step Local Switch Flow

- [x] 3.1 Break the local switch workflow into explicit steps with persisted step state and individual completion markers.
- [x] 3.2 Implement local offline and online actions as step targets that affect only the current host.
- [x] 3.3 Implement local role switching to master or standby without remote execution.
- [x] 3.4 Add step retry, resume, and partial completion behavior so the operator can continue from the last successful step.

## 4. Close External Service and Repair Actions

- [x] 4.1 Add a dedicated action to close external service exposure, at minimum stopping OpenResty.
- [x] 4.2 Add failure guidance content for known recoverable states and expose repair actions from the UI.
- [x] 4.3 Add UI feedback for successful steps, failed steps, and actionable repair state.

## 5. Verification and Cleanup

- [x] 5.1 Verify the new local plugin status command returns quickly and the plugin loads without peer dependencies.
- [x] 5.2 Verify the local plugin UI shows step-by-step controls, local health checks, and the external service shutdown action.
- [x] 5.3 Confirm the SSH plugin remains unchanged and independently installable after the local plugin is added.
