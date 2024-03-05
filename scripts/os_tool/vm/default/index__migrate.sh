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
    echo "==================vm os-tools=================="
    echo "请选择迁移模式:"
    echo "1. 生成迁移包（全数据打包）"
    echo "2. 上线同步（数据库恢复文件+项目文件rsync同步）"
    echo "========================================================"
}

# 显示菜单
show_menu

# 读取用户的选择
read -p "请输入选项数字（默认1）: " choice
choice=${choice:-"1"}

# 获取迁移临时文件存放目录
read -p "请输入迁移临时文件存放目录（默认/www/migrate/）: " dir
dir=${dir:-/www/migrate/}
export MIGRATE_DIR=$dir
# 如果目录不存在，则创建它，如果目录存在，则清空目录
if [ -d "$dir" ]; then
    read -p "目录已存在，是否清空目录？（默认y）[y/n] " yn
    yn=${yn:-y}
    case $yn in
        [Yy]* ) rm -rf $dir/*;;
        [Nn]* ) echo "已跳过清空目录";;
        * ) echo "请输入y或n";;
    esac
else
    mkdir -p $dir
fi

# 根据用户的选择执行对应的操作
case $choice in
1)
    download_and_run migrate__get_migrate_package.sh
    ;;
2)
    download_and_run migrate__rsync_migrate_final.sh
    ;;
esac

