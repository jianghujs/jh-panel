#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
install_tmp=${rootPath}/tmp/mw_install.pl

Install_App()
{
  echo '正在安装主备管理插件...' > $install_tmp
  mkdir -p $serverPath/ha_manager
  cd ${rootPath} && python3 ${rootPath}/plugins/ha_manager/index.py install_plugin >> $install_tmp 2>&1
  echo $(date "+%Y-%m-%d %H:%M:%S") '安装完成' >> $install_tmp
}

Update_App()
{
  echo '正在更新主备管理插件...' > $install_tmp
  mkdir -p $serverPath/ha_manager
  cd ${rootPath} && python3 ${rootPath}/plugins/ha_manager/index.py install_plugin >> $install_tmp 2>&1
  echo $(date "+%Y-%m-%d %H:%M:%S") '更新完成' >> $install_tmp
}

Uninstall_App()
{
  rm -rf $serverPath/ha_manager
  echo '主备管理插件卸载完成'
}

if [ "${1}" == 'install' ]; then
  Install_App
elif [ "${1}" == 'update' ]; then
  Update_App
else
  Uninstall_App
fi
