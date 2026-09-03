## Context

The current HA manager plugin is an SSH-coordinated, two-host control surface. It has strong local execution primitives already, but the user-visible flow assumes peer binding, peer orchestration, and optional cloud-monitor integration. The new local plugin must serve a different operating model: each host is managed independently, and the operator may intentionally run asymmetric states between nodes.

The local plugin must preserve the operator value of the existing health checks and switch scripting, but it must stop depending on peer reachability, peer identity, or remote execution for its primary workflow.

## Goals / Non-Goals

**Goals:**
- Provide a new plugin `ha_manager_local` that is isolated from `ha_manager_ssh` at name, directory, runtime, and state-file level.
- Support local online/offline actions on the current machine.
- Support local role switching between master and standby on the current machine only.
- Break the switch flow into explicit steps with visible status, retry behavior, and failure guidance.
- Keep local health checks and quality checks for services and scheduled tasks.
- Add a dedicated action to close external service exposure, at minimum by stopping OpenResty.
- Support repair actions for recognized failure states.

**Non-Goals:**
- No peer SSH binding or peer validation as a prerequisite for the local plugin.
- No cloud-monitor registration, polling, or remote orchestration in the local plugin.
- No requirement that both hosts transition together.
- No attempt to enforce global consistency across two hosts.
- No replacement of `ha_manager_ssh`; the two plugins should coexist.

## Decisions

1. **Create a new plugin instead of converting the SSH plugin in place.**
   The new behavior is operationally distinct and needs independent metadata, runtime files, and UI copy. Keeping it separate avoids breaking existing one-click installations and preserves a clean migration path.
   Alternatives considered: renaming the current plugin or branching behavior by mode. Both would entangle state and future maintenance.

2. **Use a step runner model for switching.**
   Each switch is represented as a sequence of local steps with explicit state transitions, rather than a single monolithic switch action. This matches the operator need to inspect, retry, and stop between stages.
   Alternatives considered: a simple two-button "master/standby" toggle, or keeping the current wizard and hiding peer steps. Both are too opaque for the requested operating style.

3. **Treat role switching as local state plus local service changes.**
   The local plugin should update local role metadata, service state, and scheduled-task state without assuming the peer is reachable or in any particular state.
   Alternatives considered: local changes plus best-effort peer notifications, or a hybrid mode that keeps peer sync as optional. Those still create hidden coupling and operator confusion.

4. **Make "close external service" a first-class command.**
   The plugin should expose a dedicated action that reduces incoming traffic before switch steps begin. OpenResty stop/mask is the minimum base behavior because it directly blocks the standard web entry path.
   Alternatives considered: burying this inside the switch flow or making it just another step. A standalone action is more useful during emergencies and pre-switch staging.

5. **Map failure states to repair actions.**
   The UI should not stop at error text. It should show what failed, what the operator should check, and which repair command can be retried safely. This is especially important for service-stop failures, task state mismatches, and role mismatch after a partial switch.
   Alternatives considered: generic error banners with no action, or a fully automatic self-heal loop. Manual repair is safer and more transparent here.

## Risks / Trade-offs

- [Risk] The local plugin may allow both hosts to drift into the same role or an inconsistent state.
  [Mitigation] Keep the UI explicit that the plugin is local-only, surface the current role and desired role prominently, and make repair actions easy to reach.

- [Risk] Stopping OpenResty alone may not fully block all ingress paths.
  [Mitigation] Define the feature as "at minimum OpenResty is closed" and keep the implementation extensible for additional local ingress controls if needed later.

- [Risk] Step-by-step execution increases operational time.
  [Mitigation] Make each step resumable and show current status, so the operator can stop at the right boundary rather than rerun the full process.

- [Risk] Reusing switch logic from the SSH plugin can accidentally carry over peer assumptions.
  [Mitigation] Keep the new plugin namespace separate and remove peer-dependent fields from the new requirements before implementation.

- [Risk] Existing users may confuse the two plugin variants.
  [Mitigation] Give them distinct names, distinct directories, and distinct UI titles, and keep the SSH version unchanged.

## Migration Plan

1. Add the new local plugin alongside the SSH version instead of modifying the old plugin in place.
2. Reuse only local-only primitives from the existing switch code and health checks.
3. Introduce the new role-step UI and step-state persistence.
4. Validate local-only service shutdown and repair commands on a single host before wiring any additional actions.
5. Keep rollback simple: the SSH plugin remains available and unchanged if the local version needs to be removed.

## Open Questions

- Which exact local steps should be first-class in v1 beyond the minimum service shutdown, task toggles, and role switch?
- Should the local plugin support one-click full execution in addition to manual step-by-step control, or only manual steps?
- Which services besides OpenResty should be part of the dedicated "close external service" action, if any?
- Which failure states deserve dedicated repair buttons on day one?
