#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

startTime=`date +%s`
if [ -d "/www/server/mdserver-web" ];then
	echo 'rename to jh-panel'
	mv /www/server/mdserver-web /www/server/jh-panel
fi

cd /www/server/jh-panel && git pull
