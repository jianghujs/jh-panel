#!/bin/bash

# 下载rustdesk安装包
wget https://github.com/rustdesk/rustdesk/releases/download/1.2.2/rustdesk-1.2.2-x86_64.deb

# 安装rustdesk
sudo apt install ./rustdesk-1.2.2-x86_64.deb -y

echo "安装rustdesk成功！"

# 修改 /etc/gdm3/custom.conf 文件以关闭wayland
sudo sed -i 's/#WaylandEnable=false/WaylandEnable=false/g' /etc/gdm3/custom.conf

systemctl enable rustdesk.service
echo "配置rustdesk自启动成功！"

