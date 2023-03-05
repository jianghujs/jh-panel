#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

cd /www/server/jh-panel
if [ -f venv/bin/activate ];then
	source venv/bin/activate
fi