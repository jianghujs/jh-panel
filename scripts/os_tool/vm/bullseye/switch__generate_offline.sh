#!/bin/bash
script_file="/tmp/offline.sh"

read -p "确定生成服务器下线（包括停止xtrabackup增量备份、xtrabackup、mysqldump定时任务、停止邮件通知）的脚本文件${script_file}吗？（默认y）[y/n]: " choice
choice=${choice:-"y"}

echo "" > $script_file

if [ $choice == "y" ]; then
  echo "pushd /www/server/jh-panel > /dev/null" >> $script_file
  echo "" >> $script_file
  echo "# 关闭定时任务" >> $script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py closeCrontab 备份数据库[backupAll]" >> $script_file
  echo "echo \"|- 关闭 备份数据库 定时任务完成✅\"" >> $script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py closeCrontab [勿删]xtrabackup-cron" >> $script_file
  echo "echo \"|- 关闭 xtrabackup 定时任务完成✅\"" >> $script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py closeCrontab [勿删]xtrabackup-inc全量备份" >> $script_file
  echo "echo \"|- 关闭 xtrabackup-inc全量备份 定时任务完成✅\"" >> $script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py closeCrontab [勿删]xtrabackup-inc增量备份" >> $script_file
  echo "echo \"|- 关闭 xtrabackup-inc增量备份 定时任务完成✅\"" >> $script_file
  echo "" >> $script_file
  echo "# 配置同步公钥到authorized_keys" >> $script_file
  STANDBY_SYNC_PUB_PATH="/root/.ssh/standby_sync.pub"
  AUTHORIZED_KEYS_PATH="/root/.ssh/authorized_keys"
  echo "if [ -f \"$STANDBY_SYNC_PUB_PATH\" ] && ! grep -Fxq \"\$(cat $STANDBY_SYNC_PUB_PATH)\" $AUTHORIZED_KEYS_PATH; then" >> $script_file
  echo "  cat \"$STANDBY_SYNC_PUB_PATH\" >> $AUTHORIZED_KEYS_PATH" >> $script_file
  echo "fi" >> $script_file
  echo "" >> $script_file
  echo "# 关闭rsyncd任务" >> $script_file
  pushd /www/server/jh-panel > /dev/null
  lsyncd_list=$(python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_list | jq -r .data | jq -r .list)
  names=$(echo "${lsyncd_list}" | jq -r '.[] | .name' | tr '\n' '|' | sed 's/|$//')
  echo "python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_status_batch {names:\"$names\",status:disabled}" >> $script_file
  popd > /dev/null
  echo "echo \"|- 关闭 rsyncd任务 完成✅\"" >> $script_file
  echo "" >> $script_file
  echo "# 关闭openresty" >> $script_file
  echo "python3 /www/server/jh-panel/plugins/openresty/index.py stop" >> $script_file
  echo "echo \"|- 关闭 OpenResty’ 完成✅\"" >> $script_file
  echo "" >> $script_file
  echo "# 关闭邮件通知" >> $script_file
  echo "python3 /www/server/jh-panel/scripts/switch.py closeEmailNotify" >> $script_file
  echo "echo \"|- 关闭 邮件通知 完成✅\"" >> $script_file
  echo "" >> $script_file
  echo "popd > /dev/null" >> $script_file
  echo "" >> $script_file
  echo "echo \"=========================服务器下线完成✅=======================\"" >> $script_file
  echo "echo \"后续操作指引：请在备用机上线后启用当前环境NAS的同步任务\"" >> $script_file
  echo "echo \"===============================================================\"" >> $script_file

  echo ""
  echo "==========================生成脚本完成✅========================"
  echo "- 脚本路径：$(pwd)/$script_file"
  echo "---------------------------------------------------------------"
  echo "请手动确认脚本内容并执行该脚本完成服务器下线操作："
  echo "vi ${script_file}"
  echo "bash ${script_file}"
  echo "==============================================================="
fi
