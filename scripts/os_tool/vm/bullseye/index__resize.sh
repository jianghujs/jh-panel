#!/bin/bash
set -e

# 下载并执行脚本的函数
download_and_run() {
    local script_name=$1
    wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
    bash /tmp/vm_${script_name} ${@:2}
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
    echo "请选择扩容工具:"
    echo "1. 扩容步骤1（重写分区表）"
    echo "2. 扩容步骤2（启用并切换swap分区、文件系统扩大）"
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
    download_and_run resize__step1.sh
    ;;
2)
    download_and_run resize__step2.sh
    ;;
esac
