#!/bin/bash

log_file=/tmp/directory_contents.csv
temp_log_file=/tmp/directory_contents_temp.csv

read -p "是否需要将结果导出到CSV文件${log_file}？（默认y）[y/n]：" yn
yn=${yn:-y}
case $yn in
    [Nn]* ) log_to_file=false;;
    * ) log_to_file=true;;
esac

if $log_to_file ; then
    # 创建临时CSV文件并写入表头
    echo "文件名,大小,创建时间,修改时间" > $temp_log_file

    # 获取所有文件和文件夹的创建时间和大小，并写入临时CSV文件
    for file in *; do
      if [ -e "$file" ]; then
        # 获取文件或文件夹的大小
        size=$(du -sh "$file" | cut -f1)
        # 获取文件或文件夹的创建时间
        ctime=$(stat -c %W "$file")
        # 获取文件或文件夹的修改时间
        mtime=$(stat -c %Y "$file")
        # 格式化时间戳为可读格式
        formatted_ctime=$(date -d @$ctime +"%Y-%m-%d %H:%M:%S")
        formatted_mtime=$(date -d @$mtime +"%Y-%m-%d %H:%M:%S")
        # 打印创建时间、修改时间、大小和文件名
        echo "$ctime $size \"$file\" $formatted_ctime $formatted_mtime"
      fi
    done | sort -k1,1nr | awk -F ' ' '{OFS=","; print $3,$2,$4,$5}' >> $temp_log_file

    # 将临时CSV文件转换为UTF-8编码并写入最终CSV文件
    iconv -f UTF-8 -t GB2312 $temp_log_file > $log_file

    # 删除临时文件
    rm $temp_log_file

    echo ""
    echo "===========================导出完成✅=========================="
    echo "- 文件所在路径：$log_file"
    echo "==============================================================="

else
    # 输出到控制台
    for file in *; do
      if [ -e "$file" ]; then
        # 获取文件或文件夹的大小
        size=$(du -sh "$file" | cut -f1)
        # 获取文件或文件夹的创建时间
        ctime=$(stat -c %W "$file")
        # 获取文件或文件夹的修改时间
        mtime=$(stat -c %Y "$file")
        # 格式化时间戳为可读格式
        formatted_ctime=$(date -d @$ctime +"%Y-%m-%d %H:%M:%S")
        formatted_mtime=$(date -d @$mtime +"%Y-%m-%d %H:%M:%S")
        # 打印创建时间、修改时间、大小和文件名
        echo "$ctime $size \"$file\" $formatted_ctime $formatted_mtime"
      fi
    done | sort -k1,1nr | awk -F ' ' '{OFS=","; print $3,$2,$4,$5}'
fi