#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
# LANG=en_US.UTF-8
is64bit=`getconf LONG_BIT`

if [ -f /etc/motd ];then
    echo "welcome to jianghu panel (base on jh-panel)" > /etc/motd
fi

startTime=`date +%s`
netEnvCn="$1"
echo "netEnvCn: ${netEnvCn}"
_os=`uname`
echo "use system: ${_os}"

# 必须以root用户运行
if [ "$EUID" -ne 0 ]
  then echo "Please run as root!"
  exit
fi

if [ ${_os} == "Darwin" ]; then
	OSNAME='macos'
elif grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release; then
	OSNAME='debian'
else
	OSNAME='unknow'
fi


echo "use system version: ${OSNAME}"
if [ "$netEnvCn" == "cn" ]; then
  wget -O ${OSNAME}_cn.sh https://gitee.com/jianghujs/jh-panel/raw/master/scripts/install_b/${OSNAME}_cn.sh && bash ${OSNAME}_cn.sh
else
  wget -O ${OSNAME}.sh https://raw.githubusercontent.com/jianghujs/jh-panel/master/scripts/install_b/${OSNAME}.sh && bash ${OSNAME}.sh
fi

# 启动面板
cd /www/server/jh-panel && bash cli.sh start
isStart=`ps -ef|grep 'gunicorn -c setting.py app:app' |grep -v grep|awk '{print $2}'`
n=0
while [ ! -f /etc/rc.d/init.d/mw ];
do
    echo -e ".\c"
    sleep 1
    let n+=1
    if [ $n -gt 20 ];then
    	echo -e "start mw fail"
    	exit 1
    fi
done

# 启动面板
cd /www/server/jh-panel && bash /etc/rc.d/init.d/mw stop
cd /www/server/jh-panel && bash /etc/rc.d/init.d/mw start
cd /www/server/jh-panel && bash /etc/rc.d/init.d/mw default

sleep 2
if [ ! -e /usr/bin/mw ]; then
	if [ -f /etc/rc.d/init.d/mw ];then
    # 添加软连接
		ln -s /etc/rc.d/init.d/mw /usr/bin/mw
	fi
fi

endTime=`date +%s`
((outTime=(${endTime}-${startTime})/60))
echo -e "Time consumed:\033[32m $outTime \033[0mMinute!"
