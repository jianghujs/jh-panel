#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
# LANG=en_US.UTF-8
is64bit=`getconf LONG_BIT`

if [ -z "$OS_TOOL_ROOT" ]; then
  OS_TOOL_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
fi
export OS_TOOL_ROOT

if [ -v RUN_DIR ]; then
  cd $RUN_DIR
fi

osType="$1"
netEnvCn="$2"
usePanelScript="$3"

# 默认获取面板配置的源
if [ -z "$netEnvCn" ]; then
  if [ -f "/www/server/jh-panel/data/net_env_cn.pl" ]; then
    netEnvCn="cn"
  fi
fi

echo "netEnvCn: ${netEnvCn}"
_os=`uname`
echo "use system: ${_os}"

echo "usePanelScript：${usePanelScript}"

if [ -z "$usePanelScript" ]; then
  if [ -f "${OS_TOOL_ROOT}/tools.sh" ]; then
    usePanelScript="true"
  fi
fi

is_pve="false"
if [ -d "/etc/pve" ] || command -v pveversion >/dev/null 2>&1; then
  is_pve="true"
fi

download_file() {
  local url="$1"
  local dest="$2"
  if command -v wget >/dev/null 2>&1; then
    wget -nv -O "$dest" "$url"
    return $?
  fi
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "$dest" "$url"
    return $?
  fi
  echo "未检测到 wget 或 curl，无法下载文件。"
  return 1
}

update_os_tool() {
  local dest_dir="/www/server/os_tool"
  local tmp_dir archive_url archive_file src_dir
  if [ "$netEnvCn" == "cn" ]; then
    archive_url="https://gitee.com/jianghujs/jh-panel/repository/archive/master.tar.gz"
  else
    archive_url="https://github.com/jianghujs/jh-panel/archive/refs/heads/master.tar.gz"
  fi
  tmp_dir=$(mktemp -d)
  archive_file="${tmp_dir}/jh-panel.tar.gz"
  trap 'rm -rf "$tmp_dir"' EXIT

  echo "开始更新，下载地址: ${archive_url}"
  if ! download_file "$archive_url" "$archive_file"; then
    echo "下载失败，请检查网络或镜像设置。"
    return 1
  fi

  if ! tar -xzf "$archive_file" -C "$tmp_dir"; then
    echo "解压失败，请检查压缩包内容。"
    return 1
  fi

  src_dir=$(find "$tmp_dir" -maxdepth 2 -type d -name "jh-panel*" | head -n 1)
  if [ -z "$src_dir" ] || [ ! -d "$src_dir/scripts/os_tool" ]; then
    echo "未找到 scripts/os_tool 目录，无法更新。"
    return 1
  fi

  mkdir -p "$dest_dir"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$src_dir/scripts/os_tool/" "$dest_dir/"
  else
    cp -a "$src_dir/scripts/os_tool/." "$dest_dir/"
  fi
  echo "更新完成: ${dest_dir}"
}

select_os_type() {
  if [ "$is_pve" == "true" ]; then
    echo "==================os-tool 菜单=================="
    echo "请选择一个操作:"
    echo "1. pve 工具"
    echo "2. 更新本地脚本"
    echo "0. 退出"
    echo "================================================"
    read -p "请输入选项数字（默认1）: " menu_choice
    menu_choice=${menu_choice:-"1"}
    case "$menu_choice" in
      1) osType="pve" ;;
      2) update_os_tool; exit $? ;;
      0) exit 0 ;;
      *) echo "无效选项"; exit 1 ;;
    esac
  else
    echo "==================os-tool 菜单=================="
    echo "请选择一个操作:"
    echo "1. vm 工具"
    echo "2. 更新本地脚本"
    echo "0. 退出"
    echo "================================================"
    read -p "请输入选项数字（默认1）: " menu_choice
    menu_choice=${menu_choice:-"1"}
    case "$menu_choice" in
      1) osType="vm" ;;
      2) update_os_tool; exit $? ;;
      0) exit 0 ;;
      *) echo "无效选项"; exit 1 ;;
    esac
  fi
}

if [ "$osType" == "menu" ]; then
  select_os_type
fi

if [ -z "$osType" ]; then
  if [ "$is_pve" == "true" ]; then
    osType="pve"
  else
    osType="vm"
  fi
fi

if [ "$osType" == "update" ]; then
  update_os_tool
  exit $?
fi

if grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release; then
	OSNAME='debian'
elif grep -Eqi "Ubuntu" /etc/issue || grep -Eq "Ubuntu" /etc/*-release; then
	OSNAME='ubuntu'
elif grep -Eqi "CentOS" /etc/issue || grep -Eq "CentOS" /etc/*-release; then
	OSNAME='centos'
else
	OSNAME='unknow'
fi

echo "use system version: ${OSNAME}"

# 获取系统codename
codename_line=$(lsb_release -a | grep Codename)
codename_value=$(echo $codename_line | cut -d ':' -f2)
CODENAME=$(echo $codename_value | xargs)
echo "Codename: ${CODENAME}"

TOOL_DIR=$CODENAME
# 如果CODENAME为focal或bullseye，则tool_dir为default
if [ $CODENAME == "bullseye" ] || [ $CODENAME == "focal" ]; then
  TOOL_DIR="default"
fi

export TOOL_DIR

if [ "$usePanelScript" == "true" ]; then 
  export USE_PANEL_SCRIPT=true
  export SCRIPT_BASE=${OS_TOOL_ROOT}/${osType}/${TOOL_DIR}
  bash $SCRIPT_BASE/index.sh
else
  toolURLBase="https://raw.githubusercontent.com/jianghujs/jh-panel/master/scripts/os_tool"
  if [ "$netEnvCn" == "cn" ]; then
    toolURLBase="https://gitee.com/jianghujs/jh-panel/raw/master/scripts/os_tool"
  fi

  URLBase="${toolURLBase}/${osType}/${TOOL_DIR}"
  echo "URLBase: ${URLBase}"
  export URLBase

  if ! wget -q --spider "${URLBase}/index.sh"; then
    echo "暂不支持在${OSNAME}执行${osType}脚本"
    exit
  fi

  echo "downloading ${URLBase}/index.sh to /tmp/${osType}_index.sh"

  wget -nv -O /tmp/${osType}_index.sh ${URLBase}/index.sh && bash /tmp/${osType}_index.sh

fi
