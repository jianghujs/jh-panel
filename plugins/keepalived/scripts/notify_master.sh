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


DESIRED_PRIORITY="100"
KEEPALIVED_INSTANCE="VI_1"
KEEPALIVED_SERVICE="keepalived"
RESTART_KEEPALIVED_ON_PROMOTE="1"

# 日志初始化
LOG_FILE="${LOG_FILE:-{$SERVER_PATH}/keepalived/notify_master.log}"
logger_init "$LOG_FILE" "notify_master" 100
log() { logger_log "$@"; }

mysql_client_set_logger log

main() {
    log "notify_master 触发"

    
    local delete_output delete_rc
    log "执行 delete_slave 清理从库配置"
    pushd {$SERVER_PATH}/jh-panel > /dev/null
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


    
    log "启动 OpenResty"
    local openresty_output openresty_rc
    pushd {$SERVER_PATH}/jh-panel > /dev/null
    openresty_output=$(python3 plugins/openresty/index.py start 2>&1)
    openresty_rc=$?
    popd > /dev/null
    if [ $openresty_rc -ne 0 ]; then
        log "OpenResty 启动命令执行失败: $openresty_output"
        exit 1
    fi
    if [ "$openresty_output" != "ok" ]; then
        log "OpenResty 启动失败: $openresty_output"
        exit 1
    fi
    log "OpenResty 启动完成"

    # 更新优先级
    priority_update "$DESIRED_PRIORITY"

    if [ "$RESTART_KEEPALIVED_ON_PROMOTE" = "1" ]; then
        keepalived_restart "$KEEPALIVED_SERVICE"
    else
        log "跳过 keepalived 重启 (RESTART_KEEPALIVED_ON_PROMOTE=$RESTART_KEEPALIVED_ON_PROMOTE)"
    fi

    # 发送通知
    log "发送提升为主通知"
    
    pushd {$SERVER_PATH}/jh-panel > /dev/null 
    python3 {$SERVER_PATH}/jh-panel/plugins/keepalived/scripts/util/notify_util.py master
    popd > /dev/null
    log "通知发送完毕"

    log "notify_master 执行完毕"
}

main "$@"
