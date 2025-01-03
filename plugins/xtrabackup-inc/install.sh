#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")


install_tmp=${rootPath}/tmp/mw_install.pl

VERSION=$2

Install_xtrabackup_inc()
{
	echo '正在安装脚本文件...' > $install_tmp
	mkdir -p /www/backup/xtrabackup_data_base
	mkdir -p /www/backup/xtrabackup_data_incremental
	# wget -O ./percona-xtrabackup.amd.deb https://repo.percona.com/apt/percona-release_latest.generic_all.deb
	# wget -O ./percona-xtrabackup.arm.deb http://ports.ubuntu.com/pool/universe/p/percona-xtrabackup/percona-xtrabackup_2.4.9-0ubuntu2_arm64.deb
	apt-get update
	apt-get install -f -y
	if [[ `arch` =~ "x86_64" ]];then
		echo $(date "+%Y-%m-%d %H:%M:%S") 'this is x86_64' >> $install_tmp
		dpkg -i percona-xtrabackup.amd.deb
		apt-get update
		apt-get install percona-xtrabackup-24 -y
	  apt-get install qpress -y
	elif [[ `arch` =~ "aarch64" ]];then
		echo $(date "+%Y-%m-%d %H:%M:%S") 'this is arm64' >> $install_tmp
		dpkg -i percona-xtrabackup.arm.deb
		apt-get update
		apt-get install percona-xtrabackup -y
    wget https://ca.us.mirror.archlinuxarm.org/aarch64/extra/qpress-1.1-4-aarch64.pkg.tar.xz
    tar -xvf qpress-1.1-4-aarch64.pkg.tar.xz
    cp -r usr/bin/qpress /usr/bin/
    rm qpress-1.1-4-aarch64.pkg.tar.xz
    rm -r usr
	else
		echo $(date "+%Y-%m-%d %H:%M:%S") '不支持的设备类型 $(arch)' >> $install_tmp
	fi
	
	mkdir -p $serverPath/xtrabackup-inc
	echo "2.4" > $serverPath/xtrabackup-inc/version.pl
	echo $(date "+%Y-%m-%d %H:%M:%S") 'xtrabackup-inc 安装成功' >> $serverPath/xtrabackup-inc/xtrabackup.log
	cp -r $rootPath/plugins/xtrabackup-inc/example/xtrabackup-full.sh $serverPath/xtrabackup-inc/xtrabackup-full.sh
	cp -r $rootPath/plugins/xtrabackup-inc/example/xtrabackup-inc.sh $serverPath/xtrabackup-inc/xtrabackup-inc.sh
	cp -r $rootPath/plugins/xtrabackup-inc/example/xtrabackup-inc-recovery.sh $serverPath/xtrabackup-inc/xtrabackup-inc-recovery.sh
	cp -r $rootPath/plugins/xtrabackup-inc/conf/backup.ini $serverPath/xtrabackup-inc/backup.ini
	cd ${rootPath} && python3 ${rootPath}/plugins/xtrabackup-inc/index.py initd_install
	echo $(date "+%Y-%m-%d %H:%M:%S") '安装完成' >> $install_tmp
}

Update_xtrabackup_inc() 
{
    echo '正在更新...' > $install_tmp
    cp -r $rootPath/plugins/xtrabackup-inc/example/xtrabackup-full.sh $serverPath/xtrabackup-inc/xtrabackup-full.sh
	cp -r $rootPath/plugins/xtrabackup-inc/example/xtrabackup-inc.sh $serverPath/xtrabackup-inc/xtrabackup-inc.sh
	cp -r $rootPath/plugins/xtrabackup-inc/example/xtrabackup-inc-recovery.sh $serverPath/xtrabackup-inc/xtrabackup-inc-recovery.sh
	cp -r $rootPath/plugins/xtrabackup-inc/conf/backup.ini $serverPath/xtrabackup-inc/backup.ini
	cd ${rootPath} && python3 ${rootPath}/plugins/xtrabackup-inc/index.py initd_install
	echo $(date "+%Y-%m-%d %H:%M:%S") '更新完成' >> $install_tmp
}


Uninstall_xtrabackup_inc()
{
	echo $(date "+%Y-%m-%d %H:%M:%S") '卸载开始' >> $install_tmp
	echo $(apt-get remove percona-xtrabackup -y) >> $install_tmp
	echo $(apt-get remove percona-xtrabackup-24 -y) >> $install_tmp
  if [[ `arch` =~ "x86_64" ]];then
    echo $(apt-get remove qpress -y) >> $install_tmp
  elif [[ `arch` =~ "aarch64" ]];then
    rm -r /usr/bin/qpress
  fi
	rm -rf $serverPath/xtrabackup-inc
	echo $(date "+%Y-%m-%d %H:%M:%S") '卸载完成' >> $install_tmp	
}

action=$1
if [ "${1}" == 'install' ];then
	Install_xtrabackup_inc
elif [ "${1}" == 'update' ];then
    Update_xtrabackup_inc
else
	Uninstall_xtrabackup_inc
fi
