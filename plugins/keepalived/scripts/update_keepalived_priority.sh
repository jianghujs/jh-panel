#!/bin/bash
# 更新 keepalived 配置中指定实例的 priority。
# 用法: update_keepalived_priority.sh [config] [instance] <priority>

set -euo pipefail

usage() {
    echo "Usage: $0 [keepalived.conf] [instance_name] <priority>" >&2
}

if [ $# -lt 1 ] || [ $# -gt 3 ]; then
    usage
    exit 1
fi

DEFAULT_CONF="${KEEPALIVED_CONF:-{$SERVER_PATH}/keepalived/etc/keepalived/keepalived.conf}"
DEFAULT_INSTANCE="${KEEPALIVED_INSTANCE:-VI_MYSQL}"

if [ $# -eq 1 ]; then
    CONF_PATH="$DEFAULT_CONF"
    INSTANCE_NAME="$DEFAULT_INSTANCE"
    NEW_PRIORITY="$1"
elif [ $# -eq 2 ]; then
    CONF_PATH="$DEFAULT_CONF"
    INSTANCE_NAME="$1"
    NEW_PRIORITY="$2"
else
    CONF_PATH="$1"
    INSTANCE_NAME="$2"
    NEW_PRIORITY="$3"
fi

if ! [[ "$NEW_PRIORITY" =~ ^[0-9]+$ ]]; then
    echo "Priority must be a numeric value, got '$NEW_PRIORITY'" >&2
    exit 1
fi

if [ ! -f "$CONF_PATH" ]; then
    echo "Keepalived config '$CONF_PATH' not found" >&2
    exit 4
fi

TMP_FILE=$(mktemp "/tmp/update_priority.XXXXXX")
cleanup() {
    rm -f "$TMP_FILE"
}
trap cleanup EXIT

python3 - "$CONF_PATH" "$INSTANCE_NAME" "$NEW_PRIORITY" > "$TMP_FILE" <<'PY'
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

case $rc in
    0)
        cat "$TMP_FILE" > "$CONF_PATH"
        exit 0
        ;;
    2|3)
        exit $rc
        ;;
    *)
        exit $rc
        ;;
esac
