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
    echo "请选择修复工具:"
    echo "1. 修复数据库文件（修复可读写但xtrabackup备份报错的数据表）"
    echo "2. 修复网站异常SSL订单（修复无法续签的SSL证书）"
    echo "3. 修复MySQL数据库用户（重建数据库用户和密码）"
    echo "4. 修复MySQL从库：从xtrabackup备份中恢复从库和GTID事务"
    echo "========================================================"
}

# 显示菜单
show_menu

# 读取用户的选择
read -p "请输入选项数字（默认1）: " choice
choice=${choice:-"1"}

# 根据用户的选择执行对应的操作
case $choice in
1)
    download_and_run repair__check_database.sh
    ;;
2)
    download_and_run repair__fix_no_order_lets_site.sh
    ;;
3)
    download_and_run repair__fix_mysql_apt_db_user.sh
    ;;
4)
    download_and_run repair__restore_mysql_slave_from_xtrabackup.sh
    ;;
esac
