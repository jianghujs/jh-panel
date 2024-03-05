#!/bin/bash
set -e
# 下载并执行脚本的函数
download_and_run() {
    local script_name=$1
    echo ">>>>>>>>>>>>>>>>>>> Running ${script_name}"
    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      bash $SCRIPT_BASE/${script_name} ${@:2}
    else
      wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
      bash /tmp/vm_${script_name} ${@:2}
    fi    
    echo -e "<<<<<<<<<<<<<<<<<<< Run ${script_name} success✔!\n"
}

if [ !"$USE_PANEL_SCRIPT" == "true" ]; then 
  download_and_run index__switch_apt_sources.sh 4
fi

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
    echo "请选择一个操作:"
    echo "1. 初始化环境"
    echo "2. 生成SSH密钥"
    echo "3. 服务器迁移"
    echo "4. 服务器修复"
    echo "5. 服务器扩容"
    echo "6. 服务器整理"
    echo "7. 服务器备份恢复"
    echo "8. 服务器状态检查"
    echo "9. 服务器切换"
    echo "========================================================"
}

# 显示菜单
show_menu

# 读取用户的选择
read -p "请输入选项数字: " choice


# 根据用户的选择执行对应的操作
case $choice in
1)
    download_and_run index__init.sh
    ;;
2)
    download_and_run index__ssh_keygen.sh
    ;;
3)
    download_and_run index__migrate.sh
    ;;
4)
    download_and_run index__repair.sh
    ;;
5)
    download_and_run index__resize.sh
    ;;
6)
    download_and_run index__arrange.sh
    ;;
7)
    download_and_run index__backup.sh
    ;;
8)
    download_and_run index__monitor.sh
    ;;
9)
    download_and_run index__switch.sh
    ;;
esac

