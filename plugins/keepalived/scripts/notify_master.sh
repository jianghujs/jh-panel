#!/bin/bash

# keepalived notify_master 入口：提升本地 MySQL 为主库并上报状态。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UTIL_DIR="$SCRIPT_DIR/util"
. "$UTIL_DIR/logging_util.sh"
. "$UTIL_DIR/priority_util.sh"
. "$UTIL_DIR/wireguard_util.sh"
. "$UTIL_DIR/keepalived_util.sh"

DESIRED_PRIORITY="${DESIRED_PRIORITY:-100}"
KEEPALIVED_SERVICE="${KEEPALIVED_SERVICE:-keepalived}"
RESTART_KEEPALIVED_ON_PROMOTE="${RESTART_KEEPALIVED_ON_PROMOTE:-0}"
VIP_GATEWAY_IP="${VIP_GATEWAY_IP:-}"
PING_GATEWAY_COUNT="${PING_GATEWAY_COUNT:-3}"
PING_GATEWAY_TIMEOUT="${PING_GATEWAY_TIMEOUT:-1}"

# 日志初始化
LOG_FILE="${LOG_FILE:-{$SERVER_PATH}/keepalived/notify_master.log}"
logger_init "$LOG_FILE" "notify_master" 100
log() { logger_log "$@"; }

main() {
    log "notify_master 触发"

    if ! keepalived_gateway_connectivity_guard; then
        log "无法连接到网关，可能发生孤岛，停止 keepalived 并终止提升流程"
        keepalived_stop "$KEEPALIVED_SERVICE"
        exit 1
    fi

    log "等待3秒，确保原主降级后再提升"
    sleep 3

    local delete_output delete_rc
    log "执行 delete_slave 清理从库配置"
    pushd /www/server/jh-panel > /dev/null
    delete_output=$(python3 plugins/mysql-apt/index.py delete_slave 2>&1)
    delete_rc=$?
    popd > /dev/null
    if [ $delete_rc -ne 0 ]; then
        log "delete_slave 命令执行失败: $delete_output"
        exit 1
    fi
    log "delete_slave 输出: $delete_output"
    local delete_status
    delete_status=$(printf '%s' "$delete_output" | jq -r '.status' 2>/dev/null || echo "")
    if [ "$delete_status" != "true" ]; then
        log "delete_slave 返回失败状态或响应无法解析，退出"
        exit 1
    fi

    # WireGuard配置切换：Master启用vip，禁用novip
    # wireguard_up "vip"
    # wireguard_down "novip"
    
    # 更新优先级
    priority_update "$DESIRED_PRIORITY"

    if [ "$RESTART_KEEPALIVED_ON_PROMOTE" = "1" ]; then
        keepalived_restart "$KEEPALIVED_SERVICE"
    else
        log "跳过 keepalived 重启 (RESTART_KEEPALIVED_ON_PROMOTE=$RESTART_KEEPALIVED_ON_PROMOTE)"
    fi

    # 发送通知
    log "发送提升为主通知"
    pushd /www/server/jh-panel > /dev/null 
    python3 /www/server/jh-panel/plugins/keepalived/scripts/util/notify_util.py master
    popd > /dev/null
    log "发送提升为主通知完成"

    log "notify_master 执行完毕"
}

main "$@"
