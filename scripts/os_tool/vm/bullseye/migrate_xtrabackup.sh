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

# 获取环境变量中的MIGRATE_DIR值
MIGRATE_DIR=${MIGRATE_DIR:-"/www/migrate/"}

# 提示”输入xtrabackup备份所在目录（默认/www/backup/xtrabackup_data_history）”
echo "请输入xtrabackup备份所在目录（默认/www/backup/xtrabackup_data_history）"
read -p "输入您的选择（默认为：/www/backup/xtrabackup_data_history）: " backup_dir
backup_dir=${backup_dir:-"/www/backup/xtrabackup_data_history"}

# 定义存储迁移信息的json对象（如：migrate_info_xtrabackup）
migrate_info_xtrabackup='{}'

# 自动复制xtrabackup备份所在目录下最新的xtrabackup_data开头的zip文件到 /MIGRATE_DIR，并重命名为“原文件名_from_[当前IP地址]”，将重命名后的文件名存到migrate_info_xtrabackup.backup_file
latest_backup=$(ls -t ${backup_dir}/xtrabackup_data*.zip | head -1)
current_ip=$(hostname -I | awk '{print $1}')

new_backup_file="$(basename ${latest_backup})_from_${current_ip}"
new_backup_file_path="${MIGRATE_DIR}/${new_backup_file}"
cp ${latest_backup} ${new_backup_file_path}
migrate_info_xtrabackup=$(echo ${migrate_info_xtrabackup} | jq --arg backup_file ${new_backup_file} '. + {backup_file: $backup_file}')

# 获取mysql密码：执行 python3 plugins/mysql-apt/index.py get_db_list，并将返回的结果转成json对象，从中获取info.root_pwd的值就是mysql的密码， 设置migrate_info_xtrabackup.mysql_root_psw为此密码
pushd /www/server/jh-panel > /dev/null
mysql_info=$(python3 /www/server/jh-panel/plugins/mysql-apt/index.py get_db_list)
popd > /dev/null
mysql_pwd=$(echo ${mysql_info} | jq -r '.info.root_pwd')
migrate_info_xtrabackup=$(echo ${migrate_info_xtrabackup} | jq --arg mysql_pwd ${mysql_pwd} '. + {mysql_root_psw: $mysql_pwd}')

# 把migrate_info_xtrabackup的内容写入到 MIGRATE_DIR/migrate_info_xtrabackup
echo ${migrate_info_xtrabackup} > ${MIGRATE_DIR}/migrate_info_xtrabackup.json

# 在MIGRATE_DIR目录生成deploy_xtrabackup.sh，内容如下：
cat << EOF > ${MIGRATE_DIR}/deploy_xtrabackup.sh
#!/bin/bash

# 提示”输入xtrabackup备份所在目录（默认/www/backup/xtrabackup_data_history）”
echo "请输入xtrabackup备份所在目录（默认/www/backup/xtrabackup_data_history）"
read -p "输入您的选择: " backup_dir
backup_dir=${backup_dir:-"/www/backup/xtrabackup_data_history"}

# 将当前目录下的xtrabackup_data开头的文件复制到xtrabackup备份所在目录
cp xtrabackup_data* ${backup_dir}

# 使用 python3 /www/server/jh-panel/plugins/xtrabackup/index.py get_recovery_backup_script "{filename: xtrabackup_data_20230821_203001.zip}" 获取并执行恢复xtrabackup文件脚本
recovery_script=\$(python3 /www/server/jh-panel/plugins/xtrabackup/index.py get_recovery_backup_script "{filename: ${new_backup_file}}")
echo "\${recovery_script}" > temp_recovery.sh
chmod +x temp_recovery.sh
./temp_recovery.sh
rm temp_recovery.sh


# 使用 jh-panel\plugins\mysql-apt\index.py set_root_pwd [migrate_info_xtrabackup文件中的mysql_root_psw]
mysql_pwd=\$(jq -r '.mysql_root_psw' ${MIGRATE_DIR}/migrate_info_xtrabackup.json)
python3 jh-panel/plugins/mysql-apt/index.py set_root_pwd ${mysql_pwd}

EOF
chmod +x ${MIGRATE_DIR}/deploy_xtrabackup.sh
