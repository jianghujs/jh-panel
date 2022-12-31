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


bash ${rootPath}/scripts/getos.sh
OSNAME=`cat ${rootPath}/data/osname.pl`
VERSION_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`
echo "${OSNAME}:${VERSION_ID}"

# system judge
if [ "$OSNAME" == "macos" ]; then
    brew install libmemcached
    brew install curl
    brew install zlib
    brew install freetype
    brew install openssl
    brew install libzip
elif [ "$OSNAME" == "opensuse" ];then
    echo "opensuse lib"
elif [ "$OSNAME" == "arch" ];then
    echo "arch lib"
elif [ "$OSNAME" == "freebsd" ];then
    echo "freebsd lib"
elif [ "$OSNAME" == "centos" ];then
    echo "centos lib"
elif [ "$OSNAME" == "rocky" ]; then
    echo "rocky lib"
elif [ "$OSNAME" == "fedora" ];then
    echo "fedora lib"
elif [ "$OSNAME" == "alma" ];then
    echo "alma lib"
elif [ "$OSNAME" == "ubuntu" ];then
    echo "ubuntu lib"
elif [ "$OSNAME" == "debian" ]; then
    echo "debian lib"
else
    echo "OK"
fi

#面板需要的库
if [ ! -f /usr/local/bin/pip3 ];then
    cn=$(curl -fsSL -m 10 http://ipinfo.io/json | grep "\"country\": \"CN\"")
    if [ ! -z "$cn" ];then
        python3 -m pip install --upgrade pip setuptools wheel -i https://mirrors.aliyun.com/pypi/simple
    else
        python3 -m pip install --upgrade pip setuptools wheel -i https://pypi.python.org/pypi
    fi
fi

which pip && pip install --upgrade pip
pip3 install --upgrade setuptools
cd /www/server/jh-panel && pip3 install -r /www/server/jh-panel/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# pip3 install flask-caching==1.10.1
# pip3 install mysqlclient


if [ ! -f /www/server/jh-panel/bin/activate ];then
    cd /www/server/jh-panel && python3 -m venv .
    cd /www/server/jh-panel && source /www/server/jh-panel/bin/activate
else
    cd /www/server/jh-panel && source /www/server/jh-panel/bin/activate
fi

pip install --upgrade pip
pip3 install --upgrade setuptools
cd /www/server/jh-panel && pip3 install -r /www/server/jh-panel/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "lib ok!"
# pip3 install flask-caching==1.10.1
# pip3 install mysqlclient

