#!/bin/bash

# 检查iotop是否安装
if ! command -v iotop &> /dev/null; then
    echo "iotop未安装，正在尝试自动安装..."
    apt-get update
    apt-get install iotop -y
    if ! command -v iotop &> /dev/null; then
        echo "安装iotop失败，请手动安装后再运行脚本。"
        exit 1
    fi
fi

log_file=iotop_rank_output.txt

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
    iotop -b -n 1 | head -n 7 | tail -n 5 | tee -a $log_file
    echo "" | tee -a $log_file
  else
    iotop -b -n 1 | head -n 7 | tail -n 5
    echo ""
  fi
  sleep 1
done
