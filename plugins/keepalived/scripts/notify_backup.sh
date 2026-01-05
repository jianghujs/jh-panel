#!/bin/bash

# keepalived notify_backup 入口：降级本节点，释放 VIP 并降低优先级。

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
FAIL_PRIORITY="${FAIL_PRIORITY:-90}"
KEEPALIVED_SERVICE="${KEEPALIVED_SERVICE:-keepalived}"
STOP_KEEPALIVED_ON_BACKUP="${STOP_KEEPALIVED_ON_BACKUP:-0}"

# 日志初始化
LOG_FILE="${LOG_FILE:-{$SERVER_PATH}/keepalived/notify_backup.log}"
logger_init "$LOG_FILE" "notify_backup" 100
log() { logger_log "$@"; }
mysql_client_set_logger log

main() {
    local target_priority="${1:-$FAIL_PRIORITY}"
    log "notify_backup 触发，目标 priority: $target_priority"

    log "切换 MySQL 为只读模式"
    mysql_client_exec "启用 super_read_only" "SET GLOBAL super_read_only = ON" || exit 1
    mysql_client_exec "启用 read_only" "SET GLOBAL read_only = ON" || exit 1

    # WireGuard配置切换：Backup启用novip，禁用vip
    # wireguard_up "novip"
    # wireguard_down "vip"
    
    # 更新优先级
    priority_update "$target_priority"

    # 发送通知
    log "发送降级通知"
    pushd /www/server/jh-panel > /dev/null 
    python3 /www/server/jh-panel/plugins/keepalived/scripts/util/notify_util.py backup
    popd > /dev/null
    log "发送降级通知完成"

    log "notify_backup 执行完毕"
}

main "$@"
