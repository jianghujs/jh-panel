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

  
  # 当前系统如果存在/appdata/backup/xtrabackup_data_history则默认为/appdata/backup/xtrabackup_data_history否则为/www/backup/xtrabackup_data_history
  default_xtrabackup_dir="/www/backup/xtrabackup_data_history"
  if [ -d "/appdata/backup/xtrabackup_data_history" ]; then
      default_xtrabackup_dir="/appdata/backup/xtrabackup_data_history"
  fi
  # 提示”输入xtrabackup备份所在目录（默认/www/backup/xtrabackup_data_history）”
  read -p "请输入xtrabackup备份所在目录（默认为：${default_xtrabackup_dir}）: " xtrabackup_dir
  xtrabackup_dir=${xtrabackup_dir:-${default_xtrabackup_dir}}

  xtrabackup_file_path=$(ls -t ${xtrabackup_dir}/xtrabackup_data*.zip | head -n 1)
  xtrabackup_file=$(basename ${xtrabackup_file_path})
  read -p "请输入xtrabackup文件名称（默认为：${xtrabackup_file}）: " xtrabackup_file_input
  xtrabackup_file=${xtrabackup_file_input:-$xtrabackup_file}
  read -p "请输入目标服务器xtrabackup备份所在目录（默认为：/www/backup/xtrabackup_data_history）: " target_xtrabackup_dir
  target_xtrabackup_dir=${target_xtrabackup_dir:-"/www/backup/xtrabackup_data_history"}
  rsync -avu -e "ssh -p ${remote_port}" --progress --delete ${xtrabackup_dir}/${xtrabackup_file} root@${remote_ip}:${target_xtrabackup_dir}/${xtrabackup_file} &>> ${MIGRATE_DIR}/rsync_migrate_final_xtrabackup_$timestamp.log
}

# 定义项目文件迁移函数
migrate_project() {
  
  # 当前系统如果存在/appdata/wwwroot/则默认为/appdata/wwwroot/否则为/www/wwwroot/
  default_project_dir="/www/wwwroot/"
  if [ -d "/appdata/wwwroot/" ]; then
      default_project_dir="/appdata/wwwroot/"
  fi

  # 提示”输入项目所在目录（默认/www/wwwroot/）”
  read -p "请输入项目所在目录（默认为：${default_project_dir}）: " project_dir
  project_dir=${project_dir:-${default_project_dir}}

  read -p "请输入目标服务器项目文件所在目录（默认为：/www/wwwroot/）: " target_project_dir
  target_project_dir=${target_project_dir:-"/www/wwwroot/"}
  read -p "请输入忽略的同步目录列表多个用逗号隔开（默认为：node_modules,logs,run）: " exclude_dirs
  exclude_dirs=${exclude_dirs:-"node_modules,logs,run"}
  rsync_exclude_string=""
  IFS=',' read -ra ADDR <<<"$exclude_dirs"
  for i in "${ADDR[@]}"; do
    rsync_exclude_string+="--exclude '$i' "
  done

  # 将目录下的软链提取到脚本
  symbolic_links_file="${MIGRATE_DIR}/symbolic_links_origin.sh"
  echo "" >  $symbolic_links_file

  # 使用find命令搜索所有目录，排除"node_modules"、"logs"、"run"目录
  find "$project_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" -o -name ".git" \) -prune -o -print | while read dir
  do
      echo "Processing directory links: $dir"

      # 如果目录是符号链接，则跳过
      if [ -L "$dir" ]; then
          echo "$dir is a symbolic link, skipping."
          continue
      fi

      # 在每个目录中，查找所有的符号链接
      ls -l "$dir" | grep "^l" | while read line
      do
          # 提取软链接文件名和目标文件名
          link=$(echo $line | awk '{print $9}')
          target=$(echo $line | awk '{print $11}')
          echo "link:${link}"
          echo "target:${target}"

          # 获取软链接和目标文件的绝对路径
          abs_link=$(readlink -f "$dir/$link")
          abs_target=$(readlink -f "$dir/$target")

          # 生成进入目录和创建相同软链接的命令，并将其追加到links.sh文件中
          echo "cd $dir" >> $symbolic_links_file
          echo "unlink $link" >> $symbolic_links_file
          echo "ln -s $abs_target $abs_link" >> $symbolic_links_file
      done
  done

  cp $MIGRATE_DIR/symbolic_links_origin.sh $MIGRATE_DIR/symbolic_links.sh 
  # 在文件中替换字符串"${project_dir}"为"\${deploy_dir}"
  sed -i 's|${project_dir}|${target_project_dir}|g' $MIGRATE_DIR/symbolic_links.sh 

  # 传输目录文件
  echo "开始传输项目文件..."
  rsync -avu -e "ssh -p ${remote_port}" ${rsync_exclude_string} --progress --delete ${project_dir} root@${remote_ip}:${target_project_dir} &>> ${MIGRATE_DIR}/rsync_migrate_final_www_$timestamp.log
  
  echo "开始传输软链配置..."
  # 传输软链配置脚本
  rsync -avu -e "ssh -p ${remote_port}" --progress --delete $MIGRATE_DIR/symbolic_links.sh root@${remote_ip}:$MIGRATE_DIR/symbolic_links.sh  &>> ${MIGRATE_DIR}/rsync_migrate_final_www_$timestamp.log
  echo "在目标服务器执行软链配置更新..."
  # 执行软链配置脚本
  ssh -p $remote_port root@${remote_ip} "bash ${MIGRATE_DIR}/symbolic_links.sh"
}

# 根据用户的选择运行对应的脚本
for key in "${script_order[@]}"; do
  for choice in $choices; do
    if [[ $key == $choice ]]; then
      ${scripts[$choice]}
    fi
  done
done
echo ""
echo "==========================执行上线同步完成✅=========================="
echo "------------------------------同步信息-------------------------------"
echo "- 目标服务器IP：$remote_ip"
echo "- 目标服务器SSH端口：$remote_port"
echo "- 同步内容："
echo "  - $xtrabackup_dir/$xtrabackup_file:$target_xtrabackup_dir/$xtrabackup_file"
echo "  - $project_dir:$target_project_dir（目录内软链以自动进行转换）"
echo ""
echo "---------------------------后续操作指引❗❗----------------------------"
echo "请在目标服务器执行以下操作："
echo "- xtrabackup文件恢复：xtrabackup文件已经同步到目标服务器的【$target_xtrabackup_dir】目录下，请在目标服务器的江湖面板-打开xtrabackup插件-mysql备份，找到【$xtrabackup_file】，点击恢复完成数据恢复工作"
echo "====================================================================="
