#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
export DEBIAN_FRONTEND=noninteractive

apt install -y locate
locale-gen en_US.UTF-8
export LC_CTYPE=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8


if grep -Eq "Ubuntu" /etc/*-release; then
    sudo ln -sf /bin/bash /bin/sh
    #sudo dpkg-reconfigure dash
fi

VERSION_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`
if [ "$VERSION_ID" == "9" ];then
    sed "s/flask==2.0.3/flask==1.1.1/g" -i /www/server/jh-panel/requirements.txt
    sed "s/cryptography==3.3.2/cryptography==2.5/g" -i /www/server/jh-panel/requirements.txt
    sed "s/configparser==5.2.0/configparser==4.0.2/g" -i /www/server/jh-panel/requirements.txt
    sed "s/flask-socketio==5.2.0/flask-socketio==4.2.0/g" -i /www/server/jh-panel/requirements.txt
    sed "s/python-engineio==4.3.2/python-engineio==3.9.0/g" -i /www/server/jh-panel/requirements.txt
    # pip3 install -r /www/server/jh-panel/requirements.txt
fi

cd /www/server/jh-panel/scripts && bash lib.sh
chmod 755 /www/server/jh-panel/data


echo -e "stop mw"
isStart=`ps -ef|grep 'gunicorn -c setting.py app:app' |grep -v grep|awk '{print $2}'`

port=7200
if [ -f /www/server/jh-panel/data/port.pl ];then
    port=$(cat /www/server/jh-panel/data/port.pl)
fi

n=0
while [[ "$isStart" != "" ]];
do
    echo -e ".\c"
    sleep 0.5
    isStart=$(lsof -n -P -i:$port|grep LISTEN|grep -v grep|awk '{print $2}'|xargs)
    let n+=1
    if [ $n -gt 15 ];then
        break;
    fi
done


echo -e "start mw"
cd /www/server/jh-panel && bash cli.sh start
isStart=`ps -ef|grep 'gunicorn -c setting.py app:app' |grep -v grep|awk '{print $2}'`
n=0
while [[ ! -f /etc/rc.d/init.d/mw ]];
do
    echo -e ".\c"
    sleep 1
    let n+=1
    if [ $n -gt 20 ];then
        echo -e "start mw fail"
        exit 1
    fi
done
echo -e "start mw success"

systemctl daemon-reload
