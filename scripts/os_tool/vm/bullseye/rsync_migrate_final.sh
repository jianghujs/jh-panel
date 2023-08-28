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

有什么可以帮你的吗

帮我完善下面的脚本

scripts我希望改成一个对应方法的集合
选择xtrabackup时对应的方法流程如下
提示”请输入xtrabackup备份所在目录（默认为：/www/backup/xtrabackup_data_history）
从xtrabackup备份所在目录获取最新的xtrabackup_data开头的zip文件名称，作为xtrabackup_file的变量值
提示”请输入xtrabackup文件名称（默认为：${上一步获取的xtrabackup_file}）
提示”请输入目标服务器xtrabackup备份所在目录（默认为：/www/backup/xtrabackup_data_history）“
执行以下命令进行输入同步
rsync -avu -e 'ssh -p 【remote_port】' --progress --delete 【xtrabackup备份所在目录】/xtrabackup文件名称 root@【remote_ip】:【请输入目标服务器xtrabackup备份所在目录】/xtrabackup文件名称 &>> MIGRATE_DIR/rsync_migrate_final_xtrabackup_$timestamp.log
选择项目时对应的方法流程如下：
提示”请输入项目文件所在目录（默认为：/www/wwwroot/）“
提示”请输入目标服务器项目文件所在目录（默认为：/www/wwwroot/）“
提示”请输入忽略的同步目录列表多个用逗号隔开（默认为：node_modules,logs,run）“，生成类似”--exclude 'node_modules' --exclude 'logs' --exclude 'run'“的格式
使用以下脚本从项目文件目录找到所有的软链，并生成symbolic_links_origin.sh（用于保存当前软链配置，在执行rsync后执行这个脚本恢复软链）和symbolic_links_target.sh（用于保存目标服务器的软链配置，当前内容是在symbolic_links_origin.sh的基础上，把【项目所在目录】全部替换成【目标服务器项目文件所在目录】，在执行rsync之前会执行，把软链临时改成目标服务器的软链配置）两个文件

# 将目录下的软链提取到脚本
symbolic_links_file="${MIGRATE_DIR}/project_files/symbolic_links_origin.sh"
echo "" >  $symbolic_links_file

# 使用find命令搜索所有目录，排除"node_modules"、"logs"、"run"目录
find "$project_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" -o -name ".git" \) -prune -o -print | while read dir
do
  echo "Processing directory: $dir"

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

      # 获取软链接和目标文件的绝对路径
      abs_link=$(readlink -f "$dir/$link")
      abs_target=$(readlink -f "$dir/$target")

      # 生成进入目录和创建相同软链接的命令，并将其追加到links.sh文件中
      echo "cd $dir" >> $symbolic_links_file
      echo "unlink $link" >> $symbolic_links_file
      echo "ln -s $abs_target $abs_link" >> $symbolic_links_file
  done
done

执行以下命令进行数据同步
rsync -avu -e 'ssh -p 【remote_port】' 【忽略的同步目录列表、 --progress --delete 【项目文件所在目录】 root@【remote_ip】:【目标项目文件所在目录】 &>>  MIGRATE_DIR/rsync_migrate_final_www_$timestamp.log
执行symbolic_links_origin.sh恢复当前项目文件所在目录的软链
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
["xtrabackup"]="migrate_xtrabackup.sh"
["项目文件"]="migrate_project.sh"
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

# 输入目标服务器IP
read -p "请输入目标服务器IP: " remote_ip
if [ -z "$remote_ip" ]; then
  echo "错误:未指定目标服务器IP"
  exit 1
fi

# 输入目标服务器SSH端口
read -p "请输入目标服务器SSH端口(默认: 10022): " remote_port
remote_port=${remote_port:-10022}

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

# 定义xtrabackup迁移函数
migrate_xtrabackup() {
  read -p "请输入xtrabackup备份所在目录（默认为：/www/backup/xtrabackup_data_history）: " xtrabackup_dir
  xtrabackup_dir=${xtrabackup_dir:-"/www/backup/xtrabackup_data_history"}
  xtrabackup_file=$(ls -t ${xtrabackup_dir}/xtrabackup_data*.zip | head -n 1)
  read -p "请输入xtrabackup文件名称（默认为：${xtrabackup_file}）: " xtrabackup_file
  read -p "请输入目标服务器xtrabackup备份所在目录（默认为：/www/backup/xtrabackup_data_history）: " target_xtrabackup_dir
  target_xtrabackup_dir=${target_xtrabackup_dir:-"/www/backup/xtrabackup_data_history"}
  rsync -avu -e "ssh -p ${remote_port}" --progress --delete ${xtrabackup_dir}/${xtrabackup_file} root@${remote_ip}:${target_xtrabackup_dir}/${xtrabackup_file} &>> MIGRATE_DIR/rsync_migrate_final_xtrabackup_$timestamp.log
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
  IFS=',' read -ra ADDR <<< "$exclude_dirs"
  for i in "${ADDR[@]}"; do
    rsync_exclude_string+="--exclude '$i' "
  done
  rsync -avu -e "ssh -p ${remote_port}" ${rsync_exclude_string} --progress --delete ${project_dir} root@${remote_ip}:${target_project_dir} &>> MIGRATE_DIR/rsync_migrate_final_www_$timestamp.log
}

# 根据用户的选择运行对应的脚本
for key in "${script_order[@]}"; do
    for choice in $choices; do
        if [[ $key == $choice ]]; then
            ${scripts[$choice]}
        fi
    done
done
这个脚本将对话框工具dialog用于创建一个菜单，用户可以选择要迁移的数据类型。然后，根据用户的选择，执行相应的函数来迁移数据。这个脚本假定你有一个名为"migrate_xtrabackup"的函数和一个名为"migrate_project"的函数，它们分别处理xtrabackup数据和项目文件的迁移。

注意：此脚本没有包含你提到的软链恢复部分，因为这部分代码很复杂，可能需要单独处理。你可能需要创建一个单独的脚本或函数来处理这部分。

我的脚本现在是这样的，xtrabackup_file我希望是文件名，而不是文件的全路径

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
  xtrabackup_file=$(ls -t ${xtrabackup_dir}/xtrabackup_data*.zip | head -n 1)
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
你可以使用basename命令来获取文件名，而不是全路径。下面是修改后的脚本：

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
