#!/bin/bash

# keepalived notify_master 入口：提升本地 MySQL 为主库并上报状态。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UTIL_DIR="$SCRIPT_DIR/util"
. "$UTIL_DIR/logging_util.sh"
. "$UTIL_DIR/mysql_util.sh"
. "$UTIL_DIR/priority_util.sh"
. "$UTIL_DIR/wireguard_util.sh"
. "$UTIL_DIR/keepalived_util.sh"

MYSQL_BIN="${MYSQL_BIN:-{$SERVER_PATH}/mysql-apt/bin/usr/bin/mysql}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-123456}"
MYSQL_PORT="${MYSQL_PORT:-33067}"
MYSQL_SOCKET="${MYSQL_SOCKET:-{$SERVER_PATH}/mysql-apt/mysql.sock}"
MYSQL_CONNECT_TIMEOUT="${MYSQL_CONNECT_TIMEOUT:-3}"
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
DESIRED_PRIORITY="${DESIRED_PRIORITY:-100}"
WG_QUICK_PROFILE="${WG_QUICK_PROFILE:-vip}"
KEEPALIVED_SERVICE="${KEEPALIVED_SERVICE:-keepalived}"
RESTART_KEEPALIVED_ON_PROMOTE="${RESTART_KEEPALIVED_ON_PROMOTE:-0}"

# 日志初始化
LOG_FILE="${LOG_FILE:-{$SERVER_PATH}/keepalived/notify_master.log}"
logger_init "$LOG_FILE" "notify_master" 100
log() { logger_log "$@"; }

mysql_client_set_logger log

main() {
    log "notify_master 触发"

    # MySQL提升为主库
    mysql_client_prepare || exit 1
    mysql_client_exec "Stopping slave threads" "STOP SLAVE" 1 || exit 1
    mysql_client_exec "Resetting slave metadata" "RESET SLAVE ALL" 1 || exit 1
    mysql_client_exec "Disabling read_only" "SET GLOBAL read_only = OFF" || exit 1
    mysql_client_exec "Disabling super_read_only" "SET GLOBAL super_read_only = OFF" || exit 1

    # 开启WireGuard配置
    wireguard_up "$WG_QUICK_PROFILE"
    # 更新优先级
    priority_update "$DESIRED_PRIORITY"

    if [ "$RESTART_KEEPALIVED_ON_PROMOTE" = "1" ]; then
        keepalived_restart "$KEEPALIVED_SERVICE"
    else
        log "跳过 keepalived 重启 (RESTART_KEEPALIVED_ON_PROMOTE=$RESTART_KEEPALIVED_ON_PROMOTE)"
    fi
    log "notify_master 执行完毕"
}

main "$@"
