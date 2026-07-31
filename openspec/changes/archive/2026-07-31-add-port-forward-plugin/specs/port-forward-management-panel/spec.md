## ADDED Requirements

### Requirement: Persisted forwarding rule configuration
The system SHALL store port forwarding rules in plugin-owned persistent configuration so enabled rules can be restored after reboot.

#### Scenario: Save forwarding rules
- **WHEN** a user creates or edits a forwarding rule and saves it
- **THEN** the system SHALL persist the rule details in the plugin configuration storage

#### Scenario: Restore after reboot
- **WHEN** the server restarts
- **THEN** the system SHALL reload enabled forwarding rules from persistent configuration and reapply them

### Requirement: TCP NAT forwarding management
The system SHALL manage TCP port forwarding by applying `iptables` DNAT, FORWARD, and MASQUERADE rules for each enabled forwarding entry.

#### Scenario: Apply a forwarding rule
- **WHEN** a forwarding rule is enabled and applied
- **THEN** the system SHALL create a DNAT rule, a forward-allow rule, a return-path allow rule, and a MASQUERADE rule for that entry

#### Scenario: Disable a forwarding rule
- **WHEN** a forwarding rule is disabled or deleted
- **THEN** the system SHALL remove only the rules associated with that forwarding entry

### Requirement: IPv4 forwarding enablement
The system SHALL enable IPv4 forwarding when applying forwarding rules.

#### Scenario: Apply with IPv4 forwarding disabled
- **WHEN** IPv4 forwarding is disabled and the user applies forwarding rules
- **THEN** the system SHALL enable IPv4 forwarding before activating the rules

### Requirement: Plugin-owned rule isolation
The system SHALL tag every managed rule with a stable unique comment prefix so status and delete operations affect only plugin-owned rules.

#### Scenario: Inspect managed rules only
- **WHEN** the user opens the forwarding status view
- **THEN** the system SHALL list only rules whose comments match the plugin prefix

#### Scenario: Remove managed rules only
- **WHEN** the user deletes a forwarding rule
- **THEN** the system SHALL leave unrelated system `iptables` rules unchanged

### Requirement: Forwarding diagnostics
The system SHALL provide diagnostics for local addresses, interface selection, routing to each target IP, target-port reachability, and rule counters.

#### Scenario: Validate a rule before apply
- **WHEN** the user checks a forwarding rule
- **THEN** the system SHALL report whether the listen IP exists, the route to the target IP is valid, and the target port is reachable

#### Scenario: Show rule counters
- **WHEN** the user opens the rule status view
- **THEN** the system SHALL show packet and byte counters for each managed forwarding rule when available
