#!/bin/bash
# MySQL健康检查脚本
# 返回0: 健康，可以作为主库
# 返回1: 不健康，不能作为主库

LOG_FILE="{$SERVER_PATH}/keepalived/keepalived.log"
MYSQL_HOST="localhost"
MYSQL_PORT='33067'
MYSQL_USER='root'
MYSQL_PASS="123456"
TIMEOUT=3
MYSQL_BIN='{$SERVER_PATH}/mysql-apt/bin/usr/bin/mysql'
MYSQL_SOCKET='{$SERVER_PATH}/mysql-apt/mysql.sock'
SLAVE_STATUS=""
KEEPALIVED_SERVICE="${KEEPALIVED_SERVICE:-keepalived}"
KEEPALIVED_STOPPED=0
FATAL_ERROR=0
PRIORITY_TOOL='{$SERVER_PATH}/keepalived/scripts/update_keepalived_priority.sh'
FAIL_PRIORITY="${FAIL_PRIORITY:-90}"

# 写入日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> $LOG_FILE
}

set_keepalived_priority() {
    local target_priority="$1"

    if [ ! -x "$PRIORITY_TOOL" ]; then
        log "WARN: priority工具 $PRIORITY_TOOL 不存在或不可执行"
        return
    fi

    KEEPALIVED_CONF="${KEEPALIVED_CONF:-}" KEEPALIVED_INSTANCE="${KEEPALIVED_INSTANCE:-}" \
        "$PRIORITY_TOOL" "$target_priority"
    local rc=$?

    case $rc in
        0)
            log "优先级已更新为 $target_priority"
            ;;
        3)
            log "当前优先级已是 $target_priority"
            ;;
        2)
            log "WARN: keepalived配置中未找到目标实例"
            ;;
        4)
            log "WARN: keepalived配置文件不存在"
            ;;
        *)
            log "WARN: priority工具执行失败 (code $rc)"
            ;;
    esac
}

stop_keepalived_service() {
    if [ $KEEPALIVED_STOPPED -eq 1 ]; then
        return
    fi

    KEEPALIVED_STOPPED=1
    log "检测到MySQL异常，准备停止keepalived服务以释放VIP"

    if command -v systemctl >/dev/null 2>&1; then
        nohup systemctl stop "$KEEPALIVED_SERVICE" >/dev/null 2>&1 &
    elif command -v service >/dev/null 2>&1; then
        nohup service "$KEEPALIVED_SERVICE" stop >/dev/null 2>&1 &
    else
        pkill keepalived >/dev/null 2>&1 || true
    fi
}

handle_failure() {
    set_keepalived_priority "$FAIL_PRIORITY"
    stop_keepalived_service
    log "MySQL健康检查失败，脚本退出并上报异常"
    exit 1
}

fatal_check() {
    if ! "$@"; then
        FATAL_ERROR=1
    fi
}

require_mysql_socket() {
    if [ ! -S "$MYSQL_SOCKET" ]; then
        log "MySQL socket $MYSQL_SOCKET 不存在，数据库未启动"
        return 1
    fi
    return 0
}

# 检查MySQL服务是否运行
check_mysql_service() {
    if [ ! -x "$MYSQL_BIN" ]; then
        log "MySQL客户端$MYSQL_BIN不可用"
        return 1
    fi

    if [ ! -S "$MYSQL_SOCKET" ]; then
        log "MySQL socket $MYSQL_SOCKET 不存在"
        return 1
    fi

    local result
    result=$(timeout $TIMEOUT "$MYSQL_BIN" --socket="$MYSQL_SOCKET" -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "SELECT 1" 2>&1)
    if [ $? -ne 0 ]; then
        log "MySQL socket连接失败: $result"
        return 1
    fi

    return 0
}

# 检查MySQL端口是否可连接
check_mysql_port() {
    timeout $TIMEOUT bash -c "echo > /dev/tcp/$MYSQL_HOST/$MYSQL_PORT" 2>/dev/null
    if [ $? -ne 0 ]; then
        log "MySQL端口$MYSQL_PORT不可达"
        return 1
    fi
    return 0
}

# 预读取复制状态，供后续检查使用
load_slave_status() {
    local result rc
    result=$(timeout $TIMEOUT "$MYSQL_BIN" -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "SHOW SLAVE STATUS\\G" 2>&1)
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

# 检查是否处于只读模式
check_mysql_writable() {
    local result read_only super_read_only
    result=$(timeout $TIMEOUT "$MYSQL_BIN" -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -N -B -e "SELECT @@GLOBAL.read_only, @@GLOBAL.super_read_only")
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

# 检查MySQL连接和简单查询
check_mysql_connect() {
    local result
    result=$(timeout $TIMEOUT "$MYSQL_BIN" -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "SELECT 1" 2>&1)
    if [ $? -ne 0 ]; then
        log "MySQL连接失败: $result"
        return 1
    fi
    return 0
}

# 检查是否可以作为主库
check_mysql_role() {
    # 如果是从库，检查复制是否正常
    local slave_status="$SLAVE_STATUS"

    if [ -n "$slave_status" ]; then
        # 是从库，检查复制状态
        local io_running=$(echo "$slave_status" | grep "Slave_IO_Running:" | awk '{print $2}')
        local sql_running=$(echo "$slave_status" | grep "Slave_SQL_Running:" | awk '{print $2}')
        local last_error=$(echo "$slave_status" | grep "Last_Error:" | awk -F: '{print $2}' | sed 's/^[ \t]*//')
        
        if [ "$io_running" = "Yes" ] && [ "$sql_running" = "Yes" ]; then
            log "从库复制正常，可以作为备选主库"
            return 0
        else
            log "从库复制异常：IO=$io_running, SQL=$sql_running, Error: $last_error"
            return 1
        fi
    else
        # 是主库或无复制
        log "当前为主库或无复制状态，可以作为主库"
        return 0
    fi
}

# 主检查流程
log "开始MySQL健康检查"

fatal_check require_mysql_socket
fatal_check check_mysql_service
fatal_check check_mysql_port
fatal_check check_mysql_connect

if [ $FATAL_ERROR -ne 0 ]; then
    handle_failure
fi

load_slave_status || exit 1
check_mysql_writable || exit 1
check_mysql_role || exit 1

log "MySQL健康检查通过"
exit 0
