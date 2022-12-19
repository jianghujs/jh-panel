#!/bin/bash
timestamp=$(date +%Y%m%d_%H%M%S)
rm -rf /www/backup/xtrabackup_data/
mkdir -p /www/backup/xtrabackup_data
xtrabackup --backup --user=root  --port=3306 --password=C3YHvGxRiuY9fho2 --target-dir=/www/backup/xtrabackup_data &>> /www/wwwlogs/xtrabackup.log
mkdir -p /www/backup/xtrabackup_data_history
zip -r /www/backup/xtrabackup_data_history/xtrabackup_data_$timestamp.zip /www/backup/xtrabackup_data
echo "  backup file output====>  /www/backup/xtrabackup_data_history/xtrabackup_data_$timestamp.zip"