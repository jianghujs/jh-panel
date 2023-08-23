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

# 定义一个关联数组来存储你的脚本
declare -A scripts
scripts=(
["xtrabackup"]="migrate_xtrabackup.sh"
["网站"]="migrate_site.sh"
["项目"]="migrate_project.sh"
)

# 定义一个数组来存储脚本的顺序
script_order=("xtrabackup" "网站" "项目")

# 创建一个数组，用于dialog的checklist选项
script_options=()
for key in "${script_order[@]}"; do
    script_options+=("$key" "" on)
done

cmd=(dialog --separate-output --checklist "请勾选要迁移的数据:" 22 76 16)
choices=$("${cmd[@]}" "${script_options[@]}" 2>&1 >/dev/tty)

# 获取迁移临时文件存放目录
read -p "请输入迁移临时文件存放目录（默认/www/migrate/）: " dir
dir=${dir:-/www/migrate/}
export MIGRATE_DIR=$dir
# 如果目录不存在，则创建它，如果目录存在，则清空目录
if [ -d "$dir" ]; then
    read -p "目录已存在，是否清空目录？（默认y）[y/n] " yn
    yn=${yn:-y}
    case $yn in
        [Yy]* ) rm -rf $dir/*;;
        [Nn]* ) exit;;
        * ) echo "请输入y或n";;
    esac
else
    mkdir -p $dir
fi


# 获取当前IP地址
pushd /www/server/jh-panel > /dev/null
local_ip=$(python3 /www/server/jh-panel/tools.py getLocalIp)
popd > /dev/null
export LOCAL_IP=$local_ip

# 下载并执行脚本的函数
download_and_run() {
    local script_name=$1
    wget -N -O ./vm/${script_name} ${URLBase}/${script_name}
    echo ">>>>>>>>>>>>>>>>>>> Running ${script_name}"
    bash ./vm/${script_name}
    echo -e "<<<<<<<<<<<<<<<<<<< Run ${script_name} success✔!\n"
}

# 根据用户的选择运行对应的脚本
for key in "${script_order[@]}"; do
    for choice in $choices; do
        if [[ $key == $choice ]]; then
            script_file=${scripts[$choice]}
            # download_and_run ${script_file}
            ./$script_file
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
EOF

# 打包迁移临时文件存放目录
timestamp=$(date +%s)
pushd ${MIGRATE_DIR} > /dev/null
zip -r ../migrate_package_${local_ip}_${timestamp}.zip .
popd > /dev/null