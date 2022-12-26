#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/www/server/nodejs/fnm
export PATH
curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

source /root/.bashrc

install_tmp=${rootPath}/tmp/mw_install.pl

bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`
OSNAME_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`


Install_cnpmcore()
{
	echo '正在安装脚本文件...' > $install_tmp
	mkdir -p $serverPath/cnpmcore
	mkdir -p $serverPath/cnpmcore/package
	cp $rootPath/plugins/cnpmcore/source/cnpmcore.zip $serverPath/cnpmcore/cnpmcore.zip
	cp $rootPath/plugins/cnpmcore/source/package.json $serverPath/cnpmcore/package/package.json
	cd $serverPath/cnpmcore
	unzip $serverPath/cnpmcore/cnpmcore.zip
	cd $serverPath/cnpmcore/cnpmcore
	eval 'fnm env'
	fnm install 16
	fnm use 16
	npm install
	echo '2.9.1' > $serverPath/cnpmcore/version.pl
	echo '安装完成' > $install_tmp
}

Uninstall_cnpmcore()
{
	cd $serverPath/cnpmcore/cnpmcore
	npm stop
	rm -rf $serverPath/cnpmcore
	echo "卸载完成" > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_cnpmcore
else
	Uninstall_cnpmcore
fi
