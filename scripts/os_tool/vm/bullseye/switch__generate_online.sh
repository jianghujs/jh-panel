#!/bin/bash

# 检查fio是否安装
if ! command -v fio &> /dev/null; then
    echo "fio未安装，正在尝试自动安装..."
    apt-get update
    apt-get install fio -y
    if ! command -v fio &> /dev/null; then
        echo "安装fio失败，请手动安装后再运行脚本。"
        exit 1
    fi
fi

# 询问用户测试类型
echo "请选择测试类型："
echo "1. 读取"
echo "2. 写入"
echo "3. 读写"
read -p "请输入你的选择（1-3，默认为1）：" test_type
test_type=${test_type:-1}
case $test_type in
    1 ) rw="read";;
    2 ) rw="write";;
    * ) rw="readwrite";;  # 默认为读写测试
esac

log_file=fio_test_output.txt

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


read -p "请输入测试时长（默认60s）：" runtime
runtime=${runtime:-"60s"}

# 定义fio测试参数
block_size="4k"
ioengine="libaio"
iodepth="1"
size="1G"
numjobs=1
status_interval="1"  # 每秒钟更新一次状态

# 执行fio测试
if $log_to_file ; then
    fio --name=myiotest --rw=$rw --bs=$block_size --ioengine=$ioengine --size=$size --runtime=$runtime --numjobs=$numjobs --time_based --end_fsync=1 | tee -a $log_file
else
    fio --name=myiotest --rw=$rw --bs=$block_size --ioengine=$ioengine --iodepth=$iodepth --size=$size --runtime=$runtime --numjobs=$numjobs --time_based --end_fsync=1 
fi
