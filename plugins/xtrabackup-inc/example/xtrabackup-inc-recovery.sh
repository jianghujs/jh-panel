#!/bin/bash
BACKUP_RESTORE_PATH=/www/backup/xtrabackup_data_restore
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

if [ ! -d "$BACKUP_BASE_PATH" ];then
    echo "未检测到全量备份目录，请先执行全量备份"
    exit
fi

timestamp=$(date +%Y%m%d_%H%M%S)
# 临时设置系统的打开文件数量上限
ulimit -n 65535
LOG_DIR=/www/server/xtrabackup-inc/logs
systemctl stop $MYSQL_NAME
mv $MYSQL_DIR/data $MYSQL_DIR/data_$timestamp
mkdir -p /www/server/xtrabackup-inc/logs
# 复制全量目录
rsync -a --delete $BACKUP_BASE_PATH/ $BACKUP_RESTORE_PATH/
# 如果备份是压缩的，需要在新的目录中解压缩
if ls $BACKUP_BASE_PATH/*.qp 1> /dev/null 2>&1; then
    BACKUP_BASE_COMPRESSED=1
else
    BACKUP_BASE_COMPRESSED=0
fi

# 如果备份是压缩的，需要在新的目录中解压缩
if [ $BACKUP_BASE_COMPRESSED -eq 1 ];then
    xtrabackup --decompress --target-dir=$BACKUP_RESTORE_PATH &>> $LOG_DIR/recovery_$timestamp.log
fi

xtrabackup --prepare --apply-log-only --target-dir=$BACKUP_RESTORE_PATH &>> $LOG_DIR/recovery_$timestamp.log
# 合并增量内容
if [ -d "$BACKUP_INC_PATH" ];then
    ZIP_CREATED=0
    # 判断本身是否是zip压缩的、如果是那么要创建单独的zip解压缓存目录解压后执行
    if ls $BACKUP_INC_PATH/*.zip 1> /dev/null 2>&1; then
        TEMP_ZIP_PATH=/www/backup/xtrabackup_data_inc_recovery_zip
        # 先删除缓存目录
        rm -rf $TEMP_ZIP_PATH
        mkdir -p $TEMP_ZIP_PATH
        unzip -q $BACKUP_INC_PATH/*.zip -d $TEMP_ZIP_PATH
        ZIP_CREATED=1
    else
        TEMP_ZIP_PATH=$BACKUP_INC_PATH
    fi

    # 如果增量备份是压缩的，创建缓存目录解压后执行
    if ls $TEMP_ZIP_PATH/*.qp 1> /dev/null 2>&1; then
        if [ $ZIP_CREATED -eq 1 ];then
            TEMP_INC_PATH=$TEMP_ZIP_PATH
        else
            TEMP_INC_PATH=/www/backup/xtrabackup_data_inc_recovery
            cp -r $TEMP_ZIP_PATH $TEMP_INC_PATH
        fi

        xtrabackup --decompress --target-dir=$TEMP_INC_PATH &>> $LOG_DIR/recovery_$timestamp.log
        xtrabackup --prepare --apply-log-only --target-dir=$BACKUP_RESTORE_PATH --incremental-dir=$TEMP_INC_PATH &>> $LOG_DIR/recovery_$timestamp.log

        # TEMP_INC_PATH 是临时解压缩的目录，如果是临时创建的，需要删除
        if [ $ZIP_CREATED -eq 0 ];then
            rm -rf $TEMP_INC_PATH
        fi

    else
        xtrabackup --prepare --apply-log-only --target-dir=$BACKUP_RESTORE_PATH --incremental-dir=$TEMP_ZIP_PATH &>> $LOG_DIR/recovery_$timestamp.log
    fi

    if [ $ZIP_CREATED -eq 1 ];then
        rm -rf $TEMP_ZIP_PATH
    fi

    if [ $BACKUP_BASE_COMPRESSED -eq 1 ];then
        # 删除 BACKUP_BASE_PATH 所有不是压缩的文件
        find $BACKUP_RESTORE_PATH -type f ! -name "*.qp" -delete
    fi
fi

# 执行恢复
xtrabackup --copy-back --target-dir=$BACKUP_RESTORE_PATH &>> $LOG_DIR/recovery_$timestamp.log
chown -R mysql:mysql $MYSQL_DIR/data 
chmod -R 755 $MYSQL_DIR/data
systemctl start $MYSQL_NAME

# 解锁
rm -f $LOCK_FILE_PATH

python3 /www/server/jh-panel/scripts/clean.py $LOG_DIR