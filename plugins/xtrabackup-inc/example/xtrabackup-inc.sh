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

# 检查锁
if [ -e $LOCK_FILE_PATH ]; then
    # 计算锁时间差
    LOCK_TIMESTAMP=$(cat $LOCK_FILE_PATH)
    CURRENT_TIMESTAMP=$(date +%s)
    TIME_DIFF=$(($CURRENT_TIMESTAMP - $LOCK_TIMESTAMP))
    # 判断时间差是否超过20分钟（20*60=1200秒）
    if [ $TIME_DIFF -gt 1200 ]; then
        echo "锁已失效"
    else
        echo "已有任务在执行，请稍后重试"
        exit
    fi
fi

# 加锁
echo $(date +%s) > $LOCK_FILE_PATH

timestamp=$(date +%Y%m%d_%H%M%S)
# 临时设置系统的打开文件数量上限
ulimit -n 65535
# BACKUP_PATH 是在 控制面板 -> Xtrabackup -> mysql备份目录 设置的目录，不要在此文件修改

# 备份增量版本
mv $BACKUP_INC_PATH $BACKUP_PATH/inc_$timestamp

mkdir -p $BACKUP_INC_PATH
LOG_DIR="/www/server/xtrabackup-inc/logs"
if [ ! -d "$LOG_DIR" ];then
    mkdir -p $LOG_DIR
fi

pushd /www/server/jh-panel > /dev/null  
backup_config=$(python3 /www/server/jh-panel/plugins/xtrabackup-inc/index.py conf)
popd > /dev/null
BACKUP_COMPRESS=$(echo "$backup_config" | jq -r '.backup_inc.backup_compress')
BACKUP_ZIP=$(echo "$backup_config" | jq -r '.backup_inc.backup_zip')

if [ $BACKUP_COMPRESS -eq 1 ];then
    xtrabackup --backup --slave-info --gtid-info --compress --compress-threads=4 --user=root  --port=33067 --password=123456 --target-dir=$BACKUP_INC_PATH --incremental-basedir=$BACKUP_BASE_PATH  2>&1 | tee -a $LOG_DIR/backup_inc_$timestamp.log
else
    xtrabackup --backup --slave-info --gtid-info --user=root  --port=33067 --password=123456 --target-dir=$BACKUP_INC_PATH --incremental-basedir=$BACKUP_BASE_PATH  2>&1 | tee -a $LOG_DIR/backup_inc_$timestamp.log
fi

if [ $? -eq 0 ] && [ -d "$BACKUP_INC_PATH/mysql" ];then
    if [ $BACKUP_ZIP -eq 1 ];then
        # 原地zip压缩并删除其他文件
        cd $BACKUP_INC_PATH && zip -q -r $BACKUP_INC_PATH.zip ./* && rm -rf $BACKUP_INC_PATH/* && mv $BACKUP_INC_PATH.zip $BACKUP_INC_PATH/
    fi

    echo "|- $timestamp 增量备份成功" | tee -a /www/server/xtrabackup-inc/xtrabackup.log
    # 备份成功记录
    pushd /www/server/jh-panel > /dev/null  
    python3 /www/server/jh-panel/plugins/xtrabackup-inc/index.py backup_callback {backup_type:inc}
    popd > /dev/null
else
    echo "|- $timestamp 增量备份失败" | tee -a /www/server/xtrabackup-inc/xtrabackup.log
fi

# 解锁
rm -f $LOCK_FILE_PATH

python3 /www/server/jh-panel/scripts/clean.py $LOG_DIR/
