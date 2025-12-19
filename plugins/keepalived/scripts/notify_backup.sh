#!/bin/bash

# Handle keepalived notify_backup events (or forced demotion from
# chk_mysql.sh) by releasing the VIP, lowering keepalived priority and
# optionally stopping the local keepalived service.

set -u

LOG_FILE='{$SERVER_PATH}/keepalived/notify_backup.log'
PRIORITY_TOOL='{$SERVER_PATH}/keepalived/scripts/update_keepalived_priority.sh'
DEFAULT_PRIORITY="${FAIL_PRIORITY:-90}"
KEEPALIVED_SERVICE="${KEEPALIVED_SERVICE:-keepalived}"
STOP_KEEPALIVED_ON_BACKUP="${STOP_KEEPALIVED_ON_BACKUP:-0}"
WG_QUICK_PROFILE="${WG_QUICK_PROFILE:-vip}"

log() {
    local now
    now=$(date +'%Y-%m-%d %H:%M:%S')
    echo "${now} [notify_backup] $*" >> "$LOG_FILE"
}

ensure_log_path() {
    local dir
    dir=$(dirname "$LOG_FILE")
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi
}

down_vip() {
    if ! command -v wg-quick >/dev/null 2>&1; then
        log "WARN: wg-quick not found, cannot down VIP"
        return
    fi

    if wg-quick down "$WG_QUICK_PROFILE" >/dev/null 2>&1; then
        log "已关闭 WireGuard 配置 $WG_QUICK_PROFILE 以释放 VIP"
    else
        log "WARN: wg-quick down $WG_QUICK_PROFILE 执行失败"
    fi
}

set_keepalived_priority() {
    local target_priority="$1"

    if [ -z "$target_priority" ]; then
        return
    fi

    if [ ! -x "$PRIORITY_TOOL" ]; then
        log "WARN: priority 工具 $PRIORITY_TOOL 不存在或不可执行"
        return
    fi

    KEEPALIVED_CONF="${KEEPALIVED_CONF:-}" KEEPALIVED_INSTANCE="${KEEPALIVED_INSTANCE:-}" \
        "$PRIORITY_TOOL" "$target_priority"
    local rc=$?

    case $rc in
        0)
            log "已将 $KEEPALIVED_INSTANCE 的 priority 调整为 $target_priority"
            ;;
        3)
            log "$KEEPALIVED_INSTANCE 的 priority 已是 $target_priority"
            ;;
        2)
            log "WARN: keepalived 配置中未找到实例"
            ;;
        4)
            log "WARN: keepalived 配置文件不存在"
            ;;
        *)
            log "WARN: priority 工具执行失败 (code $rc)"
            ;;
    esac
}

stop_keepalived_service() {
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl stop "$KEEPALIVED_SERVICE" >/dev/null 2>&1; then
            log "已通过 systemctl 停止 keepalived 服务"
        else
            log "WARN: systemctl stop $KEEPALIVED_SERVICE 失败"
        fi
    elif command -v service >/dev/null 2>&1; then
        if service "$KEEPALIVED_SERVICE" stop >/dev/null 2>&1; then
            log "已通过 service 停止 keepalived 服务"
        else
            log "WARN: service $KEEPALIVED_SERVICE stop 失败"
        fi
    else
        pkill keepalived >/dev/null 2>&1 && log "已通过 pkill 终止 keepalived" || \
            log "WARN: 无法停止 keepalived (未找到 systemctl/service)"
    fi
}

main() {
    ensure_log_path
    local target_priority="${1:-$DEFAULT_PRIORITY}"
    log "notify_backup 触发，目标 priority: $target_priority"

    down_vip
    set_keepalived_priority "$target_priority"

    if [ "$STOP_KEEPALIVED_ON_BACKUP" = "1" ]; then
        stop_keepalived_service
    fi

    log "notify_backup 执行完毕"
}

main "$@"
