#!/bin/bash
set -e

# 下载并执行脚本的函数
download_and_run() {
    local script_name=$1
    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      bash $SCRIPT_BASE/${script_name} ${@:2}
    else
      wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
      bash /tmp/vm_${script_name} ${@:2}
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
    echo "==================vm bullseye os-tools=================="
    echo "请选择整理工具:"
    echo "1. 整理项目目录-第①步（生成复制wwwroot下的项目upload、multipartTmp目录到wwwstorage脚本文件）"
    echo "2. 整理项目目录-第②步（生成链接wwwroot下的项目upload、multipartTmp目录到wwwstorage脚本文件）"
    echo "3. 整理项目目录（生成移动并链接wwwroot下的项目upload、multipartTmp目录到wwwstorage脚本文件）"
    echo "========================================================"
}

# 显示菜单
show_menu

# 读取用户的选择
read -p "请输入选项数字（默认1）: " choice
choice=${choice:-"1"}

default_project_dir="/www/wwwroot/"
default_storage_dir="/www/wwwstorage/"

read -p "输入项目所在目录（默认为：${default_project_dir}）: " project_dir
project_dir=${project_dir:-${default_project_dir}}
export PROJECT_DIR=$project_dir

read -p "输入项目数据存放目录（默认为：${default_storage_dir}）: " storage_dir
storage_dir=${storage_dir:-${default_storage_dir}}
export STORAGE_DIR=$storage_dir


# 根据用户的选择执行对应的操作
case $choice in
1)
    download_and_run arrange__generate_copy_dirs_to_wwwstorage.sh
    ;;
2)
    download_and_run arrange__generate_link_dirs_to_wwwstorage.sh
    ;;
3)
    download_and_run arrange__generate_move_and_link_upload_to_wwwstorage.sh
    ;;
esac

