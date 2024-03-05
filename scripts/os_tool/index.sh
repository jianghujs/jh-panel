#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
# LANG=en_US.UTF-8
is64bit=`getconf LONG_BIT`

if [ -v RUN_DIR ]; then
  cd $RUN_DIR
fi

osType="$1"
netEnvCn="$2"
usePanelScript="$3"

# 默认获取面板配置的源
if [ -z "$netEnvCn" ]; then
  if [ -f "/www/server/jh-panel/data/net_env_cn.pl" ]; then
    netEnvCn="cn"
  fi
fi

echo "netEnvCn: ${netEnvCn}"
_os=`uname`
echo "use system: ${_os}"

echo "usePanelScript：${usePanelScript}"

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

tool_dir=$CODENAME
# 如果CODENAME为focal或bullseye，则tool_dir为default
if [ $CODENAME == "bullseye" ] || [ $CODENAME == "focal"]; then
  tool_dir="default"
fi

if [ "$usePanelScript" == "true" ]; then 
  export USE_PANEL_SCRIPT=true
  export SCRIPT_BASE=/www/server/jh-panel/scripts/os_tool/${osType}/${tool_dir}
  bash $SCRIPT_BASE/index.sh
else
  toolURLBase="https://raw.githubusercontent.com/jianghujs/jh-panel/master/scripts/os_tool"
  if [ "$netEnvCn" == "cn" ]; then
    toolURLBase="https://gitee.com/jianghujs/jh-panel/raw/master/scripts/os_tool"
  fi

  URLBase="${toolURLBase}/${osType}/${CODENAME}"
  echo "URLBase: ${URLBase}"
  export URLBase

  if ! wget -q --spider "${URLBase}/index.sh"; then
    echo "暂不支持在${OSNAME}执行${osType}脚本"
    exit
  fi

  echo "downloading ${URLBase}/index.sh to /tmp/${osType}_index.sh"

  wget -nv -O /tmp/${osType}_index.sh ${URLBase}/index.sh && bash /tmp/${osType}_index.sh

fi
