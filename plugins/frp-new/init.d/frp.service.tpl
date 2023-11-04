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

app_file={$SERVER_PATH}

app_start(){
    cd $app_file/frp
	isStart=`ps -ef|grep frps |grep -v grep | grep -v python | awk '{print $2}'`
	if [ "$isStart" == '' ];then
        echo -e "Starting frps... \c"
        $app_file/frp/frps -c $app_file/frp/frps.toml > $app_file/frp/frps.log 2>&1 &
        echo -e "\033[32mdone\033[0m"
    else
        echo "Starting frps already running"
    fi

    isStart=`ps -ef|grep frpc |grep -v grep | grep -v python | awk '{print $2}'`
    if [ "$isStart" == '' ];then
        echo -e "Starting frpc... \c"
        $app_file/frp/frpc -c $app_file/frp/frpc.toml > $app_file/frp/frps.log 2>&1 &
        echo -e "\033[32mdone\033[0m"
    else
        echo "Starting frpc already running"
    fi
}

app_stop()
{
    echo -e "Stopping frps... \c";
    arr=`ps -ef|grep frps |grep -v grep | grep -v python | awk '{print $2}'`
    for p in ${arr[@]}
    do
        kill -9 $p &>/dev/null
    done
    echo -e "\033[32mdone\033[0m"

    echo -e "Stopping frpc... \c";
    arr=`ps -ef|grep frpc |grep -v grep | grep -v python | awk '{print $2}'`
    for p in ${arr[@]}
    do
        kill -9 $p &>/dev/null
    done
    echo -e "\033[32mdone\033[0m"
}

app_status()
{
    isStart=`ps -ef|grep frps |grep -v grep | grep -v python | awk '{print $2}'`
    if [ "$isStart" == '0' ];then
        echo -e "\033[32mfrps already running\033[0m"
    else
        echo -e "\033[31mfrps not running\033[0m"
    fi

    isStart=`ps -ef|grep frpc |grep -v grep | grep -v python | awk '{print $2}'`
    if [ "$isStart" == '0' ];then
        echo -e "\033[32mfrpc already running\033[0m"
    else
        echo -e "\033[31mfrpc not running\033[0m"
    fi
}

case "$1" in
    'start') app_start;;
    'stop') app_stop;;
    'restart'|'reload') 
        app_stop
        app_start;;
    'status') app_status;;
esac