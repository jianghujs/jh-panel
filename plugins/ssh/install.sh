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

version=$2

Install_ssh()
{
	echo '正在安装SSH管理器...' > $install_tmp
	mkdir -p $serverPath/ssh
	echo $version > $serverPath/ssh/version.pl
	echo '安装完成' > $install_tmp
}

Uninstall_ssh()
{
	echo '正在卸载SSH管理器...' > $install_tmp
	rm -rf $serverPath/ssh
	echo "卸载完成" > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_ssh
else
	Uninstall_ssh
fi
