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

latest_backup=$(ls -t ${backup_dir}/xtrabackup_data*.zip | head -1)
echo "lastest_backup: ${latest_backup}"

# 获取mysql密码：执行 python3 plugins/mysql-apt/index.py get_db_list，并将返回的结果转成json对象，从中获取info.root_pwd的值就是mysql的密码， 设置migrate_info_xtrabackup.mysql_root_psw为此密码
pushd /www/server/jh-panel > /dev/null
mysql_info=$(python3 /www/server/jh-panel/plugins/mysql-apt/index.py get_db_list_page)
popd > /dev/null
mysql_pwd=$(echo ${mysql_info} | jq -r '.info.root_pwd')
echo "mysql_pwd: ${mysql_pwd}"

# 使用 python3 /www/server/jh-panel/plugins/xtrabackup/index.py get_recovery_backup_script "{filename: xtrabackup_data_20230821_203001.zip}" 获取并执行恢复xtrabackup文件脚本
pushd /www/server/jh-panel > /dev/null
recovery_script=$(python3 /www/server/jh-panel/plugins/xtrabackup/index.py  get_recovery_backup_script "{filename:${new_backup_file}}" | jq -r .data)
popd > /dev/null
tmp_script_file="/tmp/temp_recovery.sh"
echo "pushd /www/server/jh-panel > /dev/null" > $tmp_script_file
echo "${recovery_script}" >> $tmp_script_file
echo "popd > /dev/null" >> $tmp_script_file
chmod +x $tmp_script_file
bash $tmp_script_file
rm -f $tmp_script_file
echo "恢复xtrabackup文件成功✔"


