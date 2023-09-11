#!/bin/bash

# 提示用户选择源
echo "请选择安装源："
echo "1) 国际源"
echo "2) 国内源"

# 读取用户输入，设置默认值为1
read -p "请输入你的选择（默认为1）:" source
source=${source:-1}

# 根据用户选择，执行对应的下载和安装操作
if [ $source -eq 1 ]; then
    echo "你选择了国际源，正在下载和安装..."
    wget -O install.sh https://raw.githubusercontent.com/jianghujs/jh-panel/master/scripts/install.sh && bash install.sh
elif [ $source -eq 2 ]; then
    echo "你选择了国内源，正在下载和安装..."
    wget -O install.sh https://gitee.com/jianghujs/jh-panel/raw/master/scripts/install.sh && bash install.sh cn
else
    echo "无效的选择，退出脚本。"
    exit 1
fi

