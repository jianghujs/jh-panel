#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

cd /www/server/jh-panel
if [ -f bin/activate ];then
	source bin/activate
fi