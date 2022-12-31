#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

echo "welcome to jh-panel panel"

startTime=`date +%s`

if [ ! -d /www/server/jh-panel ];then
	echo "jh-panel not exist!"
	exit 1
fi

# openresty
if [ ! -d /www/server/openresty ];then
	cd /www/server/jh-panel/plugins/openresty && bash install.sh install 1.21.4.1
else
	echo "openresty alreay exist!"
fi


# php
if [ ! -d /www/server/php/71 ];then
	cd /www/server/jh-panel/plugins/php && bash install.sh install 71
else
	echo "php71 alreay exist!"
fi


# php
if [ ! -d /www/server/php/74 ];then
	cd /www/server/jh-panel/plugins/php && bash install.sh install 74
else
	echo "php74 alreay exist!"
fi


# swap
if [ ! -d /www/server/swap ];then
	cd /www/server/jh-panel/plugins/swap && bash install.sh install 1.1
else
	echo "swap alreay exist!"
fi

# mysql
if [ ! -d /www/server/mysql ];then
	cd /www/server/jh-panel/plugins/mysql && bash install.sh install 5.6
else
	echo "mysql alreay exist!"
fi

# phpmyadmin
if [ ! -d /www/server/phpmyadmin ];then
	cd /www/server/jh-panel/plugins/phpmyadmin && bash install.sh install 4.4.15
else
	echo "phpmyadmin alreay exist!"
fi

endTime=`date +%s`
((outTime=(${endTime}-${startTime})/60))
echo -e "Time consumed:\033[32m $outTime \033[0mMinute!"

