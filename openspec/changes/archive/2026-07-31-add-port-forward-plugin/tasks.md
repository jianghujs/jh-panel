## 1. Plugin Scaffold and Data Model

- [x] 1.1 Create the `port_forward` plugin directory structure and metadata files
- [x] 1.2 Define the persistent config format for forwarding rules
- [x] 1.3 Initialize the plugin with an empty forwarding rule list

## 2. Rule Engine and Persistence

- [x] 2.1 Implement config load/save helpers for forwarding rules
- [x] 2.2 Implement validation for IPs, ports, interfaces, and enabled state
- [x] 2.3 Implement rule rendering for `iptables` DNAT, FORWARD, and MASQUERADE entries
- [x] 2.4 Implement safe delete logic using the plugin comment prefix

## 3. Boot Restore and Diagnostics

- [x] 3.1 Add IPv4 forwarding enablement during apply
- [x] 3.2 Add boot-time restore integration so enabled rules survive restart
- [x] 3.3 Implement diagnostics for local addresses, routes, target reachability, and counters
- [x] 3.4 Verify apply/delete/status/check behavior with configured forwarding entries

## 4. Panel UI and Operator Flow

- [x] 4.1 Build the forwarding rule list and edit form UI
- [x] 4.2 Add apply, delete, enable, disable, and refresh actions
- [x] 4.3 Add status and diagnostic views for operators
- [x] 4.4 Add confirmation messaging for high-risk apply/delete operations
