#!/bin/bash

# 检查/usr/bin/jq是否存在
if ! [ -x "/usr/bin/jq" ]; then
    echo "/usr/bin/jq不存在，正在尝试自动安装..."
    apt-get update
    apt-get install jq -y
    hash -r
    if ! [ -x "/usr/bin/jq" ]; then
        echo "安装jq失败，请手动安装后再运行脚本。"
        exit 1
    fi
fi

timestamp=$(date +%Y%m%d_%H%M%S)
# 临时设置系统的打开文件数量上限
ulimit -n 65535
# BACKUP_PATH 是在 控制面板 -> Xtrabackup -> mysql备份目录 设置的目录，不要在此文件修改
rm -rf $BACKUP_PATH
mkdir -p $BACKUP_PATH
HISTORY_DIR="/www/backup/xtrabackup_data_history"
LOG_DIR="/www/server/xtrabackup/logs"
BACKUP_FILE="$HISTORY_DIR/xtrabackup_data_$timestamp.zip"
if [ ! -d "$LOG_DIR" ];then
    mkdir -p $LOG_DIR
fi

pushd /www/server/jh-panel > /dev/null  
backup_config=$(python3 /www/server/jh-panel/plugins/xtrabackup/index.py get_conf)
popd > /dev/null
BACKUP_COMPRESS=$(echo "$backup_config" | jq -r '.mysql.backup_compress')

if [ $BACKUP_COMPRESS -eq 1 ];then
    xtrabackup --backup --slave-info --gtid-info --compress --compress-threads=4 --user=root  --port=33067 --password=123456 --target-dir=$BACKUP_PATH &>> $LOG_DIR/backup_$timestamp.log
else
    xtrabackup --backup --slave-info --gtid-info --user=root  --port=33067 --password=123456 --target-dir=$BACKUP_PATH &>> $LOG_DIR/backup_$timestamp.log
fi

if [ $? -eq 0 ] && [ -d "$BACKUP_PATH/mysql" ];then
    mkdir -p $HISTORY_DIR
    cd $BACKUP_PATH && zip -q -r $BACKUP_FILE ./*
    echo "backup file output====>  $BACKUP_FILE"
    echo "备份成功 $timestamp"
    # 备份成功记录
    pushd /www/server/jh-panel > /dev/null  
    python3 /www/server/jh-panel/plugins/xtrabackup/index.py backup_callback {filepath:$BACKUP_FILE}
    popd > /dev/null
else
    echo "备份失败 $timestamp"
fi
python3 /www/server/jh-panel/scripts/clean.py $LOG_DIR/
