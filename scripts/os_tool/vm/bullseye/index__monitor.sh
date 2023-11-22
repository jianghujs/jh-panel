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


download_and_run_node() {
    local script_name=$1
    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      pushd $SCRIPT_BASE > /dev/null
      npm i
      node ${script_name} ${@:2}
      popd > /dev/null
    else
      wget -nv -O /tmp/package.json ${URLBase}/package.json
      pushd /tmp/ > /dev/null
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
    echo "==================vm bullseye os-tools=================="
    echo "请选择状态监测工具:"
    echo "1. 进程占用分析（打印进程占用排名到文件）"
    echo "2. 磁盘IO占用分析（打印磁盘IO占用排名到文件）"
    echo "3. 磁盘IO测试（测试磁盘读写速度）"
    echo "4. MySQL数据库Checksum分析（打印MySQL数据库所有表的cheksum值）"
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
    download_and_run monitor__export_top_rank.sh
    ;;
2)
    download_and_run monitor__export_iotop_rank.sh
    ;;
3)
    download_and_run monitor__export_io_test.sh
    ;;
4)
    download_and_run_node monitor__export_mysql_checksum.js
    ;;
esac

