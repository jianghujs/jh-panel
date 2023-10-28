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


Install_jianghujs()
{
	echo '正在安装脚本文件...' > $install_tmp
	mkdir -p $serverPath/jianghujs
	echo '1.0' > $serverPath/jianghujs/version.pl
	echo '安装完成' > $install_tmp
}

Uninstall_jianghujs()
{
	rm -rf $serverPath/jianghujs
	echo "卸载完成" > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_jianghujs
else
	Uninstall_jianghujs
fi
