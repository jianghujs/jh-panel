#!/bin/bash
source /www/server/jh-panel/scripts/util/msg.sh

# 检查/usr/bin/jq是否存在
if ! [ -x "/usr/bin/jq" ]; then
    echo "/usr/bin/jq不存在，正在尝试自动安装..."
    apt-get update
    apt-get install jq -y
    hash -r
    if ! [ -x "/usr/bin/jq" ]; then
        echo "安装jq失败，请手动安装后再运行脚本。"
        exit 1
    fi
fi


prompt "需要在主服务器执行xtrabackup备份并将最新的xtrabackup文件同步到本地吗？（默认n）[y/n]: " host_backup_choice "n"

if [ $host_backup_choice == "y" ]; then
  # 获取主服务器IP
  
  pushd /www/server/jh-panel > /dev/null
  default_remote_ip=$(python3 /www/server/jh-panel/tools.py getStandbyIp)
  popd > /dev/null
  remote_ip_tip="请输入主服务器IP"
  if [ -n "$default_remote_ip" ]; then
    remote_ip_tip+="（默认为：${default_remote_ip}）"
  fi
  prompt "$remote_ip_tip: " remote_ip $default_remote_ip
  if [ -z "$remote_ip" ]; then
    show_error "错误:未指定主服务器IP"
    exit 1
  fi

  # 输入主服务器SSH端口
  prompt "请输入主服务器SSH端口(默认: 10022): " remote_port "10022"

  # 正在主服务器执行xtrabackup备份
  echo "正在主服务器执行xtrabackup备份..."

  # 在目标服务器执行以下脚本
  xtrabackup_script=$(cat <<EOF
  #!/bin/bash
  export BACKUP_PATH=/www/backup/xtrabackup_data
  export BACKUP_COMPRESS=0
  set -x
  bash /www/server/xtrabackup/xtrabackup.sh
EOF
  )

  # 在目标服务器执行xtrabackup备份
  ssh -p $remote_port root@$remote_ip "echo '$xtrabackup_script' > /tmp/xtrabackup.sh && chmod +x /tmp/xtrabackup.sh && /tmp/xtrabackup.sh > /tmp/xtrabackup.log 2>&1"
  if [ $? -ne 0 ]; then
    show_error "错误:主服务器执行xtrabackup备份失败"
    exit 1
  fi
  show_info "主服务器执行xtrabackup备份成功✅"
  
  # 同步主服务器最新的xtrabackup文件到本地
  echo "正在同步主服务器最新的xtrabackup文件到本地..."
  # 获取最新的xtrabackup文件
  xtrabackup_file_path=$(ssh -p $remote_port root@$remote_ip "ls -t /www/backup/xtrabackup_data_history/xtrabackup_data*.zip | head -n 1")
  if [ -z "$xtrabackup_file_path" ]; then
    show_error "错误:未找到主服务器xtrabackup备份文件"
    exit 1
  fi
  xtrabackup_file=$(basename $xtrabackup_file_path)
  echo "最新的xtrabackup文件路径为：$xtrabackup_file_path"
  echo "最新的xtrabackup文件为：$xtrabackup_file"
  rsync -avz -e "ssh -p $remote_port" root@$remote_ip:$xtrabackup_file_path /www/backup/xtrabackup_data_history/
  show_info "同步主服务器最新的xtrabackup文件到本地成功✅"
fi

# 当前系统如果存在/appdata/backup/xtrabackup_data_history则默认为/appdata/backup/xtrabackup_data_history否则为/www/backup/xtrabackup_data_history
default_backup_dir="/www/backup/xtrabackup_data_history"
if [ -d "/appdata/backup/xtrabackup_data_history" ]; then
    default_backup_dir="/appdata/backup/xtrabackup_data_history"
fi
# 提示”输入xtrabackup备份所在目录（默认/www/backup/xtrabackup_data_history）”
read -p "请输入xtrabackup备份所在目录（默认为：${default_backup_dir}）: " backup_dir
backup_dir=${backup_dir:-${default_backup_dir}}

# 获取最近的一个xtrabackup文件
xtrabackup_file_path=$(ls -t ${backup_dir}/xtrabackup_data*.zip | head -n 1)
if [ -z "$xtrabackup_file_path" ]; then
  echo "错误:未找到xtrabackup备份文件"
  exit 1
fi
xtrabackup_file=$(basename ${xtrabackup_file_path})
read -p "请输入xtrabackup文件名称（默认为：${xtrabackup_file}）: " xtrabackup_file_input
xtrabackup_file=${xtrabackup_file_input:-$xtrabackup_file}

read -p "确认要恢复本地数据库到${xtrabackup_file}并恢复从库吗？（默认y）[y/n]: " choice
choice=${choice:-"y"}
if [ "${choice}" != "y" ]; then
    echo "已取消"
    exit 0
fi

# 恢复xtrabackup
pushd /www/server/jh-panel > /dev/null
recovery_script=$(python3 /www/server/jh-panel/plugins/xtrabackup/index.py  get_recovery_backup_script "{filename:${xtrabackup_file}}" | jq -r .data)
recovery_tmp_file="/tmp/temp_recovery.sh"
recovery_log="/tmp/temp_recovery.log"
popd > /dev/null
echo "pushd /www/server/jh-panel > /dev/null" > $recovery_tmp_file
echo "${recovery_script}" >> $recovery_tmp_file
echo "popd > /dev/null" >> $recovery_tmp_file
chmod +x $recovery_tmp_file
echo "|- 正在恢复xtrabackup文件..."
bash $recovery_tmp_file > $recovery_log 2>&1
rm $recovery_tmp_file
echo "|- 恢复xtrabackup文件成功✅"

# 获取mysql-apt状态
pushd /www/server/jh-panel > /dev/null
mysql_apt_status=$(python3 /www/server/jh-panel/plugins/mysql-apt/index.py status)
popd > /dev/null
echo "|- mysql-apt状态：$mysql_apt_status"
# 如果mysql-apt状态为stop，则调用start方法
if [ "$mysql_apt_status" == "stop" ]; then
    echo "|- 正在尝试启动mysql-apt..."
    pushd /www/server/jh-panel > /dev/null
    mysql_apt_start_result=$(python3 /www/server/jh-panel/plugins/mysql-apt/index.py start)
    popd > /dev/null
    if [ $mysql_apt_start_result == "ok" ]
    then
        echo "|- mysql-apt启动成功✅"
    else
        echo "mysql-apt启动失败❌"
        exit 1
    fi
fi

# 获取/www/backup/xtrabackup_data_restore/xtrabackup_binlog_info中的binlog文件名和pos
binlog_info_file="/www/backup/xtrabackup_data_restore/xtrabackup_binlog_info"
log_file=""
log_pos=""
if [[ -f "$binlog_info_file" ]]; then
    log_file=$(awk 'NR==1 {print $1}' "$binlog_info_file")
    log_pos=$(awk 'NR==1 {print $2}' "$binlog_info_file")
    gtid_purged=$(awk 'NR==1 {for(i=3;i<=NF;i++) printf "%s ", $i; next} {for(i=1;i<=NF;i++) printf "%s ", $i} END {print ""}' "$binlog_info_file")

    # 输出结果
    echo "|- log_file：$log_file"
    echo "|- log_pos：$log_pos"
    echo "|- gtid_purged：$gtid_purged"
else
    echo "错误：$binlog_info_file 不存在。"
    exit 1
fi

# 使用binlog_file和binlog_pos恢复从库
echo "正在恢复从库..."

# gtid_purged_arg参数处理
gtid_purged_arg=${gtid_purged//:/：}
gtid_purged_arg=${gtid_purged_arg// /}
gtid_purged_arg=${gtid_purged_arg//$'\n'/}

pushd /www/server/jh-panel > /dev/null
# init_slave_result=$(python3 /www/server/jh-panel/plugins/mysql-apt/index.py init_slave_status {log_file:${log_file},log_pos:${log_pos},gtid_purged:${gtid_purged})
init_slave_result=$(python3 /www/server/jh-panel/plugins/mysql-apt/index.py init_slave_status {gtid_purged:${gtid_purged_arg}})
# python3 /www/server/jh-panel/plugins/mysql-apt/index.py init_slave_status {gtid_purged:${gtid_purged_arg}}
popd > /dev/null

init_slave_status=$(echo $init_slave_result | jq -r '.status')
init_slave_msg=$(echo $init_slave_result | jq -r '.msg')
if [ $init_slave_status == "true" ]
then
    echo "恢复从库成功✅"
else
    echo "恢复从库失败，错误信息为：$init_slave_msg"
    exit 1
fi

echo ""
echo "==========================从xtrabackup恢复从库完成✅========================"
echo "- xtrabackup文件路径：$backup_dir/$xtrabackup_file"
echo "- log_file：$log_file"
echo "- log_pos：$log_pos"
echo "- gtid_purged：$gtid_purged"
echo "==============================================================="

