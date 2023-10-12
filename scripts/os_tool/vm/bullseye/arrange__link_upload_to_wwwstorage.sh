#!/bin/bash

project_dir=${PROJECT_DIR:-"/www/wwwroot/"}
storage_dir=${STORAGE_DIR:-"/www/wwwstorage/"}

read -p "确定要将${project_dir}下的upload目录链接到${storage_dir}吗？确认后可能会清空${project_dir}下的upload目录，请做好数据备份！（默认n）[y/n]: " choice
choice=${choice:-"n"}

if [ $choice == "y" ]; then
    # 搜索所有目录，排除"node_modules"、"logs"、"run"目录
    find "$storage_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" -o -name ".git" \) -prune -o -name "upload" -type d -print | while read dir
    do
        # 获取相对路径
        relative_path="${dir#$storage_dir}"

        # 构建目标目录路径
        target_dir="$project_dir$relative_path"

        if [ -d "$target_dir" ]; then
            echo "|-- 正在删除 $target_dir ..."
            rm -rf "$target_dir"
            echo "|-- 删除 $target_dir 成功✅"
        fi
        
        
        # 创建软链接
        ln -s "$dir" "$target_dir"

        echo "|-- 创建 $target_dir 到 $dir 软链接成功✅"
    done

    
    echo ""
    echo "===========================整理完成✅=========================="
    echo "- 项目所在目录：$project_dir"
    echo "- 项目数据存放目录：$storage_dir"
    echo "---------------------------------------------------------------"
    echo "${project_dir}下的upload目录已链接到${storage_dir}"
    echo "==============================================================="
fi