#!/bin/bash
set -e

# 确认清空分区表
read -p "确定要清空重新生成分区吗？可能会丢失硬盘数据，请确定已经做好数据备份！（默认n）[y/n]" confirm
confirm=${confirm:-n}
if [ "$confirm" != "y" ]; then
    exit
fi

# 获取总硬盘大小
total_size=$(fdisk -l /dev/sda | grep "Disk /dev/sda" | cut -d ',' -f1 | cut -d ' ' -f3)
total_size=$(($total_size*1024))

echo "total_size:${total_size}"
# 获取extended分区大小
read -p "请输入extended分区大小？（单位MB，默认975MB）：" extended_size
extended_size=${extended_size:-975}

# 获取swap分区大小
read -p "请输入swap分区大小？（单位MB，默认975MB）：" swap_size
swap_size=${swap_size:-975}

# 计算主分区大小
default_primary_size=$(($total_size - $extended_size - $swap_size))
read -p "请输入主分区大小？（单位MB，默认${default_primary_size}MB）：" primary_size
primary_size=${primary_size:-$default_primary_size}

# 调整分区表
echo "开始调整分区表..."
fdisk /dev/sda <<EOF
d


d


d

n
p
1

+${primary_size}M
n
e
2

+${extended_size}M
n
l


t
5
swap
w
EOF

# 更新/etc/fstab
swap_uuid=$(blkid -s UUID -o value /dev/sda5)
sed -i "/swap/ s/UUID=[^ ]*/UUID=${swap_uuid}/g" /etc/fstab
echo "更新/etc/fstab完成✅"

echo ""
echo "===========================分区调整完成✅=========================="
fdisk -l /dev/sda
echo ""
echo "---------------------------后续操作指引❗❗----------------------------"
echo "请重启系统后执行“服务器扩容-扩容步骤2”脚本"
echo "====================================================================="

# 重启提示
read -p "要重启系统吗？（默认y）[y/n]" reboot_confirm
reboot_confirm=${reboot_confirm:-y}
if [ "$reboot_confirm" = "y" ]; then
    reboot
fi


