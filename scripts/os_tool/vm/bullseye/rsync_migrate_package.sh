#!/bin/bash

# 定义传输文件变量
if [ -z "$MIGRATE_FILE" ]; then
  read -p "请输入传输文件所在位置: " MIGRATE_FILE
  if [ -z "$MIGRATE_FILE" ]; then
    echo "错误:未指定传输文件"
    exit 1
  fi
fi

# 获取环境变量中的MIGRATE_DIR值
MIGRATE_DIR=${MIGRATE_DIR:-"/www/migrate/"}

echo "传输文件: $MIGRATE_FILE"

# 输入目标服务器IP
read -p "请输入目标服务器IP: " remote_ip
if [ -z "$remote_ip" ]; then
  echo "错误:未指定目标服务器IP"
  exit 1
fi
export RSYNC_MIGRATE_PACKAGE_REMOTE_IP=$remote_ip

# 输入目标服务器SSH端口
read -p "请输入目标服务器SSH端口(默认: 10022): " remote_port
remote_port=${remote_port:-10022}
export RSYNC_MIGRATE_PACKAGE_REMOTE_PORT=$remote_port

# 输入目标文件位置 
read -p "请输入目标文件位置(默认:/root/$(basename $MIGRATE_FILE)): " remote_path
remote_path=${remote_path:-/root/$(basename $MIGRATE_FILE)}
export RSYNC_MIGRATE_PACKAGE_REMOTE_PART=$remote_path

# 在脚本的最后，把环境变量写到一个文件中
echo "RSYNC_MIGRATE_PACKAGE_REMOTE_IP=$RSYNC_MIGRATE_PACKAGE_REMOTE_IP" > $MIGRATE_DIR/rsync_migrate_package_config
echo "RSYNC_MIGRATE_PACKAGE_REMOTE_PORT=$RSYNC_MIGRATE_PACKAGE_REMOTE_PORT" >> $MIGRATE_DIR/rsync_migrate_package_config
echo "RSYNC_MIGRATE_PACKAGE_REMOTE_PART=$RSYNC_MIGRATE_PACKAGE_REMOTE_PART" >> $MIGRATE_DIR/rsync_migrate_package_config

# 执行同步
echo "正在执行同步..."
rsync -avu -e "ssh -p $remote_port" --progress --delete "$MIGRATE_FILE" "root@$remote_ip:$remote_path" &>> ${MIGRATE_DIR}rsync_migration.log
echo "同步完成"