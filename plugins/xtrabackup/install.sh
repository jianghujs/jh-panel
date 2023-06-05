#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")


install_tmp=${rootPath}/tmp/mw_install.pl

VERSION=$2

Install_xtrabackup()
{
	echo '正在安装脚本文件...' > $install_tmp
	mkdir -p /www/backup/xtrabackup_data_history
	# wget -O ./percona-xtrabackup.amd.deb https://repo.percona.com/apt/percona-release_latest.generic_all.deb
	# wget -O ./percona-xtrabackup.arm.deb http://ports.ubuntu.com/pool/universe/p/percona-xtrabackup/percona-xtrabackup_2.4.9-0ubuntu2_arm64.deb
	apt-get update
	apt-get install -f -y
	if [[ `arch` =~ "x86_64" ]];then
		echo $(date "+%Y-%m-%d %H:%M:%S") 'this is x86_64' >> $install_tmp
		dpkg -i percona-xtrabackup.amd.deb
		apt-get update
		apt-get install percona-xtrabackup-24 -y
	elif [[ `arch` =~ "aarch64" ]];then
		echo $(date "+%Y-%m-%d %H:%M:%S") 'this is arm64' >> $install_tmp
		dpkg -i percona-xtrabackup.arm.deb
		apt-get update
		apt-get install percona-xtrabackup -y
	else
		echo $(date "+%Y-%m-%d %H:%M:%S") '不支持的设备类型 $(arch)' >> $install_tmp
	fi
	
	mkdir -p $serverPath/xtrabackup
	echo "2.4" > $serverPath/xtrabackup/version.pl
	echo $(date "+%Y-%m-%d %H:%M:%S") 'xtrabackup 安装成功' >> $serverPath/xtrabackup/xtrabackup.log
	cp -r $rootPath/plugins/xtrabackup/xtrabackup.sh.example $serverPath/xtrabackup/xtrabackup.sh
	cd ${rootPath} && python3 ${rootPath}/plugins/xtrabackup/index.py initd_install
	echo $(date "+%Y-%m-%d %H:%M:%S") '安装完成' >> $install_tmp
}

Uninstall_xtrabackup()
{
	echo $(date "+%Y-%m-%d %H:%M:%S") '卸载开始' >> $install_tmp
	echo $(apt-get remove percona-xtrabackup -y) >> $install_tmp
	echo $(apt-get remove percona-xtrabackup-24 -y) >> $install_tmp
	rm -rf $serverPath/xtrabackup
	echo $(date "+%Y-%m-%d %H:%M:%S") '卸载完成' >> $install_tmp	
}

action=$1
if [ "${1}" == 'install' ];then
	Install_xtrabackup
else
	Uninstall_xtrabackup
fi
