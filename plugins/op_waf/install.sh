#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin:/opt/homebrew/bin
export PATH

# cd /www/server/mdserver-web/plugins/op_waf && bash install.sh install 0.4.1

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

install_tmp=${rootPath}/tmp/mw_install.pl

action=$1
version=$2
sys_os=`uname`

if [ -f ${rootPath}/bin/activate ];then
	source ${rootPath}/bin/activate
fi

if [ "$sys_os" == "Darwin" ];then
	BAK='_bak'
else
	BAK=''
fi

Fail(){
	echo "op_waf install error: $1"
	echo "install error: $1" > $install_tmp
	exit 1
}

Download_File(){
	url=$1
	output=$2
	mkdir -p $(dirname "$output")
	rm -f "$output"
	if command -v wget >/dev/null 2>&1; then
		wget --no-check-certificate --timeout=30 --tries=2 -O "$output" "$url"
	else
		curl -L --fail --connect-timeout 10 --max-time 60 -o "$output" "$url"
	fi
}

Check_Zip(){
	zip_file=$1
	[ -s "$zip_file" ] && unzip -tq "$zip_file" >/dev/null 2>&1
}

Prepare_Lsqlite3(){
	lsqlite3_zip=$serverPath/source/op_waf/lsqlite3_fsl09y.zip
	lsqlite3_dir=$serverPath/source/op_waf/lsqlite3_fsl09y
	lsqlite3_tmp=$serverPath/source/op_waf/lsqlite3_tmp
	lsqlite3_urls="https://github.com/LuaDist/lsqlite3/archive/refs/heads/master.zip http://lua.sqlite.org/index.cgi/zip/lsqlite3_fsl09y.zip?uuid=fsl_9y"

	if [ -d "$lsqlite3_dir" ];then
		return 0
	fi

	if ! Check_Zip "$lsqlite3_zip";then
		rm -f "$lsqlite3_zip"
		for download_url in $lsqlite3_urls; do
			echo "download lsqlite3: $download_url"
			if Download_File "$download_url" "$lsqlite3_zip" && Check_Zip "$lsqlite3_zip";then
				break
			fi
			rm -f "$lsqlite3_zip"
		done
	fi

	Check_Zip "$lsqlite3_zip" || Fail "lsqlite3 源码包下载失败或不是有效 zip，请检查网络或手动放置有效文件: $lsqlite3_zip"

	rm -rf "$lsqlite3_tmp"
	mkdir -p "$lsqlite3_tmp"
	unzip -q "$lsqlite3_zip" -d "$lsqlite3_tmp" || Fail "lsqlite3 源码包解压失败: $lsqlite3_zip"

	if [ -d "$lsqlite3_tmp/lsqlite3_fsl09y" ];then
		mv "$lsqlite3_tmp/lsqlite3_fsl09y" "$lsqlite3_dir"
	elif [ -d "$lsqlite3_tmp/lsqlite3-master" ];then
		mv "$lsqlite3_tmp/lsqlite3-master" "$lsqlite3_dir"
	else
		rm -rf "$lsqlite3_tmp"
		Fail "lsqlite3 源码包目录结构异常"
	fi
	rm -rf "$lsqlite3_tmp"

	if [ ! -f "$lsqlite3_dir/lsqlite3-0.9.5-1.rockspec" ];then
		[ -f "$lsqlite3_dir/Makefile" ] && mv "$lsqlite3_dir/Makefile" "$lsqlite3_dir/Makefile.origin"
		cat > "$lsqlite3_dir/Makefile" <<'EOF'
# Makefile for lsqlite3 library for Lua

LIBNAME= lsqlite3

LUAEXE= lua

ROCKSPEC= $(shell find . -name $(LIBNAME)-*-*.rockspec)

all: install

install:
	luarocks make $(ROCKSPEC)

test:
	$(LUAEXE) test/test.lua
	$(LUAEXE) test/tests-sqlite3.lua lsqlite3
	$(LUAEXE) test/tests-sqlite3.lua lsqlite3complete

.PHONY: all test install
EOF
		cat > "$lsqlite3_dir/lsqlite3-0.9.5-1.rockspec" <<'EOF'
package = "lsqlite3"
version = "0.9.5-1"
source = {
    url = "https://github.com/LuaDist/lsqlite3/archive/refs/heads/master.zip",
    file = "lsqlite3_fsl09y.zip"
}
description = {
    summary = "A binding for Lua to the SQLite3 database library",
    detailed = [[
        lsqlite3 is a thin wrapper around the public domain SQLite3 database engine.
    ]],
    license = "MIT",
    homepage = "http://lua.sqlite.org/"
}
dependencies = {
    "lua >= 5.1, < 5.5"
}
external_dependencies = {
    SQLITE = {
        header = "sqlite3.h"
    }
}
build = {
    type = "builtin",
    modules = {
        lsqlite3 = {
            sources = { "lsqlite3.c" },
            defines = {'LSQLITE_VERSION="0.9.5"'},
            libraries = { "sqlite3" },
            incdirs = { "$(SQLITE_INCDIR)" },
            libdirs = { "$(SQLITE_LIBDIR)" }
        },
    }
}
EOF
	fi
}


Install_App(){
	
	echo '正在安装脚本文件...' > $install_tmp
	mkdir -p $serverPath/source/op_waf
	mkdir -p $serverPath/op_waf

	# luarocks
	if [ ! -f $serverPath/source/op_waf/luarocks-3.5.0.tar.gz ];then
		Download_File http://luarocks.org/releases/luarocks-3.5.0.tar.gz $serverPath/source/op_waf/luarocks-3.5.0.tar.gz || Fail "luarocks 下载失败"
	fi
	
	# which luarocks
	if [ ! -d $serverPath/op_waf/luarocks ];then
		cd $serverPath/source/op_waf && tar xvf luarocks-3.5.0.tar.gz || Fail "luarocks 解压失败"
		# cd luarocks-3.9.1 && ./configure && make bootstrap

		cd luarocks-3.5.0 && ./configure --prefix=$serverPath/op_waf/luarocks \
		--with-lua-include=$serverPath/openresty/luajit/include/luajit-2.1 \
		--with-lua-bin=$serverPath/openresty/luajit/bin || Fail "luarocks configure 失败"
		make -I${serverPath}/openresty/luajit/bin || Fail "luarocks 编译失败"
		make install || Fail "luarocks 安装失败"
	fi

	Prepare_Lsqlite3

	PATH=${serverPath}/openresty/luajit:${serverPath}/openresty/luajit/include/luajit-2.1:$PATH
	export PATH=$PATH:$serverPath/op_waf/luarocks/bin

	if [ ! -f $serverPath/op_waf/waf/conf/lsqlite3.so ];then
		if [ "${sys_os}" == "Darwin" ];then
			cd $serverPath/source/op_waf/lsqlite3_fsl09y || Fail "lsqlite3 源码目录不存在"
			find_cfg=`cat Makefile | grep 'SQLITE_DIR'`
			if [ "$find_cfg" == "" ];then
				LIB_SQLITE_DIR=`brew info sqlite | grep /usr/local/Cellar/sqlite | cut -d \  -f 1 | awk 'END {print}'`
				echo $LIB_SQLITE_DIR
				sed -i $BAK "s#\$(ROCKSPEC)#\$(ROCKSPEC) SQLITE_DIR=${LIB_SQLITE_DIR}#g"  Makefile
			fi
			make || Fail "lsqlite3 编译失败"
		else
			cd $serverPath/source/op_waf/lsqlite3_fsl09y && make || Fail "lsqlite3 编译失败"
		fi
	fi

	# copy to code path
	DEFAULT_DIR=$serverPath/op_waf/luarocks/lib/lua/5.1
	if [ -f ${DEFAULT_DIR}/lsqlite3.so ];then
		mkdir -p $serverPath/op_waf/waf/conf
		cp -rf ${DEFAULT_DIR}/lsqlite3.so $serverPath/op_waf/waf/conf/lsqlite3.so
	else
		Fail "lsqlite3.so 未生成: ${DEFAULT_DIR}/lsqlite3.so"
	fi

	cn=$(curl -fsSL -m 10 http://ipinfo.io/json | grep "\"country\": \"CN\"")
	HTTP_PREFIX="https://"
	if [ ! -z "$cn" ];then
	    HTTP_PREFIX="https://mirror.ghproxy.com/"
	fi

	# download GeoLite Data
	GeoLite2_TAG=`curl -sL "https://api.github.com/repos/P3TERX/GeoLite.mmdb/releases/latest" | grep '"tag_name":' | cut -d'"' -f4`
	#if [ ! -f $serverPath/op_waf/GeoLite2-City.mmdb ];then
	wget --no-check-certificate -O $serverPath/op_waf/GeoLite2-City.mmdb ${HTTP_PREFIX}github.com/P3TERX/GeoLite.mmdb/releases/download/${GeoLite2_TAG}/GeoLite2-City.mmdb
	#fi

	#if [ ! -f $serverPath/op_waf/GeoLite2-Country.mmdb ];then
	wget --no-check-certificate -O $serverPath/op_waf/GeoLite2-Country.mmdb ${HTTP_PREFIX}github.com/P3TERX/GeoLite.mmdb/releases/download/${GeoLite2_TAG}/GeoLite2-Country.mmdb
	#fi

	libmaxminddb_ver='1.7.1'
	if [ ! -f $serverPath/op_waf/waf/mmdb/lib/libmaxminddb.a ] && [ ! -f $serverPath/op_waf/waf/mmdb/lib/libmaxminddb.so ];then
		libmaxminddb_local_path=$serverPath/source/op_waf/libmaxminddb-${libmaxminddb_ver}.tar.gz
		libmaxminddb_url_path=${HTTP_PREFIX}github.com/maxmind/libmaxminddb/releases/download/${libmaxminddb_ver}/libmaxminddb-${libmaxminddb_ver}.tar.gz
		if [ ! -f ${libmaxminddb_local_path} ]; then
			wget --no-check-certificate -O ${libmaxminddb_local_path} ${libmaxminddb_url_path}
		fi

		cd $serverPath/source/op_waf && tar -zxvf ${libmaxminddb_local_path} && \
		cd $serverPath/source/op_waf/libmaxminddb-${libmaxminddb_ver} && \
		./configure --prefix=$serverPath/op_waf/waf/mmdb && make && make install
	fi

	echo "${version}" > $serverPath/op_waf/version.pl
	echo 'install ok' > $install_tmp

	cd ${rootPath} && python3 ${rootPath}/plugins/op_waf/index.py start
	echo "cd ${rootPath} && python3 ${rootPath}/plugins/op_waf/index.py start"
	sleep 2
	cd ${rootPath} && python3 ${rootPath}/plugins/op_waf/index.py reload
}

Uninstall_App(){

	cd ${rootPath} && python3 ${rootPath}/plugins/op_waf/index.py stop
	if [ "$?" == "0" ];then
		rm -rf $serverPath/op_waf
	fi
}


action=$1
if [ "${1}" == 'install' ];then
	Install_App
else
	Uninstall_App
fi
