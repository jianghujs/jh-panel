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

DESIRED_PRIORITY="90"
KEEPALIVED_INSTANCE="VI_1"

# 日志初始化
LOG_FILE="${LOG_FILE:-{$SERVER_PATH}/keepalived/notify_backup.log}"
logger_init "$LOG_FILE" "notify_backup" 100
log() { logger_log "$@"; }
mysql_client_set_logger log

main() {
    log "notify_backup 触发"

    # 设置数据库为只读模式，防止执行过程写入数据
    log "执行 set_db_read_only 设置数据库只读"
    local readonly_output readonly_rc
    pushd {$SERVER_PATH}/jh-panel > /dev/null
    readonly_output=$(python3 plugins/mysql-apt/index.py set_db_read_only 2>&1)
    readonly_rc=$?
    popd > /dev/null
    if [ $readonly_rc -ne 0 ]; then
        log "set_db_read_only 命令执行失败: $readonly_output"
        exit 1
    fi
    log "set_db_read_only 输出: $readonly_output"
    local readonly_status
    readonly_status=$(printf '%s' "$readonly_output" | jq -r '.status' 2>/dev/null || echo "")
    if [ "$readonly_status" != "true" ]; then
        log "set_db_read_only 返回失败状态或响应无法解析，退出"
        exit 1
    fi



    log "执行 init_slave_status 初始化从库状态"
    local init_output init_rc
    pushd {$SERVER_PATH}/jh-panel > /dev/null
    init_output=$(python3 plugins/mysql-apt/index.py init_slave_status 2>&1)
    init_rc=$?
    popd > /dev/null
    if [ $init_rc -ne 0 ]; then
        log "init_slave_status 命令执行失败: $init_output"
        exit 1
    fi
    log "init_slave_status 输出: $init_output"
    local init_status
    init_status=$(printf '%s' "$init_output" | jq -r '.status' 2>/dev/null || echo "")
    if [ "$init_status" != "true" ]; then
        log "init_slave_status 返回失败状态或响应无法解析，退出"
        exit 1
    fi


    log "停止 OpenResty"
    local openresty_output openresty_rc
    pushd {$SERVER_PATH}/jh-panel > /dev/null
    openresty_output=$(python3 plugins/openresty/index.py stop 2>&1)
    openresty_rc=$?
    popd > /dev/null
    if [ $openresty_rc -ne 0 ]; then
        log "OpenResty 停止命令执行失败: $openresty_output"
        exit 1
    fi
    if [ "$openresty_output" != "ok" ]; then
        log "OpenResty 停止失败: $openresty_output"
        exit 1
    fi
    log "OpenResty 停止完成"
    
     # 设置优先级
    priority_update "$DESIRED_PRIORITY"
    if [ $? -ne 0 ]; then
        log "priority_update 更新失败"
        exit 1
    fi
    log "priority_update 更新成功"


    # 发送通知
    log "发送降级通知"
    pushd {$SERVER_PATH}/jh-panel > /dev/null 
    python3 {$SERVER_PATH}/jh-panel/plugins/keepalived/scripts/util/notify_util.py backup
    popd > /dev/null
    log "通知发送完毕"

    log "notify_backup 执行完毕"
}

main "$@"
