#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
# LANG=en_US.UTF-8
is64bit=`getconf LONG_BIT`

osType="$1"
netEnvCn="$2"
echo "netEnvCn: ${netEnvCn}"
_os=`uname`
echo "use system: ${_os}"

if grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release; then
	OSNAME='debian'
elif grep -Eqi "Ubuntu" /etc/issue || grep -Eq "Ubuntu" /etc/*-release; then
	OSNAME='ubuntu'
elif grep -Eqi "CentOS" /etc/issue || grep -Eq "CentOS" /etc/*-release; then
	OSNAME='centos'
else
	OSNAME='unknow'
fi

echo "use system version: ${OSNAME}"

# 获取系统codename
codename_line=$(lsb_release -a | grep Codename)
codename_value=$(echo $codename_line | cut -d ':' -f2)
CODENAME=$(echo $codename_value | xargs)
echo "Codename: ${CODENAME}"

toolURLBase="https://raw.githubusercontent.com/jianghujs/jh-panel/master/scripts/os_tool"
if [ "$netEnvCn" == "cn" ]; then
  toolURLBase="https://gitee.com/jianghujs/jh-panel/raw/master/scripts/os_tool"
fi

URLBase="${toolURLBase}/${osType}/${CODENAME}"
echo "URLBase: ${URLBase}"
export URLBase

if ! wget -q --spider "${URLBase}/index.sh"; then
  echo "暂不支持在${_os}执行${osType}脚本"
	exit
fi

# 检查并创建子文件夹
if [ ! -d "$osType" ]; then
  mkdir "$osType"
fi

echo "downloading ${URLBase}/index.sh to ./${osType}/index.s"

wget -nv -O /tmp/${osType}_index.sh ${URLBase}/index.sh && bash /tmp/${osType}_index.sh
