#!/bin/bash
source /www/server/jh-panel/scripts/util/msg.sh

# 安装pygments
if ! command -v pygmentize &> /dev/null; then
    echo "pygmentize未安装，正在尝试自动安装..."
    apt-get update
    apt-get install python3-pygments -y
    if ! command -v pygmentize &> /dev/null; then
        echo "安装pygmentize失败，请手动安装后再运行脚本。"
        exit 1
    fi
fi

tmp_prepare_script_file="/tmp/online__prepare.sh"
tmp_online_script_file="/tmp/online__online.sh"
tmp_merge_file="/tmp/online_merge.sh"
script_file="/tmp/online.sh"

echo -ne "\033[1;31m提示：\033[0m 为减少服务中断时间，请确保\033[1m程序（JianghuJS、Docker）\033[0m和\033[1m配置\033[0m正确后执行上线操作，确定执行吗？（默认n）[y/n]: " 
read check_choice
check_choice=${check_choice:-n}
if [ $check_choice != "y" ]; then
  echo "已取消执行上线操作"
  exit 0
fi

echo "-----------------------"
echo "即将生成服务器上线脚本到${script_file}，包含内容如下："
echo "1. ? 确认执行预备上线操作"
echo "2. （可选）执行xtrabackup增量恢复"
echo "3. （可选）检查数据一致性"
echo "4. （可选）同步服务器文件"
echo "5. （可选）恢复网站数据"
echo "6. （可选）恢复插件数据"
echo "7. ? 确认上线操作"
echo "8. （可选）主从切换"
echo "9. 启动xtrabackup增量备份、xtrabackup、mysqldump、续签Let's Encrypt证书定时任务"
echo "10. 从authorized_keys删除同步公钥"
echo "11. 启动rsyncd任务"
echo "12. 启动Openresty"
echo "13. 开启邮件通知"
echo "-----------------------"
prompt "确认生成吗？（默认y）[y/n]: " choice "y"

if [ $choice == "y" ]; then
  pushd /www/server/jh-panel > /dev/null
  # 清空文件并添加依赖
  echo "source /www/server/jh-panel/scripts/util/msg.sh" > $tmp_prepare_script_file
  echo "source /www/server/jh-panel/scripts/util/msg.sh" > $tmp_online_script_file
  echo "source /www/server/jh-panel/scripts/util/msg.sh" > $tmp_merge_file
  echo "source /www/server/jh-panel/scripts/util/msg.sh" > $script_file

  echo "log_file=\"/tmp/online.log\"" >> $tmp_prepare_script_file
  echo "echo \"\" > \$log_file" >> $tmp_prepare_script_file
  echo "" >> $tmp_prepare_script_file

  # 获取本地服务器IP
  default_local_ip=$(python3 /www/server/jh-panel/tools.py getPanelIp)
  local_ip_tip="请输入本地服务器IP"
  if [ -n "$default_local_ip" ]; then
    local_ip_tip+="（默认为：${default_local_ip}）"
  fi
  prompt "$local_ip_tip: " local_ip $default_local_ip
  if [ -z "$local_ip" ]; then
    show_error "错误:未指定本地服务器IP"
    exit 1
  fi
  echo "export LOCAL_IP=$local_ip" >> $tmp_prepare_script_file

  # 获取备用服务器IP
  default_remote_ip=$(python3 /www/server/jh-panel/tools.py getStandbyIp)
  remote_ip_tip="请输入备用服务器IP"
  if [ -n "$default_remote_ip" ]; then
    remote_ip_tip+="（默认为：${default_remote_ip}）"
  fi
  prompt "$remote_ip_tip: " remote_ip $default_remote_ip
  if [ -z "$remote_ip" ]; then
    show_error "错误:未指定备用服务器IP"
    exit 1
  fi
  echo "export REMOTE_IP=$remote_ip" >> $tmp_prepare_script_file

  echo "" >> $tmp_prepare_script_file


  prerepre_online_opts=""
  # 增量恢复
  echo "pushd /www/server/jh-panel > /dev/null" >> $tmp_prepare_script_file
  echo "" >> $tmp_prepare_script_file
  prompt "需要执行增量恢复吗？（默认n）[y/n]: " xtrabackup_inc_restore_choice "n"

  if [ $xtrabackup_inc_restore_choice == "y" ]; then
    prerepre_online_opts+="- xtrabackup增量恢复\n"
    echo "# 执行xtrabackup增量恢复" >> $tmp_prepare_script_file
    pushd /www/server/jh-panel > /dev/null
    recovery_script=$(python3 /www/server/jh-panel/plugins/xtrabackup-inc/index.py get_inc_recovery_cron_script | jq -r .data)
    popd > /dev/null
    echo "${recovery_script}" >> $tmp_prepare_script_file
    echo "show_info \"|- xtrabackup增量恢复完成✅\"" >> $tmp_prepare_script_file
    echo "" >> $tmp_prepare_script_file
  fi

  # 主备服务器checksum检查
  prompt "需要检查主备服务器的checksum吗？（默认y）[y/n]: " checksum_choice "y"

  if [ $checksum_choice == "y" ]; then
    prerepre_online_opts+="- 检查主备服务器checksum\n"
    echo "# 检查主备服务器checksum" >> $tmp_prepare_script_file
    echo "echo \"|- 检查主备服务器checksum...\"" >> $tmp_prepare_script_file
    echo "pushd /www/server/jh-panel/scripts/os_tool/vm/${TOOL_DIR}/ > /dev/null"  >> $tmp_prepare_script_file
    echo "npm i" >> $tmp_prepare_script_file
    echo "node /www/server/jh-panel/scripts/os_tool/vm/${TOOL_DIR}/monitor__export_mysql_checksum_compare.js" >> $tmp_prepare_script_file
    echo "popd > /dev/null" >> $tmp_prepare_script_file
    echo "source /tmp/compare_checksum_diff" >> $tmp_prepare_script_file
    echo "if [[ -n \$checksum_diff ]]; then" >> $tmp_prepare_script_file
    echo "  checksum_diff=\$(echo \"\$checksum_diff\" | tr ',' '\n')" >> $tmp_prepare_script_file
    echo "  echo \"|- checksum结果存在以下不同：\"" >> $tmp_prepare_script_file
    echo "  echo -e \"\033[0;31m\$checksum_diff\033[0m\"" >> $tmp_prepare_script_file
    echo "  prompt \"要忽略checksum结果继续吗？（默认n）[y/n]: \" checksum_ignore_choice \"n\"" >> $tmp_prepare_script_file
    echo "  if [ \$checksum_ignore_choice == \"n\" ]; then" >> $tmp_prepare_script_file
    echo "    show_error \"错误:数据不一致，上线终止\"" >> $tmp_prepare_script_file
    echo "    exit 1" >> $tmp_prepare_script_file
    echo "  fi" >> $tmp_prepare_script_file
    echo "fi" >> $tmp_prepare_script_file
    echo "show_info \"|- 主备服务器checksum检查完成✅\"" >> $tmp_prepare_script_file
    echo "" >> $tmp_prepare_script_file
  fi

  
  # 同步文件
  prompt "需要从目标服务器更新文件到本地吗？（默认y）[y/n]: " sync_file_choice "y"

  if [ $sync_file_choice == "y" ]; then
    prerepre_online_opts+="- 同步文件\n"
    if [ -z "$remote_ip" ]; then
      # 输入需要同步服务器IP
      prompt "请输入线上服务器IP: " remote_ip
      if [ -z "$remote_ip" ]; then
        show_error "错误:未指定目标服务器IP"
        exit 1
      fi
    fi

    # 输入目标服务器SSH端口
    prompt "请输入线上服务器SSH端口(默认: 10022): " remote_port "10022"
    
    # 输入需要同步的目录（多个用英文逗号隔开，默认为：/www/wwwroot,/www/wwwstorage,/www/backup:"
    prompt "输入需要同步的目录（多个用英文逗号隔开，默认为：/www/wwwroot,/www/wwwstorage,/www/backup）: " sync_file_dirs_input "/www/wwwroot,/www/wwwstorage,/www/backup"
    IFS=',' read -ra sync_file_dirs <<< "$sync_file_dirs_input"

    # 提示"请输入需要忽略的目录（多个用英文逗号隔开，默认为：node_modules,logs,run）:"
    prompt "请输入需要忽略的目录（多个用英文逗号隔开，默认为：node_modules,logs,run）: " ignore_dirs_input "node_modules,logs,run"
    IFS=',' read -ra ignore_dirs <<< "$ignore_dirs_input"
    
    for sync_file_dir in "${sync_file_dirs[@]}"; do
      echo "# 从线上服务器同步${sync_file_dir}" >> $tmp_prepare_script_file
      echo "echo \"|- 开始从线上服务器同步${sync_file_dir}...\"" >> $tmp_prepare_script_file
      rsync_command="rsync -avzP --delete -e \"ssh -p $remote_port\" "
      for ignore_dir in "${ignore_dirs[@]}"; do
        rsync_command+="--exclude=${ignore_dir} "
      done
      rsync_command+="\"root@$remote_ip:${sync_file_dir}/\" \"${sync_file_dir}/\""
      rsync_command+=" &> ./sync_file.log"
      echo $rsync_command >> $tmp_prepare_script_file
      echo "show_info \"|- 从线上服务器同步${sync_file_dir}完成✅\"" >> $tmp_prepare_script_file
      echo "" >> $tmp_prepare_script_file
    done
  fi


  # 恢复网站数据
  prompt "需要恢复网站配置吗？（默认n）[y/n]: " site_setting_restore_choice "n"

  if [ $site_setting_restore_choice == "y" ]; then
    prerepre_online_opts+="- 恢复网站配置\n"
    echo "# 恢复网站配置" >> $tmp_prepare_script_file
    default_site_setting_backup_dir="/www/backup/site_setting"
    prompt "请输入网站配置备份文件所在目录（默认为：${default_site_setting_backup_dir}）: " site_setting_backup_dir $default_site_setting_backup_dir
    # 获取最近的一个网站配置all文件
    site_setting_file_path=$(ls -t ${site_setting_backup_dir}/all_*.zip | head -n 1)
    if [ -z "$site_setting_file_path" ]; then
      show_error "错误:未找到网站配置备份文件"
      exit 1
    fi
    site_setting_file=$(basename ${site_setting_file_path})
    prompt "请输入网站配置备份文件名称（默认为：${site_setting_file}）: " site_setting_file_input $site_setting_file
    
    echo "site_setting_restore_tmp=/tmp/site_setting-restore" >> $tmp_prepare_script_file
    echo "unzip -o $site_setting_backup_dir/$site_setting_file -d \$site_setting_restore_tmp/ >> \$log_file" >> $tmp_prepare_script_file
    
    echo "pushd \$site_setting_restore_tmp > /dev/null" >> $tmp_prepare_script_file
    echo "python3 /www/server/jh-panel/scripts/migrate.py importSiteInfo \$(pwd)/site_info.json" >> $tmp_prepare_script_file
    echo "echo \"导入站点数据完成✅!\"" >> $tmp_prepare_script_file
    
    echo "# 合并letsencrypt.json" >> $tmp_prepare_script_file
    echo "python3 /www/server/jh-panel/scripts/migrate.py importLetsencryptOrder \$(pwd)/letsencrypt.json" >> $tmp_prepare_script_file
    echo "echo \"合并letsencrypt.json完成✅!\"" >> $tmp_prepare_script_file

    echo "# 解压合并当前目录下的web_conf.zip到/www/server/web_conf/" >> $tmp_prepare_script_file
    echo "unzip -o ./web_conf.zip -d /www/server/web_conf/ >> \$log_file" >> $tmp_prepare_script_file
    echo "echo \"恢复网站配置完成✅!\"" >> $tmp_prepare_script_file

    echo "# 重启openresty" >> $tmp_prepare_script_file
    echo "pushd /www/server/jh-panel > /dev/null" >> $tmp_prepare_script_file
    echo "python3 /www/server/jh-panel/plugins/openresty/index.py restart" >> $tmp_prepare_script_file
    echo "popd > /dev/null" >> $tmp_prepare_script_file
    echo "echo \"重启openresty完成✅!\"" >> $tmp_prepare_script_file

    echo "popd > /dev/null" >> $tmp_prepare_script_file
    echo "show_info \"|- 恢复网站配置✅\"" >> $tmp_prepare_script_file
    echo "" >> $tmp_prepare_script_file
  fi

  # 恢复插件数据
  echo "" >> $tmp_prepare_script_file
  prompt "需要恢复插件配置吗？（默认n）[y/n]: " plugin_setting_restore_choice "n"

  if [ $plugin_setting_restore_choice == "y" ]; then
    prerepre_online_opts+="- 恢复插件配置\n"
    echo "# 恢复插件配置" >> $tmp_prepare_script_file
    default_plugin_setting_backup_dir="/www/backup/plugin_setting"
    prompt "请输入插件配置备份文件所在目录（默认为：${default_plugin_setting_backup_dir}）: " plugin_setting_backup_dir $default_plugin_setting_backup_dir
    # 获取最近的一个插件配置all文件
    plugin_setting_file_path=$(ls -t ${plugin_setting_backup_dir}/all_*.zip | head -n 1)
    if [ -z "$plugin_setting_file_path" ]; then
      show_error "错误:未找到插件配置备份文件"
      exit 1
    fi
    plugin_setting_file=$(basename ${plugin_setting_file_path})
    prompt "请输入插件配置备份文件名称（默认为：${plugin_setting_file}）: " plugin_setting_file_input $plugin_setting_file
    
    echo "plugin_setting_restore_tmp=/tmp/plugin_setting-restore" >> $tmp_prepare_script_file
    echo "unzip -o $plugin_setting_backup_dir/$plugin_setting_file -d \$plugin_setting_restore_tmp/ >> \$log_file" >> $tmp_prepare_script_file
    
    echo "pushd \$plugin_setting_restore_tmp > /dev/null" >> $tmp_prepare_script_file
    echo "for zipfile in *.zip; do" >> $tmp_prepare_script_file
    echo "    filename=\$(basename \"\$zipfile\" .zip)" >> $tmp_prepare_script_file
    echo "    server_dir=/www/server/\$filename" >> $tmp_prepare_script_file
    echo "    mkdir -p \$server_dir" >> $tmp_prepare_script_file
    echo "    echo \"正在解压 \$zipfile 到 \$server_dir\"" >> $tmp_prepare_script_file
    echo "    unzip -o \"\$zipfile\" -d \"\$server_dir\" >> \$log_file" >> $tmp_prepare_script_file
    echo "done" >> $tmp_prepare_script_file

    echo "popd > /dev/null" >> $tmp_prepare_script_file
    echo "show_info \"|- 恢复插件配置✅\"" >> $tmp_prepare_script_file
    echo "" >> $tmp_prepare_script_file
  fi
  echo "popd > /dev/null" >> $tmp_prepare_script_file

  
  confirm_online_opts=""
  # 主从切换
  prompt "需要将当前数据库提升为主吗？（默认y）[y/n]: " switch_master_slave_choice "y"
  echo "pushd /www/server/jh-panel > /dev/null" >> $tmp_online_script_file
  if [ $switch_master_slave_choice == "y" ]; then
    confirm_online_opts+="- 将当前数据库提升为主\n"
    echo "# 将当前数据库提升为主" >> $tmp_online_script_file
    echo "echo \"|- 将当前数据库提升为主...\"" >> $tmp_online_script_file
    echo "pushd /www/server/jh-panel/scripts/os_tool/vm/${TOOL_DIR}/ > /dev/null"  >> $tmp_online_script_file
    echo "source /root/.bashrc" >> $tmp_online_script_file
    echo "export PATH=\"/www/server/nodejs/fnm:\$PATH\"" >> $tmp_online_script_file 
    echo "npm i" >> $tmp_online_script_file
    echo "node \"/www/server/jh-panel/scripts/os_tool/vm/${TOOL_DIR}/switch__mysql_master.js\"" >> $tmp_online_script_file
    echo "echo \"|- 将当前数据库提升为主完成✅\"" >> $tmp_online_script_file
    echo "popd > /dev/null" >> $tmp_online_script_file
  fi

  # 调整计划任务
  echo "# 调整计划任务" >> $tmp_online_script_file
  echo "echo \"|- 调整计划任务...\"" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py closeCrontab 备份数据库[backupAll]" >> $tmp_online_script_file
  echo "show_info \"|- 关闭 备份数据库 定时任务完成✅\"" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py closeCrontab [勿删]xtrabackup-cron" >> $tmp_online_script_file
  echo "show_info \"|- 关闭 xtrabackup 定时任务完成✅\"" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py closeCrontab [勿删]xtrabackup-inc全量备份" >> $tmp_online_script_file
  echo "show_info \"|- 关闭 xtrabackup-inc全量备份 定时任务完成✅\"" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py closeCrontab [勿删]xtrabackup-inc增量备份" >> $tmp_online_script_file
  echo "show_info \"|- 关闭 xtrabackup-inc增量备份 定时任务完成✅\"" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openCrontab 备份网站配置[backupAll]" >> $tmp_online_script_file
  echo "show_info \"|- 开启 备份网站配置 定时任务完成✅\"" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openCrontab 备份插件配置[backupAll]" >> $tmp_online_script_file
  echo "show_info \"|- 开启 备份插件配置 定时任务完成✅\"" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openCrontab [勿删]lsyncd实时任务定时同步" >> $tmp_online_script_file
  echo "show_info \"|- 开启 lsyncd实时任务定时同步 定时任务完成✅\"" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openCrontab [勿删]服务器报告" >> $tmp_online_script_file
  echo "show_info \"|- 开启 服务器报告 定时任务完成✅\"" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openCrontab \"[勿删]续签Let's Encrypt证书\"" >> $tmp_online_script_file
  echo "show_info \"|- 开启 续签Let's Encrypt证书 定时任务完成✅\"" >> $tmp_online_script_file
  echo "" >> $tmp_online_script_file
  echo "# 删除authorized_keys的同步公钥" >> $tmp_online_script_file
  STANDBY_SYNC_PUB_PATH="/root/.ssh/standby_sync.pub"
  AUTHORIZED_KEYS_PATH="/root/.ssh/authorized_keys"
  echo "if [ -f \"$STANDBY_SYNC_PUB_PATH\" ] && grep -Fxq \"\$(cat $STANDBY_SYNC_PUB_PATH)\" $AUTHORIZED_KEYS_PATH; then" >> $tmp_online_script_file
  echo "   grep -Fxv \"\$(cat $STANDBY_SYNC_PUB_PATH)\" $AUTHORIZED_KEYS_PATH > /root/.ssh/temp && mv /root/.ssh/temp $AUTHORIZED_KEYS_PATH" >> $tmp_online_script_file
  echo "fi" >> $tmp_online_script_file
  echo "" >> $tmp_online_script_file

  # 启用rsyncd任务
  confirm_online_opts+="- 启用rsyncd任务\n"
  echo "# 启用rsyncd任务" >> $tmp_online_script_file
  pushd /www/server/jh-panel > /dev/null
  lsyncd_list=$(python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_list | jq -r .data | jq -r .list)
  names=$(echo "${lsyncd_list}" | jq -r '.[] | .name' | tr '\n' '|' | sed 's/|$//')
  echo "python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_status_batch {names:\"$names\",status:enabled}" >> $tmp_online_script_file
  echo "systemctl restart lsyncd" >> $tmp_online_script_file
  popd > /dev/null
  echo "show_info \"|- 启用 rsyncd任务 完成✅\"" >> $tmp_online_script_file
  echo "" >> $tmp_online_script_file

  # 启用openresty
  confirm_online_opts+="- 启用Openresty\n"
  echo "# 启用openresty" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/plugins/openresty/index.py start" >> $tmp_online_script_file
  echo "show_info \"|- 启动 OpenResty’ 完成✅\"" >> $tmp_online_script_file
  echo "" >> $tmp_online_script_file

  # 开启邮件通知
  confirm_online_opts+="- 开启邮件通知\n"
  echo "# 开启邮件通知" >> $tmp_online_script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py openEmailNotify" >> $tmp_online_script_file
  echo "show_info \"|- 开启 邮件通知 完成✅\"" >> $tmp_online_script_file
  echo "" >> $tmp_online_script_file
  echo "popd > /dev/null" >> $tmp_online_script_file
  echo "" >> $tmp_online_script_file

  echo "source /root/.bashrc" >> $tmp_merge_file
  echo "source /www/server/jh-panel/scripts/util/msg.sh" >> $tmp_merge_file
  
  # 确认预上线操作
  echo "# 确认预上线操作" >> $tmp_merge_file
  echo "echo \"-------------------------\"" >> $tmp_merge_file
  echo "echo \"即将执行预上线操作，包括如下\"" >> $tmp_merge_file
  echo -e "echo -e \"$prerepre_online_opts\"" >> $tmp_merge_file
  echo "echo \"-------------------------\"" >> $tmp_merge_file
  echo "prompt \"确定要执行预上线操作吗？（默认n）[y/n]: \" confirm_prepare_online_choice \"n\"" >> $tmp_merge_file
  echo "if [ \$confirm_prepare_online_choice == \"n\" ]; then" >> $tmp_merge_file
  echo "  show_info \"已取消执行预上线操作\"" >> $tmp_merge_file
  echo "  exit 0" >> $tmp_merge_file
  echo "fi" >> $tmp_merge_file
  echo "" >> $tmp_merge_file
  cat $tmp_prepare_script_file >> $tmp_merge_file


  # 确认上线操作
  echo "# 确认上线操作" >> $tmp_merge_file
  echo "echo \"-------------------------\"" >> $tmp_merge_file
  echo "echo \"即将执行上线操作，包括如下\"" >> $tmp_merge_file
  echo -e "echo -e \"$confirm_online_opts\"" >> $tmp_merge_file
  echo "echo \"-------------------------\"" >> $tmp_merge_file
  echo "prompt \"确定要执行上线操作吗？（默认n）[y/n]: \" confirm_online_choice \"n\"" >> $tmp_merge_file
  echo "if [ \$confirm_online_choice == \"n\" ]; then" >> $tmp_merge_file
  echo "  show_info \"已取消执行上线操作\"" >> $tmp_merge_file
  echo "  exit 0" >> $tmp_merge_file
  echo "fi" >> $tmp_merge_file
  echo "" >> $tmp_merge_file
  cat $tmp_online_script_file >> $tmp_merge_file
  echo "echo \"\"" >> $tmp_merge_file

  # 合并文件
  cat $tmp_merge_file > $script_file

  echo "echo \"=========================服务器上线完成✅=======================\"" >> $script_file
  echo "echo \"后续操作指引：\"" >> $script_file
  echo "echo \"1. 请检查项目运行情况\"" >> $script_file
  echo "echo \"2. 切换网站DNS\"" >> $script_file
  echo "echo \"===============================================================\"" >> $script_file

  echo ""
  echo "==========================生成脚本完成✅========================"
  echo "- 脚本路径：$script_file"
  echo "- 脚本内容："
  show_info "---------------------------------------------------------------"
  pygmentize $script_file
  show_info "---------------------------------------------------------------"
  echo "==============================================================="
  prompt "是否执行上面的脚本？（默认n）[y/n]: " run_script_choice "n"
  if [ $run_script_choice != "y" ]; then
    show_info "已取消执行脚本"
    echo -e "\033[1;32m提示:\033[0m 您也可以手动确认脚本内容并执行该脚本完成服务器上线操作："
    echo "vi ${script_file}"
    echo "bash ${script_file}"
    exit 0
  fi
  bash $script_file
  popd > /dev/null
fi