#!/bin/bash
echo "开始配置Debian开机自启动虚拟机..."

# 让用户输入用户名和用户组，如果没有输入则使用默认值
read -p "请输入虚拟机所在用户：" username

while true; do
# 列出虚拟机列表，并显示是否已设置自启动
echo "虚拟机列表："
vm_list=$(sudo -u $username VBoxManage list vms)
i=1
while IFS= read -r line; do
    vm_name=$(echo "$line" | awk -F '"' '{print $2}')
    # 替换虚拟机名称中的括号为下划线，并去除空格
    script_vm_name=$(echo "$vm_name" | sed -e 's/[(]/_/g' -e 's/[)]//g' -e 's/\[.*\]//g' | tr '[:upper:]' '[:lower:]')
    
    if systemctl is-active --quiet "vboxautostart_${script_vm_name}"; then
        echo "$i. $vm_name ✔"
    else
        echo "$i. $vm_name"
    fi
    i=$((i+1))
done <<< "$vm_list"

# 让用户选择要设置开机自启动的虚拟机
read -p "请输入要设置开机自启动的虚拟机编号（输入 q 退出）：" vm_index

if [ "$vm_index" = "q" ]; then
  break
fi

if [ "$vm_index" != "q" ]; then
    # 获取选择的虚拟机名称
    vm_name=$(echo "$vm_list" | awk -v vm_index="$vm_index" 'NR==vm_index{print $1}' | awk -F '"' '{print $2}')

    # 替换虚拟机名称中的括号为下划线，并去除空格
    script_vm_name=$(echo "$vm_name" | sed -e 's/[(]/_/g' -e 's/[)]//g' -e 's/\[.*\]//g' | tr '[:upper:]' '[:lower:]')

    # 检查服务是否存在来判断自启动状态
    echo "vboxautostart_${script_vm_name}"
    if systemctl is-active --quiet "vboxautostart_${script_vm_name}"; then
        echo "已设置过开机自启动，将删除自启动配置"
        sudo systemctl stop "vboxautostart_${script_vm_name}"
        sudo systemctl disable "vboxautostart_${script_vm_name}"
        sudo rm -f "/etc/systemd/system/vboxautostart_${script_vm_name}.service"
        sudo systemctl daemon-reload
        echo "自启动配置已删除，重启系统后生效"
    else
        echo "设置开机自启动..."
        sudo bash -c "cat > /etc/systemd/system/vboxautostart_${script_vm_name}.service << EOF
[Unit]
Description=VirtualBox autostart for ${vm_name}
After=network.target virtualbox.service
Before=runlevel2.target shutdown.target

[Service]
User=${username}
Group=${username}
Type=forking
Restart=no
TimeoutSec=5min
IgnoreSIGPIPE=no
KillMode=process
GuessMainPid=no
RemainAfterExit=yes
ExecStart=/usr/bin/VBoxManage startvm \"${vm_name}\" --type headless
ExecStop=/usr/bin/VBoxManage controlvm \"${vm_name}\" acpipowerbutton

[Install]
WantedBy=multi-user.target
EOF"
        sudo systemctl daemon-reload
        sudo systemctl enable "vboxautostart_${script_vm_name}"
        sudo systemctl start "vboxautostart_${script_vm_name}"
        echo "开机自启动已设置"
    fi
fi

echo "配置完成！"
done

