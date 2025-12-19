#!/bin/bash
# MySQL helpers: client wrapper + health-check routines.

MYSQL_CLIENT_READY=0
MYSQL_CLIENT_CMD=()
MYSQL_CLIENT_LOGGER=""

mysql_client_set_logger() {
    MYSQL_CLIENT_LOGGER="$1"
}

mysql_client_log() {
    if [ -n "$MYSQL_CLIENT_LOGGER" ] && declare -F "$MYSQL_CLIENT_LOGGER" >/dev/null 2>&1; then
        "$MYSQL_CLIENT_LOGGER" "$@"
    elif declare -F log >/dev/null 2>&1; then
        log "$@"
    elif declare -F logger_log >/dev/null 2>&1; then
        logger_log "$@"
    else
        echo "$@"
    fi
}

mysql_client_prepare() {
    local timeout="${MYSQL_CONNECT_TIMEOUT:-3}"
    local bin="${MYSQL_BIN:-mysql}"

    if [ ! -x "$bin" ] && command -v mysql >/dev/null 2>&1; then
        bin="$(command -v mysql)"
    fi

    if [ ! -x "$bin" ]; then
        mysql_client_log "ERROR: mysql client not found at $bin"
        return 1
    fi

    MYSQL_CLIENT_CMD=("$bin" "--connect-timeout=$timeout" "--batch")
    if [ -n "${MYSQL_SOCKET:-}" ] && [ -S "$MYSQL_SOCKET" ]; then
        MYSQL_CLIENT_CMD+=("-S" "$MYSQL_SOCKET")
    else
        MYSQL_CLIENT_CMD+=("-h" "${MYSQL_HOST:-127.0.0.1}" "-P" "${MYSQL_PORT:-3306}")
    fi
    MYSQL_CLIENT_CMD+=("-u" "${MYSQL_USER:-root}")
    MYSQL_CLIENT_READY=1
    return 0
}

mysql_client_run() {
    local sql="$1"
    if [ "$MYSQL_CLIENT_READY" -ne 1 ]; then
        mysql_client_prepare || return 1
    fi

    if [ -n "${MYSQL_PASSWORD:-}" ]; then
        MYSQL_PWD="$MYSQL_PASSWORD" "${MYSQL_CLIENT_CMD[@]}" -e "$sql"
    else
        "${MYSQL_CLIENT_CMD[@]}" -e "$sql"
    fi
}

mysql_client_exec() {
    local message="$1"
    local sql="$2"
    local ignore_failure="${3:-0}"

    if mysql_client_run "$sql"; then
        mysql_client_log "$message"
        return 0
    fi

    local rc=$?
    if [ "$ignore_failure" = "1" ]; then
        mysql_client_log "WARN: $message failed but ignored (code $rc)"
        return 0
    fi

    mysql_client_log "ERROR: $message failed (code $rc)"
    return $rc
}

mysql_health_trigger_notify_backup() {
    if [ -x "${NOTIFY_BACKUP_SCRIPT:-}" ]; then
        STOP_KEEPALIVED_ON_BACKUP=1 \
        KEEPALIVED_SERVICE="${KEEPALIVED_SERVICE:-keepalived}" \
        KEEPALIVED_CONF="${KEEPALIVED_CONF:-}" \
        KEEPALIVED_INSTANCE="${KEEPALIVED_INSTANCE:-}" \
        FAIL_PRIORITY="${FAIL_PRIORITY:-90}" \
        "${NOTIFY_BACKUP_SCRIPT}" "${FAIL_PRIORITY:-90}"
        return
    fi

    log "WARN: notify_backup脚本不存在或不可执行，将尝试直接停止keepalived服务"
    if command -v systemctl >/dev/null 2>&1; then
        nohup systemctl stop "${KEEPALIVED_SERVICE:-keepalived}" >/dev/null 2>&1 &
    elif command -v service >/dev/null 2>&1; then
        nohup service "${KEEPALIVED_SERVICE:-keepalived}" stop >/dev/null 2>&1 &
    else
        pkill keepalived >/dev/null 2>&1 || true
    fi
}

mysql_health_handle_failure() {
    mysql_health_trigger_notify_backup
    log "MySQL健康检查失败，脚本退出并上报异常"
    exit 1
}

mysql_health_fatal_check() {
    if ! "$@"; then
        FATAL_ERROR=1
    fi
}

mysql_health_require_socket() {
    if [ ! -S "$MYSQL_SOCKET" ]; then
        log "MySQL socket $MYSQL_SOCKET 不存在，数据库未启动"
        return 1
    fi
    return 0
}

mysql_health_check_service() {
    if [ ! -x "$MYSQL_BIN" ]; then
        log "MySQL客户端$MYSQL_BIN不可用"
        return 1
    fi

    if [ ! -S "$MYSQL_SOCKET" ]; then
        log "MySQL socket $MYSQL_SOCKET 不存在"
        return 1
    fi

    local result
    result=$(timeout $TIMEOUT "$MYSQL_BIN" --socket="$MYSQL_SOCKET" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" 2>&1)
    if [ $? -ne 0 ]; then
        log "MySQL socket连接失败: $result"
        return 1
    fi

    return 0
}

mysql_health_check_port() {
    timeout $TIMEOUT bash -c "echo > /dev/tcp/$MYSQL_HOST/$MYSQL_PORT" 2>/dev/null
    if [ $? -ne 0 ]; then
        log "MySQL端口$MYSQL_PORT不可达"
        return 1
    fi
    return 0
}

mysql_health_load_slave_status() {
    local result rc
    result=$(timeout $TIMEOUT "$MYSQL_BIN" -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SHOW SLAVE STATUS\\G" 2>&1)
    rc=$?
    if [ $rc -ne 0 ]; then
        log "读取复制状态失败: $result"
        return 1
    fi

    if echo "$result" | grep -q "Slave_IO_State"; then
        SLAVE_STATUS="$result"
    else
        SLAVE_STATUS=""
    fi

    return 0
}

mysql_health_check_writable() {
    local result read_only super_read_only
    result=$(timeout $TIMEOUT "$MYSQL_BIN" -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -N -B -e "SELECT @@GLOBAL.read_only, @@GLOBAL.super_read_only")
    if [ $? -ne 0 ]; then
        log "读取read_only状态失败: $result"
        return 1
    fi

    read_only=$(echo "$result" | awk '{print $1}')
    super_read_only=$(echo "$result" | awk '{print $2}')

    if [ "$read_only" != "0" ] || [ "$super_read_only" != "0" ]; then
        if [ -n "$SLAVE_STATUS" ]; then
            log "检测到复制从库，只读模式(read_only=$read_only, super_read_only=$super_read_only)允许存在"
            return 0
        fi

        log "MySQL处于只读模式(read_only=$read_only, super_read_only=$super_read_only)"
        return 1
    fi

    return 0
}

mysql_health_check_connect() {
    local result
    result=$(timeout $TIMEOUT "$MYSQL_BIN" -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" 2>&1)
    if [ $? -ne 0 ]; then
        log "MySQL连接失败: $result"
        return 1
    fi
    return 0
}

mysql_health_check_role() {
    local slave_status="$SLAVE_STATUS"

    if [ -n "$slave_status" ]; then
        local io_running=$(echo "$slave_status" | grep "Slave_IO_Running:" | awk '{print $2}')
        local sql_running=$(echo "$slave_status" | grep "Slave_SQL_Running:" | awk '{print $2}')
        local last_error=$(echo "$slave_status" | grep "Last_Error:" | awk -F: '{print $2}' | sed 's/^[ \t]*//')

        if [ "$io_running" = "Yes" ] && [ "$sql_running" = "Yes" ]; then
            log "从库复制正常，可以作为备选主库"
            return 0
        fi

        log "从库复制异常：IO=$io_running, SQL=$sql_running, Error: $last_error"
        return 1
    fi

    log "当前为主库或无复制状态，可以作为主库"
    return 0
}

mysql_health_run() {
    log "开始MySQL健康检查"
    FATAL_ERROR=0

    mysql_health_fatal_check mysql_health_require_socket
    mysql_health_fatal_check mysql_health_check_service
    mysql_health_fatal_check mysql_health_check_port
    mysql_health_fatal_check mysql_health_check_connect

    if [ ${FATAL_ERROR:-0} -ne 0 ]; then
        mysql_health_handle_failure
    fi

    mysql_health_load_slave_status || exit 1
    mysql_health_check_writable || exit 1
    mysql_health_check_role || exit 1

    log "MySQL健康检查通过"
    exit 0
}
