#!/bin/bash
# chkconfig: 2345 55 25
# description: MW Cloud Service

### BEGIN INIT INFO
# Provides:          Midoks
# Required-Start:    $all
# Required-Stop:     $all
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: starts mw
# Description:       starts the mw
### END INIT INFO


PATH=/usr/local/bin:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export LANG=en_US.UTF-8

mw_path=/www/server/jh-panel
PATH=$PATH:$mw_path/bin


if [ -f $mw_path/bin/activate ];then
    source $mw_path/bin/activate
fi

ssl_param=''
if [ -f /www/server/jh-panel/data/ssl.pl ];then
    ssl_param=' --keyfile /www/server/jh-panel/ssl/private.pem --certfile /www/server/jh-panel/ssl/cert.pem '
fi

mw_start_panel()
{
    isStart=`ps -ef|grep 'gunicorn -c /www/server/jh-panel/setting.py app:app $ssl_param ' |grep -v grep|awk '{print $2}'`;
    if [ "$isStart" == '' ];then
        echo -e "starting jh-panel... \c"
        cd $mw_path &&  gunicorn -c /www/server/jh-panel/setting.py app:app $ssl_param ;
        port=$(cat ${mw_path}/data/port.pl)
        isStart=""
        while [[ "$isStart" == "" ]];
        do
            echo -e ".\c"
            sleep 0.5
            isStart=$(lsof -n -P -i:$port|grep LISTEN|grep -v grep|awk '{print $2}'|xargs)
            let n+=1
            if [ $n -gt 15 ];then
                break;
            fi
        done
        if [ "$isStart" == '' ];then
            echo -e "\033[31mfailed\033[0m"
            echo '------------------------------------------------------'
            tail -n 20 ${mw_path}/logs/error.log
            echo '------------------------------------------------------'
            echo -e "\033[31mError: jh-panel service startup failed.\033[0m"
            return;
        fi
        echo -e "\033[32mdone\033[0m"
    else
        echo "starting jh-panel... mw(pid $(echo $isStart)) already running"
    fi
}


mw_start_task()
{
    isStart=$(ps aux |grep '/www/server/jh-panel/task.py'|grep -v grep|awk '{print $2}')
    if [ "$isStart" == '' ];then
        echo -e "starting jh-tasks... \c"
        cd $mw_path && python3 /www/server/jh-panel/task.py >> ${mw_path}/logs/task.log 2>&1 &
        sleep 0.3
        isStart=$(ps aux |grep '/www/server/jh-panel/task.py'|grep -v grep|awk '{print $2}')
        if [ "$isStart" == '' ];then
            echo -e "\033[31mfailed\033[0m"
            echo '------------------------------------------------------'
            tail -n 20 $mw_path/logs/task.log
            echo '------------------------------------------------------'
            echo -e "\033[31mError: jh-tasks service startup failed.\033[0m"
            return;
        fi
        echo -e "\033[32mdone\033[0m"
    else
        echo "starting jh-tasks... jh-tasks (pid $(echo $isStart)) already running"
    fi
}

mw_start()
{
    mw_start_task
	mw_start_panel
}

# /www/server/jh-panel/tmp/panelTask.pl && service mw restart_task
mw_stop_task()
{
    if [ -f $mw_path/tmp/panelTask.pl ];then
        echo -e "\033[32mthe task is running and cannot be stopped\033[0m"
        exit 0
    fi

    echo -e "stopping jh-tasks... \c";
    pids=$(ps aux | grep '/www/server/jh-panel/task.py'|grep -v grep|awk '{print $2}')
    arr=($pids)
    for p in ${arr[@]}
    do
            kill -9 $p
    done
    echo -e "\033[32mdone\033[0m"
}

mw_stop_panel()
{
    echo -e "stopping jh-panel... \c";
    arr=`ps aux|grep 'gunicorn -c /www/server/jh-panel/setting.py app:app'|grep -v grep|awk '{print $2}'`;
    for p in ${arr[@]}
    do
        kill -9 $p &>/dev/null
    done
    
    pidfile=${mw_path}/logs/mw.pid
    if [ -f $pidfile ];then
        rm -f $pidfile
    fi
    echo -e "\033[32mdone\033[0m"
}

mw_stop()
{
    mw_stop_task
    mw_stop_panel
}

mw_status()
{
    isStart=$(ps aux|grep 'gunicorn -c /www/server/jh-panel/setting.py app:app $ssl_param '|grep -v grep|awk '{print $2}');
    if [ "$isStart" != '' ];then
        echo -e "\033[32mmw (pid $(echo $isStart)) already running\033[0m"
    else
        echo -e "\033[31mmw not running\033[0m"
    fi
    
    isStart=$(ps aux |grep '/www/server/jh-panel/task.py'|grep -v grep|awk '{print $2}')
    if [ "$isStart" != '' ];then
        echo -e "\033[32mmw-task (pid $isStart) already running\033[0m"
    else
        echo -e "\033[31mmw-task not running\033[0m"
    fi
}


mw_reload()
{
	isStart=$(ps aux|grep 'gunicorn -c /www/server/jh-panel/setting.py app:app $ssl_param '|grep -v grep|awk '{print $2}');
    
    if [ "$isStart" != '' ];then
    	echo -e "reload mw... \c";
	    arr=`ps aux|grep 'gunicorn -c /www/server/jh-panel/setting.py app:app $ssl_param '|grep -v grep|awk '{print $2}'`;
		for p in ${arr[@]}
        do
                kill -9 $p
        done
        cd $mw_path && gunicorn -c /www/server/jh-panel/setting.py app:app $ssl_param 
        isStart=`ps aux|grep 'gunicorn -c /www/server/jh-panel/setting.py app:app $ssl_param '|grep -v grep|awk '{print $2}'`;
        if [ "$isStart" == '' ];then
            echo -e "\033[31mfailed\033[0m"
            echo '------------------------------------------------------'
            tail -n 20 $mw_path/logs/error.log
            echo '------------------------------------------------------'
            echo -e "\033[31mError: mw service startup failed.\033[0m"
            return;
        fi
        echo -e "\033[32mdone\033[0m"
    else
        echo -e "\033[31mmw not running\033[0m"
        mw_start
    fi
}

mw_close(){
    echo 'True' > $mw_path/data/close.pl
}

mw_open()
{
    if [ -f $mw_path/data/close.pl ];then
        rm -rf $mw_path/data/close.pl
    fi
}

mw_unbind_domain()
{
    if [ -f $mw_path/data/bind_domain.pl ];then
        rm -rf $mw_path/data/bind_domain.pl
    fi
}

error_logs()
{
	tail -n 100 $mw_path/logs/error.log
}

mw_update()
{
    cn=$(curl -fsSL -m 10 http://ipinfo.io/json | grep "\"country\": \"CN\"")
    if [ ! -z "$cn" ];then
        curl -fsSL https://cdn.jsdelivr.net/gh/jianghujs/jh-panel@latest/scripts/update.sh | bash
    else
        curl -fsSL https://raw.githubusercontent.com/jianghujs/jh-panel/master/scripts/update.sh | bash
    fi
}

mw_update_dev()
{
    cn=$(curl -fsSL -m 10 http://ipinfo.io/json | grep "\"country\": \"CN\"")
    if [ ! -z "$cn" ];then
        curl -fsSL https://gitee.com/jianghujs/jh-panel/raw/dev/scripts/update_dev.sh | bash
    else
        curl -fsSL https://raw.githubusercontent.com/jianghujs/jh-panel/dev/scripts/update_dev.sh | bash
    fi
    cd /www/server/jh-panel
}

mw_install_app()
{
    bash $mw_path/scripts/quick/app.sh
}

mw_close_admin_path(){
    if [ -f $mw_path/data/admin_path.pl ]; then
        rm -rf $mw_path/data/admin_path.pl
    fi
}

mw_force_kill()
{
    PLIST=`ps -ef|grep 'gunicorn -c /www/server/jh-panel/setting.py app:app' |grep -v grep|awk '{print $2}'`
    for i in $PLIST
    do
        kill -9 $i
    done

    pids=`ps -ef|grep /www/server/jh-panel/task.py | grep -v grep |awk '{print $2}'`
    arr=($pids)
    for p in ${arr[@]}
    do
        kill -9 $p
    done
}

mw_debug(){
    mw_stop
    mw_force_kill

    port=7200    
    if [ -f $mw_path/data/port.pl ];then
        port=$(cat $mw_path/data/port.pl)
    fi

    if [ -d /www/server/jh-panel ];then
        cd /www/server/jh-panel
    fi
    gunicorn -b :$port -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1  app:app $ssl_param --log-level "debug"  --capture-output;
}


mw_os_tool(){
  bash /www/server/jh-panel/scripts/os_tool/index.sh vm "" "true"
}

# 获取运行命令的目录
export RUN_DIR=$(pwd)

case "$1" in
    'start') mw_start;;
    'stop') mw_stop;;
    'reload') mw_reload;;
    'restart') 
        mw_stop
        mw_force_kill
        mw_start;;
    'restart_panel')
        mw_stop_panel
        mw_start_panel;;
    'restart_task')
        mw_stop_task
        mw_start_task;;
    'status') mw_status;;
    'logs') error_logs;;
    'close') mw_close;;
    'open') mw_open;;
    'update') mw_update;;
    'update_dev') mw_update_dev;;
    'install_app') mw_install_app;;
    'close_admin_path') mw_close_admin_path;;
    'unbind_domain') mw_unbind_domain;;
    'debug') mw_debug;;
    'os_tool') mw_os_tool;;
    'default')
        cd $mw_path
        port=7200
        
        if [ -f $mw_path/data/port.pl ];then
            port=$(cat $mw_path/data/port.pl)
        fi

        if [ ! -f $mw_path/data/default.pl ];then
            echo -e "\033[33mInstall Failed\033[0m"
            exit 1
        fi

        password=$(cat $mw_path/data/default.pl)
        if [ -f $mw_path/data/domain.conf ];then
            address=$(cat $mw_path/data/domain.conf)
        fi
        if [ -f $mw_path/data/admin_path.pl ];then
            auth_path=$(cat $mw_path/data/admin_path.pl)
        fi

        protocol="http"
        if [ -f $mw_path/data/ssl.pl ];then
            protocol="https"
        fi
	    
        if [ "$address" = "" ];then
            v4=$(python3 $mw_path/tools.py getServerIp 4)
            v4_local=$(python3 $mw_path/tools.py getLocalIp 4)
            v6=$(python3 $mw_path/tools.py getServerIp 6)

            if [ "$v4" != "" ] && [ "$v6" != "" ]; then
                address="JH-Panel-Url-Ipv4: $protocol://$v4:$port$auth_path \nJH-Panel-Url-Ipv4(LAN):$protocol://$v4_local:$port$auth_path \nJH-Panel-Url-Ipv6:$protocol://[$v6]:$port$auth_path"
            elif [ "$v4" != "" ]; then
                address="JH-Panel-Url: $protocol://$v4:$port$auth_path \nJH-Panel-Url(LAN):$protocol://$v4_local:$port$auth_path"
            elif [ "$v6" != "" ]; then

                if [ ! -f $mw_path/data/ipv6.pl ];then
                    #  Need to restart ipv6 to take effect
                    echo 'True' > $mw_path/data/ipv6.pl
                    mw_stop
                    mw_start
                fi
                address="JH-Panel-Url: $protocol://[$v6]:$port$auth_path"
            else
                address="JH-Panel-Url: $protocol://you-network-ip:$port$auth_path"
            fi
        else
            address="JH-Panel-Url: $protocol://$address:$port$auth_path"
        fi

        show_panel_ip="$port|"
        echo -e "=================================================================="
        echo -e "\033[32mJH-Panel default info!\033[0m"
        echo -e "=================================================================="
        echo -e "$address"
        echo -e `python3 $mw_path/tools.py username`
        echo -e `python3 $mw_path/tools.py password`
        # echo -e "password: $password"
        echo -e "\033[33mWarning:\033[0m"
        echo -e "\033[33mIf you cannot access the panel. \033[0m"
        echo -e "\033[33mrelease the following port (${show_panel_ip}888|80|443|22|10022|33067|10744) in the security group.\033[0m"
        echo -e "=================================================================="
        ;;
    *)
        cd $mw_path && python3 $mw_path/tools.py cli $1 $2
        ;;
esac
