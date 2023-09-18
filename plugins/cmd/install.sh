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

Install_cmd()
{
	echo '正在安装cmd...' > $install_tmp
	mkdir -p $serverPath/cmd

	# # install cmd
	# apt-get update
	# apt-get install \
	# 	ca-certificates \
	# 	curl \
	# 	gnupg \
	# 	lsb-release -y

	# mkdir -p /etc/apt/keyrings
	# rm -rf /etc/apt/keyrings/docker.gpg
	# curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

	# echo \
	# "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
	# $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

	# apt-get update  

	# chmod a+r /etc/apt/keyrings/docker.gpg
	# apt-get update
	
	# ceVersion=$(apt-cache madison docker-ce | grep ${version} | awk '{print $3}')
	# apt-get install docker-ce=${ceVersion} -y --allow-downgrades

	# # install docker-compose
	# if [ -x "$(command -v docker-compose)" ]; then
	# 	echo "Docker-compose had been installed"
	# else
	# 	echo "Installing docker-compose..."
	# 	cp -r ./docker-compose /usr/local/bin/
	# 	chmod +x /usr/local/bin/docker-compose
	# 	docker-compose -v
	# fi

	echo $version > $serverPath/cmd/version.pl
	echo '安装完成' > $install_tmp
}

Uninstall_cmd()
{
	echo '正在卸载cmd...' > $install_tmp

	# # uninstall docker
	# apt-get purge docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-ce-rootless-extras -y
	# rm -rf /var/lib/docker
	# rm -rf /var/lib/containerd

	# # uninstall docker-compose
	# rm -rf /usr/local/bin/docker-compose

	rm -rf $serverPath/cmd
	echo "卸载完成" > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_cmd
else
	Uninstall_cmd
fi
