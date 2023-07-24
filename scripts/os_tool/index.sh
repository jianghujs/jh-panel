#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
# LANG=en_US.UTF-8
is64bit=`getconf LONG_BIT`

netEnvCn="$1"
osType="$2"
echo "netEnvCn: ${netEnvCn}"
_os=`uname`
echo "use system: ${_os}"

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

#!/bin/bash

# 使用 lsb_release -a 命令并从输出中提取 "Codename" 的行
codename_line=$(lsb_release -a | grep Codename)
# 使用冒号分隔符将行分割为两部分，并获取第二部分（即 Codename 的值）
codename_value=$(echo $codename_line | cut -d ':' -f2)
# 去除值前面的空格
CODENAME=$(echo $codename_value | xargs)

# 打印 Codename 的值
echo "Codename: ${CODENAME}"

toolURLBase="https://raw.githubusercontent.com/jianghujs/jh-panel/master/scripts/os_tool"
if [ "$netEnvCn" == "cn" ]; then
  toolURLBase = "https://gitee.com/jianghujs/jh-panel/raw/master/scripts/os_tool"
fi

URLBase = "${toolURLBase}/${osType}/${CODENAME}"
echo "URLBase: ${URLBase}"
export urlBase

# 检查并创建子文件夹
if [ ! -d "$osType" ]; then
  mkdir "$osType"
fi

wget -O ./${osType}/index.sh ${urlBase}/index.sh && bash ./${osType}/index.sh
