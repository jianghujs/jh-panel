#!/bin/bash


export BACKUP_PATH=${BACKUP_PATH:-/www/backup/xtrabackup_inc_data}
export BACKUP_BASE_PATH=${BACKUP_BASE_PATH:-/www/backup/xtrabackup_inc_data/base}
export BACKUP_INC_PATH=${BACKUP_INC_PATH:-/www/backup/xtrabackup_inc_data/inc}

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
# 最大等待次数
MAX_WAIT_COUNT=30
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
HISTORY_DIR="/www/backup/xtrabackup_inc_data_history"

# 移动BACKUP_BASE_PATH到历史版本
if [ -d "$BACKUP_BASE_PATH" ];then
    mv $BACKUP_PATH $HISTORY_DIR/xtrabackup_inc_data_${timestamp}
fi

mkdir -p $BACKUP_BASE_PATH
LOG_DIR="/www/server/xtrabackup-inc/logs"
if [ ! -d "$LOG_DIR" ];then
    mkdir -p $LOG_DIR
fi

pushd /www/server/jh-panel > /dev/null  
backup_config=$(python3 /www/server/jh-panel/plugins/xtrabackup-inc/index.py conf)
popd > /dev/null
BACKUP_COMPRESS=$(echo "$backup_config" | jq -r '.backup_full.backup_compress')
BACKUP_ZIP=$(echo "$backup_config" | jq -r '.backup_full.backup_zip')

if [ $BACKUP_COMPRESS -eq 1 ];then
    xtrabackup --backup --slave-info --gtid-info --compress --compress-threads=4 --user=root  --port=33067 --password=123456 --target-dir=$BACKUP_BASE_PATH  2>&1 | tee -a $LOG_DIR/backup_full_$timestamp.log
else
    xtrabackup --backup --slave-info --gtid-info --user=root  --port=33067 --password=123456 --target-dir=$BACKUP_BASE_PATH  2>&1 | tee -a $LOG_DIR/backup_full_$timestamp.log
fi

if [ $? -eq 0 ] && [ -d "$BACKUP_BASE_PATH/mysql" ];then

    # 删除增量目录
    lsof $BACKUP_INC_PATH | awk 'NR>1 {print $2}' | xargs -r kill -9
    rm -rf $BACKUP_INC_PATH
    mkdir -p $HISTORY_DIR

    # 预备增量恢复
    rsync -a --delete $BACKUP_BASE_PATH/ /www/backup/xtrabackup_data_restore/
    echo "|- $timestamp 全量备份成功" | tee -a /www/server/xtrabackup-inc/xtrabackup.log

    # 备份成功记录
    pushd /www/server/jh-panel > /dev/null  
    python3 /www/server/jh-panel/plugins/xtrabackup-inc/index.py backup_callback {backup_type:full}
    popd > /dev/null
else
    echo "|- $timestamp 全量备份失败" | tee -a /www/server/xtrabackup-inc/xtrabackup.log
fi

# 解锁
rm -f $LOCK_FILE_PATH

python3 /www/server/jh-panel/scripts/clean.py $LOG_DIR/

# 删除历史备份
export SAVE_ALL_DAY=${SAVE_ALL_DAY:-1}
export SAVE_OTHER=${SAVE_OTHER:-1}
export SAVE_MAX_DAY=${SAVE_MAX_DAY:-3}
python3 /www/server/jh-panel/scripts/clean.py $HISTORY_DIR/  "{\"saveAllDay\": \"$SAVE_ALL_DAY\", \"saveOther\": \"$SAVE_OTHER\", \"saveMaxDay\": \"$SAVE_MAX_DAY\"}"