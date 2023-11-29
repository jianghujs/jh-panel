#!/bin/bash

# 检查锁
# 最大等待次数
MAX_WAIT_COUNT=10
# 每次等待的时间（秒）
WAIT_TIME=30
if [ -e $LOCK_FILE_PATH ]; then
    # 计算锁时间差
    LOCK_TIMESTAMP=$(cat $LOCK_FILE_PATH)
    CURRENT_TIMESTAMP=$(date +%s)
    TIME_DIFF=$(($CURRENT_TIMESTAMP - $LOCK_TIMESTAMP))
    # 判断时间差是否超过20分钟（20*60=1200秒）
    if [ $TIME_DIFF -gt 1200 ]; then
        echo "锁已失效"
    else
        for ((i=0; i<MAX_WAIT_COUNT; i++)); do
            echo "已有任务在执行，等待 ${WAIT_TIME} 秒后重试"
            sleep ${WAIT_TIME}
            # 重新检查锁
            if [ ! -e $LOCK_FILE_PATH ]; then
                break
            fi
        done

        # 检查是否达到最大等待次数
        if [ -e $LOCK_FILE_PATH ]; then
            echo "已有任务在执行，请稍后重试"
            exit
        fi
    fi
fi

# 加锁
echo $(date +%s) > $LOCK_FILE_PATH

timestamp=$(date +%Y%m%d_%H%M%S)
# 临时设置系统的打开文件数量上限
ulimit -n 65535
# BACKUP_PATH 是在 控制面板 -> Xtrabackup -> mysql备份目录 设置的目录，不要在此文件修改

# 备份目录
BACKUP_BASE_PREV_PATH=$BACKUP_BASE_PATH.prev
if [ -d "$BACKUP_BASE_PREV_PATH" ];then
    rm -rf $BACKUP_BASE_PREV_PATH
fi

if [ -d "$BACKUP_BASE_PATH" ];then
    mv $BACKUP_BASE_PATH $BACKUP_BASE_PREV_PATH
    echo "|- 备份全量目录到${BACKUP_BASE_PREV_PATH}完成"
fi

mkdir -p $BACKUP_BASE_PATH
LOG_DIR="/www/server/xtrabackup-inc/logs"
if [ ! -d "$LOG_DIR" ];then
    mkdir -p $LOG_DIR
fi

if [ $BACKUP_COMPRESS -eq 1 ];then
    xtrabackup --backup --compress --compress-threads=4 --user=root  --port=33067 --password=123456 --target-dir=$BACKUP_BASE_PATH &>> $LOG_DIR/backup_full_$timestamp.log
else
    xtrabackup --backup --user=root  --port=33067 --password=123456 --target-dir=$BACKUP_BASE_PATH &>> $LOG_DIR/backup_full_$timestamp.log
fi

if [ $? -eq 0 ] && [ -d "$BACKUP_BASE_PATH/mysql" ];then
    # 预备增量恢复
    rsync -a --delete $BACKUP_BASE_PATH/ /www/backup/xtrabackup_data_restore/
    # 删除增量目录
    rm -rf $BACKUP_INC_PATH
    echo "|- $timestamp 全量备份成功" >> /www/server/xtrabackup-inc/xtrabackup.log
    # 备份成功记录
    pushd /www/server/jh-panel > /dev/null  
    python3 /www/server/jh-panel/plugins/xtrabackup-inc/index.py backup_callback {backup_type:full}
    popd > /dev/null
else
    echo "|- $timestamp 全量备份失败" >> /www/server/xtrabackup-inc/xtrabackup.log
    # 恢复目录
    if [ -d "$BACKUP_BASE_PATH" ];then
        rm -rf $BACKUP_BASE_PATH
    fi
    if [ -d "$BACKUP_BASE_PREV_PATH" ];then
        cp -r $BACKUP_BASE_PREV_PATH $BACKUP_BASE_PATH
        echo "|- 恢复全量目录内容完成"
    fi
fi

# 解锁
rm -f $LOCK_FILE_PATH

python3 /www/server/jh-panel/scripts/clean.py $LOG_DIR/