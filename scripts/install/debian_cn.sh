#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
export LANG=en_US.UTF-8
export DEBIAN_FRONTEND=noninteractive

APT_UPDATE_LOG="/tmp/jh-panel-apt-update.log"
DEBIAN_VERSION_ID=""
DEBIAN_CODENAME=""

if [ -f /etc/os-release ]; then
	. /etc/os-release
	DEBIAN_VERSION_ID="${VERSION_ID:-}"
	DEBIAN_CODENAME="${VERSION_CODENAME:-}"
fi

# Debian 11 的 bullseye-backports 已从普通镜像下线，旧配置会导致 apt update 返回 404。
disable_expired_bullseye_backports()
{
	local source_file
	local backup_file
	local backup_suffix

	if [ "${DEBIAN_CODENAME}" != "bullseye" ] && [ "${DEBIAN_VERSION_ID}" != "11" ]; then
		return 0
	fi

	backup_suffix=$(date +%Y%m%d%H%M%S)
	for source_file in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do
		[ -f "${source_file}" ] || continue
		if grep -Eq '^[[:space:]]*deb(-src)?[[:space:]].*[[:space:]]bullseye-backports([[:space:]]|$)' "${source_file}"; then
			backup_file="${source_file}.jh-panel-backup-${backup_suffix}"
			cp -a "${source_file}" "${backup_file}"
			sed -Ei '/^[[:space:]]*deb(-src)?[[:space:]].*[[:space:]]bullseye-backports([[:space:]]|$)/ s|^[[:space:]]*|# jh-panel: bullseye-backports 已归档，已禁用 |' "${source_file}"
			echo "|- 已禁用失效源 bullseye-backports，原配置备份到 ${backup_file}"
		fi
	done
}

update_apt_sources()
{
	echo "-----------------------"
	echo "正在检查 Debian APT 软件源"
	echo "系统版本: Debian ${DEBIAN_VERSION_ID:-未知} (${DEBIAN_CODENAME:-未知})"
	echo "-----------------------"

	disable_expired_bullseye_backports

	LC_ALL=C apt-get update -o Acquire::Retries=3 2>&1 | tee "${APT_UPDATE_LOG}"
	if [ "${PIPESTATUS[0]}" -ne 0 ] || grep -Eq '^(E:|W: Failed to fetch)' "${APT_UPDATE_LOG}"; then
		echo -e "\e[1;31m× APT 软件源更新失败，安装已停止，避免继续产生依赖报错。\e[0m"
		echo "请检查上方错误，或查看日志: ${APT_UPDATE_LOG}"
		echo "常见原因: 第三方源失效、发行版代号配置错误、网络或 DNS 异常。"
		exit 1
	fi

	echo -e "\e[0;32m|- APT 软件源更新成功✅\e[0m"
}

# 检查是否为root用户
if [ "$EUID" -ne 0 ]
  then echo "Please run as root!"
  exit 1
fi

# apt 修改为阿里源(cn only)
sed -i 's#http://deb.debian.org#https://mirrors.aliyun.com#g' /etc/apt/sources.list

# apt 更新
update_apt_sources
# apt 安装相应工具
apt install -y devscripts
apt install -y wget zip unzip
apt install -y git

# 安装中文环境
sed -i -e "s/# en_US.UTF-8.*/en_US.UTF-8 UTF-8/" /etc/locale.gen
sed -i -e "s/# zh_CN.UTF-8.*/zh_CN.UTF-8 UTF-8/" /etc/locale.gen
sed -i -e "s/# zh_CN.GBK.*/zh_CN.GBK GBK/" /etc/locale.gen
sed -i -e "s/# zh_CN.GB2312.*/zh_CN.GB2312 GB2312/" /etc/locale.gen
apt install -y locales ttf-wqy-microhei
dpkg-reconfigure --frontend=noninteractive locales 

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

# 判断是否存在jh-panel目录，存在则删除
if [ -d "/www/server/jh-panel" ]; then
  echo "目录 /www/server/jh-panel 存在"
  read -p "是否删除该目录？[y/n]: " answer
  if [[ $answer == 'y' ]]; then
    rm -rf "/www/server/jh-panel"
    echo "目录已删除"
  fi
fi

# git clone jh-panel from gitee (cn only)
echo "git clone https://gitee.com/jianghujs/jh-panel /www/server/jh-panel"
git clone https://gitee.com/jianghujs/jh-panel /www/server/jh-panel


# 创建软连接，将bash指向sh
ln -sf /bin/bash /bin/sh

# 32位系统需要安装rust
__GET_BIT=`getconf LONG_BIT`
if [ "$__GET_BIT" == "32" ];then
	# install rust | 32bit need
	# curl https://sh.rustup.rs -sSf | sh
	apt install -y rustc
fi

# synchronize time first
apt-get install ntpdate -y
ntpdate time.nist.gov | logger -t NTP

# 继续安装工具及环境
apt install -y wget curl lsof unzip
apt install -y python3-pip
apt install -y python3-dev
apt install -y python3-venv
apt install -y cron
apt install -y expect

apt install -y locate
locale-gen en_US.UTF-8
localedef -v -c -i en_US -f UTF-8 en_US.UTF-8

# 安装acme.sh(创建和配置https证书)
if [ ! -d /root/.acme.sh ];then	
	git clone https://gitee.com/neilpang/acme.sh.git /www/server/acme.sh
	cd /www/server/acme.sh
	./acme.sh --install
fi

# 防火墙开放端口
if [ -f /usr/sbin/ufw ];then
	ufw allow 22/tcp
	ufw allow 80/tcp
	ufw allow 443/tcp
	ufw allow 888/tcp
	ufw allow 10022/tcp
	ufw allow 10744/tcp
	ufw allow 33067/tcp
	# ufw allow 7200/tcp
	# ufw allow 3306/tcp
	# ufw allow 30000:40000/tcp
	
	# 关闭防火墙（安装时先关闭）
	ufw disable
fi

# 若防火墙不存在，则安装firewalld
if [ ! -f /usr/sbin/ufw ];then
	apt install -y firewalld
	systemctl enable firewalld
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

	# fix:debian10 firewalld faq
	# https://kawsing.gitbook.io/opensystem/andoid-shou-ji/untitled/fang-huo-qiang#debian-10-firewalld-0.6.3-error-commandfailed-usrsbinip6tablesrestorewn-failed-ip6tablesrestore-v1.8
	sed -i 's#IndividualCalls=no#IndividualCalls=yes#g' /etc/firewalld/firewalld.conf

	# 重启防火墙
	firewall-cmd --reload
fi

# 安装时不开启防火墙
systemctl stop firewalld

# fix zlib1g-dev fail
echo -e "\e[0;32mfix zlib1g-dev install question start\e[0m"
Install_TmpFile=/tmp/debian-fix-zlib1g-dev.txt
apt install -y zlib1g-dev > ${Install_TmpFile}
if [ "$?" != "0" ];then
	ZLIB1G_BASE_VER=$(cat ${Install_TmpFile} | grep zlib1g | awk -F "=" '{print $2}' | awk -F ")" '{print $1}')
	ZLIB1G_BASE_VER=`echo ${ZLIB1G_BASE_VER} | sed "s/^[ \s]\{1,\}//g;s/[ \s]\{1,\}$//g"`
	# echo "1${ZLIB1G_BASE_VER}1"
	echo -e "\e[1;31mapt install zlib1g=${ZLIB1G_BASE_VER} zlib1g-dev\e[0m"
	echo "Y" | apt install zlib1g=${ZLIB1G_BASE_VER}  zlib1g-dev
fi
rm -rf ${Install_TmpFile}
echo -e "\e[0;32mfix zlib1g-dev install question end\e[0m"


#fix libunwind-dev fail
echo -e "\e[0;32mfix libunwind-dev install question start\e[0m"
Install_TmpFile=/tmp/debian-fix-libunwind-dev.txt
apt install -y libunwind-dev > ${Install_TmpFile}
if [ "$?" != "0" ];then
	liblzma5_BASE_VER=$(cat ${Install_TmpFile} | grep liblzma-dev | awk -F "=" '{print $2}' | awk -F ")" '{print $1}')
	liblzma5_BASE_VER=`echo ${liblzma5_BASE_VER} | sed "s/^[ \s]\{1,\}//g;s/[ \s]\{1,\}$//g"`
	echo -e "\e[1;31mapt install liblzma5=${liblzma5_BASE_VER} libunwind-dev\e[0m"
	echo "Y" | apt install liblzma5=${liblzma5_BASE_VER} libunwind-dev
fi
rm -rf ${Install_TmpFile}
echo -e "\e[0;32mfix libunwind-dev install question end\e[0m"


apt install -y libvpx-dev 
apt install -y libxpm-dev
apt install -y libwebp-dev
apt install -y libfreetype6-dev

sudo localedef -i en_US -f UTF-8 en_US.UTF-8

# debian 版本
VERSION_ID=`cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F "\"" '{print $2}'`
if [ "$VERSION_ID" == "9" ];then
	sed "s/flask==2.0.3/flask==1.1.1/g" -i /www/server/jh-panel/requirements.txt
	sed "s/cryptography==3.3.2/cryptography==2.5/g" -i /www/server/jh-panel/requirements.txt
	sed "s/configparser==5.2.0/configparser==4.0.2/g" -i /www/server/jh-panel/requirements.txt
	sed "s/flask-socketio==5.2.0/flask-socketio==4.2.0/g" -i /www/server/jh-panel/requirements.txt
	sed "s/python-engineio==4.3.2/python-engineio==3.9.0/g" -i /www/server/jh-panel/requirements.txt
fi

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

# 安装pip3
if [ ! -f /usr/local/bin/pip3 ];then
  python3 -m pip install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
fi
# pip 设置清华源(cn only)
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装python依赖
cd /www/server/jh-panel/scripts/install && bash lib.sh
chmod 755 /www/server/jh-panel/data

# 安装后文件会被清空(cn only)
mkdir -p /www/server/jh-panel/data
echo "True" > /www/server/jh-panel/data/net_env_cn.pl
