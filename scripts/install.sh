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

if [ grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release ]; then
	OSNAME='debian'
elif grep -Eqi "Ubuntu" /etc/issue || grep -Eq "Ubuntu" /etc/*-release; then
	OSNAME='ubuntu'
elif grep -Eqi "CentOS" /etc/issue || grep -Eq "CentOS" /etc/*-release; then
	OSNAME='centos'
else
	OSNAME='unknow'
fi


echo "use system version: ${OSNAME}"
if [ "$netEnvCn" == "cn" ]; then
  wget -O switch_apt_sources.sh https://gitee.com/jianghujs/jh-panel/raw/master/scripts/switch_apt_sources.sh && bash switch_apt_source.sh 2
  wget -O ${OSNAME}_cn.sh https://gitee.com/jianghujs/jh-panel/raw/master/scripts/install/${OSNAME}_cn.sh && bash ${OSNAME}_cn.sh
else
  wget -O switch_apt_sources.sh https://gitee.com/jianghujs/jh-panel/raw/master/scripts/switch_apt_sources.sh && bash switch_apt_source.sh 1
  wget -O ${OSNAME}.sh https://raw.githubusercontent.com/jianghujs/jh-panel/master/scripts/install/${OSNAME}.sh && bash ${OSNAME}.sh
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
    ln -s /etc/rc.d/init.d/mw /usr/bin/jh
	fi
fi

endTime=`date +%s`
((outTime=(${endTime}-${startTime})/60))
echo -e "Time consumed:\033[32m $outTime \033[0mMinute!"
