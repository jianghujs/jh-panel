#!/bin/bash

#定义源列表
OPTIONS=(
    "保持原配置"
    "官方源 (http://archive.ubuntu.com/ubuntu)"
    "科大源 (https://mirrors.ustc.edu.cn/ubuntu/)"
    "网易源 (http://mirrors.163.com/ubuntu/)"
)

#定义源地址
UBUNTU_SOURCES_FILE="/etc/apt/sources.list"

#定义官方源脚本
UBUNTU_SOURCES="deb http://archive.ubuntu.com/ubuntu/ jammy main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ jammy-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu jammy-security main restricted universe multiverse
deb-src http://archive.ubuntu.com/ubuntu/ jammy main restricted universe multiverse
deb-src http://archive.ubuntu.com/ubuntu/ jammy-updates main restricted universe multiverse
deb-src http://archive.ubuntu.com/ubuntu/ jammy-backports main restricted universe multiverse
deb-src http://security.ubuntu.com/ubuntu jammy-security main restricted universe multiverse"

#定义科大源脚本
USTC_SOURCES="deb https://mirrors.ustc.edu.cn/ubuntu/ jammy main restricted universe multiverse
deb-src https://mirrors.ustc.edu.cn/ubuntu/ jammy main restricted universe multiverse
deb https://mirrors.ustc.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
deb-src https://mirrors.ustc.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
deb https://mirrors.ustc.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse
deb-src https://mirrors.ustc.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse
deb https://mirrors.ustc.edu.cn/ubuntu/ jammy-security main restricted universe multiverse
deb-src https://mirrors.ustc.edu.cn/ubuntu/ jammy-security main restricted universe multiverse"

#定义网易源脚本
NETEASE_SOURCES="deb http://mirrors.163.com/ubuntu/ jammy main restricted universe multiverse
deb-src http://mirrors.163.com/ubuntu/ jammy main restricted universe multiverse
deb http://mirrors.163.com/ubuntu/ jammy-updates main restricted universe multiverse
deb-src http://mirrors.163.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://mirrors.163.com/ubuntu/ jammy-backports main restricted universe multiverse
deb-src http://mirrors.163.com/ubuntu/ jammy-backports main restricted universe multiverse
deb http://mirrors.163.com/ubuntu/ jammy-security main restricted universe multiverse
deb-src http://mirrors.163.com/ubuntu/ jammy-security main restricted universe multiverse"

#接受默认项，如果输入为空，则默认选择第一项
if [[ -z "$1" ]]
then
    DEFAULT_CHOICE=1
else
    DEFAULT_CHOICE=$1
fi

# 显示源列表
echo "请选择一个 apt 源（国外推荐使用官方源，国内推荐使用科大源）:"
for i in "${!OPTIONS[@]}"; do 
    printf "%3d%s) %s" $((i+1)) "." "${OPTIONS[$i]}"
    if [[ "$i" -eq "(( $1 - 1 ))" ]]; then
        printf "（默认）"
    fi
    printf "\n"
done

#等待用户输入
while true; do
    read -p "请输入选项（数字）[默认 $DEFAULT_CHOICE]: " CHOICE
    CHOICE=${CHOICE:-$DEFAULT_CHOICE}
    if [[ "$CHOICE" =~ ^[1-4]$ ]]; then
        break
    fi
done

echo "你选择的是：${OPTIONS[$CHOICE-1]}"
CHOSEN_OPTION="${OPTIONS[$CHOICE-1]}"

#找到并替换 UBUNTU_SOURCES_FILE 文件中的源地址
if grep -q "$CHOSEN_OPTION" "$UBUNTU_SOURCES_FILE"; then
    echo "已经选择了该源，无需更改。"
elif [[ "$CHOSEN_OPTION" =~ "官方源" ]]; then
    echo "正在将新源地址添加到 $UBUNTU_SOURCES_FILE 文件中..."
    echo "$UBUNTU_SOURCES" > "$UBUNTU_SOURCES_FILE"
    echo "源地址更改完成。"
elif [[ "$CHOSEN_OPTION" =~ "科大源" ]]; then
    echo "正在将新源地址添加到 $UBUNTU_SOURCES_FILE 文件中..."
    echo "$USTC_SOURCES" > "$UBUNTU_SOURCES_FILE"
    echo "源地址更改完成。"
elif [[ "$CHOSEN_OPTION" =~ "网易源" ]]; then
    echo "正在将新源地址添加到 $UBUNTU_SOURCES_FILE 文件中..."
    echo "$NETEASE_SOURCES" > "$UBUNTU_SOURCES_FILE"
    echo "源地址更改完成。"
elif [[ "$CHOSEN_OPTION" =~ "保持原配置" ]]; then
    echo "保持原配置"
else
    #添加源地址到$UBUNTU_SOURCES_FILE文件末尾
    echo "正在将新源地址添加到 $UBUNTU_SOURCES_FILE 文件中..."
    echo " " >> "$UBUNTU_SOURCES_FILE"
    echo "deb ${CHOSEN_OPTION}/ jammy main restricted universe multiverse" >> "$UBUNTU_SOURCES_FILE"
    echo "源地址更改完成。"
fi

