#!/bin/bash
timestamp=$(date +%Y%m%d_%H%M%S)

# 定义结果文件名
RESULT_FILENAME="innochecksum_result_$timestamp.log"
DAMAGED_FILENAME="innochecksum_bad_table_$timestamp.txt"
RECOVER_FILENAME="innochecksum_recover_table_$timestamp.sql"

# 函数来同时输出到命令行和日志文件
log_echo() {
    local message="$1"
    echo "$message" | tee -a "$RESULT_FILENAME"
}

# 检查是否已安装innochecksum，如果没有则安装
if ! command -v innochecksum &> /dev/null; then
    log_echo "Check failed because innochecksum is not installed. Run the following command to install:"
    log_echo "sudo apt-get install mariadb-server-core-10.5"
else
    isMySQLRunning=0

    # 检查MySQL是否在运行
    if systemctl is-active mysql-apt &> /dev/null; then
        isMySQLRunning=1
        # 停止MySQL服务器
        systemctl stop mysql-apt
        log_echo "MySQL server has been stopped..."
    else
        log_echo "MySQL server is not running. Skipped stopping MySQL server..."
    fi

    # 提示用户输入MySQL数据目录的路径
    read -p "Enter MySQL data directory path (default: /www/server/mysql-apt/data): " MYSQL_DATA_DIR
    MYSQL_DATA_DIR=${MYSQL_DATA_DIR:-"/www/server/mysql-apt/data"}

    echo -e "Database\tTable" >> "$DAMAGED_FILENAME"

    # 初始化损坏表格计数
    corruptedTableCount=0

    # 获取MySQL数据目录中的数据库目录列表
    DATABASE_DIRS=("$MYSQL_DATA_DIR"/*/)

    # 遍历数据库目录
    for DB_DIR in "${DATABASE_DIRS[@]}"; do
        # 获取数据库名称
        DB=$(basename "$DB_DIR")
        log_echo "Checking database $DB ..."

        # 遍历数据库目录中的数据页文件（.ibd）
        for TABLE_FILE in "$DB_DIR"*.ibd; do
            # 获取数据表名称
            TB=$(basename "$TABLE_FILE" .ibd)

            if [ "$TB" == "*" ]; then
                log_echo "No data table"
            else
                # 使用innochecksum检查数据页是否损坏
                innochecksum "$TABLE_FILE" 2>&1 | grep -q "Error"
                if [ $? -eq 0 ]; then
                    ((corruptedTableCount++))
                    log_echo "$TB: Corrupted"
                    echo -e "$DB\t$TB" >> "$DAMAGED_FILENAME"

                    echo "-- Database: $DB, Table: $TB" >> "$RECOVER_FILENAME"
                    TB_RECOVER="${TB}_recover"
                    echo "CREATE TABLE $DB.$TB_RECOVER AS SELECT * FROM $DB.$TB;" >> "$RECOVER_FILENAME"
                    echo "TRUNCATE TABLE $DB.$TB;" >> "$RECOVER_FILENAME"
                    echo "DROP TABLE $DB.$TB;" >> "$RECOVER_FILENAME"
                    echo "ALTER TABLE $DB.$TB_RECOVER RENAME TO $DB.$TB;" >> "$RECOVER_FILENAME"
                    echo >> "$RECOVER_FILENAME"          
                else
                    log_echo "$TB: Normal"
                fi
            fi        
        done
        
        log_echo ""
    done

    # 根据是否存在损坏的数据页输出相应信息
    if [ $corruptedTableCount -eq 0 ]; then
        echo "No corrupted data pages found" >> "$DAMAGED_FILENAME"
        log_echo "No corrupted data pages found"
        echo "Check result saved as: $RESULT_FILENAME"
    else
        log_echo "Total corrupted data tables: $corruptedTableCount"
        log_echo "List of corrupted data tables: $DAMAGED_FILENAME"
        echo "Check result saved as: $RESULT_FILENAME"
        log_echo "A SQL script for recovering corrupted tables has been generated: $RECOVER_FILENAME"
    fi

    # 检查之前MySQL是否在运行。是，则启动MySQL服务器
    if [ $isMySQLRunning -eq 1 ]; then
        # 启动MySQL服务器
        systemctl start mysql-apt
        log_echo "MySQL server has been started."
    fi
fi