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

# 下载并执行脚本的函数
download_and_run() {
    local script_name=$1
    wget -nv -O /tmp/host_${script_name} ${URLBase}/${script_name}
    echo ">>>>>>>>>>>>>>>>>>> Running ${script_name}"
    bash /tmp/host_${script_name} ${@:2}
    echo -e "<<<<<<<<<<<<<<<<<<< Run ${script_name} success✔!\n"
}

echo "初始化环境"

# 定义一个关联数组来存储你的脚本
declare -A scripts
scripts=(
["切换apt源"]="init__switch_apt_sources.sh"
["分配固定IP"]="init__set_static_ip_multi_network.sh"
["禁用睡眠"]="init__nosleep.sh"
["安装并配置xrdp自启动"]="init__install_xrdp.sh"
["安装并配置rustdesk自启动"]="init__install_rustdesk.sh"
["安装并配置VirtualBox自启动"]="init__install_virtualbox.sh"
)

# 定义一个数组来存储脚本的顺序
script_order=("切换apt源" "分配固定IP" "禁用睡眠" "安装并配置xrdp自启动" "安装并配置rustdesk自启动" "安装并配置VirtualBox自启动")

 # 创建一个数组，用于dialog的checklist选项
script_options=()
for key in "${keys[@]}"; do
    if [ "$key" == "安装并配置rustdesk自启动" ]; then
        script_options+=("$key" "" off)
    else
        script_options+=("$key" "" on)
    fi
done

cmd=(dialog --separate-output --checklist "请选择要运行的脚本:" 22 76 16)
choices=$("${cmd[@]}" "${script_options[@]}" 2>&1 >/dev/tty)

# 根据用户的选择运行对应的脚本
for key in "${script_order[@]}"; do
    for choice in $choices; do
        if [[ $key == $choice ]]; then
            script_file=${scripts[$choice]}
            download_and_run ${script_file}
        fi
    done
done

# 提示用户是否需要重启
read -p "部分设置需要重启系统才能生效，是否重启？[Y/n]（默认为Y）： " response
if [[ "$response" =~ ^([yY][eE][sS]|[yY]|"")$ ]]; then
    sudo reboot
fi
;;
