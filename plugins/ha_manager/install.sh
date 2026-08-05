#!/bin/bash

action=$1
version=$2

case "$action" in
  install|update)
    mkdir -p /www/server/ha_manager
    echo "$version" > /www/server/ha_manager/version.pl
    ;;
  uninstall)
    rm -rf /www/server/ha_manager
    ;;
esac

exit 0
