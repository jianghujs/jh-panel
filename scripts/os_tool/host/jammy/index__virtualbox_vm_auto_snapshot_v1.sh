#!/bin/bash

# VirtualBox快照定时备份脚本

# 提示用户输入要查看和设置定时任务的账号名
read -p "请输入要查看和设置定时任务的账号名： " username

# 获取虚拟机列表
vm_list=$(sudo -u $username VBoxManage list vms)

# 提示选择设置定时任务的虚拟机
echo "请选择需要设置定时任务的虚拟机："
i=1
while IFS= read -r line; do
  vm_name=$(echo "$line" | awk -F '"' '{print $2}')
  cron_exists=$(sudo -u $username crontab -l | grep -c "$vm_name")
  if [ "$cron_exists" -eq 1 ]; then
    echo "$i. $vm_name ✔"
  else
    echo "$i. $vm_name"
  fi
  i=$((i+1))
done <<< "$vm_list"

# 读取用户选择的虚拟机
read -p "请输入虚拟机的编号： " vm_index

# 获取选择的虚拟机名称
vm_name=$(echo "$vm_list" | awk -v vm_index="$vm_index" 'NR==vm_index{print $1}' | awk -F '"' '{print $2}')

# 替换虚拟机名称中的括号为下划线，并去除空格
script_vm_name=$(echo "$vm_name" | sed 's/[( )]/_/g' | tr -d ' ')

# 检查是否已设置定时任务
cron_exists=$(sudo -u $username crontab -l | grep -c "$script_vm_name")

if [ "$cron_exists" -eq 1 ]; then
  current_task=$(sudo -u $username crontab -l | grep "$script_vm_name")
  current_cron=$(sudo -u $username crontab -l | grep "$script_vm_name" | awk '{print $1}')
  echo "已经设置过定时任务了，当前定时任务为："
  echo "$current_task"

  # 提示用户选择操作
  echo "请选择要执行的操作："
  echo "1. 修改定时任务"
  echo "2. 删除定时任务"
  read -p "请输入选项： " choice

  case $choice in
    1)
      # 读取备份计划cron，默认为当前设置的cron
      read -p "请输入新的备份计划cron（默认为当前设置的cron：$current_cron）： " cron
      cron=${cron:-"$current_cron"}

      # 创建备份脚本
      backup_script="/opt/script/vboxautosnapshot_$script_vm_name.sh"
      echo "#!/bin/bash" > "$backup_script"
      echo "timestamp=\$(date +%Y%m%d%H%M%S)" >> "$backup_script"
      echo "sudo -u $username VBoxManage snapshot \"$vm_name\" take \"backup-\$timestamp\"" >> "$backup_script"
      chmod +x "$backup_script"

      # 创建临时crontab文件
      temp_crontab=$(mktemp)

      # 将现有的crontab导出到临时文件
      sudo -u $username crontab -l > "$temp_crontab"

      # 添加或替换定时任务
      sed -i "/$script_vm_name/d" "$temp_crontab"
      echo "$cron $backup_script" >> "$temp_crontab"

      # 导入更新后的crontab
      sudo -u $username crontab "$temp_crontab"

      # 删除临时文件
      rm "$temp_crontab"

      echo "定时任务修改成功！"
      ;;
    2)
      # 创建临时crontab文件
      temp_crontab=$(mktemp)

      # 将现有的crontab导出到临时文件，并删除对应的定时任务行
      sudo -u $username crontab -l | sed "/$script_vm_name/d" > "$temp_crontab"

      # 导入更新后的crontab
      sudo -u $username crontab "$temp_crontab"

      # 删除临时文件
      rm "$temp_crontab"

      echo "定时任务删除成功！"
      ;;
    *)
      echo "无效的选项"
      ;;
  esac
else
  # 读取备份计划cron，默认为每天2点
  read -p "请输入备份计划cron（默认为每天2点：0 2 * * *）： " cron
  cron=${cron:-"0 2 * * *"}

  # 确保目录存在
  script_dir="/opt/script"
  if [ ! -d "$script_dir" ]; then
    sudo mkdir -p "$script_dir"
    sudo chown $username "$script_dir"
  fi

  # 创建备份脚本
  backup_script="$script_dir/vboxautosnapshot_$script_vm_name.sh"
  echo "#!/bin/bash" > "$backup_script"
  echo "timestamp=\$(date +%Y%m%d%H%M%S)" >> "$backup_script"
  echo "sudo -u $username VBoxManage snapshot \"$vm_name\" take \"backup-\$timestamp\"" >> "$backup_script"
  chmod +x "$backup_script"

  # 创建临时crontab文件
  temp_crontab=$(mktemp)

  # 将现有的crontab导出到临时文件
  sudo -u $username crontab -l > "$temp_crontab"

  # 添加定时任务
  echo "$cron $backup_script" >> "$temp_crontab"

  # 导入更新后的crontab
  sudo -u $username crontab "$temp_crontab"

  # 删除临时文件
  rm "$temp_crontab"

  echo "定时任务设置成功！"
fi


