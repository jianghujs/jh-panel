#!/bin/bash

# 安装ssh
echo "开始安装SSH..."
apt-get install -y ssh
echo "SSH安装完成."

# 备份原始配置
echo "开始备份原始SSH配置..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
echo "原始SSH配置备份完成."

# 检查并添加PermitRootLogin配置
echo "检查并添加PermitRootLogin配置..."
if ! grep -q "^PermitRootLogin" /etc/ssh/sshd_config; then
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
    echo "PermitRootLogin配置添加完成."
else
    echo "PermitRootLogin配置已存在，无需添加."
fi

# 检查并添加PasswordAuthentication配置
echo "检查并添加PasswordAuthentication配置..."
if ! grep -q "^PasswordAuthentication" /etc/ssh/sshd_config; then
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config
    echo "PasswordAuthentication配置添加完成."
else
    echo "PasswordAuthentication配置已存在，无需添加."
fi

# 重启ssh服务
echo "重启SSH服务..."
/etc/init.d/ssh restart
echo "SSH服务重启完成."
