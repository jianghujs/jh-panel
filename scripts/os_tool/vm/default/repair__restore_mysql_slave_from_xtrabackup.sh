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


prompt "是否需要在主服务器执行xtrabackup备份？（默认n）[y/n]: " execute_backup_choice "n"

# 第一步：在主服务器执行xtrabackup备份
if [ $execute_backup_choice == "y" ]; then
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
fi

prompt "是否需要将最新的xtrabackup文件同步到本地？（默认n）[y/n]: " sync_backup_choice "n"

# 第二步：同步主服务器最新的xtrabackup文件到本地
if [ $sync_backup_choice == "y" ]; then
  # 如果第一步没有执行，需要重新获取主服务器信息
  if [ $execute_backup_choice != "y" ]; then
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
  fi

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

if [ -z "$recovery_script" ] || [ "$recovery_script" == "null" ]; then
    show_error "错误:xtrabackup恢复脚本生成失败，已停止，避免误启动mysql-apt导致密码被重新初始化"
    exit 1
fi

# 恢复脚本由xtrabackup插件生成，默认末尾会启动MySQL。
# 这里先移除启动动作，等确认data/mysql已恢复完成后，再由下方统一启动mysql-apt。
# unzip返回码1通常只是告警，允许继续执行prepare/copy-back；严重错误仍然中断。
recovery_script=$(printf '%s\n' "$recovery_script" | awk '
    /^[[:space:]]*systemctl[[:space:]]+start[[:space:]]+(mysql-apt|mysql)([[:space:]]|$)/ {next}
    /^[[:space:]]*systemctl[[:space:]]+stop[[:space:]]+(mysql-apt|mysql)([[:space:]]|$)/ {
        next
    }
    /^[[:space:]]*mv[[:space:]]+\/www\/server\/(mysql-apt|mysql)\/data[[:space:]]+/ {
        datadir = ($0 ~ /\/www\/server\/mysql-apt\/data/) ? "/www/server/mysql-apt/data" : "/www/server/mysql/data"
        print "RESTORE_MYSQL_DATA_DIR=\"" datadir "\""
        print $0
        print "if [ -e \"" datadir "\" ]; then"
        print "    echo \"|- 清理copy-back目标目录内容：" datadir "\""
        print "    find \"" datadir "\" -mindepth 1 -maxdepth 1 -exec rm -rf {} +"
        print "fi"
        print "mkdir -p \"" datadir "\""
        next
    }
    /^[[:space:]]*unzip[[:space:]]+-d[[:space:]]+/ {
        print "set +e"
        print $0
        print "unzip_status=$?"
        print "echo \"|- unzip返回码：$unzip_status\""
        print "set -e"
        print "if [ \"$unzip_status\" -gt 1 ]; then echo \"错误:unzip解压失败，返回码：$unzip_status\"; exit \"$unzip_status\"; fi"
        next
    }
    /^[[:space:]]*xtrabackup[[:space:]].*--copy-back/ {
        print "if systemctl is-active --quiet mysql-apt 2>/dev/null || systemctl is-active --quiet mysql 2>/dev/null; then"
        print "    echo \"错误:copy-back前检测到MySQL仍在运行，已中断恢复\""
        print "    exit 1"
        print "fi"
        print "RESTORE_MYSQL_DATA_DIR=${RESTORE_MYSQL_DATA_DIR:-/www/server/mysql-apt/data}"
        print "mkdir -p \"$RESTORE_MYSQL_DATA_DIR\""
        print "if find \"$RESTORE_MYSQL_DATA_DIR\" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then"
        print "    echo \"|- copy-back前清空目标目录内容：$RESTORE_MYSQL_DATA_DIR\""
        print "    find \"$RESTORE_MYSQL_DATA_DIR\" -mindepth 1 -maxdepth 1 -exec rm -rf {} +"
        print "fi"
        print "if find \"$RESTORE_MYSQL_DATA_DIR\" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then"
        print "    echo \"错误:copy-back目标目录仍非空：$RESTORE_MYSQL_DATA_DIR\""
        print "    find \"$RESTORE_MYSQL_DATA_DIR\" -mindepth 1 -maxdepth 1 -maxdepth 1 -print | head -n 20"
        print "    exit 1"
        print "fi"
        print $0
        next
    }
    {print}
')

restore_mysql_service=""
if [ -d "/www/server/mysql-apt" ]; then
    restore_mysql_service="mysql-apt"
elif [ -d "/www/server/mysql" ]; then
    restore_mysql_service="mysql"
fi

if [ -n "$restore_mysql_service" ]; then
    echo "|- 正在停止${restore_mysql_service}..."
    if [ "$restore_mysql_service" == "mysql-apt" ]; then
        pushd /www/server/jh-panel > /dev/null
        stop_restore_mysql_result=$(python3 /www/server/jh-panel/plugins/mysql-apt/index.py stop)
        popd > /dev/null
        if [ "$stop_restore_mysql_result" != "ok" ]; then
            show_error "错误:停止${restore_mysql_service}失败：$stop_restore_mysql_result"
            exit 1
        fi
    else
        if ! systemctl stop "$restore_mysql_service"; then
            show_error "错误:停止${restore_mysql_service}失败"
            exit 1
        fi
    fi

    for i in $(seq 1 30); do
        if ! systemctl is-active --quiet "$restore_mysql_service"; then
            break
        fi
        sleep 1
    done
    if systemctl is-active --quiet "$restore_mysql_service"; then
        show_error "错误:${restore_mysql_service}未停止，已停止恢复"
        exit 1
    fi

    echo "|- 正在临时mask ${restore_mysql_service}，防止恢复过程中被定时任务自动拉起..."
    if ! systemctl mask "$restore_mysql_service" > /dev/null 2>&1; then
        show_error "错误:临时mask ${restore_mysql_service}失败，已停止恢复"
        exit 1
    fi
fi

echo "set -e" > $recovery_tmp_file
echo "set -o pipefail" >> $recovery_tmp_file
echo "pushd /www/server/jh-panel > /dev/null" >> $recovery_tmp_file
echo "${recovery_script}" >> $recovery_tmp_file
echo "popd > /dev/null" >> $recovery_tmp_file
chmod +x $recovery_tmp_file
echo "|- 正在恢复xtrabackup文件..."
bash $recovery_tmp_file > $recovery_log 2>&1
recovery_status=$?
rm $recovery_tmp_file
if [ $recovery_status -ne 0 ]; then
    show_error "错误:xtrabackup恢复失败，已停止，避免误启动mysql-apt导致密码被重新初始化"
    if [ -n "$restore_mysql_service" ]; then
        echo "|- ${restore_mysql_service}仍处于mask状态，确认数据目录正常后可手动执行：systemctl unmask ${restore_mysql_service}"
    fi
    echo "|- 恢复日志：$recovery_log"
    tail -n 80 "$recovery_log"
    latest_xtrabackup_recovery_log=$(ls -t /www/server/xtrabackup/logs/recovery_*.log 2>/dev/null | head -n 1)
    if [ -n "$latest_xtrabackup_recovery_log" ]; then
        echo "|- xtrabackup详细日志：$latest_xtrabackup_recovery_log"
        tail -n 120 "$latest_xtrabackup_recovery_log"
    fi
    exit 1
fi

mysql_apt_data_dir="/www/server/mysql-apt/data"
if [ -f "/www/server/mysql-apt/etc/my.cnf" ]; then
    mysql_apt_data_dir=$(awk -F= '/^[[:space:]]*datadir[[:space:]]*=/{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2; exit}' /www/server/mysql-apt/etc/my.cnf)
    mysql_apt_data_dir=${mysql_apt_data_dir:-/www/server/mysql-apt/data}
fi

if [ ! -d "$mysql_apt_data_dir/mysql" ]; then
    show_error "错误:恢复后未检测到MySQL系统库目录：$mysql_apt_data_dir/mysql"
    echo "|- 已停止，避免mysql-apt start触发空数据目录初始化并改写面板记录密码"
    if [ -n "$restore_mysql_service" ]; then
        echo "|- ${restore_mysql_service}仍处于mask状态，确认数据目录正常后可手动执行：systemctl unmask ${restore_mysql_service}"
    fi
    echo "|- 恢复日志：$recovery_log"
    tail -n 80 "$recovery_log"
    latest_xtrabackup_recovery_log=$(ls -t /www/server/xtrabackup/logs/recovery_*.log 2>/dev/null | head -n 1)
    if [ -n "$latest_xtrabackup_recovery_log" ]; then
        echo "|- xtrabackup详细日志：$latest_xtrabackup_recovery_log"
        tail -n 120 "$latest_xtrabackup_recovery_log"
    fi
    exit 1
fi

if [ -n "$restore_mysql_service" ]; then
    echo "|- 正在解除${restore_mysql_service}的mask..."
    if ! systemctl unmask "$restore_mysql_service" > /dev/null 2>&1; then
        show_error "错误:解除${restore_mysql_service}的mask失败，请手动执行：systemctl unmask ${restore_mysql_service}"
        exit 1
    fi
fi

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
