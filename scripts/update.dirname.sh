#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

startTime=`date +%s`
if [ -d "/www/server/mdserver-web" ];then
	echo 'rename to jh-panel'
	mv /www/server/mdserver-web /www/server/jh-panel
fi

cd /www/server/jh-panel && git pull

if [ -f /usr/bin/mw ];then
	rm -rf /usr/bin/mw
fi

if [ ! -e /usr/bin/mw ]; then
	if [ ! -f /usr/bin/mw ];then
		ln -s /etc/rc.d/init.d/mw /usr/bin/mw
	fi
fi

mw 1
endTime=`date +%s`
((outTime=($endTime-$startTime)/60))
echo -e "Time consumed:\033[32m $outTime \033[0mMinute!"