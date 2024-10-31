#!/bin/bash

log_file=/tmp/top_rank_output.txt

read -p "是否需要将结果打印到日志文件${log_file}？（默认n）[y/n]" yn
yn=${yn:-n}
case $yn in
    [Nn]* ) log_to_file=false;;
    * ) log_to_file=true;;
esac

read -p "请输入要显示的进程数（默认5）：" process_num
process_num=${process_num:-5}
log_line_num=$(($process_num + 1))

# 清空日志文件
if $log_to_file ; then
    echo "" > $log_file
fi

while true; do
    if $log_to_file ; then
        top -b -n 1 | head -n $(($log_line_num + 6)) | tail -n $log_line_num | tee -a $log_file
        echo "" | tee -a $log_file
    else
        top -b -n 1 | head -n $(($log_line_num + 6)) | tail -n $log_line_num
        echo ""
    fi
    sleep 1
done
