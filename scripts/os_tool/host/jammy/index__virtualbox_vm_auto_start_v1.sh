#!/bin/bash
echo "开始配置 Debian 开机自启动虚拟机..."

# 让用户输入用户名和用户组，如果没有输入则使用默认值
read -p "请输入虚拟机所在用户：" username

read -p "请输入虚拟机所在用户组：" usergroup

# 创建自启动服务
read -p "请输入你的虚拟机名：" original_vmname

# 将虚拟机名中的括号替换为下划线以创建服务名和脚本文件名
vmname=${original_vmname//\(/_}
vmname=${vmname//\)/}

# 确定服务名和脚本文件名
servicename="vboxautostart_${vmname}"
scriptname="${servicename}.sh"

# 备份原有的 /etc/default/virtualbox 文件
if [ -f "/etc/default/virtualbox" ]; then
    cp /etc/default/virtualbox /etc/default/virtualbox.bak
    echo "已备份 /etc/default/virtualbox 文件为 /etc/default/virtualbox.bak"
fi

# 在 /etc/default/virtualbox 中添加配置
if ! grep -q "VBOXAUTOSTART_DB=/etc/vbox" /etc/default/virtualbox; then
    echo -e "\n# Auto Starting VMs\n\nVBOXAUTOSTART_DB=/etc/vbox\nVBOXAUTOSTART_CONFIG=/etc/vbox/autostart.cfg\n" >> /etc/default/virtualbox
    echo "已在 /etc/default/virtualbox 中添加配置"
fi

# 备份原有的 /etc/systemd/system/${servicename}.service 文件
if [ -f "/etc/systemd/system/${servicename}.service" ]; then
    cp /etc/systemd/system/${servicename}.service /etc/systemd/system/${servicename}.service.bak
    echo "已备份 /etc/systemd/system/${servicename}.service 文件为 /etc/systemd/system/${servicename}.service.bak"
fi

# 新建 /etc/systemd/system/${servicename}.service 文件
cat > /etc/systemd/system/${servicename}.service << EOF
[Unit]
Description=${original_vmname}
After=network.target virtualbox.service
Before=runlevel2.target shutdown.target

[Service]
User=${username}
Group=${usergroup}
Type=forking
Restart=no
TimeoutSec=5min
IgnoreSIGPIPE=no
KillMode=process
GuessMainPid=no
RemainAfterExit=yes
ExecStart=/usr/bin/VBoxManage startvm "${original_vmname}" --type headless
ExecStop=/usr/bin/VBoxManage controlvm "${original_vmname}"  acpipowerbutton

[Install]
WantedBy=multi-user.target
EOF

echo "已创建 /etc/systemd/system/${servicename}.service 文件"

# 设置开机启动
systemctl daemon-reload
systemctl enable ${servicename}

echo "已设置开机启动服务 ${servicename}"
echo "配置完成！"
