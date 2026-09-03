#!/bin/bash

action=$1
version=$2
if [ -z "$version" ]; then
  version="1.0"
fi

case "$action" in
  install|update)
    mkdir -p /www/server/ha_manager_local
    echo "$version" > /www/server/ha_manager_local/version.pl
    ;;
  uninstall)
    rm -rf /www/server/ha_manager_local
    ;;
esac

exit 0
