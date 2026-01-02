#!/bin/bash
# MySQL健康检查入口脚本，主体逻辑位于 util/mysql_util.sh 中。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UTIL_DIR="$SCRIPT_DIR/util"
. "$UTIL_DIR/logging_util.sh"
. "$UTIL_DIR/mysql_util.sh"
. "$UTIL_DIR/keepalived_util.sh"
. "$UTIL_DIR/priority_util.sh"

MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-33067}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-123456}"
TIMEOUT="${TIMEOUT:-3}"
MYSQL_BIN="${MYSQL_BIN:-{$SERVER_PATH}/mysql-apt/bin/usr/bin/mysql}"
MYSQL_SOCKET="${MYSQL_SOCKET:-{$SERVER_PATH}/mysql-apt/mysql.sock}"
KEEPALIVED_SERVICE="${KEEPALIVED_SERVICE:-keepalived}"
FAIL_PRIORITY="${FAIL_PRIORITY:-90}"
NOTIFY_BACKUP_SCRIPT="${NOTIFY_BACKUP_SCRIPT:-{$SERVER_PATH}/keepalived/scripts/notify_backup.sh}"
SLAVE_STATUS=""

# 日志初始化
LOG_FILE="${LOG_FILE:-{$SERVER_PATH}/keepalived/chk_mysql.log}"
logger_init "$LOG_FILE" "chk_mysql" 100
log() { logger_log "$@"; }

# 执行MySQL健康检查
mysql_health_run
