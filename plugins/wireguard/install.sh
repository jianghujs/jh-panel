#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin

# for mac
export PATH=$PATH:/opt/homebrew/bin

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

Install_App()
{
	mkdir -p $serverPath/wireguard
	mkdir -p /etc/wireguard

	if command -v wg >/dev/null 2>&1; then
		echo '检测到 wg 已安装'
	else
		echo '开始安装 WireGuard 相关组件...'
		if command -v apt-get >/dev/null 2>&1; then
			apt-get update -y
			apt-get install -y wireguard wireguard-tools || apt-get install -y wireguard-tools
		elif command -v yum >/dev/null 2>&1; then
			yum install -y wireguard-tools || yum install -y wireguard
		elif command -v dnf >/dev/null 2>&1; then
			dnf install -y wireguard-tools || dnf install -y wireguard
		elif command -v zypper >/dev/null 2>&1; then
			zypper install -y wireguard-tools || zypper install -y wireguard
		elif command -v pacman >/dev/null 2>&1; then
			pacman -Sy --noconfirm wireguard-tools || pacman -Sy --noconfirm wireguard
		elif command -v brew >/dev/null 2>&1; then
			brew install wireguard-tools
		else
			echo 'WARN: 未找到可用的包管理器，请手动安装 WireGuard'
		fi
	fi

	if command -v wg >/dev/null 2>&1; then
		echo 'WireGuard 安装完成'
		cd ${rootPath} && python3 ${rootPath}/plugins/wireguard/index.py initd_install
	else
		echo 'WARN: 未检测到 wg 命令，请确认安装结果'
	fi

	echo '1.0' > $serverPath/wireguard/version.pl
}

Uninstall_App()
{
	rm -rf $serverPath/wireguard
	echo 'WireGuard 插件标记已清理（未卸载系统包）'
}

action=$1
if [ "${action}" == 'install' ]; then
	Install_App
else
	Uninstall_App
fi
