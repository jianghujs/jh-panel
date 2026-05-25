#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin

ROLE=$1
ACTION=$2
PLUGIN_PATH={$PLUGIN_PATH}
PANEL_ROOT=$(dirname "$(dirname "$PLUGIN_PATH")")

if [ -z "$ROLE" ] || [ -z "$ACTION" ]; then
  echo "usage: $0 <server|client> <start|stop|restart|reload|status>"
  exit 1
fi

cd "$PANEL_ROOT" || exit 1
{$PYTHON_BIN} "$PLUGIN_PATH/index.py" service_runner "$ROLE" "$ACTION"
