#!/bin/bash

log_file=top_rank_output.txt

read -p "是否需要将结果打印到日志文件${log_file}？（默认n）[y/n]" yn
yn=${yn:-n}
case $yn in
    [Nn]* ) log_to_file=false;;
    * ) log_to_file=true;;
esac

# 清空日志文件
if $log_to_file ; then
    echo "" > $log_file
fi

while true; do
    if $log_to_file ; then
        top -b -n 1 | head -n 11 | tail -n 5 | tee -a $log_file
        echo "" | tee -a $log_file
    else
        top -b -n 1 | head -n 11 | tail -n 5
        echo ""
    fi
    sleep 1
done
