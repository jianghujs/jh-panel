#!/bin/bash
script_file="/tmp/online.sh"


echo "-----------------------"
echo "即将生成服务器上线脚本到${script_file}，包含内容如下："
echo "1. （可选）执行xtrabackup增量恢复"
echo "1. （可选）恢复网站数据"
echo "1. （可选）恢复插件数据"
echo "2. （可选）检查数据一致性"
echo "3. （可选）同步服务器文件"
echo "4. 启动xtrabackup增量备份、xtrabackup、mysqldump定时任务"
echo "5. 从authorized_keys删除同步公钥"
echo "6. 启动rsyncd任务"
echo "7. 启动Openresty"
echo "8. 开启邮件通知"
echo "-----------------------"
read -p "确认生成吗？（默认y）[y/n]: " choice
choice=${choice:-"y"}

echo "" > $script_file

if [ $choice == "y" ]; then
  
  read -p "请输入本地服务器IP: " local_ip
  if [ -z "$local_ip" ]; then
    echo "错误:未指定本地服务器IP"
    exit 1
  fi
  echo "export LOCAL_IP=$local_ip" >> $script_file

  read -p "请输入备用服务器IP: " remote_ip
  if [ -z "$remote_ip" ]; then
    echo "错误:未指定备用服务器IP"
    exit 1
  fi
  echo "export REMOTE_IP=$remote_ip" >> $script_file

  echo "" >> $script_file

  
  # 增量恢复
  echo "pushd /www/server/jh-panel > /dev/null" >> $script_file
  echo "" >> $script_file
  read -p "需要执行增量恢复吗？（默认n）[y/n]: " xtrabackup_inc_restore_choice
  xtrabackup_inc_restore_choice=${xtrabackup_inc_restore_choice:-"n"}

  if [ $xtrabackup_inc_restore_choice == "y" ]; then
    echo "# 执行xtrabackup增量恢复" >> $script_file
    pushd /www/server/jh-panel > /dev/null
    recovery_script=$(python3 /www/server/jh-panel/plugins/xtrabackup-inc/index.py get_inc_recovery_cron_script | jq -r .data)
    popd > /dev/null
    echo "${recovery_script}" >> $script_file
    echo "echo \"|- xtrabackup增量恢复完成✅\"" >> $script_file
    echo "" >> $script_file
  fi

  # 恢复网站数据
  echo "pushd /www/server/jh-panel > /dev/null" >> $script_file
  echo "" >> $script_file
  read -p "需要恢复网站配置吗？（默认n）[y/n]: " site_setting_restore_choice
  site_setting_restore_choice=${site_setting_restore_choice:-"n"}

  if [ $site_setting_restore_choice == "y" ]; then
    echo "# 恢复网站配置" >> $script_file
    default_site_setting_backup_dir="/www/backup/siteSetting"
    read -p "请输入网站配置备份文件所在目录（默认为：${default_site_setting_backup_dir}）: " site_setting_backup_dir
    site_setting_backup_dir=${site_setting_backup_dir:-${default_site_setting_backup_dir}}
    # 获取最近的一个网站配置all文件
    site_setting_file_path=$(ls -t ${site_setting_backup_dir}/all_*.zip | head -n 1)
    site_setting_file=$(basename ${site_setting_file_path})
    read -p "请输入网站配置备份文件名称（默认为：${site_setting_file}）: " site_setting_file_input
    site_setting_file=${site_setting_file_input:-$site_setting_file}
    
    echo "site_setting_restore_tmp=/tmp/siteSettingRestore" >> $script_file
    echo "unzip -o $site_setting_backup_dir/$site_setting_file -d \$site_setting_restore_tmp/" >> $script_file
    
    echo "pushd \$site_setting_restore_tmp > /dev/null" >> $script_file
    echo "python3 /www/server/jh-panel/scripts/migrate.py importSiteInfo \$(pwd)/site_info.json" >> $script_file
    echo "echo \"导入站点数据完成✔!\"" >> $script_file
    
    echo "# 合并letsencrypt.json" >> $script_file
    echo "local_letsencrypt_path=/www/server/jh-panel/data/letsencrypt.json" >> $script_file
    echo "add_letsencrypt_path=\$(pwd)/letsencrypt.json" >> $script_file
    echo "local_letsencrypt_content=\$(cat \"\$local_letsencrypt_path\")" >> $script_file
    echo "add_letsencrypt_content=\$(cat "\$add_letsencrypt_path")" >> $script_file
    echo "merged_letsencrypt_content=\$(jq -sc '.[0] * .[1]' <<< "\$local_letsencrypt_content \$add_letsencrypt_content")" >> $script_file
    echo "echo \"\$merged_letsencrypt_content\" > \"\$local_letsencrypt_path\"" >> $script_file

    echo "echo \"# 解压合并当前目录下的web_conf.zip到/www/server/web_conf/\"" >> $script_file
    echo "unzip -o ./web_conf.zip -d /www/server/web_conf/" >> $script_file
    echo "echo \"恢复网站配置完成✔!\"" >> $script_file

    echo "# 重启openresty" >> $script_file
    echo "pushd /www/server/jh-panel > /dev/null" >> $script_file
    echo "python3 /www/server/jh-panel/plugins/openresty/index.py restart" >> $script_file
    echo "popd > /dev/null" >> $script_file
    echo "echo \"重启openresty完成✔!\"" >> $script_file

    echo "popd > /dev/null" >> $script_file
    echo "echo \"|- 恢复网站配置✅\"" >> $script_file
    echo "" >> $script_file
  fi

  # 主备服务器checksum检查
  read -p "需要检查主备服务器的checksum吗？（默认y）[y/n]: " checksum_choice
  checksum_choice=${checksum_choice:-"y"}

  if [ $checksum_choice == "y" ]; then
    echo "# 检查主备服务器checksum" >> $script_file
    echo "echo \"|- 检查主备服务器checksum...\"" >> $script_file
    echo "pushd /www/server/jh-panel/scripts/os_tool/vm/bullseye/ > /dev/null"  >> $script_file
    echo "npm i" >> $script_file
    echo "node /www/server/jh-panel/scripts/os_tool/vm/bullseye/monitor__export_mysql_checksum_compare.js" >> $script_file
    echo "popd > /dev/null" >> $script_file
    echo "source /tmp/compare_checksum_diff" >> $script_file
    echo "if [[ -n \$checksum_diff ]]; then" >> $script_file
    echo "  checksum_diff=\$(echo \"\$checksum_diff\" | tr ',' '\n')" >> $script_file
    echo "  echo \"|- checksum结果存在以下不同：\"" >> $script_file
    echo "  echo -e \"\033[0;31m\$checksum_diff\033[0m\"" >> $script_file
    echo "  read -p \"确定要继续上线吗？（默认n）[y/n]: \" checksum_ignore_choice" >> $script_file
    echo "  checksum_ignore_choice=\${checksum_ignore_choice:-\"n\"}" >> $script_file
    echo "  if [ \$checksum_ignore_choice == \"n\" ]; then" >> $script_file
    echo "    echo \"错误:数据不一致，上线终止\"" >> $script_file
    echo "    exit 1" >> $script_file
    echo "  fi" >> $script_file
    echo "fi" >> $script_file
    echo "echo \"|- 主备服务器checksum检查完成✅\"" >> $script_file
    echo "" >> $script_file
  fi

  # 主从切换
  read -p "需要进行主从切换吗？（默认y）[y/n]: " switch_master_slave_choice
  switch_master_slave_choice=${switch_master_slave_choice:-"y"}

  if [ $switch_master_slave_choice == "y" ]; then
    echo "# 主从切换" >> $script_file
    echo "echo \"|- 主从切换...\"" >> $script_file
    echo "pushd /www/server/jh-panel/scripts/os_tool/vm/bullseye/ > /dev/null"  >> $script_file
    echo "npm i" >> $script_file
    echo "node /www/server/jh-panel/scripts/os_tool/vm/bullseye/switch__master_slave.js" >> $script_file
    echo "echo \"|- 主从切换完成✅\"" >> $script_file
    echo "popd > /dev/null" >> $script_file
  fi

  # 同步文件
  read -p "需要从目标服务器更新文件到本地吗？（默认n）[y/n]: " sync_file_choice
  sync_file_choice=${sync_file_choice:-"n"}

  if [ $sync_file_choice == "y" ]; then
    if [ -z "$remote_ip" ]; then
      # 输入需要同步服务器IP
      read -p "请输入线上服务器IP: " remote_ip
      if [ -z "$remote_ip" ]; then
        echo "错误:未指定目标服务器IP"
        exit 1
      fi
    fi

    # 输入目标服务器SSH端口
    read -p "请输入线上服务器SSH端口(默认: 10022): " remote_port
    remote_port=${remote_port:-10022}

    # 输入需要同步的目录（多个用英文逗号隔开，默认为：/www/wwwroot,/www/wwwstorage,/www/backup:"
    read -p "输入需要同步的目录（多个用英文逗号隔开，默认为：/www/wwwroot,/www/wwwstorage,/www/backup）: " sync_file_dirs_input
    sync_file_dirs_input=${sync_file_dirs_input:-"/www/wwwroot,/www/wwwstorage,/www/backup"}
    IFS=',' read -ra sync_file_dirs <<< "$sync_file_dirs_input"

    # 提示"请输入需要忽略的目录（多个用英文逗号隔开，默认为：node_modules,logs,run,.git）:"
    read -p "请输入需要忽略的目录（多个用英文逗号隔开，默认为：node_modules,logs,run,.git）: " ignore_dirs_input
    ignore_dirs_input=${ignore_dirs_input:-"node_modules,logs,run,.git"}
    IFS=',' read -ra ignore_dirs <<< "$ignore_dirs_input"
    
    for sync_file_dir in "${sync_file_dirs[@]}"; do
      echo "# 从线上服务器同步${sync_file_dir}" >> $script_file
      echo "echo \"|- 开始从线上服务器同步${sync_file_dir}...\"" >> $script_file
      rsync_command="rsync -avzP --delete -e \"ssh -p $remote_port\" "
      for ignore_dir in "${ignore_dirs[@]}"; do
        rsync_command+="--exclude=${ignore_dir} "
      done
      rsync_command+="\"root@$remote_ip:${sync_file_dir}/\" \"${sync_file_dir}/\""
      rsync_command+=" &> ./sync_file.log"
      echo $rsync_command >> $script_file
      echo "echo \"|- 从线上服务器同步${sync_file_dir}完成✅\"" >> $script_file
      echo "" >> $script_file
    done
  fi

  # 开启定时任务
  echo "# 开启定时任务" >> $script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openCrontab 备份数据库[backupAll]" >> $script_file
  echo "echo \"|- 开启 备份数据库 定时任务完成✅\"" >> $script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openCrontab [勿删]xtrabackup-cron" >> $script_file
  echo "echo \"|- 开启 xtrabackup 定时任务完成✅\"" >> $script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openCrontab [勿删]xtrabackup-inc全量备份" >> $script_file
  echo "echo \"|- 开启 xtrabackup-inc全量备份 定时任务完成✅\"" >> $script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openCrontab [勿删]xtrabackup-inc增量备份" >> $script_file
  echo "echo \"|- 开启 xtrabackup-inc增量备份 定时任务完成✅\"" >> $script_file
  echo "" >> $script_file
  echo "# 删除authorized_keys的同步公钥" >> $script_file
  STANDBY_SYNC_PUB_PATH="/root/.ssh/standby_sync.pub"
  AUTHORIZED_KEYS_PATH="/root/.ssh/authorized_keys"
  echo "if [ -f \"$STANDBY_SYNC_PUB_PATH\" ] && grep -Fxq \"\$(cat $STANDBY_SYNC_PUB_PATH)\" $AUTHORIZED_KEYS_PATH; then" >> $script_file
  echo "   grep -Fxv \"\$(cat $STANDBY_SYNC_PUB_PATH)\" $AUTHORIZED_KEYS_PATH > /root/.ssh/temp && mv /root/.ssh/temp $AUTHORIZED_KEYS_PATH" >> $script_file
  echo "fi" >> $script_file
  echo "" >> $script_file

  # 启用rsyncd任务
  echo "# 启用rsyncd任务" >> $script_file
  pushd /www/server/jh-panel > /dev/null
  lsyncd_list=$(python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_list | jq -r .data | jq -r .list)
  names=$(echo "${lsyncd_list}" | jq -r '.[] | .name' | tr '\n' '|' | sed 's/|$//')
  echo "python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_status_batch {names:\"$names\",status:enabled}" >> $script_file
  echo "systemctl restart lsyncd" >> $script_file
  popd > /dev/null
  echo "echo \"|- 启用 rsyncd任务 完成✅\"" >> $script_file
  echo "" >> $script_file

  # 启用openresty
  echo "# 启用openresty" >> $script_file
  echo "python3 /www/server/jh-panel/plugins/openresty/index.py start" >> $script_file
  echo "echo \"|- 启动 OpenResty’ 完成✅\"" >> $script_file
  echo "" >> $script_file

  # 开启邮件通知
  echo "# 开启邮件通知" >> $script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openEmailNotify" >> $script_file
  echo "echo \"|- 开启 邮件通知 完成✅\"" >> $script_file
  echo "" >> $script_file
  echo "popd > /dev/null" >> $script_file
  echo "" >> $script_file
  echo "echo \"\"" >> $script_file

  echo "echo \"=========================服务器上线完成✅=======================\"" >> $script_file
  echo "echo \"后续操作指引：\"" >> $script_file
  echo "echo \"1. 请检查项目运行情况\"" >> $script_file
  echo "echo \"2. 切换网站DNS\"" >> $script_file
  echo "echo \"===============================================================\"" >> $script_file

  echo ""
  echo "==========================生成脚本完成✅========================"
  echo "- 脚本路径：$(pwd)/$script_file"
  echo "---------------------------------------------------------------"
  echo "请手动确认脚本内容并执行该脚本完成服务器上线操作："
  echo "vi ${script_file}"
  echo "bash ${script_file}"
  echo "上线完成后，可以在两台服务器使用mysql插件的获取Checksum功能，对比结果确保数据库的一致性"
  echo "==============================================================="
fi
