#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
export LANG=en_US.UTF-8
export DEBIAN_FRONTEND=noninteractive

# 检查是否为root用户
if [ "$EUID" -ne 0 ]
  then echo "Please run as root!"
  exit
fi

# apt 更新
apt update -y
apt-get update -y 
# install git,zip, unzip
apt install -y wget zip unzip
apt install -y git


# 创建www用户组
if id www &> /dev/null ;then 
  echo ""
else
	groupadd www
	useradd -g www -s /bin/bash www
fi

# 创建www目录
mkdir -p /www/server
mkdir -p /www/wwwroot
mkdir -p /www/wwwlogs
mkdir -p /www/backup/database
mkdir -p /www/backup/site

# git clone jh-panel from gitee (cn only)
echo "git clone https://gitee.com/jianghujs/jh-panel /www/server/jh-panel"
git clone https://gitee.com/jianghujs/jh-panel /www/server/jh-panel


# 添加软连接, bash指向sh
sudo ln -sf /bin/bash /bin/sh

# install lib
apt install -y wget curl lsof unzip
apt install -y python3-pip
apt install -y python3-venv
apt install -y python3-dev
apt install -y expect

apt install -y cron

apt install -y locate
locale-gen en_US.UTF-8
localedef -v -c -i en_US -f UTF-8 en_US.UTF-8

# 设置防火墙开放端口
if [ -f /usr/sbin/ufw ];then

	ufw allow 22/tcp
	ufw allow 80/tcp
	ufw allow 443/tcp
	ufw allow 888/tcp
	# ufw allow 7200/tcp
	# ufw allow 3306/tcp
	# ufw allow 30000:40000/tcp
  
  # 关闭防火墙（安装时先关闭）
  ufw disable
fi

# 若防火墙不存在则安装firewalld
if [ ! -f /usr/sbin/ufw ];then
	apt install -y firewalld
	systemctl enable firewalld
	systemctl start firewalld

	firewall-cmd --permanent --zone=public --add-port=22/tcp
	firewall-cmd --permanent --zone=public --add-port=80/tcp
	firewall-cmd --permanent --zone=public --add-port=443/tcp
	firewall-cmd --permanent --zone=public --add-port=888/tcp
	# firewall-cmd --permanent --zone=public --add-port=7200/tcp
	# firewall-cmd --permanent --zone=public --add-port=3306/tcp
	# firewall-cmd --permanent --zone=public --add-port=30000-40000/tcp

	# fix:debian10 firewalld faq
	# https://kawsing.gitbook.io/opensystem/andoid-shou-ji/untitled/fang-huo-qiang#debian-10-firewalld-0.6.3-error-commandfailed-usrsbinip6tablesrestorewn-failed-ip6tablesrestore-v1.8
	sed -i 's#IndividualCalls=no#IndividualCalls=yes#g' /etc/firewalld/firewalld.conf
  # 重载防火墙
	firewall-cmd --reload
fi

#安装时不开启防火墙
systemctl stop firewalld


apt install -y devscripts
apt install -y net-tools
apt install -y python3-dev
apt install -y autoconf
apt install -y gcc

apt install -y libffi-dev
apt install -y cmake automake make

apt install -y webp scons
apt install -y libwebp-dev
apt install -y lzma lzma-dev
apt install -y libunwind-dev

apt install -y libpcre3 libpcre3-dev 
apt install -y openssl
apt install -y libssl-dev

apt install -y libmemcached-dev
apt install -y libsasl2-dev
apt install -y imagemagick 
apt install -y libmagickwand-dev

apt install -y libxml2 libxml2-dev libbz2-dev libmcrypt-dev libpspell-dev librecode-dev
apt install -y libgmp-dev libgmp3-dev libreadline-dev libxpm-dev
apt install -y dia pkg-config
apt install -y zlib1g-dev
apt install -y libjpeg-dev libpng-dev
apt install -y libfreetype6
apt install -y libjpeg62-turbo-dev
apt install -y libfreetype6-dev
apt install -y libevent-dev libncurses5-dev libldap2-dev
apt install -y libzip-dev
apt install -y libicu-dev

apt install -y build-essential

apt install -y libcurl4-openssl-dev
apt install -y curl libcurl4-gnutls-dev
#https://blog.csdn.net/qq_36228377/article/details/123154344
# ln -s  /usr/include/x86_64-linux-gnu/curl  /usr/include/curl
if [ ! -d /usr/include/curl ];then
    ln -s  /usr/include/x86_64-linux-gnu/curl  /usr/include/curl
fi


apt install -y graphviz bison re2c flex
apt install -y libsqlite3-dev
apt install -y libonig-dev

apt install -y perl g++ libtool    
apt install -y libxslt1-dev

apt install -y libmariadb-dev
#apt install -y libmysqlclient-dev   
apt install -y libmariadb-dev-compat
#apt install -y libmariadbclient-dev


# mysql8.0 在ubuntu22需要的库
apt install -y patchelf

VERSION_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`
if [ "${VERSION_ID}" == "22.04" ];then
	apt install -y python3-cffi
    pip3 install -U --force-reinstall --no-binary :all: gevent
fi

# 安装pip3
if [ ! -f /usr/local/bin/pip3 ];then
    python3 -m pip install --upgrade pip setuptools wheel
fi
# pip 设置清华源(cn only)
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装python依赖
cd /www/server/jh-panel/scripts/install_b && bash lib.sh
chmod 755 /www/server/jh-panel/data


if [ "${VERSION_ID}" == "22.04" ];then
	apt install -y python3-cffi
    pip3 install -U --force-reinstall --no-binary :all: gevent
fi

# 安装后文件会被清空(cn only)
mkdir -p /www/server/jh-panel/data
echo "True" > /www/server/jh-panel/data/net_env_cn.pl
