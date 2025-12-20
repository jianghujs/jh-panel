#!/bin/bash
# Utilities for controlling keepalived service state.

keepalived_util_log() {
    if declare -F log >/dev/null 2>&1; then
        log "$@"
    elif declare -F logger_log >/dev/null 2>&1; then
        logger_log "$@"
    else
        echo "$@"
    fi
}

keepalived_restart() {
    local service="${1:-${KEEPALIVED_SERVICE:-keepalived}}"

    if command -v systemctl >/dev/null 2>&1; then
        if systemctl restart "$service"; then
            keepalived_util_log "$service 服务已通过 systemctl 重启"
            return 0
        fi
        keepalived_util_log "WARN: systemctl restart $service 失败"
    elif command -v service >/dev/null 2>&1; then
        if service "$service" restart; then
            keepalived_util_log "$service 服务已通过 service 重启"
            return 0
        fi
        keepalived_util_log "WARN: service $service restart 失败"
    else
        keepalived_util_log "WARN: 未找到 systemctl 或 service，无法自动重启 $service"
        return 1
    fi
}

keepalived_stop() {
    local service="${1:-${KEEPALIVED_SERVICE:-keepalived}}"

    if command -v systemctl >/dev/null 2>&1; then
        if systemctl stop "$service"; then
            keepalived_util_log "$service 服务已通过 systemctl 停止"
            return 0
        fi
        keepalived_util_log "WARN: systemctl stop $service 失败"
    elif command -v service >/dev/null 2>&1; then
        if service "$service" stop; then
            keepalived_util_log "$service 服务已通过 service 停止"
            return 0
        fi
        keepalived_util_log "WARN: service $service stop 失败"
    else
        if pkill keepalived >/dev/null 2>&1; then
            keepalived_util_log "已通过 pkill keepalived 释放 VIP"
            return 0
        fi
        keepalived_util_log "WARN: 无法停止 keepalived (未找到 systemctl/service)"
        return 1
    fi
}

# Resolve the configured gateway IP or infer it from the default route.
keepalived_resolve_gateway_ip() {
    local explicit="${1:-${VIP_GATEWAY_IP:-}}"
    if [ -n "$explicit" ]; then
        echo "$explicit"
        return 0
    fi

    if command -v ip >/dev/null 2>&1; then
        local gw
        gw=$(ip route | awk '/default/ {print $3; exit}')
        if [ -n "$gw" ]; then
            echo "$gw"
            return 0
        fi
    fi
    return 1
}

# Parse keepalived config and return the first virtual IP.
keepalived_detect_config_virtual_ip() {
    local config="${1:-${KEEPALIVED_CONFIG:-}}"
    if [ -z "$config" ] || [ ! -f "$config" ]; then
        return 1
    fi

    awk '
        /^[ \t]*#/ {next}
        /virtual_ipaddress/ {capture=1; next}
        capture {
            if ($0 ~ /}/) {exit}
            gsub(/[,;]/, "")
            for (i = 1; i <= NF; ++i) {
                if ($i != "") {print $i; exit}
            }
        }
    ' "$config"
}

# Parse keepalived config and return the interface name.
keepalived_detect_config_interface() {
    local config="${1:-${KEEPALIVED_CONFIG:-}}"
    if [ -z "$config" ] || [ ! -f "$config" ]; then
        return 1
    fi

    awk '
        /^[ \t]*#/ {next}
        /^[ \t]*interface[ \t]+/ {print $2; exit}
    ' "$config"
}

# Resolve VIP using overrides or config.
keepalived_resolve_vip_ip() {
    local explicit="${1:-${VIP_CHECK_IP:-}}"
    if [ -n "$explicit" ]; then
        echo "$explicit"
        return 0
    fi

    local vip
    vip=$(keepalived_detect_config_virtual_ip) || vip=""
    if [ -n "$vip" ]; then
        echo "$vip"
        return 0
    fi
    return 1
}

# Resolve interface for ARP probing.
keepalived_resolve_vip_interface() {
    local explicit="${1:-${VIP_ARP_INTERFACE:-}}"
    if [ -n "$explicit" ]; then
        echo "$explicit"
        return 0
    fi

    local iface
    iface=$(keepalived_detect_config_interface) || iface=""
    if [ -n "$iface" ]; then
        echo "$iface"
        return 0
    fi

    echo "${KEEPALIVED_DEFAULT_INTERFACE:-client}"
    return 0
}

# Ping gateway / ARP VIP to detect if another master already holds the VIP.
keepalived_existing_master_check() {
    local ping_count="${PING_GATEWAY_COUNT:-3}"
    local ping_timeout="${PING_GATEWAY_TIMEOUT:-1}"
    local arping_count="${ARPING_DETECT_COUNT:-3}"
    local conflict=0
    local gateway_attempted=0
    local arping_attempted=0

    local gateway
    gateway=$(keepalived_resolve_gateway_ip) || gateway=""
    if [ -n "$gateway" ] && command -v ping >/dev/null 2>&1; then
        gateway_attempted=1
        keepalived_util_log "尝试 ping 网关 $gateway"
        if ping -c "$ping_count" -W "$ping_timeout" "$gateway" >/dev/null 2>&1; then
            keepalived_util_log "网关 $gateway ping 正常"
        else
            keepalived_util_log "WARN: ping 网关 $gateway 失败，可能已有主占用 VIP"
            conflict=1
        fi
    else
        keepalived_util_log "WARN: 缺少网关信息或 ping 命令不可用，跳过 ping 检查"
    fi

    local vip_ip
    vip_ip=$(keepalived_resolve_vip_ip) || vip_ip=""
    local vip_iface
    vip_iface=$(keepalived_resolve_vip_interface) || vip_iface=""
    if command -v arping >/dev/null 2>&1 && [ -n "$vip_ip" ] && [ -n "$vip_iface" ]; then
        arping_attempted=1
        keepalived_util_log "使用 arping 检查 VIP $vip_ip (接口 $vip_iface)"
        if arping -q -D -c "$arping_count" -I "$vip_iface" "$vip_ip"; then
            keepalived_util_log "ARP 检查通过：VIP $vip_ip 未被其他主占用"
        else
            keepalived_util_log "WARN: arping 检测到 VIP $vip_ip 可能已在其他主上"
            conflict=1
        fi
    else
        keepalived_util_log "WARN: 缺少 arping 命令或 VIP/接口信息，跳过 ARP 检查"
    fi

    if [ "$gateway_attempted" -eq 0 ] && [ "$arping_attempted" -eq 0 ]; then
        keepalived_util_log "WARN: 未执行任何主存在性检测，默认继续"
        return 0
    fi

    if [ "$conflict" -ne 0 ]; then
        keepalived_util_log "检测到网络中已有主占用 VIP"
        return 1
    fi
    return 0
}
