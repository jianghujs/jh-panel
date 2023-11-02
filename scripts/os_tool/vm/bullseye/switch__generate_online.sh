#!/bin/bash
script_file="online.sh"

read -p "确定生成服务器上线（包括执行xtrabackup增量恢复、更新wwwroot目录、启动xtrabackup增量备份、xtrabackup、mysqldump定时任务、开启邮件通知）的脚本文件${script_file}吗？（默认y）[y/n]: " choice
choice=${choice:-"y"}

echo "" > $script_file

if [ $choice == "y" ]; then
  read -p "需要从目标服务器更新文件到本地吗？（默认n）[y/n]: " sync_file_choice
  sync_file_choice=${sync_file_choice:-"n"}

  if [ $sync_file_choice == "y" ]; then
    # 输入需要同步服务器IP
    read -p "请输入线上服务器IP: " remote_ip
    if [ -z "$remote_ip" ]; then
      echo "错误:未指定目标服务器IP"
      exit 1
    fi

    # 输入目标服务器SSH端口
    read -p "请输入线上服务器SSH端口(默认: 10022): " remote_port
    remote_port=${remote_port:-10022}

    # 输入需要同步的目录（多个用英文逗号隔开，默认为：/www/wwwroot,/www/wwwstorage,/www/backup:"
    read -p "输入需要同步的目录（多个用英文逗号隔开，默认为：/www/wwwroot,/www/wwwstorage,/www/backup）: " sync_file_dirs_input
    sync_file_dirs_input=${sync_file_dirs_input:-"/www/wwwroot,/www/wwwstorage,/www/backup"}
    IFS=',' read -ra sync_file_dirs <<< "$sync_file_dirs_input"
    
    for sync_file_dir in "${sync_file_dirs[@]}"; do
      echo "# 从线上服务器同步${sync_file_dir}" >> $script_file
      echo "echo \"|- 开始从线上服务器同步${sync_file_dir}...\"" >> $script_file
      echo "rsync -avzP --delete -e \"ssh -p $remote_port\" --progress \"root@$remote_ip:${sync_file_dir}/\" \"${sync_file_dir}/\"" >> $script_file
      echo "echo \"|- 从线上服务器同步${sync_file_dir}完成✅\"" >> $script_file
      echo "" >> $script_file
    done
  fi


  echo "pushd /www/server/jh-panel > /dev/null" >> $script_file
  echo "" >> $script_file
  echo "# 执行xtrabackup增量恢复" >> $script_file
  pushd /www/server/jh-panel > /dev/null
  recovery_script=$(python3 /www/server/jh-panel/plugins/xtrabackup-inc/index.py get_recovery_backup_script | jq -r .data)
  popd > /dev/null
  echo "${recovery_script}" >> $script_file
  echo "echo \"|- xtrabackup增量恢复完成✅\"" >> $script_file
  echo "" >> $script_file

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
  echo "bash ${script_file}"
  echo "==============================================================="
fi
