#!/bin/bash

# 更新包列表
echo "开始更新包列表..."
apt update
echo "包列表更新完成."

# 安装xrdp
echo "开始安装xrdp..."
apt install xrdp
echo "xrdp安装完成."

# 启动xrdp服务
echo "启动xrdp服务..."
systemctl start xrdp
echo "xrdp服务已启动."

# 将xrdp服务设置为开机启动
echo "将xrdp服务设置为开机启动..."
systemctl enable xrdp
echo "xrdp服务已设置为开机启动."
