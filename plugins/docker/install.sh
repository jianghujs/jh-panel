#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# This is the trap command. It will execute `rm -rf $serverPath/docker` when the script exits due to an error.
trap 'rm -rf $serverPath/docker' ERR INT TERM

# cd /www/server/mdserver-web/plugins/docker && /bin/bash install.sh uninstall 1.0
# cd /www/server/mdserver-web/plugins/docker && /bin/bash install.sh install 1.0

install_tmp=${rootPath}/tmp/mw_install.pl
VERSION=$2

if [ -f ${rootPath}/bin/activate ];then
	source ${rootPath}/bin/activate
fi

Install_Docker()
{
	# which docker
	# if [ "$?" == "0" ];then
	# 	echo '安装已经完成docker' > $install_tmp
	# 	exit 0
	# fi

	echo '正在安装脚本文件...' > $install_tmp
	mkdir -p $serverPath/source

	if [ ! -d  $serverPath/docker ];then
		curl -fsSL https://get.docker.com | bash
		mkdir -p $serverPath/docker
	fi

	pip install docker
	pip install pytz
	
	# install docker-compose
	if [ -x "$(command -v docker-compose)" ]; then
		echo "Docker-compose had been installed"
	else
		echo "Installing docker-compose..."

    # 根据系统架构下载对应的docker-compose，目前只支持x86_64和aarch64，后续可以根据需求添加 现有版本 v2.23.1
		ARCH=$(uname -m)
		if [ "$ARCH" = "x86_64" ]; then
		    ARCH="x86_64"
		elif [ "$ARCH" = "aarch64" ]; then
		    ARCH="aarch64"
		fi
		# sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$ARCH" -o /usr/local/bin/docker-compose
		cp -r ./docker-compose-$(uname -s | tr '[:upper:]' '[:lower:]')-$ARCH /usr/local/bin/docker-compose
		sudo chmod +x /usr/local/bin/docker-compose
		docker-compose -v
	fi

	if [ -d $serverPath/docker ];then
		echo "${VERSION}" > $serverPath/docker/version.pl
		echo '安装完成' > $install_tmp

		cd ${rootPath} && python3 ${rootPath}/plugins/docker/index.py start
		cd ${rootPath} && python3 ${rootPath}/plugins/docker/index.py initd_install
	fi
}

Uninstall_Docker()
{
	CMD=yum
	which apt
	if [ "$?" == "0" ];then
		CMD=apt
	fi

	if [ -f /usr/lib/systemd/system/docker.service ];then
		systemctl stop docker
		systemctl disable docker
		rm -rf /usr/lib/systemd/system/docker.service
		systemctl daemon-reload
	fi

	$CMD remove -y docker docker-ce-cli containerd.io
	# docker-client \
	# docker-client-latest \
	# docker-common \
	# docker-latest \
	# docker-latest-logrotate \
	# docker-logrotate \
	# docker-selinux \
	# docker-engine-selinux \
	# docker-engine \
	# docker-ce

	# uninstall docker-compose
	rm -rf /usr/local/bin/docker-compose

	rm -rf $serverPath/docker
	echo "Uninstall_Docker" > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_Docker
else
	Uninstall_Docker
fi
