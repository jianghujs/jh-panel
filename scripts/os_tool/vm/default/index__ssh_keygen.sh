#!/bin/bash
set -e

source "${OS_TOOL_ROOT:-/www/server/jh-panel/scripts/os_tool}/tools.sh"

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
    echo "请选择工具:"
    echo "1. 生成指定域名SSH密钥（用于gitea、github公钥配置）"
    echo "2. 生成服务器同步SSH密钥（用于生成服务器同步专用密钥）"
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
    download_and_run ssh_keygen__host.sh
    ;;
2)
    download_and_run ssh_keygen__standby_sync.sh
    ;;
esac
