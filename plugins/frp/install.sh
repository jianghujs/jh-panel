#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
sysName=`uname`

install_tmp=${rootPath}/tmp/mw_install.pl

echo "use system: ${sysName}"

bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`
OSNAME_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`


VERSION=0.44.0

pluginSourceDir=${rootPath}/plugins/frp/source

serDir=/usr/lib/systemd/system
if [ ! -d $serDir ];then
	serDir=/lib/systemd/system
fi

Install_Plugin()
{
	echo '正在安装脚本文件...' > $install_tmp

	APP_DIR=${serverPath}/source/frp

	mkdir -p $serverPath/frp
	mkdir -p $APP_DIR

	rm -rf $serDir/frpc.service
	rm -rf $serDir/frps.service
	
	localPkg=""
	extractDir=""

	if [ "$OSNAME" == "macos" ];then
		localPkg=${pluginSourceDir}/frp_${VERSION}_darwin_amd64.tar.gz
		extractDir=frp_${VERSION}_darwin_amd64
		if [ -f "$localPkg" ] && [ -s "$localPkg" ];then
			cp -f "$localPkg" $APP_DIR/frp.tar.gz
		else
			wget  --no-check-certificate -O $APP_DIR/frp.tar.gz https://github.com/fatedier/frp/releases/download/v${VERSION}/frp_${VERSION}_darwin_amd64.tar.gz
		fi
		cd $APP_DIR && tar -zxvf $APP_DIR/frp.tar.gz
		mv $APP_DIR/${extractDir}/* $serverPath/frp
	else
		localPkg=${pluginSourceDir}/frp_${VERSION}_linux_amd64.tar.gz
		extractDir=frp_${VERSION}_linux_amd64
		if [ -f "$localPkg" ] && [ -s "$localPkg" ];then
			cp -f "$localPkg" $APP_DIR/frp.tar.gz
		else
			wget  --no-check-certificate -O $APP_DIR/frp.tar.gz https://github.com/fatedier/frp/releases/download/v${VERSION}/frp_${VERSION}_linux_amd64.tar.gz
		fi
		cd $APP_DIR && tar -zxvf $APP_DIR/frp.tar.gz
		mv $APP_DIR/${extractDir}/* $serverPath/frp
	fi

	# rm -rf $APP_DIR/frp.tar.gz
	# rm -rf $APP_DIR/frp_${VERSION}_linux_amd64

	echo ${VERSION} > $serverPath/frp/version.pl
	echo 'install frpc' > $install_tmp

	# 初始化模式与服务模板
	cd ${rootPath} && python3 ${rootPath}/plugins/frp/index.py initd_install
	cd ${rootPath} && python3 ${rootPath}/plugins/frp/index.py start
}


Uninstall_Plugin()
{
	rm -rf $serverPath/frp

	if [ ! -d $serDir ];then
		echo "pass"
	else
		systemctl stop frps
		systemctl stop frpc
	  	rm -rf $serDir/frps.service
	  	rm -rf $serDir/frpc.service
	  	systemctl daemon-reload
	fi

	echo "Uninstall_frpc" > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_Plugin
else
	Uninstall_Plugin
fi
