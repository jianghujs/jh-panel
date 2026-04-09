## ADDED Requirements

### Requirement: System monitor alerts are sent once per active problem
The system SHALL send a monitor alert when a specific `systemTask` problem key becomes active for the first time, and SHALL NOT resend that same problem while it remains active.

#### Scenario: First detection sends an alert
- **WHEN** a monitor cycle detects a problem key that was not active in the previous persisted monitor-alert state
- **THEN** the system sends a notification for that problem key

#### Scenario: Ongoing problem does not resend
- **WHEN** a later monitor cycle detects the same problem key and that key is still marked active in persisted monitor-alert state
- **THEN** the system does not send another notification for that problem key

### Requirement: Cleared problems can alert again after reoccurrence
The system SHALL remove a problem key from the active monitor-alert state after the underlying issue is no longer detected, so that a later reoccurrence is treated as a new alert.

#### Scenario: Recovery clears active state
- **WHEN** a monitor cycle no longer detects a previously active problem key
- **THEN** the system removes that problem key from persisted active monitor-alert state

#### Scenario: Reoccurrence sends again after recovery
- **WHEN** a problem key was previously removed because the issue cleared and a later monitor cycle detects the same key again
- **THEN** the system sends a new notification for that problem key

### Requirement: Monitor alert deduplication uses stable per-problem keys
The system SHALL identify monitor problems using stable keys derived from monitor type and monitored entity, so that unrelated problems are tracked independently and dynamic message text does not break deduplication.

#### Scenario: Different problems are tracked independently
- **WHEN** one active problem remains unresolved and a different problem key becomes active in a later monitor cycle
- **THEN** the system sends a notification only for the newly active problem key

#### Scenario: Dynamic message values do not create duplicate alerts
- **WHEN** a problem remains active but its rendered message text changes because observed values or timestamps changed
- **THEN** the system still treats it as the same active problem key and does not resend the alert
