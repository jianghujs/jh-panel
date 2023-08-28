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

# # 为当前目录及其子目录下的所有.sh文件添加执行权限
# for file in $(find . -name "*.sh"); do
#     chmod +x "$file"
# done

# 定义一个关联数组来存储你的脚本
declare -A scripts
scripts=(
["xtrabackup"]="migrate_xtrabackup.sh"
["网站"]="migrate_site.sh"
["项目文件"]="migrate_project.sh"
["插件数据-jianghujs管理器"]="migrate_plugin_data.sh"
)

# 定义一个数组来存储脚本的顺序
script_order=("xtrabackup" "网站" "项目文件" "插件数据-jianghujs管理器")

# 创建一个数组，用于dialog的checklist选项
script_options=()
for key in "${script_order[@]}"; do
    script_options+=("$key" "" on)
done

cmd=(dialog --separate-output --checklist "请勾选要迁移的数据:" 22 76 16)
choices=$("${cmd[@]}" "${script_options[@]}" 2>&1 >/dev/tty)

# 获取环境变量中的MIGRATE_DIR值
MIGRATE_DIR=${MIGRATE_DIR:-"/www/migrate/"}

# 获取当前IP地址
pushd /www/server/jh-panel > /dev/null
local_ip=$(python3 /www/server/jh-panel/tools.py getLocalIp)
popd > /dev/null
export LOCAL_IP=$local_ip

# 下载并执行脚本的函数
download_and_run() {
    local script_name=$1
    wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
    bash /tmp/vm_${script_name} ${@:2}
}

# 根据用户的选择运行对应的脚本
for key in "${script_order[@]}"; do
    for choice in $choices; do
        if [[ $key == $choice ]]; then
            script_file=${scripts[$choice]}
            download_and_run ${script_file}
            # ./$script_file
        fi
    done
done

# 生成deploy.sh文件
cat <<EOF > ${MIGRATE_DIR}/deploy.sh
#!/bin/bash
for file in "deploy_xtrabackup.sh" "deploy_site.sh" "deploy_project.sh"; do
    if [ -f "\$file" ]; then
        bash \$file
    fi
done
echo "导入迁移包完成✔!"
EOF

# 打包迁移临时文件存放目录
timestamp=$(date +%s)
pushd ${MIGRATE_DIR} > /dev/null
migrate_file=migrate_package_${local_ip}_${timestamp}.zip
zip -r ../${migrate_file} .
popd > /dev/null
pushd ${MIGRATE_DIR}/../ > /dev/null
export MIGRATE_FILE=$(pwd)/${migrate_file} 
popd > /dev/null

# 提示是否rsync同步
read -p "是否要使用rsync将备份文件同步到其他服务器?(默认n)[y/n]" sync
sync=${sync:-n}

case $sync in
  [Yy]*) 
    # ./rsync_migrate_package.sh
    download_and_run rsync_migrate_package.sh
    ;;
  [Nn]*)
    exit;;
  *) echo "请输入y或n";;
esac

echo ""
echo "===========================生成迁移包完成✅=========================="
echo "------------------------------基本信息-------------------------------"
echo "- 迁移临时文件存放目录：$MIGRATE_DIR"
echo "- 迁移包路径：$MIGRATE_FILE"
if [ $sync == "y" ]; then
echo "- 已将文件同步到以下服务器："
echo "  - 服务器IP：${RSYNC_MIGRATE_PACKAGE_REMOTE_IP}"
echo "  - 目标服务器SSH端口：${RSYNC_MIGRATE_PACKAGE_REMOTE_PORT}"
echo "  - 目标文件位置：${RSYNC_MIGRATE_PACKAGE_REMOTE_PART}"
fi
echo ""
echo "---------------------------后续操作指引❗❗----------------------------"
echo "请在目标服务器执行以下操作："
echo "1. 解压迁移包"
echo "2. 在解压后的目录中的执行以下命令进行迁移包部署操作："
echo "   bash deploy.sh"
echo "====================================================================="

