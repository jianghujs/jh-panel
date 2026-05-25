#!/bin/bash
# chkconfig: 2345 55 25
# description: MW Cloud Service

### BEGIN INIT INFO
# Provides:          bt
# Required-Start:    $all
# Required-Stop:     $all
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: starts mw
# Description:       starts the mw
### END INIT INFO

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin

wrapper="{$SERVER_PATH}/frp-wrapper.sh"

app_start(){
    echo "Starting frps..."
    $wrapper server start
    echo "Starting frpc..."
    $wrapper client start
}

app_stop()
{
    echo "Stopping frps..."
    $wrapper server stop
    echo "Stopping frpc..."
    $wrapper client stop
}

app_status()
{
    echo "frps status:"
    $wrapper server status
    echo "frpc status:"
    $wrapper client status
}

case "$1" in
    'start') app_start;;
    'stop') app_stop;;
    'restart'|'reload')
        app_stop
        app_start;;
    'status') app_status;;
esac
