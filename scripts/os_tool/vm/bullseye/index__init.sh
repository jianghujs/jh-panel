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
    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      bash $SCRIPT_BASE/${script_name} ${@:2}
    else
      wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
      bash /tmp/vm_${script_name} ${@:2}
    fi    
}

echo "初始化环境"

# 定义一个关联数组来存储你的脚本
declare -A scripts
scripts=(
["安装中文包"]="init__install_cn_language.sh"
["分配固定IP"]="init__set_static_ip.sh"
["配置SSH权限"]="init__ssh_root_login.sh"
["安装江湖面板"]="init__install_jhpanel.sh"
)

# 定义一个数组来存储脚本的顺序
script_order=("安装中文包" "分配固定IP" "配置SSH权限" "安装江湖面板")

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
            download_and_run ${script_file}
        fi
    done
done
