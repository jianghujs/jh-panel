#!/bin/bash

# 函数：将 CIDR 格式的子网掩码转换为点分十进制格式
cidr_to_netmask() {
  local i mask=""
  local full_octets=$(($1/8))
  local partial_octet=$(($1%8))

  for ((i=0;i<4;i+=1)); do
    if [ $i -lt $full_octets ]; then
      mask+="255"
    elif [ $i -eq $full_octets ]; then
      mask+=$((256 - 2**(8-$partial_octet)))
    else
      mask+="0"
    fi
    test $i -lt 3 && mask+="."
  done

  echo $mask
}

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
current_ip=$(ip -4 addr show $iface | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n1)
current_cidr=$(ip -o -f inet addr show $iface | awk -F '/' '{print $2}' | awk '{print $1}')
current_netmask=$(cidr_to_netmask $current_cidr)
current_netmask=${current_netmask:-255.255.255.0}
current_gateway=$(ip route | grep default | grep -oP '(?<=via\s)\d+(\.\d+){3}')

# 获取用户输入的网络配置，如果用户没有输入，那么使用当前的配置
read -p "输入静态 IP 地址（默认为$current_ip）： " ip_addr
ip_addr=${ip_addr:-$current_ip}

read -p "输入子网掩码（默认为$current_netmask）： " netmask
netmask=${netmask:-$current_netmask}

read -p "输入默认网关（默认为$current_gateway）： " gateway
gateway=${gateway:-$current_gateway}

default_dns="8.8.8.8 8.8.4.4"
read -p "输入 DNS 服务器（空格分隔，默认为$default_dns）： " dns_servers
dns_servers=${dns_servers:-$default_dns}

# 创建网络配置文件的备份
cp /etc/network/interfaces /etc/network/interfaces.bak
echo "已创建网络配置文件的备份：/etc/network/interfaces.bak"

# 检查网络配置文件中是否已经存在对应接口的配置
if grep -q "iface enp0s3 inet dhcp" /etc/network/interfaces; then
  sed -i "/iface $iface inet dhcp/d" /etc/network/interfaces
fi
if grep -q "iface $iface inet static" /etc/network/interfaces; then
  # 存在，直接替换
  sed -i "/iface $iface inet static/,+4d" /etc/network/interfaces
else
  # 不存在，添加新的配置
  echo "" >> /etc/network/interfaces
fi

# 写入新的网络配置
echo "iface $iface inet static" >> /etc/network/interfaces
echo "address $ip_addr" >> /etc/network/interfaces
echo "netmask $netmask" >> /etc/network/interfaces
echo "gateway $gateway" >> /etc/network/interfaces
echo "dns-nameservers $dns_servers" >> /etc/network/interfaces

# 重新启动网络服务以应用新的配置
/etc/init.d/networking restart

ifup $iface

echo "网络配置已成功更新。"