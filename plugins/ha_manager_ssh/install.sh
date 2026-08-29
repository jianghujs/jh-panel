#!/bin/bash

action=$1
version=$2
if [ -z "$version" ]; then
  version="1.0"
fi

case "$action" in
  install|update)
    mkdir -p /www/server/ha_manager_ssh/data
    mkdir -p /www/server/ha_manager_ssh/logs/switch
    mkdir -p /www/server/ha_manager_ssh/logs/peer
    chmod 700 /www/server/ha_manager_ssh /www/server/ha_manager_ssh/data /www/server/ha_manager_ssh/logs || true
    cd /www/server/jh-panel && python3 /www/server/jh-panel/plugins/ha_manager_ssh/index.py init_keypair '{}' >/dev/null 2>&1 || true
    echo "$version" > /www/server/ha_manager_ssh/version.pl
    ;;
  uninstall)
    rm -rf /www/server/ha_manager_ssh
    ;;
esac

exit 0
