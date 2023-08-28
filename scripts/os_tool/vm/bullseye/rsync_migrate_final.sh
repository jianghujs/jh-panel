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

# 获取环境变量中的MIGRATE_DIR值
MIGRATE_DIR=${MIGRATE_DIR:-"/www/migrate/"}

# 定义一个关联数组来存储你的脚本
declare -A scripts
scripts=(
  ["xtrabackup"]="migrate_xtrabackup"
  ["项目文件"]="migrate_project"
)

# 定义一个数组来存储脚本的顺序
script_order=("xtrabackup" "项目文件")

# 创建一个数组，用于dialog的checklist选项
script_options=()
for key in "${script_order[@]}"; do
  script_options+=("$key" "" on)
done

cmd=(dialog --separate-output --checklist "请勾选要迁移的数据:" 22 76 16)
choices=$("${cmd[@]}" "${script_options[@]}" 2>&1 >/dev/tty)

# 输入目标服务器IP
read -p "请输入目标服务器IP: " remote_ip
if [ -z "$remote_ip" ]; then
  echo "错误:未指定目标服务器IP"
  exit 1
fi

# 输入目标服务器SSH端口
read -p "请输入目标服务器SSH端口(默认: 10022): " remote_port
remote_port=${remote_port:-10022}

# 定义xtrabackup迁移函数
migrate_xtrabackup() {

  # 提示是否需要进行xtrabackup备份操作
  read -p "是否需要执行xtrabackup备份？（默认n）[y/n]: " backup_choice
  backup_choice=${backup_choice:-"n"}

  if [ $backup_choice == "y" ]; then
    pushd /www/server/jh-panel >/dev/null
    backup_script_data=$(python3 /www/server/jh-panel/plugins/xtrabackup/index.py backup_script)
    popd >/dev/null
    backup_script=$(echo ${backup_script_data} | jq -r '.data')
    echo "${backup_script}" >${MIGRATE_DIR}/temp_xtrabackup_backup.sh
    chmod +x ${MIGRATE_DIR}/temp_xtrabackup_backup.sh
    ${MIGRATE_DIR}/temp_xtrabackup_backup.sh
    rm ${MIGRATE_DIR}/temp_xtrabackup_backup.sh
  fi

  read -p "请输入xtrabackup备份所在目录（默认为：/www/backup/xtrabackup_data_history）: " xtrabackup_dir
  xtrabackup_dir=${xtrabackup_dir:-"/www/backup/xtrabackup_data_history"}
  xtrabackup_file_path=$(ls -t ${xtrabackup_dir}/xtrabackup_data*.zip | head -n 1)
  xtrabackup_file=$(basename ${xtrabackup_file_path})
  read -p "请输入xtrabackup文件名称（默认为：${xtrabackup_file}）: " xtrabackup_file
  read -p "请输入目标服务器xtrabackup备份所在目录（默认为：/www/backup/xtrabackup_data_history）: " target_xtrabackup_dir
  target_xtrabackup_dir=${target_xtrabackup_dir:-"/www/backup/xtrabackup_data_history"}
  rsync -avu -e "ssh -p ${remote_port}" --progress --delete ${xtrabackup_dir}/${xtrabackup_file} root@${remote_ip}:${target_xtrabackup_dir}/${xtrabackup_file} &>> ${MIGRATE_DIR}/rsync_migrate_final_xtrabackup_$timestamp.log
}

# 定义项目文件迁移函数
migrate_project() {
  read -p "请输入项目文件所在目录（默认为：/www/wwwroot/）: " project_dir
  project_dir=${project_dir:-"/www/wwwroot/"}
  read -p "请输入目标服务器项目文件所在目录（默认为：/www/wwwroot/）: " target_project_dir
  target_project_dir=${target_project_dir:-"/www/wwwroot/"}
  read -p "请输入忽略的同步目录列表多个用逗号隔开（默认为：node_modules,logs,run）: " exclude_dirs
  exclude_dirs=${exclude_dirs:-"node_modules,logs,run"}
  rsync_exclude_string=""
  IFS=',' read -ra ADDR <<<"$exclude_dirs"
  for i in "${ADDR[@]}"; do
    rsync_exclude_string+="--exclude '$i' "
  done
  rsync -avu -e "ssh -p ${remote_port}" ${rsync_exclude_string} --progress --delete ${project_dir} root@${remote_ip}:${target_project_dir} &>>MIGRATE_DIR/rsync_migrate_final_www_$timestamp.log
}

# 根据用户的选择运行对应的脚本
for key in "${script_order[@]}"; do
  for choice in $choices; do
    if [[ $key == $choice ]]; then
      ${scripts[$choice]}
    fi
  done
done
