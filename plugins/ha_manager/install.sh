#!/bin/bash

action=$1
version=$2

case "$action" in
  install|update)
    mkdir -p /www/server/ha_manager
    mkdir -p /www/server/jh-panel/plugins/ha_manager/data
    mkdir -p /www/server/jh-panel/plugins/ha_manager/logs/switch
    mkdir -p /www/server/jh-panel/plugins/ha_manager/logs/peer
    chmod 700 /www/server/jh-panel/plugins/ha_manager/data /www/server/jh-panel/plugins/ha_manager/logs || true
    echo "$version" > /www/server/ha_manager/version.pl
    ;;
  uninstall)
    rm -rf /www/server/ha_manager
    ;;
esac

exit 0
