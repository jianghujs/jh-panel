#!/bin/bash

set -e
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

# 为当前目录及其子目录下的所有.sh文件添加执行权限
for file in $(find . -name "*.sh"); do
    chmod +x "$file"
done

show_menu() {
    echo "请选择一个操作:"
    echo "1. 初始化环境"
}

# 显示菜单
show_menu

# 读取用户的选择
read -p "请输入选项数字: " choice

# 根据用户的选择执行对应的操作
case $choice in
1)
    echo "初始化环境"
    
    # 定义一个关联数组来存储你的脚本
    declare -A scripts
    scripts=(
    ["分配固定IP"]="set_static_ip.sh"
    ["配置SSH权限"]="ssh_root_login.sh"
    ["安装江湖面板"]="install_jhpanel.sh"
    )

    # 定义一个数组来存储脚本的顺序
    script_order=("分配固定IP" "配置SSH权限" "安装江湖面板")

    # 创建一个数组，用于dialog的checklist选项
    script_options=()
    for key in "${script_order[@]}"; do
        script_options+=("$key" "" on)
    done

    cmd=(dialog --separate-output --checklist "请选择要运行的脚本:" 22 76 16)
    choices=$("${cmd[@]}" "${script_options[@]}" 2>&1 >/dev/tty)

    # 根据用户的选择运行对应的脚本
    for key in "${script_order[@]}"; do
        for choice in $choices; do
            if [[ $key == $choice ]]; then
                script_file=${scripts[$choice]}
                echo ">>>>>>>>>>>>>>>>>>> Running $script_file"
                echo $URLBase+$script_file
                bash $URLBase+$script_file
                echo -e "<<<<<<<<<<<<<<<<<<< Run $script_file success✔!\n"
            fi
        done
    done
    ;;
esac

