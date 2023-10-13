#!/bin/bash
set -e

# 下载并执行脚本的函数
download_and_run_bash() {
    local script_name=$1
    wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
    bash /tmp/vm_${script_name} ${@:2}
}

download_and_run_node() {
    local script_name=$1
    wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
    node /tmp/vm_${script_name} ${@:2}
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
    echo "请选择备份恢复工具:"
    echo "1. MySQL数据库批量导出（导出指定数据库到文件）"
    echo "2. MySQL数据库批量导入（导入文件中的数据库）"
    echo "3. 使用mydumper批量导出MySQL数据库"
    echo "4. 使用myloader批量导入MySQL数据库"
    echo "========================================================"
}

# 显示菜单
show_menu

# 读取用户的选择
read -p "请输入选项数字（默认1）: " choice
choice=${choice:-"1"}

if [ -e "/www/server/nodejs/fnm" ];then
  export PATH="/www/server/nodejs/fnm:$PATH"
  eval "$(fnm env --use-on-cd --shell bash)"
fi
if ! command -v npm > /dev/null;then
  echo "No npm"
  exit 1
fi

wget -nv -O /tmp/package.json ${URLBase}/package.json
pushd /tmp/ > /dev/null
npm i
popd > /dev/null

# 根据用户的选择执行对应的操作
case $choice in
1)
    download_and_run_node backup__dump_mysql_database_all.js
    ;;
2)
    download_and_run_node backup__import_mysql_database_all.js
    ;;
3)
    download_and_run_bash backup__dump_mysql_database_mydumper.sh
    ;;
4)
    download_and_run_bash backup__import_mysql_database_myloader.sh
    ;;
esac

