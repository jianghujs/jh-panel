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
    echo "请选择整理工具:"
    echo "1. 整理目录-第①步（生成复制wwwroot下的项目upload、multipartTmp等目录到wwwstorage脚本文件）"
    echo "2. 整理目录-第②步（生成链接wwwroot下的项目upload、multipartTmp等目录到wwwstorage脚本文件）"
    echo "3. 整理目录（生成移动并链接wwwroot下的项目upload、multipartTmp等目录到wwwstorage脚本文件）"
    echo "4. 查找指定目录（查找并生成指定名称（如.git）目录的路径列表文件，可用于rsync、zip打包）"
    echo "5. 整理项目配置文件数据库连接信息，统一使用数据库自己的用户"
    echo "6. 清理系统crontab"
    echo "7. 将使用自定义证书的站点改为letsencrypt证书"
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
    download_and_run arrange__generate_copy_dirs_to_wwwstorage.sh
    ;;
2)
    download_and_run arrange__generate_link_dirs_to_wwwstorage.sh
    ;;
3)
    download_and_run arrange__generate_move_and_link_dirs_to_wwwstorage.sh
    ;;
4)
    download_and_run arrange__generate_find_dirs_path_file.sh
    ;;
5)
    download_and_run arrange__fix_project_config_use_database_root_user.sh
    ;;
6)
    pushd /www/server/jh-panel > /dev/null
    python3 /www/server/jh-panel/scripts/arrange.py cleanSysCrontab
    popd > /dev/null
    ;;
7)
    download_and_run arrange__change_site_ssl_to_letsencrypt.sh
    ;;
esac

