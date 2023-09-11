#!/bin/bash

# 获取所有非本地回环的网络接口
interfaces=( $(ip link | awk -F: '$0 !~ "lo|vir|^[^0-9]"{print $2;getline}') )

# 列出所有的网络接口
echo "可用的网络接口："
for i in "${!interfaces[@]}"; do
  echo "$((i+1)): ${interfaces[$i]}"
done

# 提示用户选择一个接口，如果用户没有输入，那么默认选择第一个接口
read -p "输入你想要配置的接口的编号（默认为1）： " selection
if [[ -z $selection ]]; then
  iface=${interfaces[0]}
else
  if [[ $selection -ge 1 && $selection -le ${#interfaces[@]} ]]; then
    iface=${interfaces[$((selection-1))]}
  else
    echo "无效的选择。默认选择第一个接口。"
    iface=${interfaces[0]}
  fi
fi
echo "已选择接口：$iface"

# 获取当前的网络配置
current_ip=$(ip -4 addr show $iface | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
current_gateway=$(ip route | grep default | grep -oP '(?<=via\s)\d+(\.\d+){3}' | head -n 1)

# 获取用户输入的网络配置，如果用户没有输入，那么使用当前的配置
read -p "输入静态 IP 地址（默认为$current_ip）： " ip_addr
ip_addr=${ip_addr:-$current_ip}

read -p "输入默认网关（默认为$current_gateway）： " gateway
gateway=${gateway:-$current_gateway}

default_dns="8.8.8.8,8.8.4.4"
read -p "输入 DNS 服务器（逗号分隔，默认为$default_dns）： " dns_servers
dns_servers=${dns_servers:-$default_dns}

# 创建网络配置文件的备份
cp /etc/netplan/01-network-manager-all.yaml /etc/netplan/01-network-manager-all.yaml.bak
echo "已创建网络配置文件的备份：/etc/netplan/01-network-manager-all.yaml.bak"

# 生成新的网络配置
cat > /etc/netplan/01-network-manager-all.yaml << EOF
network:
  version: 2
  renderer: NetworkManager
  ethernets:
    $iface:
      addresses:
        - $ip_addr/24
      routes:
        - to: default
          via: $gateway
      nameservers:
        addresses: [$dns_servers]
EOF

# 应用新的网络配置
netplan apply

echo "网络配置已成功更新。"

