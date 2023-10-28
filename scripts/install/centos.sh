#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
LANG=en_US.UTF-8

# 检查是否为root用户
if [ "$EUID" -ne 0 ]
  then echo "Please run as root!"
  exit
fi

# 安装相应工具 zip, unzip, git
yum install -y wget zip unzip git


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

# git clone jh-panel from github
echo "git clone https://github.com/jianghujs/jh-panel /www/server/jh-panel"
git clone https://github.com/jianghujs/jh-panel /www/server/jh-panel


if [ ! -f /usr/bin/applydeltarpm ];then
	yum -y provides '*/applydeltarpm'
	yum -y install deltarpm
fi

VERSION_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`

setenforce 0
sed -i 's#SELINUX=enforcing#SELINUX=disabled#g' /etc/selinux/config

yum install -y wget lsof crontabs
yum install -y python3-devel
yum install -y python3-pip
yum install -y python-devel
yum install -y vixie-cron
yum install -y curl-devel libmcrypt libmcrypt-devel
yum install -y mysql-devel
yum install -y expect



#https need
if [ ! -d /root/.acme.sh ];then	
	curl https://get.acme.sh | sh
fi

if [ -f /etc/init.d/iptables ];then

	iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 22 -j ACCEPT
	iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 80 -j ACCEPT
	iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 443 -j ACCEPT
	iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 888 -j ACCEPT
	iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 10022 -j ACCEPT
	iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 10744 -j ACCEPT
	iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 33067 -j ACCEPT
	# iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 7200 -j ACCEPT
	# iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 3306 -j ACCEPT
	# iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport 30000:40000 -j ACCEPT
	service iptables save

	iptables_status=`service iptables status | grep 'not running'`
	if [ "${iptables_status}" == '' ];then
		service iptables restart
	fi

	#安装时不开启
	service iptables stop
fi


if [ ! -f /etc/init.d/iptables ];then
	yum install firewalld -y
	systemctl enable firewalld
	#取消服务锁定
	systemctl unmask firewalld
	systemctl start firewalld

	firewall-cmd --permanent --zone=public --add-port=22/tcp
	firewall-cmd --permanent --zone=public --add-port=80/tcp
	firewall-cmd --permanent --zone=public --add-port=443/tcp
	firewall-cmd --permanent --zone=public --add-port=888/tcp
	firewall-cmd --permanent --zone=public --add-port=10022/tcp
	firewall-cmd --permanent --zone=public --add-port=10744/tcp
	firewall-cmd --permanent --zone=public --add-port=33067/tcp
	# firewall-cmd --permanent --zone=public --add-port=7200/tcp
	# firewall-cmd --permanent --zone=public --add-port=3306/tcp
	# firewall-cmd --permanent --zone=public --add-port=30000-40000/tcp


	sed -i 's#AllowZoneDrifting=yes#AllowZoneDrifting=no#g' /etc/firewalld/firewalld.conf
	firewall-cmd --reload
	#安装时不开启
	systemctl stop firewalld
fi

yum groupinstall -y "Development Tools"
yum install -y epel-release

yum install -y oniguruma oniguruma-devel
#centos8 stream | use dnf
if [ "$?" != "0" ];then
	yum install -y dnf dnf-plugins-core
	dnf config-manager --set-enabled powertools
	yum install -y oniguruma oniguruma-devel
	dnf upgrade -y libmodulemd
fi


yum install -y libtirpc libtirpc-devel
yum install -y rpcgen
yum install -y openldap openldap-devel  
yum install -y bison re2c
yum install -y cmake3
yum install -y autoconf
yum install -y make cmake gcc gcc-c++

yum install -y libmemcached libmemcached-devel
yum install -y curl curl-devel
yum install -y zlib zlib-devel
yum install -y libzip libzip-devel
yum install -y pcre pcre-devel
yum install -y icu libicu-devel 
yum install -y freetype freetype-devel
yum install -y openssl openssl-devel
yum install -y libxml2 libxml2-devel
yum install -y graphviz
yum install -y sqlite-devel
yum install -y oniguruma oniguruma-devel
yum install -y ImageMagick ImageMagick-devel


yum install -y libzstd-devel
yum install -y libevent libevent-devel unzip zip
# yum install -y python-imaging
yum install -y libicu-devel  bzip2-devel  pcre pcre-devel

yum install -y gd gd-devel
yum install -y libjpeg-devel libpng-devel libwebp libwebp-devel

yum install -y net-tools
yum install -y ncurses-devel
yum install -y libXpm-devel


for yumPack in flex file libtool libtool-libs kernel-devel patch wget glib2 glib2-devel tar bzip2 bzip2-devel libevent libevent-devel ncurses ncurses-devel curl curl-devel libcurl libcurl-devel e2fsprogs e2fsprogs-devel libidn libidn-devel vim-minimal gettext gettext-devel ncurses-devel gmp-devel libcap diffutils ca-certificates net-tools psmisc git-core c-ares-devel libicu-devel libxslt libxslt-devel zip unzip glibc.i686 libstdc++.so.6 cairo-devel ncurses-devel libaio-devel perl perl-devel perl-Data-Dumper expat-devel readline-devel;
do yum -y install $yumPack;done


if [ "$VERSION_ID" -eq "8" ];then
	dnf upgrade -y libmodulemd
fi

if [ "$VERSION_ID" -eq "9" ];then
	yum install -y patchelf
	dnf --enablerepo=crb install -y libtirpc-devel
	dnf --enablerepo=crb install -y libmemcached libmemcached-devel
	dnf --enablerepo=crb install -y libtool libtool-libs
	dnf --enablerepo=crb install -y gnutls-devel
	dnf --enablerepo=crb install -y mysql-devel

	dnf --enablerepo=crb install -y libvpx-devel libXpm-devel libwebp libwebp-devel
	dnf --enablerepo=crb install -y libjpeg-devel libpng-devel
	dnf --enablerepo=crb install -y oniguruma oniguruma-devel
	dnf --enablerepo=crb install -y libzip libzip-devel
	# yum remove -y chardet
fi

# 安装pip3
if [ ! -f /usr/local/bin/pip3 ];then
  python3 -m pip install --upgrade pip setuptools wheel
fi

# 安装python依赖
cd /www/server/jh-panel/scripts && bash lib.sh
chmod 755 /www/server/jh-panel/data


# 安装后文件会被清空(cn only)
mkdir -p /www/server/jh-panel/data
echo "True" > /www/server/jh-panel/data/net_env_cn.pl

