## 1. Plugin Scaffold

- [ ] 1.1 Create the `ha_manager_local` plugin directory and metadata with isolated name, title, runtime path, and asset references.
- [ ] 1.2 Create a new local plugin backend entrypoint based on the SSH plugin structure, but remove peer-binding and cloud-monitor dependencies from the primary flow.
- [ ] 1.3 Create the local plugin frontend entrypoint and asset wiring with the new plugin name and UI title.

## 2. Local State and Health Model

- [ ] 2.1 Add local-only state files and initialization logic for role, desired role, switch status, and step progress.
- [ ] 2.2 Reuse or adapt the local health-check logic so the plugin can report service, scheduled-task, rsync, and OpenResty state without peer access.
- [ ] 2.3 Ensure the status view renders correctly when no peer host is configured or reachable.

## 3. Step-by-Step Local Switch Flow

- [ ] 3.1 Break the local switch workflow into explicit steps with persisted step state and individual completion markers.
- [ ] 3.2 Implement local offline and online actions as step targets that affect only the current host.
- [ ] 3.3 Implement local role switching to master or standby without remote execution.
- [ ] 3.4 Add step retry, resume, and partial completion behavior so the operator can continue from the last successful step.

## 4. Close External Service and Repair Actions

- [ ] 4.1 Add a dedicated action to close external service exposure, at minimum stopping OpenResty.
- [ ] 4.2 Add failure guidance content for known recoverable states and expose repair actions from the UI.
- [ ] 4.3 Add UI feedback for successful steps, failed steps, and actionable repair state.

## 5. Verification and Cleanup

- [ ] 5.1 Verify the new local plugin status command returns quickly and the plugin loads without peer dependencies.
- [ ] 5.2 Verify the local plugin UI shows step-by-step controls, local health checks, and the external service shutdown action.
- [ ] 5.3 Confirm the SSH plugin remains unchanged and independently installable after the local plugin is added.
