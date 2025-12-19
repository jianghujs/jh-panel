#!/bin/bash

# Promote the local MySQL replica to primary by disabling read-only mode
# and clearing replication state. Intended to be triggered by keepalived's
# notify_master hook when the VIP floats to this node.

set -u

MYSQL_BIN='{$SERVER_PATH}/mysql-apt/bin/usr/bin/mysql'
MYSQL_USER='root'
MYSQL_PASSWORD='123456'
MYSQL_PORT='33067'
MYSQL_SOCKET='{$SERVER_PATH}/mysql-apt/mysql.sock'
LOG_FILE='{$SERVER_PATH}/keepalived/promote_slave.log'

MYSQL_CMD=()
DESIRED_PRIORITY="${DESIRED_PRIORITY:-100}"
PRIORITY_TOOL='{$SERVER_PATH}/keepalived/scripts/update_keepalived_priority.sh'

log() {
    local now
    now=$(date +'%Y-%m-%d %H:%M:%S')
    echo "${now} [promote_slave] $*" >> "$LOG_FILE"
}

ensure_log_path() {
    local dir
    dir=$(dirname "$LOG_FILE")
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi
}

resolve_mysql_bin() {
    if [ -x "$MYSQL_BIN" ]; then
        return
    fi

    if command -v mysql >/dev/null 2>&1; then
        MYSQL_BIN="$(command -v mysql)"
    fi
}

build_mysql_cmd() {
    MYSQL_CMD=("$MYSQL_BIN" "--connect-timeout=3" "--batch")
    if [ -n "$MYSQL_SOCKET" ] && [ -S "$MYSQL_SOCKET" ]; then
        MYSQL_CMD+=("-S" "$MYSQL_SOCKET")
    else
        MYSQL_CMD+=("-h" "127.0.0.1" "-P" "$MYSQL_PORT")
    fi
    MYSQL_CMD+=("-u" "$MYSQL_USER")
}

run_mysql() {
    local sql="$1"
    if [ -n "$MYSQL_PASSWORD" ]; then
        MYSQL_PWD="$MYSQL_PASSWORD" "${MYSQL_CMD[@]}" -e "$sql"
    else
        "${MYSQL_CMD[@]}" -e "$sql"
    fi
}

execute_step() {
    local message="$1"
    local sql="$2"
    local ignore_failure="${3:-0}"

    if run_mysql "$sql"; then
        log "$message"
        return 0
    fi

    local rc=$?
    if [ "$ignore_failure" = "1" ]; then
        log "WARN: $message failed but ignored (code $rc)"
        return 0
    fi

    log "ERROR: $message failed (code $rc)"
    return $rc
}

update_keepalived_priority() {
    local target_priority="${1:-$DESIRED_PRIORITY}"

    if [ ! -x "$PRIORITY_TOOL" ]; then
        log "WARN: priority工具 $PRIORITY_TOOL 不存在或不可执行"
        return
    fi

    "$PRIORITY_TOOL" "$target_priority"
    local rc=$?

    case $rc in
        0)
            log "已将$KEEPALIVED_INSTANCE 的priority更新为 $target_priority"
            ;;
        3)
            log "$KEEPALIVED_INSTANCE 的priority已是 $target_priority"
            ;;
        2)
            log "WARN: keepalived配置中未找到目标实例"
            ;;
        4)
            log "WARN: keepalived配置文件不存在，无法更新priority"
            ;;
        *)
            log "WARN: priority工具执行失败 (code $rc)"
            ;;
    esac
}

restart_keepalived() {
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl restart keepalived; then
            log "keepalived服务已重启以应用新priority"
        else
            log "WARN: systemctl restart keepalived 失败"
        fi
    elif command -v service >/dev/null 2>&1; then
        if service keepalived restart; then
            log "keepalived服务已通过service重启"
        else
            log "WARN: service keepalived restart 失败"
        fi
    else
        log "WARN: 未找到systemctl或service，无法自动重启keepalived"
    fi
}

up_vip() {
    if command -v wg-quick >/dev/null 2>&1; then
        wg-quick up vip
    else
        log "WARN: wg-quick not found, cannot up vip"
    fi
}

main() {
    ensure_log_path
    resolve_mysql_bin

    if [ ! -x "$MYSQL_BIN" ]; then
        log "ERROR: mysql client not found at $MYSQL_BIN"
        exit 1
    fi

    log "Promotion script triggered"
    build_mysql_cmd

    execute_step "Stopping slave threads" "STOP SLAVE" 1 || exit 1
    execute_step "Resetting slave metadata" "RESET SLAVE ALL" 1 || exit 1
    execute_step "Disabling read_only" "SET GLOBAL read_only = OFF" || exit 1
    execute_step "Disabling super_read_only" "SET GLOBAL super_read_only = OFF" || exit 1

    up_vip
    update_keepalived_priority
    restart_keepalived
    log "Promotion finished successfully"
}

main "$@"
