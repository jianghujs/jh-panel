#!/bin/bash

# 下载并添加Oracle VirtualBox公钥
echo "开始下载并添加Oracle VirtualBox公钥..."
wget -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O- | apt-key add -
wget -q https://www.virtualbox.org/download/oracle_vbox.asc -O- | apt-key add -
echo "Oracle VirtualBox公钥下载并添加完成."

# 添加VirtualBox源到源列表
echo "添加VirtualBox源到源列表..."
echo "deb [arch=amd64] http://download.virtualbox.org/virtualbox/debian $(lsb_release -cs) contrib" | tee -a /etc/apt/sources.list.d/virtualbox.list
echo "VirtualBox源添加完成."

# 更新包列表
echo "开始更新包列表..."
apt update
echo "包列表更新完成."

# 安装VirtualBox
echo "开始安装VirtualBox..."
apt install -y virtualbox-7.0
echo "VirtualBox安装完成."

