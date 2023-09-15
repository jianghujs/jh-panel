#!/bin/bash
set -e
# 让用户输入用户名，如果没有输入则使用默认值
read -p "请输入虚拟机所在用户：" username

while true; do
    # 列出虚拟机列表
    echo "虚拟机列表："
    vm_list=$(sudo -u $username VBoxManage list vms)
    i=1
    while IFS= read -r line; do
        vm_name=$(echo "$line" | awk -F '"' '{print $2}')
        echo "$i. $vm_name"
        i=$((i+1))
    done <<< "$vm_list"

    # 让用户选择要扩容的虚拟机
    read -p "请输入要扩容的虚拟机编号（输入 q 退出）：" vm_index

    if [ "$vm_index" = "q" ]; then
        break
    fi

    if [ "$vm_index" != "q" ]; then
        # 获取选择的虚拟机名称
        vm_name=$(echo "$vm_list" | awk -v vm_index="$vm_index" 'NR==vm_index{print $1}' | awk -F '"' '{print $2}')

        # 查询虚拟机使用的虚拟硬盘文件
        vm_disk=$(sudo -u $username VBoxManage showvminfo "$vm_name" --machinereadable | grep '.vdi\|.vmdk\|.vhd' | awk -F '=' '{print $2}' | tr -d '"')

        # 判断硬盘是否在Snapshots目录下
        if [[ $vm_disk == *"/Snapshots/"* ]]; then
            echo "当前虚拟机存在快照点，为保证数据完整，请将虚拟机最新快照点clone出一个新的虚拟机，在新虚拟机上进行扩容操作"
        else            
            # 获取当前硬盘大小
            current_disk_size=$(sudo -u $username VBoxManage showhdinfo "$vm_disk" | grep "Capacity" | awk '{print $2}')
            echo "当前硬盘大小（单位MB）：${current_disk_size}"
            read -p "请输入新硬盘大小（单位MB）：" disk_size
            disk_name=$(basename "$vm_disk")
            disk_path=$(dirname "$vm_disk")

            # 判断输入的大小是否小于当前硬盘大小
            if (( disk_size < current_disk_size )); then
                echo "新硬盘大小不能小于原硬盘大小"
                continue
            fi
            
            # 提示是否需要进行备份虚拟硬盘
            read -p "是否需要备份虚拟硬盘？（默认y）[y/n]: " backup_choice
            backup_choice=${backup_choice:-"y"}
            
            if [ $backup_choice == "y" ]; then
                disk_bak="${disk_path}/${disk_name}_$(date +%y%m%d%H%M%S)_bak.vdi"
                echo "正在备份到${disk_bak}..."
                sudo -u $username VBoxManage clonehd "$vm_disk" "$disk_bak" --format VDI
                echo "备份完成✅"
            fi
            
            read -p "确定要扩容${vm_disk}到${disk_size}MB吗？（默认y）[y/n]: " resize_choice
            resize_choice=${resize_choice:-"y"}
        
            if [ $resize_choice == "y" ]; then
                echo "正在扩容${vm_disk}至${disk_size}M..."
                sudo -u $username VBoxManage modifyhd "$vm_disk" --resize $disk_size
                echo "扩容完成✅"
            fi
        fi
    fi
done
