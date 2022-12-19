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
	mkdir -p $serverPath/xtrabackup
	# arm
	# wget http://ports.ubuntu.com/pool/universe/p/percona-xtrabackup/percona-xtrabackup_2.4.9-0ubuntu2_arm64.deb
	# amd
	wget https://repo.percona.com/apt/percona-release_latest.generic_all.deb
	dpkg -i  percona-xtrabackup_2.4.9-0ubuntu2_arm64.deb
	apt-get update
	apt-get -f install
	apt-get install percona-xtrabackup
	# apt-get install percona-xtrabackup-24
	ln -s /www/server/mysql/bin/mysql /usr/bin
	mkdir -p /var/run/mysqld
	ln -s /www/server/mysql/mysql.sock /var/run/mysqld/mysqld.sock
	xtrabackup --version
	echo "2.4" > $serverPath/xtrabackup/version.pl
	echo '安装完成' > $install_tmp
}

Uninstall_xtrabackup()
{
	echo '卸载开始' > $install_tmp	
	apt-get remove percona-xtrabackup* -y
	rm -rf $serverPath/xtrabackup
	echo '卸载完成' > $install_tmp	
}

action=$1
if [ "${1}" == 'install' ];then
	Install_xtrabackup
else
	Uninstall_xtrabackup
fi
