#!/bin/bash
# 需要root权限
if [ "$EUID" -ne 0 ]
  then echo "请以root用户运行"
  exit
fi

# 备份原始配置文件
cp /etc/systemd/logind.conf /etc/systemd/logind.conf.bak
echo "已备份配置文件"

# 检查并添加配置
if ! grep -q "^HandleLidSwitch=ignore" /etc/systemd/logind.conf; then
    echo "HandleLidSwitch=ignore" >> /etc/systemd/logind.conf
    echo "添加HandleLidSwitch配置"
fi

if ! grep -q "^HandleLidSwitchExternalPower=ignore" /etc/systemd/logind.conf; then
    echo "HandleLidSwitchExternalPower=ignore" >> /etc/systemd/logind.conf
    echo "添加HandleLidSwitchExternalPower配置"
fi

if ! grep -q "^IdleAction=ignore" /etc/systemd/logind.conf; then
    echo "IdleAction=ignore" >> /etc/systemd/logind.conf
    echo "添加IdleAction配置"
fi

if ! grep -q "^IdleActionSec=0min" /etc/systemd/logind.conf; then
    echo "IdleActionSec=0min" >> /etc/systemd/logind.conf
    echo "添加IdleActionSec配置"
fi

# 重启服务
# systemctl restart systemd-logind.service
# echo "服务重启完成"

echo "等待重启后生效"
