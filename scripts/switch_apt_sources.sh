#!/bin/bash

#定义源列表
OPTIONS=(
    "官方源 (http://deb.debian.org/debian)"
    "科大源 (https://mirrors.ustc.edu.cn/debian/)"
    "网易源 (https://mirrors.163.com/debian/)"
)

#定义源地址
DEBIAN_SOURCES_FILE="/etc/apt/sources.list"

#定义官方源脚本
DEBIAN_SOURCES="deb http://deb.debian.org/debian/ bullseye main non-free contrib
deb http://deb.debian.org/debian/ bullseye-updates main non-free contrib
deb-src http://deb.debian.org/debian/ bullseye main non-free contrib
deb-src http://deb.debian.org/debian/ bullseye-updates main non-free contrib
deb http://deb.debian.org/debian/ bullseye-backports main contrib non-free
deb-src http://deb.debian.org/debian/ bullseye-backports main contrib non-free
deb http://deb.debian.org/debian-security/ bullseye-security main contrib non-free
deb-src http://deb.debian.org/debian-security/ bullseye-security main contrib non-free" 

#定义科大源脚本
USTC_SOURCES="deb https://mirrors.ustc.edu.cn/debian bullseye main contrib non-free
deb-src https://mirrors.ustc.edu.cn/debian bullseye main contrib non-free
deb https://mirrors.ustc.edu.cn/debian-security/ bullseye-security main
deb-src https://mirrors.ustc.edu.cn/debian-security/ bullseye-security main
deb https://mirrors.ustc.edu.cn/debian bullseye-updates main
deb-src https://mirrors.ustc.edu.cn/debian bullseye-updates main"

#定义网易源脚本
NETEASE_SOURCES="deb https://mirrors.163.com/debian/ bullseye main non-free contrib
deb-src htttps://mirrors.163.com/debian/ bullseye main non-free contrib
deb https://mirrors.163.com/debian-security/ bullseye-security main
deb-src https://mirrors.163.com/debian-security/ bullseye-security main
deb https://mirrors.163.com/debian/ bullseye-updates main non-free contrib
deb-src https://mirrors.163.com/debian/ bullseye-updates main non-free contrib
deb https://mirrors.163.com/debian/ bullseye-backports main non-free contrib
deb-src https://mirrors.163.com/debian/ bullseye-backports main non-free contrib" 

#接受默认项，如果输入为空，则默认选择第一项
if [[ -z "$1" ]]
then
    DEFAULT_CHOICE=1
else
    DEFAULT_CHOICE=$1
fi

echo "$DEFAULT_CHOICE"

# 显示源列表
echo "请选择一个 apt 源:"
for i in "${!OPTIONS[@]}"; do 
    printf "%3d%s) %s" $((i+1)) "." "${OPTIONS[$i]}"
    if [[ "$i" -eq "(( $1 - 1 ))" ]]; then
        printf "（默认）"
    fi
    printf "\n"
done

#等待用户输入
while true; do
    read -p "请输入选项（数字）[$DEFAULT_CHOICE]: " CHOICE
    CHOICE=${CHOICE:-$DEFAULT_CHOICE}
    if [[ "$CHOICE" =~ ^[1-5]$ ]]; then
        break
    fi
done

echo "你选择的是：${OPTIONS[$CHOICE-1]}"
CHOSEN_OPTION="${OPTIONS[$CHOICE-1]}"

#找到并替换 DEBIAN_SOURCES_FILE 文件中的源地址
if grep -q "$CHOSEN_OPTION" "$DEBIAN_SOURCES_FILE"; then
    echo "已经选择了该源，无需更改。"
elif [[ "$CHOSEN_OPTION" =~ "官方源" ]]; then
    echo "正在将新源地址添加到 $DEBIAN_SOURCES_FILE 文件中..."
    echo "$DEBIAN_SOURCES" > "$DEBIAN_SOURCES_FILE"
    echo "源地址更改完成。"
elif [[ "$CHOSEN_OPTION" =~ "科大源" ]]; then
    echo "正在将新源地址添加到 $DEBIAN_SOURCES_FILE 文件中..."
    echo "$USTC_SOURCES" > "$DEBIAN_SOURCES_FILE"
    echo "源地址更改完成。"
elif [[ "$CHOSEN_OPTION" =~ "网易源" ]]; then
    echo "正在将新源地址添加到 $DEBIAN_SOURCES_FILE 文件中..."
    echo "$NETEASE_SOURCES" > "$DEBIAN_SOURCES_FILE"
    echo "源地址更改完成。"
else
    #添加源地址到$DEBIAN_SOURCES_FILE文件末尾
    echo "正在将新源地址添加到 $DEBIAN_SOURCES_FILE 文件中..."
    echo " " >> "$DEBIAN_SOURCES_FILE"
    echo "deb ${CHOSEN_OPTION}/ stable main contrib non-free" >> "$DEBIAN_SOURCES_FILE"
    echo "源地址更改完成。"
fi
