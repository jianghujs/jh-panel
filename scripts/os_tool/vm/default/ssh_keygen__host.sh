#!/bin/bash

# 备份文件
backup_file() {
    local file=$1
    if [ -f "$file" ]; then
        local backup_file="${file}_$(date +%Y%m%d%H%M%S).bak"
        cp $file $backup_file
        echo "已备份文件：$backup_file"
    fi
}

# 获取本机IP
get_local_ip() {
    ip=$(hostname -I | awk '{print $1}')
    echo $ip
}

# 生成密钥文件名
generate_key_filename() {
    local domain=$1
    filename=$(echo $domain | awk -F. '{if (NF > 2) print $(NF-2); else print $1}')
    echo $filename
}

# 配置ssh
config_ssh() {
    local domain=$1
    local filename=$2
    config_file="$HOME/.ssh/config"

    # 删除原有配置
    if [ -f "$config_file" ]; then
		sed -i "/Host $domain/,+6d" $config_file
    fi
	
    
    # 添加新配置
    echo "Host $domain" >> $config_file
    echo "    HostName $domain" >> $config_file
    echo "    User git" >> $config_file
    echo "    Port 22" >> $config_file
    echo "    PreferredAuthentications publickey" >> $config_file
    echo "    IdentityFile ~/.ssh/$filename" >> $config_file

    echo "已更新ssh配置"
}

# 输入域名
read -p "请输入要生成的域名（默认：gitea.openjianghu.org）: " domain
domain=${domain:-"gitea.openjianghu.org"}

# 输入邮箱
default_email=$(get_local_ip)"@jianghujs.org"
read -p "请输入邮箱（默认：$default_email）: " email
email=${email:-$default_email}

# 输入密钥文件名
default_filename=$(generate_key_filename $domain)
read -p "请输入密钥文件名（默认：$default_filename）: " filename
filename=${filename:-$default_filename}

# 检查是否存在密钥文件
if [ -f "/root/.ssh/$filename" ] || [ -f "/root/.ssh/$filename.pub" ]; then
    # 提示用户是否删除旧的密钥文件
    read -p "文件已经存在，要删除已有文件吗？（默认y）[y/n]: " choice
    choice=${choice:-"y"}

    # 如果用户选择删除旧的密钥文件
    if [ "$choice" == "y" ] || [ "$choice" == "Y" ]; then
        rm -f "/root/.ssh/$filename"
        rm -f "/root/.ssh/$filename.pub"
    else
        echo "密钥文件已存在，不会生成新的密钥。"
        exit 1
    fi
fi

# 生成密钥
echo -e "\n" | ssh-keygen -t rsa -C "$email" -f "/root/.ssh/$filename" -N "" > /dev/null

echo "==== 生成/root/.ssh/$filename文件成功✅"

# 配置ssh
backup_file "/root/.ssh/config"
config_ssh $domain $filename

echo "==== 配置$domain关联密钥文件/root/.ssh/$filename成功✅"


# 打印域名、邮箱、密钥文件位置和公钥内容
echo "================ 密钥信息 ================"
echo "域名: $domain"
echo "邮箱: $email"
echo "密钥文件位置: /root/.ssh/$filename"
echo "公钥内容:"
cat "/root/.ssh/$filename.pub"
echo "========================================="