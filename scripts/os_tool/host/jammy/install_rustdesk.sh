#!/bin/bash

# 下载rustdesk安装包
wget https://gitee.com/rustdesk/rustdesk/attach_files/1093882/download/rustdesk-1.1.9.deb

# 安装rustdesk
sudo apt install ./rustdesk-1.1.9.deb -y

echo "安装rustdesk成功！"

# 修改 /etc/gdm3/custom.conf 文件以关闭wayland
sudo sed -i 's/#WaylandEnable=false/WaylandEnable=false/g' /etc/gdm3/custom.conf

systemctl enable rustdesk.service
echo "配置rustdesk自启动成功！"

