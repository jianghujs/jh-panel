#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")
installPath=/www/server/nodejs
installFnmPath=${installPath}/fnm
# logPath=${installPath}/nodejs.plugin.log
install_tmp=${rootPath}/tmp/mw_install.pl
# fnm command not found to ubuntu20.04
bashrcFile=/root/.bashrc
profileFile=/etc/profile


Install_nodejs()
{
	echo '正在安装脚本文件...' > $install_tmp

	mkdir -p $installPath
	OS="$(uname -s)"
	if [ "$OS" = "Linux" ]; then
		# Based on https://stackoverflow.com/a/45125525
		case "$(uname -m)" in
			arm | armv7*)
				unzip -q "$curPath/script/fnm-arm32.zip" -d "$installFnmPath"
				;;
			aarch* | armv8*)
				unzip -q "$curPath/script/fnm-arm64.zip" -d "$installFnmPath"
				;;
			*)
				unzip -q "$curPath/script/fnm-linux.zip" -d "$installFnmPath"
		esac
	else
		echo "OS $OS is not supported."
		echo "If you think that's a bug - please file an issue to https://github.com/Schniz/fnm/issues"
		exit 1
	fi

	chmod u+x "$installFnmPath/fnm"

	echo "Installing for Bash. Appending the following to $bashrcFile:"
    echo ""
    echo '  export PATH="'"$installFnmPath"':$PATH"  #fnm env'
    echo '  eval "`fnm env`"  #fnm env'
	# source 写一份
	echo '' >>$bashrcFile
    echo 'export PATH="'"$installFnmPath"':$PATH"  #fnm env' >>$bashrcFile
    echo 'eval "`fnm env`"  #fnm env' >>$bashrcFile
	# profile 写一份
	echo '' >>$profileFile
    echo 'export PATH="'"$installFnmPath"':$PATH"  #fnm env' >>$profileFile
    echo 'eval "`fnm env`"  #fnm env' >>$profileFile
	
	source $bashrcFile
	echo "Installing node v16.7: fnm install v16.17 && fnm use v16.17 && fnm default v16.17"
	if [ -f "/www/server/jh-panel/data/net_env_cn.pl" ]; then
		echo "正在使用国内镜像安装..."
		fnm install v16.17 --node-dist-mirror=https://npmmirror.com/mirrors/node && fnm use v16.17 && fnm default v16.17
	else
		fnm install v16.17 && fnm use v16.17 && fnm default v16.17
	fi
	echo '1.0' > $installPath/version.pl
	echo '安装完成' > $install_tmp
}

Uninstall_nodejs()
{	
	sed -i '/#fnm env/d' $bashrcFile
	sed -i '/#fnm env/d' $profileFile
	rm -rf $installPath
	source $bashrcFile
	echo "卸载完成" > $install_tmp
}

action=$1
if [ "${1}" == 'install' ];then
	Install_nodejs
else
	Uninstall_nodejs
fi
