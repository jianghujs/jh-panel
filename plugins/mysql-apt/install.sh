#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# https://downloads.mysql.com/archives/community/

# cd /www/server/jh-panel/plugins/mysql-apt && bash install.sh install 8.0
# cd /www/server/jh-panel/plugins/mysql-apt && bash install.sh uninstall 8.0
# cd /www/server/jh-panel && python3 /www/server/jh-panel/plugins/mysql-apt/index.py start 8.0

install_tmp=${rootPath}/tmp/mw_install.pl


action=$1
type=$2


if [ "${2}" == "" ];then
	echo '缺少安装脚本...' > $install_tmp
	exit 0
fi 

if [ ! -d $curPath/versions/$2 ];then
	echo '缺少安装脚本2...' > $install_tmp
	exit 0
fi

if [ "${action}" == "uninstall" ];then
	
	cd ${rootPath} && python3 ${rootPath}/plugins/mysql-apt/index.py stop ${type}
	cd ${rootPath} && python3 ${rootPath}/plugins/mysql-apt/index.py initd_uninstall ${type}
	cd $curPath

	if [ -f /usr/lib/systemd/system/mysql-apt.service ] || [ -f /lib/systemd/system/mysql-apt.service ];then
		systemctl stop mysql-apt
		systemctl disable mysql-apt
		rm -rf /usr/lib/systemd/system/mysql-apt.service
		rm -rf /lib/systemd/system/mysql-apt.service
		systemctl daemon-reload
	fi
fi

sh -x $curPath/versions/$2/install.sh $1

if [ "${action}" == "install" ];then
# 	#初始化 
	cd ${rootPath} && python3 ${rootPath}/plugins/mysql-apt/index.py start ${type}
	cd ${rootPath} && python3 ${rootPath}/plugins/mysql-apt/index.py initd_install ${type}
	cd ${rootPath} && python3 ${rootPath}/plugins/mysql-apt/index.py set_db_status_by_system_memory ${type}
  mkdir -p /www/server/mysql-apt/etc/mode/
  rsync -a --delete ${rootPath}/plugins/mysql-apt/conf/gtid.cnf  ${serverPath}/mysql-apt/etc/mode/gtid.cnf
	cd ${rootPath} && python3 ${rootPath}/plugins/mysql-apt/index.py restart ${type}
fi
