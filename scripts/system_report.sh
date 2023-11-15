#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

export LANG=en_US.UTF-8
MW_PATH=/www/server/jh-panel/bin/activate
if [ -f $MW_PATH ];then
    source $MW_PATH
fi

pushd /www/server/jh-panel/ > /dev/null 
python3 /www/server/jh-panel/scripts/report.py send
popd > /dev/null
echo "----------------------------------------------------------------------------"
endDate=`date +"%Y-%m-%d %H:%M:%S"`
echo "★[$endDate] Successful"
echo "----------------------------------------------------------------------------"
