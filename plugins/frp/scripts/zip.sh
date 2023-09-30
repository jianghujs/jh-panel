#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

wget -O /tmp/mw_plugin.zip https://github.com/mw-plugin/simple-plugin/archive/refs/heads/main.zip
cd /tmp && unzip /tmp/mw_plugin.zip 

mkdir -p /www/server/mdserver-web/plugins/simple-plugin
cp -rf  /tmp/simple-plugin-main/* /www/server/mdserver-web/plugins/simple-plugin

rm -rf /tmp/mw_plugin.zip
rm -rf /tmp/simple-plugin-main


# 安装 && 启动
cd /www/server/mdserver-web/plugins/simple-plugin && /bin/bash install.sh install 0.1
cd /www/server/mdserver-web && python3 /www/server/mdserver-web/plugins/simple-plugin/index.py start