#!/bin/bash
# Utilities for manipulating keepalived instance priority.

PRIORITY_TOOL_DEFAULT="{$SERVER_PATH}/keepalived/scripts/update_keepalived_priority.sh"

priority_util_log() {
    if declare -F log >/dev/null 2>&1; then
        log "$@"
    elif declare -F logger_log >/dev/null 2>&1; then
        logger_log "$@"
    else
        echo "$@"
    fi
}

priority_update() {
    local target_priority="$1"
    if [ -z "$target_priority" ]; then
        return 0
    fi

    local tool
    tool="${PRIORITY_TOOL:-$PRIORITY_TOOL_DEFAULT}"

    if [ ! -x "$tool" ]; then
        priority_util_log "WARN: priority工具 $tool 不存在或不可执行"
        return 1
    fi

    KEEPALIVED_CONF="${KEEPALIVED_CONF:-}" KEEPALIVED_INSTANCE="${KEEPALIVED_INSTANCE:-}" \
        "$tool" "$target_priority"
    local rc=$?

    case $rc in
        0)
            priority_util_log "已将${KEEPALIVED_INSTANCE:-目标实例}的priority更新为 $target_priority"
            ;;
        3)
            priority_util_log "${KEEPALIVED_INSTANCE:-目标实例}的priority已是 $target_priority"
            ;;
        2)
            priority_util_log "WARN: keepalived配置中未找到目标实例"
            ;;
        4)
            priority_util_log "WARN: keepalived配置文件不存在，无法更新priority"
            ;;
        *)
            priority_util_log "WARN: priority工具执行失败 (code $rc)"
            ;;
    esac

    return 0
}
