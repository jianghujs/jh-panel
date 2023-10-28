#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH


curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

install_tmp=${rootPath}/tmp/mw_install.pl

bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`
OSNAME_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`


Install_nfs-util()
{
	echo '正在安装脚本文件...' > $install_tmp
	apt-get update
	apt-get install nfs-kernel-server -y
	mkdir -p $serverPath/nfs-util
	echo '1.0' > $serverPath/nfs-util/version.pl
	echo '安装完成' > $install_tmp
}

Uninstall_nfs-util()
{
	apt-get remove nfs-kernel-server -y
	apt-get remove nfs-common -y
	rm -rf $serverPath/nfs-util
	echo "卸载完成" > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_nfs-util
else
	Uninstall_nfs-util
fi
