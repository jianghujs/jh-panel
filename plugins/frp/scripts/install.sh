#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH


curPath=`pwd`
rootPath=$(dirname "$curPath")

cd /www/server/mdserver-web/plugins && rm -rf frp && git clone https://github.com/mw-plugin/frp && cd frpc && rm -rf .git && cd /www/server/mdserver-web/plugins/frp && bash install.sh install 1.0