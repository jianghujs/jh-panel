#!/bin/bash

# keepalived notify_backup 入口：降级本节点，释放 VIP 并降低优先级。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UTIL_DIR="$SCRIPT_DIR/util"
. "$UTIL_DIR/logging_util.sh"
. "$UTIL_DIR/priority_util.sh"
. "$UTIL_DIR/wireguard_util.sh"
. "$UTIL_DIR/keepalived_util.sh"

FAIL_PRIORITY="${FAIL_PRIORITY:-90}"
KEEPALIVED_SERVICE="${KEEPALIVED_SERVICE:-keepalived}"
STOP_KEEPALIVED_ON_BACKUP="${STOP_KEEPALIVED_ON_BACKUP:-0}"
WG_QUICK_PROFILE="${WG_QUICK_PROFILE:-vip}"

# 日志初始化
LOG_FILE="${LOG_FILE:-{$SERVER_PATH}/keepalived/notify_backup.log}"
logger_init "$LOG_FILE" "notify_backup" 100
log() { logger_log "$@"; }

main() {
    local target_priority="${1:-$FAIL_PRIORITY}"
    log "notify_backup 触发，目标 priority: $target_priority"

    # 关闭WireGuard配置（解决Wireguard不支持VIP漂移问题）
    # wireguard_down "$WG_QUICK_PROFILE"
    
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
