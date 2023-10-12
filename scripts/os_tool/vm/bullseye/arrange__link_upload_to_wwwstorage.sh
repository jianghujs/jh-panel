#!/bin/bash

project_dir=${PROJECT_DIR:-"/www/wwwroot/"}
storage_dir=${STORAGE_DIR:-"/www/wwwstorage/"}
project_dir_exist_upload_dirs=()

read -p "确定要将${project_dir}下的upload目录链接到${storage_dir}吗？（默认n）[y/n]: " choice
choice=${choice:-"n"}

if [ $choice == "y" ]; then

    # 查找project_dir下已存在的upload目录
    echo "|- 正在查找项目目录下已存在的upload目录..."
	while IFS= read -r -d '' dir; do
		# 获取相对路径
        relative_path="${dir#$storage_dir}"

        # 构建目标目录路径
        target_dir="$project_dir$relative_path"    
		
		if [ -d "$target_dir" ]; then
        	project_dir_exist_upload_dirs+=("$target_dir")
        fi
	done < <(find "$storage_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" -o -name ".git" \) -prune -o -name "upload" -type d -print0)
    

	if [ ${#project_dir_exist_upload_dirs[@]} -gt 0 ]; then
        echo "在${project_dir}找到以下upload目录，需要删除后才能建立软链："
        for dir in "${project_dir_exist_upload_dirs[@]}"
        do
            echo "- $dir"
        done

        read -p "确认删除以上目录？(默认n) [y/n]: " delete_choice
        delete_choice=${delete_choice:-"n"}
        if [ $delete_choice == "n" ]; then
            exit	  
        fi
        for dir in "${project_dir_exist_upload_dirs[@]}"
        do
            echo "|-- 正在删除 $dir ..."
            rm -rf "$dir"
            echo "|-- 删除 $dir 成功✅"
        done
        echo "|-- 已完成${project_dir}目录下的upload目录清理✅"
		
    fi
    echo "|- 开始创建${project_dir}下的软链..."

    # 搜索所有目录，排除"node_modules"、"logs"、"run"目录
    find "$storage_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" -o -name ".git" \) -prune -o -name "upload" -type d -print | while read dir
    do
        # 获取相对路径
        relative_path="${dir#$storage_dir}"

        # 构建目标目录路径
        target_dir="$project_dir$relative_path"
  
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