#!/bin/bash
# Utilities for keepalived alert settings + notifications.

ALERT_SETTINGS_FILE="${ALERT_SETTINGS_FILE:-{$SERVER_PATH}/keepalived/config/alert_settings.json}"
KEEPALIVED_NOTIFY_HELPER="${KEEPALIVED_NOTIFY_HELPER:-/www/server/jh-panel/plugins/keepalived/notify_util.py}"
KEEPALIVED_CONF_FILE="${KEEPALIVED_CONF_FILE:-{$SERVER_PATH}/keepalived/etc/keepalived/keepalived.conf}"

alert_util_bool(){
    local key="$1"
    if [ ! -f "$ALERT_SETTINGS_FILE" ]; then
        echo "0"
        return
    fi
    python3 - "$ALERT_SETTINGS_FILE" "$key" <<'PY'
import json
import sys
path = sys.argv[1]
key = sys.argv[2]
try:
    with open(path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
except Exception:
    data = {}
value = bool(data.get(key, False))
print('1' if value else '0')
PY
}

alert_util_send_notification(){
    local title="$1"
    local body="$2"
    local stype="$3"
    local trigger="${4:-600}"
    if [ ! -x "$KEEPALIVED_NOTIFY_HELPER" ]; then
        echo "notify helper $KEEPALIVED_NOTIFY_HELPER 不存在" >&2
        return 1
    fi
    python3 "$KEEPALIVED_NOTIFY_HELPER" --title "$title" --content "$body" --stype "$stype" --msgtype "html" --trigger-time "$trigger"
}

alert_util_primary_vip(){
    if [ ! -f "$KEEPALIVED_CONF_FILE" ]; then
        return
    fi
    python3 - "$KEEPALIVED_CONF_FILE" <<'PY'
import sys
from pathlib import Path
conf = Path(sys.argv[1])
vip = ''
if conf.exists():
    content = conf.read_text(encoding='utf-8', errors='ignore')
    lines = iter(content.splitlines())
    in_block = False
    for raw in lines:
        line = raw.strip()
        if line.startswith('virtual_ipaddress'):
            in_block = True
            continue
        if in_block:
            if line.startswith('}'):
                break
            if line and not line.startswith('#'):
                vip = line.split()[0]
                break
print(vip)
PY
}

alert_util_get_host_ip(){
    hostname -I 2>/dev/null | awk '{print $1}'
}

alert_util_has_vip(){
    local vip="$1"
    if [ -z "$vip" ]; then
        echo "未知"
        return 1
    fi
    if ip addr | grep -w "$vip" >/dev/null 2>&1; then
        echo "是"
    else
        echo "否"
    fi
}

alert_util_mysql_rw_state(){
    local output
    output=$(mysql_client_run "SELECT @@GLOBAL.read_only, @@GLOBAL.super_read_only" 2>/dev/null)
    if [ $? -ne 0 ] || [ -z "$output" ]; then
        echo "未知 (无法连接 MySQL)"
        return 1
    fi
    local values
    values=$(echo "$output" | tail -n 1)
    local ro
    local sro
    ro=$(echo "$values" | awk '{print $1}')
    sro=$(echo "$values" | awk '{print $2}')
    if [ "$ro" = "0" ] && [ "$sro" = "0" ]; then
        echo "可写"
    else
        echo "只读"
    fi
}

alert_util_build_event_body(){
    local event="$1"
    local extra="$2"
    local vip="$(alert_util_primary_vip)"
    local mysql_state="$(alert_util_mysql_rw_state)"
    local vip_owned="$(alert_util_has_vip "$vip")"
    local host_ip="$(alert_util_get_host_ip)"
    local now_time
    now_time="$(date '+%Y-%m-%d %H:%M:%S')"
    local hostname_value
    hostname_value="$(hostname)"
    echo "<p>事件：${event}</p><p>时间：${now_time}</p><p>主机：${hostname_value} (${host_ip})</p><p>VIP：${vip}</p><p>是否持有VIP：${vip_owned}</p>${extra}<p>MySQL 读写状态：${mysql_state}</p>"
}

alert_util_notify_promote(){
    local body
    body=$(alert_util_build_event_body "Keepalived 提升为主" "")
    alert_util_send_notification "Keepalived 提升为主" "$body" "keepalived-promote" 0
}

alert_util_notify_demote(){
    local target_priority="$1"
    local extra="<p>目标优先级：${target_priority}</p>"
    local body
    body=$(alert_util_build_event_body "Keepalived 降级为备" "$extra")
    alert_util_send_notification "Keepalived 降级为备" "$body" "keepalived-demote" 0
}
