#!/bin/bash
# Utilities around wg-quick VIP operations.

wireguard_util_log() {
    if declare -F log >/dev/null 2>&1; then
        log "$@"
    elif declare -F logger_log >/dev/null 2>&1; then
        logger_log "$@"
    else
        echo "$@"
    fi
}

wireguard_interface_up() {
    local profile="$1"

    if command -v wg >/dev/null 2>&1 && wg show "$profile" >/dev/null 2>&1; then
        return 0
    fi

    if ip link show "$profile" >/dev/null 2>&1; then
        return 0
    fi

    return 1
}

wireguard_up() {
    local profile="${1:-${WG_QUICK_PROFILE:-vip}}"
    if ! command -v wg-quick >/dev/null 2>&1; then
        wireguard_util_log "WARN: wg-quick not found, cannot up ${profile}"
        return 1
    fi

    if wireguard_interface_up "$profile"; then
        wireguard_util_log "WireGuard 配置 ${profile} 已运行"
        return 0
    fi

    if wg-quick up "$profile" >/dev/null 2>&1; then
        wireguard_util_log "已启动 WireGuard 配置 $profile"
    else
        wireguard_util_log "WARN: wg-quick up $profile 执行失败"
        return 1
    fi
}

wireguard_down() {
    local profile="${1:-${WG_QUICK_PROFILE:-vip}}"
    if ! command -v wg-quick >/dev/null 2>&1; then
        wireguard_util_log "WARN: wg-quick not found, cannot down ${profile}"
        return 1
    fi

    if ! wireguard_interface_up "$profile"; then
        wireguard_util_log "WireGuard 配置 ${profile} 未运行，跳过关闭"
        return 0
    fi

    if wg-quick down "$profile" >/dev/null 2>&1; then
        wireguard_util_log "已关闭 WireGuard 配置 $profile"
    else
        wireguard_util_log "WARN: wg-quick down $profile 执行失败"
        return 1
    fi
}
