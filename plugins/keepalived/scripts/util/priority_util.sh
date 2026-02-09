#!/bin/bash
# Utilities for manipulating keepalived instance priority.

PRIORITY_DEFAULT_CONF="{$SERVER_PATH}/keepalived/etc/keepalived/keepalived.conf"
PRIORITY_DEFAULT_INSTANCE="VI_1"

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

    if ! [[ "$target_priority" =~ ^[0-9]+$ ]]; then
        priority_util_log "WARN: priority 必须是数字，当前值: $target_priority"
        return 0
    fi

    local conf="${KEEPALIVED_CONF:-$PRIORITY_DEFAULT_CONF}"
    local instance="${KEEPALIVED_INSTANCE:-$PRIORITY_DEFAULT_INSTANCE}"

    if [ ! -f "$conf" ]; then
        priority_util_log "WARN: keepalived配置文件 $conf 不存在，无法更新 priority"
        return 0
    fi

    local tmp rc
    tmp=$(mktemp "/tmp/priority_util.XXXXXX") || return 0

    python3 - "$conf" "$instance" "$target_priority" > "$tmp" <<'PY'
import re
import sys
from pathlib import Path

if len(sys.argv) != 4:
    sys.exit(1)

conf_path = Path(sys.argv[1])
instance = sys.argv[2]
desired = sys.argv[3]

text = conf_path.read_text()
pattern = re.compile(rf"(vrrp_instance\s+{re.escape(instance)}\s*{{.*?\bpriority\s+)(\d+)", re.S)
match = pattern.search(text)

if not match:
    sys.stdout.write(text)
    sys.exit(2)

current = match.group(2)
if current == desired:
    sys.stdout.write(text)
    sys.exit(3)

updated = pattern.sub(lambda m: m.group(1) + desired, text, count=1)
sys.stdout.write(updated)
sys.exit(0)
PY
    rc=$?

    local display_instance="$instance"

    case $rc in
        0)
            if cat "$tmp" > "$conf"; then
                priority_util_log "已将${display_instance}的priority更新为 $target_priority"
            else
                priority_util_log "WARN: priority写入 $conf 失败"
            fi
            ;;
        3)
            priority_util_log "${display_instance}的priority已是 $target_priority"
            ;;
        2)
            priority_util_log "WARN: keepalived配置中未找到实例 ${display_instance}"
            ;;
        *)
            priority_util_log "WARN: priority更新失败 (code $rc)"
            ;;
    esac

    rm -f "$tmp"
    return 0
}
