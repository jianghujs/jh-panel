#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
install_tmp=${rootPath}/tmp/mw_install.pl

Install_Iptables_Persistence()
{
  if [ -f /etc/debian_version ]; then
    export DEBIAN_FRONTEND=noninteractive
    if ! command -v netfilter-persistent >/dev/null 2>&1; then
      apt-get update -y >> $install_tmp 2>&1
      apt-get install -y iptables-persistent netfilter-persistent >> $install_tmp 2>&1
    fi
    systemctl enable netfilter-persistent >/dev/null 2>&1 || true
    return 0
  fi

  if [ -f /etc/redhat-release ] || [ -f /etc/centos-release ] || [ -f /etc/almalinux-release ] || [ -f /etc/rocky-release ]; then
    if ! rpm -q iptables-services >/dev/null 2>&1; then
      if command -v dnf >/dev/null 2>&1; then
        dnf install -y iptables-services >> $install_tmp 2>&1
      else
        yum install -y iptables-services >> $install_tmp 2>&1
      fi
    fi
    systemctl enable iptables >/dev/null 2>&1 || true
    return 0
  fi

  return 0
}

Install_App()
{
  echo '正在安装端口转发管理器...' > $install_tmp
  mkdir -p $serverPath/port_forward
  echo '1.0' > $serverPath/port_forward/version.pl
  Install_Iptables_Persistence >> $install_tmp 2>&1
  cd ${rootPath} && python3 ${rootPath}/plugins/port_forward/index.py install_plugin >> $install_tmp 2>&1
  echo $(date "+%Y-%m-%d %H:%M:%S") '安装完成' >> $install_tmp
}

Update_App()
{
  echo '正在更新端口转发管理器...' > $install_tmp
  mkdir -p $serverPath/port_forward
  echo '1.0' > $serverPath/port_forward/version.pl
  Install_Iptables_Persistence >> $install_tmp 2>&1
  cd ${rootPath} && python3 ${rootPath}/plugins/port_forward/index.py install_plugin >> $install_tmp 2>&1
  echo $(date "+%Y-%m-%d %H:%M:%S") '更新完成' >> $install_tmp
}

Uninstall_App()
{
  cd ${rootPath} && python3 ${rootPath}/plugins/port_forward/index.py uninstall_plugin >> $install_tmp 2>&1
  rm -rf $serverPath/port_forward
  echo '端口转发管理器卸载完成' >> $install_tmp
}

if [ "${1}" == 'install' ]; then
  Install_App
elif [ "${1}" == 'update' ]; then
  Update_App
else
  Uninstall_App
fi
