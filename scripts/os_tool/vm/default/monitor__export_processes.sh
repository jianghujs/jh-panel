#!/bin/bash

log_file=/tmp/processes_output.cvs

read -p "是否需要将结果导出到cvs文件${log_file}？（默认n）[y/n]：" yn
yn=${yn:-n}
case $yn in
    [Nn]* ) log_to_file=false;;
    * ) log_to_file=true;;
esac


if $log_to_file ; then
    # ps aux --sort=-%mem | head -n 101 > $log_file
    ps aux | awk 'BEGIN{OFS=","}{ print $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11}' > $log_file
    
    echo ""
    echo "===========================导出完成✅=========================="
    echo "- 文件所在路径：$log_file"
    echo "==============================================================="

else
    ps aux
fi
