#!/bin/bash

# Promote the local MySQL replica to primary by disabling read-only mode
# and clearing replication state. Intended to be triggered by keepalived's
# notify_master hook when the VIP floats to this node.

set -u

MYSQL_BIN='/usr/bin/mysql'
MYSQL_USER='root'
MYSQL_PASSWORD='123456'
MYSQL_PORT='3306'
MYSQL_SOCKET='/tmp/mysql.sock'
LOG_FILE='{$SERVER_PATH}/keepalived/promote_slave.log'

MYSQL_CMD=()

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

    log "Promotion finished successfully"
}

main "$@"

