## Context

The current project has a firewall API for port allow/deny rules, plus separate plugins for FRP and HAProxy. None of them model the exact behavior of the shell script, which is kernel-level TCP forwarding between interfaces using `iptables` DNAT, FORWARD, and MASQUERADE rules. The new plugin must be operationally safe, reboot-persistent, and easy to reason about from the panel.

## Goals / Non-Goals

**Goals:**
- Manage TCP NAT forwarding rules from the panel.
- Persist rules so they are restored after reboot.
- Keep plugin-owned rules isolated with stable metadata.
- Provide verification and diagnostics for operators.

**Non-Goals:**
- Do not replace general firewall management.
- Do not support full `nftables`, `ufw`, or `firewalld` management in v1.
- Do not implement application-layer proxying or load balancing.
- Do not auto-discover or auto-correct arbitrary system firewall state.

## Decisions

1. **Use a dedicated plugin instead of extending `firewall_api`**. The behavior is not a simple allow/deny rule; it introduces NAT, forward-chain policy, persistence, and boot recovery. Keeping this separate avoids mixing two different operational domains.

2. **Store rules in plugin-owned JSON config**. The plugin should treat its configuration file as the source of truth, then render rules into `iptables` on apply. This matches the project’s panel-driven management model and makes reboot recovery deterministic.

3. **Restore via boot-time service or startup hook**. Reapplying from config at boot is more predictable than relying on ad hoc runtime state or manual `iptables-save` editing. This also keeps the panel as the authoritative control plane.

3a. **Use native iptables persistence when available**. When `netfilter-persistent`, `iptables-persistent`, or distro `service iptables save` support exists, the plugin should trigger that save path after apply/delete. The plugin-owned config remains the source of truth, and the boot-time restore service remains a fallback for systems without those packages.

4. **Support `iptables` only in v1**. The existing script already uses `iptables`, and the panel environment appears to rely on it for lower-level firewall behavior. Adding backend abstraction now would increase complexity without improving the initial use case.

5. **Use comment-prefixed rules for safe ownership**. Every NAT and FORWARD rule must carry a unique comment prefix so delete/status operations can target only plugin-owned entries. This prevents accidental modification of unrelated system rules.

6. **Model each forward as a fully specified tuple**: listen IP, listen interface, listen port, target IP, target interface, target port, enabled flag, and remark. This matches the shell script’s assumptions and avoids ambiguous routing behavior.

## Risks / Trade-offs

- [Boot restore may race with network readiness] -> Use a boot-time unit that runs after networking is up, and keep restore idempotent.
- [iptables backend differences across distributions] -> Document `iptables` as the supported backend for v1 and surface version/state in diagnostics.
- [Manual system firewall changes can conflict with plugin-managed rules] -> Restrict delete/apply to the plugin comment prefix and surface the active rules clearly in the UI.
- [Misconfigured interfaces or routing can break forwarding] -> Include preflight checks for local IPs, route lookup, and target-port reachability before apply.

## Migration Plan

1. Introduce the new plugin with no impact on existing firewall rules.
2. Seed plugin config with the current forwarding definitions as default examples.
3. On first apply, create the plugin-owned `iptables` rules and boot-time restore entry.
4. Validate that restart restores the same rule set from config.
5. If rollback is needed, disable the boot-time restore and remove the plugin-owned rules only.

## Open Questions

- Should the boot-time restore be implemented as a dedicated systemd oneshot unit, or by reusing an existing startup mechanism already used by other plugins?
- Should the UI allow multiple independent forwarding rules per plugin instance, or one ordered rule list with enable/disable toggles?
