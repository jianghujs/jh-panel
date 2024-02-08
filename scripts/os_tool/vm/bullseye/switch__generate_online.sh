#!/bin/bash
script_file="/tmp/online.sh"


echo "-----------------------"
echo "即将生成服务器上线脚本到${script_file}，包含内容如下："
echo "1. （可选）检查数据一致性"
echo "2. （可选）同步服务器文件"
echo "3. （可选）执行xtrabackup增量恢复"
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
  
  read -p "请输入本地服务器外网IP: " local_ip
  if [ -z "$local_ip" ]; then
    echo "错误:未指定本地服务器外网IP"
    exit 1
  fi
  echo "export LOCAL_IP=$local_ip" >> $script_file

  read -p "请输入备用服务器外网IP: " remote_ip
  if [ -z "$remote_ip" ]; then
    echo "错误:未指定备用服务器外网IP"
    exit 1
  fi
  echo "export REMOTE_IP=$remote_ip" >> $script_file

  echo "" > $script_file

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
