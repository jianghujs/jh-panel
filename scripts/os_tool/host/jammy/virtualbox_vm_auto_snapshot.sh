#!/bin/bash

# VirtualBox快照定时备份脚本

# 提示用户输入要查看和设置定时任务的账号名
read -p "请输入要查看和设置定时任务的账号名： " username

while true; do
  # 获取虚拟机列表
  vm_list=$(sudo -u $username VBoxManage list vms)

  # 提示选择设置定时任务的虚拟机
  echo "请选择需要设置定时任务的虚拟机："
  i=1
  while IFS= read -r line; do
    vm_name=$(echo "$line" | awk -F '"' '{print $2}')
    # 替换虚拟机名称中的括号为下划线，并去除空格
    script_vm_name=$(echo "$vm_name" | sed -e 's/[(]/_/g' -e 's/[)]//g' -e 's/\[.*\]//g' | tr '[:upper:]' '[:lower:]')
    
    cron_exists=$(sudo -u $username crontab -l | grep -E -c "^[0-9*]+\s+[0-9*]+\s+[0-9*]+\s+[0-9*]+\s+[0-9*]+\s+/opt/script/vboxautosnapshot_$(sed 's/[][()]/\\&/g' <<< "$script_vm_name").sh$")

    if [ "$cron_exists" -eq 1 ]; then
      echo "$i. $vm_name ✔"
    else
      echo "$i. $vm_name"
    fi
    i=$((i+1))
  done <<< "$vm_list"

    # 读取用户选择的虚拟机
  read -p "请输入虚拟机的编号（输入 q 退出）： " vm_index

  if [ "$vm_index" = "q" ]; then
    break
  fi

  # 获取选择的虚拟机名称
  vm_name=$(echo "$vm_list" | awk -v vm_index="$vm_index" 'NR==vm_index{print $1}' | awk -F '"' '{print $2}')

  # 替换虚拟机名称中的括号为下划线，并去除空格
  script_vm_name=$(echo "$vm_name" | sed -e 's/[(]/_/g' -e 's/[)]//g' -e 's/\[.*\]//g' | tr '[:upper:]' '[:lower:]')
  
  # 检查是否已设置定时任务
  cron_exists=$(sudo -u $username crontab -l | grep -E -c "^[0-9*]+\s+[0-9*]+\s+[0-9*]+\s+[0-9*]+\s+[0-9*]+\s+/opt/script/vboxautosnapshot_$(sed 's/[][()]/\\&/g' <<< "$script_vm_name").sh$")


  if [ "$cron_exists" -eq 1 ]; then
    current_task=$(sudo -u $username crontab -l | grep "$script_vm_name")
    current_cron=$(echo "$current_task" | sed 's/\/.*//')
    echo "已经设置过定时任务了，当前定时任务为："

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
        temp_crontab=$(sudo -u $username bash -c 'mktemp')

        # 将现有的crontab导出到临时文件
        sudo -u $username bash -c "crontab $temp_crontab"

        # 添加或替换定时任务
        sed -i "/$script_vm_name/d" "$temp_crontab"
        sudo -u $username bash -c "echo '$cron $backup_script' >> $temp_crontab"

        # 导入更新后的crontab
        sudo -u $username crontab "$temp_crontab"

        # 删除临时文件
        sudo -u $username rm "$temp_crontab"

        echo "定时任务修改成功！"
        ;;
      2)
        # 创建临时crontab文件
        temp_crontab=$(sudo -u $username bash -c 'mktemp')
        # 将现有的crontab导出到临时文件，并删除对应的定时任务行
        sudo -u $username bash -c "crontab -l | sed \"/$script_vm_name/d\" >> \"$temp_crontab\""
        
        # 导入更新后的crontab
        sudo -u $username crontab "$temp_crontab"

        # 删除临时文件
        sudo -u $username rm "$temp_crontab"

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
    echo "sudo -u $username VBoxManage snapshot \"$vm_name\" take \"auto-snapshot-\$timestamp\"" >> "$backup_script"

    # 添加清理旧快照的代码
    echo "snapshots=\$(sudo -u $username VBoxManage snapshot \"$vm_name\" list --machinereadable | grep -o 'auto-snapshot-[0-9]\{14\}')" >> "$backup_script"
    echo "IFS=$'\n' snapshots=(\$snapshots)" >> "$backup_script"
    echo "snapshots=(\$(printf '%s\n' \"\${snapshots[@]}\" | sort -r))" >> "$backup_script"
    echo "for ((i=0; i<\${#snapshots[@]}; i++)); do" >> "$backup_script"
    echo "  snapshot=\${snapshots[i]}" >> "$backup_script"
    echo "  snapshot_timestamp=\${snapshot:14}" >> "$backup_script"
    echo "  snapshot_date=\${snapshot_timestamp:0:8}" >> "$backup_script"
    echo "  snapshot_time=\${snapshot_timestamp:8}" >> "$backup_script"
    echo "  snapshot_datetime=\$(date -d \"\${snapshot_date:0:4}-\${snapshot_date:4:2}-\${snapshot_date:6:2} \${snapshot_time:0:2}:\${snapshot_time:2:2}:\${snapshot_time:4:2}\")" >> "$backup_script"
    echo "  snapshot_seconds=\$(date -d \"\$snapshot_datetime\" +%s)" >> "$backup_script"
    echo "  current_seconds=\$(date +%s)" >> "$backup_script"
    echo "  age_days=\$(( (current_seconds - snapshot_seconds) / 86400 ))" >> "$backup_script"
    echo "  if ((age_days > 3 && (i < 1 || snapshot_date != \${snapshots[i-1]:14:8}))); then" >> "$backup_script"
    echo "    continue" >> "$backup_script"
    echo "  fi" >> "$backup_script"
    echo "  if ((age_days > 10)); then" >> "$backup_script"
    echo "    sudo -u $username VBoxManage snapshot \"$vm_name\" delete \"\$snapshot\"" >> "$backup_script"
    echo "  fi" >> "$backup_script"
    echo "done" >> "$backup_script"
    chmod +x "$backup_script"

    # 创建临时crontab文件
    temp_crontab=$(sudo -u $username bash -c 'mktemp')


    # 将现有的crontab导出到临时文件
    sudo -u $username bash -c "crontab -l > $temp_crontab"
    
    # 添加定时任务
    sudo -u $username bash -c "echo '$cron $backup_script' >> $temp_crontab"
    
    # 导入更新后的crontab
    sudo -u $username crontab "$temp_crontab"
    
    # 删除临时文件
    sudo rm "$temp_crontab"

    echo "定时任务设置成功！"
  fi
done

