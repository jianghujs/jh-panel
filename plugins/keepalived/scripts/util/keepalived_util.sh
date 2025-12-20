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

keepalived_gateway_connectivity_guard() {
    local gateway
    gateway=$(keepalived_resolve_gateway_ip) || gateway=""
    if [ -z "$gateway" ]; then
        keepalived_util_log "WARN: 无法解析网关地址，跳过连通性检查"
        return 0
    fi

    if ! command -v ping >/dev/null 2>&1; then
        keepalived_util_log "WARN: 系统缺少 ping 命令，跳过网关连通性检查"
        return 0
    fi

    local ping_count="${PING_GATEWAY_COUNT:-3}"
    local ping_timeout="${PING_GATEWAY_TIMEOUT:-1}"
    keepalived_util_log "检测网关 $gateway 连通性 (count=$ping_count timeout=$ping_timeout)"
    if ping -c "$ping_count" -W "$ping_timeout" "$gateway" >/dev/null 2>&1; then
        keepalived_util_log "网关 $gateway 连通正常"
        return 0
    fi

    keepalived_util_log "ERROR: 无法连接网关 $gateway，可能发生网络隔离"
    return 1
}
