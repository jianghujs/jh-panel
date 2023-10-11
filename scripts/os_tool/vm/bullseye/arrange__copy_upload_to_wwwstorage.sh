#!/bin/bash

project_dir=${PROJECT_DIR:-"/www/wwwroot/"}
storage_dir=${STORAGE_DIR:-"/www/wwwstorage/"}

read -p "确定要将${project_dir}下的upload目录复制到${storage_dir}吗？（默认n）[y/n]: " choice
choice=${choice:-"n"}

if [ $choice == "y" ]; then
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
        echo "|-- 正在复制 $dir 到 $target_dir ..."
        rsync -a "$dir/" "$target_dir"

        echo "|-- 复制 $dir 到 $target_dir 成功✅"
    done

    
    echo ""
    echo "===========================整理完成✅=========================="
    echo "- 项目所在目录：$project_dir"
    echo "- 项目数据存放目录：$storage_dir"
    echo "---------------------------------------------------------------"
    echo "${project_dir}下的upload目录已全部复制到${storage_dir}"
    echo "==============================================================="
fi