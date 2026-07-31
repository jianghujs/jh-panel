## Why

The project can already manage firewall allow/deny rules, but it does not provide a first-class way to create and persist TCP NAT port forwarding rules like the existing shell script. We need a panel-managed plugin so these rules survive reboot, can be inspected from the UI, and remain isolated from ordinary firewall port rules.

## What Changes

- Add a new plugin for TCP port forwarding / NAT management.
- Persist forwarding rules in plugin-owned configuration storage.
- Apply and remove `iptables` NAT rules with a stable comment prefix so only plugin-managed rules are touched.
- Enable IPv4 forwarding and restore active forwarding rules after reboot.
- Provide status and diagnostics for routing, interface selection, target reachability, and rule counters.
- Expose a UI for creating, editing, enabling, disabling, and deleting forwarding rules.

## Capabilities

### New Capabilities
- `port-forward-management-panel`: Manage TCP DNAT/FORWARD/MASQUERADE rules, persist them across reboot, and provide status/diagnostics in the panel.

### Modified Capabilities
- None

## Impact

Affected areas include a new plugin module, plugin storage under the server data directory, startup persistence via system service or equivalent boot-time restore, and panel UI/API endpoints for rule lifecycle management. No existing firewall requirement changes are needed.
