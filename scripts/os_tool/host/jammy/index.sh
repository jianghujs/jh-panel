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
    echo "2. 配置VirtualBox虚拟机自启动"
    echo "3. 配置virtualbox虚拟机定时快照"
    echo "======================================================="
}

# 显示菜单
show_menu

# 读取用户的选择
read -p "请输入选项数字: " choice

# 下载并执行脚本的函数
download_and_run() {
    local script_name=$1
    wget -q -O /tmp/host_${script_name} ${URLBase}/${script_name}
    echo ">>>>>>>>>>>>>>>>>>> Running ${script_name}"
    bash /tmp/host_${script_name} ${@:2}
    echo -e "<<<<<<<<<<<<<<<<<<< Run ${script_name} success✔!\n"
}

# 根据用户的选择执行对应的操作
case $choice in
    1)
        echo "初始化环境"
        
        # 定义一个关联数组来存储你的脚本
        declare -A scripts
        scripts=(
        ["切换apt源"]="switch_apt_sources.sh"
        ["分配固定IP"]="set_static_ip_multi_network.sh"
        ["禁用睡眠"]="nosleep.sh"
        ["安装并配置xrdp自启动"]="install_xrdp.sh"
        ["安装并配置rustdesk自启动"]="install_rustdesk.sh"
        ["安装并配置VirtualBox自启动"]="install_virtualbox.sh"
        )

        # 创建一个数组，用于存储键的顺序
        keys=("切换apt源" "分配固定IP" "禁用睡眠" "安装并配置xrdp自启动" "安装并配置rustdesk自启动" "安装并配置VirtualBox自启动")

        # 创建一个数组，用于dialog的checklist选项
        script_options=()
        for key in "${keys[@]}"; do
            script_options+=("$key" "" on)
        done

        cmd=(/usr/bin/dialog --separate-output --checklist "请选择要运行的脚本:" 22 76 16)
        choices=$("${cmd[@]}" "${script_options[@]}" 2>&1 >/dev/tty)

        # 根据用户的选择以正确的顺序运行对应的脚本
        for key in "${keys[@]}"; do
            for choice in $choices; do
                if [ "$choice" == "$key" ]; then
                    script_file=${scripts[$choice]}
                    download_and_run ${script_file}
                    break
                fi
            done
        done
        
        # 提示用户是否需要重启
        read -p "部分设置需要重启系统才能生效，是否重启？[Y/n]（默认为Y）： " response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY]|"")$ ]]; then
            sudo reboot
        fi
        ;;
    2)
        download_and_run virtualbox_vm_auto_start.sh
        ;;
    3)
        download_and_run virtualbox_vm_auto_snapshot.sh
        ;;
esac

