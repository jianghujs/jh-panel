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


Install_nodejs()
{
	echo '正在安装脚本文件...' > $install_tmp


	curl -o- http://npmjs.org/install.sh | bash
	# sh ./script/npmjs.install.sh

	apt install -y nodejs
	apt install -y npm
	npm install nodejs -g
	# if [ "$OSNAME" == 'debian' ] && [ "$OSNAME" == 'ubuntu' ];then
	# 	apt install -y nodejs
	# 	apt install -y npm
	# 	npm install nodejs -g
	# else 
	# 	yum install -y nodejs
	# 	yum install -y npm
	# 	npm install nodejs -g
	# fi
	
	curl -fsSL https://fnm.vercel.app/install | bash
	# sh ./script/fnm.install.sh

	mkdir -p $serverPath/nodejs
	echo '1.0' > $serverPath/nodejs/version.pl
	echo '安装完成' > $install_tmp
}

Uninstall_nodejs()
{
	rm -rf $serverPath/nodejs
	echo "卸载完成" > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_nodejs
else
	Uninstall_nodejs
fi
