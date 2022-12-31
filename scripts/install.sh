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

_os=`uname`
echo "use system: ${_os}"

if [ "$EUID" -ne 0 ]
  then echo "Please run as root!"
  exit
fi

if [ "$netEnvCn" == "cn" ]; then
	sed -i 's#http://deb.debian.org#https://mirrors.aliyun.com#g' /etc/apt/sources.list
fi


if [ ${_os} == "Darwin" ]; then
	OSNAME='macos'
elif grep -Eq "openSUSE" /etc/*-release; then
	OSNAME='opensuse'
	zypper refresh
elif grep -Eq "FreeBSD" /etc/*-release; then
	OSNAME='freebsd'
elif grep -Eqi "CentOS" /etc/issue || grep -Eq "CentOS" /etc/*-release; then
	OSNAME='centos'
	yum install -y wget zip unzip git
elif grep -Eqi "Fedora" /etc/issue || grep -Eq "Fedora" /etc/*-release; then
	OSNAME='fedora'
	yum install -y wget zip unzip git
elif grep -Eqi "Rocky" /etc/issue || grep -Eq "Rocky" /etc/*-release; then
	OSNAME='rocky'
	yum install -y wget zip unzip git
elif grep -Eqi "AlmaLinux" /etc/issue || grep -Eq "AlmaLinux" /etc/*-release; then
	OSNAME='alma'
	yum install -y wget zip unzip git
elif grep -Eqi "Amazon Linux" /etc/issue || grep -Eq "Amazon Linux" /etc/*-release; then
	OSNAME='amazon'
	yum install -y wget zip unzip git
elif grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release; then
	OSNAME='debian'
	apt update -y
	apt install -y devscripts
	apt install -y wget zip unzip
	apt install -y git
elif grep -Eqi "Ubuntu" /etc/issue || grep -Eq "Ubuntu" /etc/*-release; then
	OSNAME='ubuntu'
	apt install -y wget zip unzip
	apt install -y git
else
	OSNAME='unknow'
fi


if [ $OSNAME != "macos" ];then
	if id www &> /dev/null ;then 
	    echo ""
	else
	    groupadd www
		useradd -g www -s /bin/bash www
	fi

	mkdir -p /www/server
	mkdir -p /www/wwwroot
	mkdir -p /www/wwwlogs
	mkdir -p /www/backup/database
	mkdir -p /www/backup/site


	# # https://cdn.jsdelivr.net/gh/jianghujs/jh-panel@latest/scripts/install.sh

	# if [ ! -d /www/server/jh-panel ];then

	# 	cn=$(curl -fsSL -m 10 http://ipinfo.io/json | grep "\"country\": \"CN\"")
	# 	if [ ! -z "$cn" ];then
	# 		# curl -sSLo /tmp/master.zip https://gitee.com/jianghujs/jh-panel/repository/archive/master.zip
	# 		curl -sSLo /tmp/master.zip https://codeload.github.com/jianghujs/jh-panel/zip/master
	# 	else
	# 		curl -sSLo /tmp/master.zip https://codeload.github.com/jianghujs/jh-panel/zip/master
	# 	fi

	# 	cd /tmp && unzip /tmp/master.zip
	# 	mv -f /tmp/jh-panel-master /www/server/jh-panel
	# 	rm -rf /tmp/master.zip
	# 	rm -rf /tmp/jh-panel-master
	# fi
	if [ "$netEnvCn" == "cn" ]; then
		echo "git clone https://gitee.com/jianghujs/jh-panel /www/server/mdserver-web"
		git clone https://gitee.com/jianghujs/jh-panel /www/server/mdserver-web
	else
		echo "git clone https://github.com/jianghujs/jh-panel /www/server/mdserver-web"
		git clone https://github.com/jianghujs/jh-panel /www/server/mdserver-web
	fi
fi

echo "use system version: ${OSNAME}"
cd /www/server/jh-panel && bash scripts/install/${OSNAME}.sh

# 安装后文件会被清空
if [ "$netEnvCn" == "cn" ]; then
    mkdir -p /www/server/jh-panel/data
    echo "True" > /www/server/jh-panel/data/net_env_cn.pl
fi

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

cd /www/server/jh-panel && bash /etc/rc.d/init.d/mw stop
cd /www/server/jh-panel && bash /etc/rc.d/init.d/mw start
cd /www/server/jh-panel && bash /etc/rc.d/init.d/mw default

sleep 2
if [ ! -e /usr/bin/mw ]; then
	if [ -f /etc/rc.d/init.d/mw ];then
		ln -s /etc/rc.d/init.d/mw /usr/bin/mw
	fi
fi

endTime=`date +%s`
((outTime=(${endTime}-${startTime})/60))
echo -e "Time consumed:\033[32m $outTime \033[0mMinute!"

