# -*- coding: utf-8 -*-
#!/bin/bash

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
export DEBIAN_FRONTEND=noninteractive

# https://downloads.mysql.com/archives/community/

# debug
# cd /www/server/jh-panel/plugins/mysql-apt && bash install.sh install 8.0
# /www/server/mysql-apt/bin/usr/sbin/mysqld --defaults-file=/www/server/mysql-apt/etc/my.cnf --daemonize

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
sysName=`uname`

install_tmp=${rootPath}/tmp/mw_install.pl
myDir=${serverPath}/source/mysql-apt

bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`
VERSION_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`

MYSQL_VER=5.7.38
if [ "$OSNAME" == "debian" ];then
	# mysql5.7现在仅有10的编译版
	VERSION_ID="10"
fi

if [ "$OSNAME" == "ubuntu" ];then
	# mysql5.7现在仅有18.04的编译版
	VERSION_ID="18.04"
fi

SUFFIX_NAME=${MYSQL_VER}-1${OSNAME}${VERSION_ID}_amd64

APT_INSTALL()
{
	########
	mkdir -p $myDir
	mkdir -p $serverPath/mysql-apt/bin

	apt update -y
	apt install -y libnuma1 libaio1 libmecab2
	cd ${myDir} 

	if [[ `arch` =~ "x86_64" ]];then
		# https://mirrors.aliyun.com/mysql/MySQL-5.7/mysql-server_${SUFFIX_NAME}.deb-bundle.tar
		wget --no-check-certificate -O ${myDir}/mysql-server_${SUFFIX_NAME}.deb-bundle.tar https://cdn.mysql.com/archives/mysql-5.7/mysql-server_${SUFFIX_NAME}.deb-bundle.tar
		# wget --no-check-certificate -O ${myDir}/mysql-server_${SUFFIX_NAME}.deb-bundle.tar https://mirrors.aliyun.com/mysql/MySQL-5.7/mysql-server_${SUFFIX_NAME}.deb-bundle.tar?spm=a2c6h.25603864.0.0.2bd563afjw9OEj

		chmod +x ${myDir}/mysql-server_${SUFFIX_NAME}.deb-bundle.tar
		tar vxf ${myDir}/mysql-server_${SUFFIX_NAME}.deb-bundle.tar

		dpkg -X mysql-common_${SUFFIX_NAME}.deb $serverPath/mysql-apt/bin
		dpkg -X mysql-community-client-plugins_${SUFFIX_NAME}.deb $serverPath/mysql-apt/bin
		dpkg -X mysql-community-client-core_${SUFFIX_NAME}.deb $serverPath/mysql-apt/bin
		dpkg -X mysql-community-client_${SUFFIX_NAME}.deb $serverPath/mysql-apt/bin
		dpkg -X mysql-client_${SUFFIX_NAME}.deb $serverPath/mysql-apt/bin
		dpkg -X mysql-community-server-core_${SUFFIX_NAME}.deb $serverPath/mysql-apt/bin
		dpkg -X mysql-community-server_${SUFFIX_NAME}.deb $serverPath/mysql-apt/bin
		dpkg -X mysql-server_${SUFFIX_NAME}.deb $serverPath/mysql-apt/bin
	elif [[ `arch` =~ "aarch64" ]];then
		wget --no-check-certificate -O ${myDir}/mysql-client-core-5.7_arm64.deb  https://launchpad.net/~ubuntu-security-proposed/+archive/ubuntu/ppa/+build/25998745/+files/mysql-client-core-5.7_5.7.42-0ubuntu0.18.04.1_arm64.deb
		wget --no-check-certificate -O ${myDir}/mysql-client-5.7_arm64.deb  https://launchpad.net/~ubuntu-security-proposed/+archive/ubuntu/ppa/+build/25998745/+files/mysql-client-5.7_5.7.42-0ubuntu0.18.04.1_arm64.deb
		wget --no-check-certificate -O ${myDir}/mysql-server-core-5.7_arm64.deb  https://launchpad.net/~ubuntu-security-proposed/+archive/ubuntu/ppa/+build/25998745/+files/mysql-server-core-5.7_5.7.42-0ubuntu0.18.04.1_arm64.deb
		wget --no-check-certificate -O ${myDir}/mysql-server-5.7_arm64.deb  https://launchpad.net/~ubuntu-security-proposed/+archive/ubuntu/ppa/+build/25998745/+files/mysql-server-5.7_5.7.42-0ubuntu0.18.04.1_arm64.deb
		
		dpkg -X mysql-client-core-5.7_arm64.deb $serverPath/mysql-apt/bin
		dpkg -X mysql-client-5.7_arm64.deb $serverPath/mysql-apt/bin
		dpkg -X mysql-server-core-5.7_arm64.deb $serverPath/mysql-apt/bin
		dpkg -X mysql-server-core-5.7_arm64.deb $serverPath/mysql-apt/bin
	else
		echo $(date "+%Y-%m-%d %H:%M:%S") '不支持的设备类型 $(arch)' >> $install_tmp
	fi
	#######
}

APT_UNINSTALL()
{
	###
	rm -rf $myDir
	###
}


Install_mysql()
{
	echo '正在安装脚本文件...' > $install_tmp
	if id mysql &> /dev/null ;then 
	    echo "mysql uid is `id -u mysql`"
	    echo "mysql shell is `grep "^mysql:" /etc/passwd |cut -d':' -f7 `"
	else
	    groupadd mysql
		useradd -g mysql mysql
	fi


	isApt=`which apt`
	if [ "$isApt" != "" ];then
		APT_INSTALL
	fi

	if [ "$?" == "0" ];then
		mkdir -p $serverPath/mysql-apt
		echo '5.7' > $serverPath/mysql-apt/version.pl
		# mysql 全局配置
		rm -rf /usr/bin/mysql
		mv /etc/my.cnf /etc/my.cnf.$(date "+%Y-%m-%d_%H-%M-%S")
		ln -s /www/server/mysql-apt/bin/usr/bin/mysql /usr/bin
		ln -s /www/server/mysql-apt/etc/my.cnf /etc/my.cnf
		echo '安装完成' > $install_tmp
	else
		echo "暂时不支持该系统" > $install_tmp
	fi
}

Uninstall_mysql()
{

	isApt=`which apt`
	if [ "$isApt" != "" ];then
		APT_UNINSTALL
	fi

	rm -rf $serverPath/mysql-apt
	echo '卸载完成' > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_mysql
else
	Uninstall_mysql
fi
