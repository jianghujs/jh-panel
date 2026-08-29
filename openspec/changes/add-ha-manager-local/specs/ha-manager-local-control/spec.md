## ADDED Requirements

### Requirement: Local plugin identity
The system SHALL provide a new HA manager plugin named `ha_manager_local` that is separate from the SSH-based HA manager plugin in plugin name, plugin directory, runtime directory, and stored state.

#### Scenario: Local plugin is independently identifiable
- **WHEN** the local HA manager plugin is installed
- **THEN** the system SHALL expose it as `ha_manager_local` without reusing the SSH plugin identity or runtime paths

### Requirement: Local status and health checks
The system SHALL display the current host role, desired role, switch state, and health-check results for the local host without requiring a peer host to be reachable.

#### Scenario: Status is available without a peer
- **WHEN** the operator opens the local HA manager status view
- **THEN** the system SHALL show local role and health information even if no peer host is configured or reachable

### Requirement: Local online and offline control
The system SHALL allow the operator to execute local online and offline actions that affect only the current host.

#### Scenario: Offline action runs locally
- **WHEN** the operator triggers a local offline action
- **THEN** the system SHALL apply the offline action to the current host without contacting another host

### Requirement: Local role switching
The system SHALL allow the operator to switch the current host to master or standby as a local action without requiring peer coordination.

#### Scenario: Switch to master locally
- **WHEN** the operator chooses to switch the current host to master
- **THEN** the system SHALL execute the local switch flow on the current host and update the local role state accordingly

### Requirement: Step-by-step switch guidance
The system SHALL break local switching into explicit steps that the operator can execute, inspect, retry, and continue independently.

#### Scenario: Operator executes one step at a time
- **WHEN** the operator starts a local switch workflow
- **THEN** the system SHALL present the switch as a sequence of named steps with individual completion state

### Requirement: External service shutdown
The system SHALL provide a dedicated action to close external service exposure on the current host, and the action SHALL at minimum stop OpenResty.

#### Scenario: Close external service
- **WHEN** the operator clicks the external service shutdown action
- **THEN** the system SHALL stop OpenResty on the current host and report whether the shutdown succeeded

### Requirement: Local quality checks
The system SHALL include local quality checks for services and scheduled tasks relevant to the host role, including OpenResty and rsync-related state.

#### Scenario: Quality checks reflect the current role
- **WHEN** the system evaluates local quality checks
- **THEN** the reported expected state SHALL depend on the current host role and SHALL not require peer comparison

### Requirement: Step failure guidance and repair actions
The system SHALL surface a human-readable failure explanation and at least one repair action for recognized recoverable switch failures.

#### Scenario: Repair action is available after a failure
- **WHEN** a switch step fails in a recognized way
- **THEN** the system SHALL display guidance for the failure and SHALL expose a repair action that can be retried by the operator

### Requirement: No peer orchestration in local mode
The local plugin SHALL NOT require SSH peer binding, peer health validation, or cloud-monitor orchestration to complete its primary local operations.

#### Scenario: Primary flow remains local-only
- **WHEN** the operator uses the local plugin for status, offline, online, or role-switch actions
- **THEN** the system SHALL complete the primary local operation without needing peer binding or remote execution
