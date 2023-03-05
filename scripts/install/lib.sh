#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin

curPath=`pwd`
rootPath=$(dirname "$curPath")
serverPath=$(dirname "$rootPath")
sourcePath=$serverPath/source/lib
libPath=$serverPath/lib

mkdir -p $sourcePath
mkdir -p $libPath
rm -rf ${libPath}/lib.pl


#面板需要的库
# which pip && pip install --upgrade pip
# pip3 install --upgrade setuptools
# cd /www/server/jh-panel && pip3 install -r /www/server/jh-panel/requirements.txt

# pip3 install flask-caching==1.10.1
# pip3 install mysqlclient

# 使用虚拟环境
if [ ! -f /www/server/jh-panel/venv/venv/bin/activate ];then
    cd /www/server/jh-panel && python3 -m venv venv
    cd /www/server/jh-panel && source /www/server/jh-panel/venv/bin/activate
else
    cd /www/server/jh-panel && source /www/server/jh-panel/venv/bin/activate
fi

pip install --upgrade pip
pip3 install --upgrade setuptools
cd /www/server/jh-panel && pip3 install -r /www/server/jh-panel/requirements.txt

echo "lib is ok!"
# pip3 install flask-caching==1.10.1
# pip3 install mysqlclient

