#!/bin/bash

# 定义传输文件变量
if [ -z "$RSYNC_FILE" ]; then
  read -p "请输入传输文件所在位置: " RSYNC_FILE
  if [ -z "$RSYNC_FILE" ]; then
    echo "错误:未指定传输文件"
    exit 1
  fi
fi

echo "传输文件: $RSYNC_FILE"

# 输入目标服务器IP
read -p "请输入目标服务器IP: " remote_ip
if [ -z "$remote_ip" ]; then
  echo "错误:未指定目标服务器IP"
  exit 1
fi
export RSYNC_REMOTE_IP=$remote_ip

# 输入目标服务器SSH端口
read -p "请输入目标服务器SSH端口(默认: 10022): " remote_port
remote_port=${remote_port:-10022}
export RSYNC_REMOTE_PORT=$remote_port

# 输入目标文件位置 
read -p "请输入目标文件位置(默认:/root/$(basename $RSYNC_FILE)): " remote_path
remote_path=${remote_path:-/root/$(basename $RSYNC_FILE)}
export RSYNC_REMOTE_PART=$remote_path

# 在脚本的最后，把环境变量写到一个文件中
echo "RSYNC_REMOTE_IP=$RSYNC_REMOTE_IP" > /tmp/rsync_file_config
echo "RSYNC_REMOTE_PORT=$RSYNC_REMOTE_PORT" >> /tmp/rsync_file_config
echo "RSYNC_REMOTE_PART=$RSYNC_REMOTE_PART" >> /tmp/rsync_file_config

# 执行同步
echo "正在执行同步..."
rsync -av -e "ssh -p $remote_port" --progress --delete "$RSYNC_FILE" "root@$remote_ip:$remote_path"
echo "同步完成"