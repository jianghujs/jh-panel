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
