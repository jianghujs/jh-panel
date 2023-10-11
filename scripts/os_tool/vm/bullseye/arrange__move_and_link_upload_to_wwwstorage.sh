#!/bin/bash

project_dir="/www/wwwroot/"
storage_dir="/www/wwwstorage/"

# 搜索所有目录，排除"node_modules"、"logs"、"run"目录
find "$project_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" -o -name ".git" \) -prune -o -name "upload" -type d -print | while read dir
do
    echo "========》正在处理 $dir "

    # 获取相对路径
    relative_path="${dir#$project_dir}"

    # 构建目标目录路径
    target_dir="$storage_dir$relative_path"

    # 创建目标目录及其父目录
    mkdir -p "$target_dir"
	
    # 使用 rsync 命令将 upload 目录复制到目标目录
    echo "|-- 正在移动 $dir 到 $target_dir ..."
    rsync -a "$dir/" "$target_dir"

    # 删除原始 upload 目录
    rm -rf "$dir"
	
    echo "|-- 移动 $dir 到 $target_dir 成功✅"
	

    # 创建软链接
    ln -s "$target_dir" "$dir"

    echo "|-- 创建 $dir 到 $target_dir 软链接成功✅"
done
