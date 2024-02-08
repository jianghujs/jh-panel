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
    echo "请选择切换工具:"
    echo "1. 获取服务器下线脚本（停止xtrabackup增量备份、xtrabackup、mysqldump定时任务、停止邮件通知）"
    echo "2. 获取服务器上线脚本（执行xtrabackup增量恢复、更新wwwroot目录、启动xtrabackup增量备份、xtrabackup、mysqldump定时任务、开启邮件通知）"
    echo "3. Mysql主从切换"
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
    download_and_run switch__generate_offline.sh
    ;;
2)
    download_and_run switch__generate_online.sh
    ;;
3)
    download_and_run_node switch__master_slave.js
    ;;
esac

