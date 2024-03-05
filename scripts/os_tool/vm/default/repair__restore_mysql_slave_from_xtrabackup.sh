#!/bin/bash

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
pushd /www/server/jh-panel > /dev/null

# gtid_purged_arg参数处理
gtid_purged_arg=${gtid_purged//:/：}
gtid_purged_arg=${gtid_purged_arg// /}
gtid_purged_arg=${gtid_purged_arg//$'\n'/}

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

