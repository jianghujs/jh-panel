#!/bin/bash
set -e

# 下载并执行脚本的函数
download_and_run_bash() {
    local script_name=$1
    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      bash $SCRIPT_BASE/${script_name} ${@:2}
    else
      wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
      bash /tmp/vm_${script_name} ${@:2}
    fi    
}

download_and_run_node() {
    local script_name=$1
    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      pushd $SCRIPT_BASE > /dev/null
      source /root/.bashrc
      npm i
      node ${script_name} ${@:2}
      popd > /dev/null
    else
      wget -nv -O /tmp/package.json ${URLBase}/package.json
      pushd /tmp/ > /dev/null
      source /root/.bashrc
      npm i
      popd > /dev/null
      
      wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
      node /tmp/vm_${script_name} ${@:2}
    fi    
}

# 检查/usr/bin/dialog是否存在
if ! [ -x "/usr/bin/dialog" ]; then
    echo "/usr/bin/dialog不存在，正在尝试自动安装..."
    apt-get update
    apt-get install dialog -y
    hash -r
    if ! [ -x "/usr/bin/dialog" ]; then
        echo "安装dialog失败，请手动安装后再运行脚本。"
        exit 1
    fi
fi

# # 为当前目录及其子目录下的所有.sh文件添加执行权限
# for file in $(find . -name "*.sh"); do
#     chmod +x "$file"
# done

show_menu() {
    echo "==================vm os-tools=================="
    echo "请选择备份恢复工具:"
    echo "1. MySQL数据库备份-mysqldump版（使用mysqldump批量导出数据库）"
    echo "2. MySQL数据库恢复-mysqldump版（批量恢复使用mysqldump导出的数据库文件，视图部分逐条执行）"
    echo "3. MySQL数据库备份-mydumper版（使用mydumper批量导出数据库）"
    echo "4. MySQL数据库恢复-mydumper版（恢复使用myloader批量导出的数据库文件）"
    echo "5. 网站配置恢复（从指定的备份中恢复网站配置，包括网站列表、网站配置、letsencrypt订单）"
    echo "6. 插件配置恢复（从指定的备份中恢复插件数据，包括jianghujs、docker插件）"
    echo "提示：mysqldump版适用于导出数据库结构合并到其他服务器，mydumper版适用于大数据量的快速备份恢复。"
    echo "========================================================"
}

# 显示菜单
show_menu

# 读取用户的选择
read -p "请输入选项数字（默认1）: " choice
choice=${choice:-"1"}

if [ -e "/www/server/nodejs/fnm" ];then
  export PATH="/www/server/nodejs/fnm:$PATH"
  eval "$(fnm env --use-on-cd --shell bash)"
fi
if ! command -v npm > /dev/null;then
  echo "No npm"
  exit 1
fi

# 根据用户的选择执行对应的操作
case $choice in
1)
    download_and_run_node backup__dump_mysql_database_all.js
    ;;
2)
    download_and_run_node backup__import_mysql_database_all.js
    ;;
3)
    download_and_run_bash backup__dump_mysql_database_mydumper.sh
    ;;
4)
    download_and_run_bash backup__import_mysql_database_myloader.sh
    ;;
5)
    download_and_run_bash backup__restore_site_setting.sh
    ;;
6)
    download_and_run_bash backup__restore_plugin_setting.sh
    ;;
esac

