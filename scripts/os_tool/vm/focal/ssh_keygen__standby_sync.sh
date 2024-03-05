#!/bin/bash

# 获取本机IP
get_local_ip() {
    ip=$(hostname -I | awk '{print $1}')
    echo $ip
}

# 下载并执行脚本的函数
download_and_run() {
    local script_name=$1
    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      bash $SCRIPT_BASE/${script_name} ${@:2}
    else
      wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
      bash /tmp/vm_${script_name} ${@:2}
    fi    
}

# 输入邮箱
default_email=$(get_local_ip).sync"@jianghujs.org"
read -p "请输入邮箱（默认：$default_email）: " email
email=${email:-$default_email}

filename="standby_sync"

# 生成密钥
echo -e "\n" | ssh-keygen -t rsa -C "$email" -f "/root/.ssh/$filename" -N "" > /dev/null

echo "==== 生成/root/.ssh/$filename文件成功✅"

# 提示是否rsync同步
read -p "需要将证书文件rsync同步到备用服务器吗?(默认n)[y/n]" sync
sync=${sync:-n}


if [ $sync == "y" ]; then
    # 输入目标服务器IP
    read -p "请输入备用服务器IP: " remote_ip
    if [ -z "$remote_ip" ]; then
    echo "错误:未指定目标服务器IP"
    exit 1
    fi

    # 输入目标服务器SSH端口
    read -p "请输入备用服务器SSH端口(默认: 10022): " remote_port
    remote_port=${remote_port:-10022}

    rsync -av -e "ssh -p ${remote_port}" --progress /root/.ssh/$filename /root/.ssh/$filename.pub root@${remote_ip}:/root/.ssh/
fi


# 打印域名、邮箱、密钥文件位置和公钥内容
echo "================ 密钥信息 ================"
echo "邮箱: $email"
echo "密钥文件位置: /root/.ssh/$filename"
if [ $sync == "y" ]; then
echo "- 已将证书文件同步到以下服务器："
echo "  - 服务器IP：${RSYNC_MIGRATE_PACKAGE_REMOTE_IP}"
echo "  - 目标服务器SSH端口：${RSYNC_MIGRATE_PACKAGE_REMOTE_PORT}"
else
echo "请将/root/.ssh目录下的$filename、$filename.pub文件传输到备用服务器 "
fi
echo "========================================="