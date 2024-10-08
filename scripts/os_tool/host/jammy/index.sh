#!/bin/bash

set -e
# 检查/usr/bin/dialog是否存在
if ! [ -x "/usr/bin/dialog" ]; then
    echo "/usr/bin/dialog不存在，正在尝试自动安装..."
    sudo apt-get update
    sudo apt-get install dialog -y
    hash -r
    if ! [ -x "/usr/bin/dialog" ]; then
        echo "安装dialog失败，请手动安装后再运行脚本。"
        exit 1
    fi
fi

# 为当前目录及其子目录下的所有.sh文件添加执行权限
for file in $(find . -name "*.sh"); do
    chmod +x "$file"
done

# 检查是否以root用户运行
if [ "$EUID" -eq 0 ]; then
    if [ -z "$SUDO_COMMAND" ]; then
        echo "请不要使用root账户来执行此脚本，以防配置不生效。执行此脚本需要添加sudo。"
        exit
    fi
else
    echo "请使用'sudo'来执行此脚本。"
    exit
fi

show_menu() {
    echo "==================host jammy os-tools=================="
    echo "请选择一个操作:"
    echo "1. 初始化环境"
    echo "2. VirtualBox虚拟机自启动"
    echo "3. Virtualbox虚拟机定时快照"
    echo "4. Virtualbox虚拟机磁盘扩容"
    echo "======================================================="
}

# 显示菜单
show_menu

# 读取用户的选择
read -p "请输入选项数字: " choice

# 下载并执行脚本的函数
download_and_run() {
    local script_name=$1
    echo ">>>>>>>>>>>>>>>>>>> Running ${script_name}"
    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      bash $SCRIPT_BASE/${script_name} ${@:2}
    else
      wget -nv -O /tmp/host_${script_name} ${URLBase}/${script_name}
      bash /tmp/host_${script_name} ${@:2}
    fi    
    echo -e "<<<<<<<<<<<<<<<<<<< Run ${script_name} success✔!\n"
}

# 根据用户的选择执行对应的操作
case $choice in
    1)
        download_and_run index__init.sh
        ;;
    2)
        download_and_run index__virtualbox_vm_auto_start.sh
        ;;
    3)
        download_and_run index__virtualbox_vm_auto_snapshot.sh
        ;;
    4)
        download_and_run index__virtualbox_vm_diskresize.sh
        ;;
esac

