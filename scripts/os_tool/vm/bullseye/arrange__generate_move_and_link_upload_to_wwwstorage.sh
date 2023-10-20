#!/bin/bash

project_dir=${PROJECT_DIR:-"/www/wwwroot/"}
storage_dir=${STORAGE_DIR:-"/www/wwwstorage/"}
script_file="move_and_link_upload_to_wwwstorage.sh"

read -p "确定要生成移动并链接${project_dir}下的upload目录到${storage_dir}的脚本文件吗？（默认y）[y/n]: " choice
choice=${choice:-"y"}

echo "" > $script_file

if [ $choice == "y" ]; then

    # 搜索所有目录，排除"node_modules"、"logs"、"run"目录
    find "$project_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" -o -name ".git" \) -prune -o -name "upload" -type d -print | while read dir
    do
        # 获取相对路径
        relative_path="${dir#$project_dir}"

        # 构建目标目录路径
        target_dir="$storage_dir$relative_path"

        # 创建目标目录及其父目录
        echo "# 移动 ${dir} 到 ${target_dir}" >> $script_file
        echo "mkdir -p \"$target_dir\"" >> $script_file
        
        # 使用 rsync 命令将 upload 目录复制到目标目录
        echo "rsync -a \"$dir/\" \"$target_dir\"" >> $script_file

        # 删除原始 upload 目录
        echo "rm -rf \"$dir\"" >> $script_file
        
        echo "|-- 添加 移动${dir} 到 ${target_dir}命令成功✅"
        

        # 创建软链接
        echo "# 链接 ${dir} 到 ${target_dir}" >> $script_file
        echo "ln -s \"$target_dir\" \"$dir\"" >> $script_file

        echo "|-- 添加 链接${dir} 到 ${target_dir}命令成功✅"
    done

    
    echo ""
    echo "===========================整理完成✅=========================="
    echo "- 项目所在目录：$project_dir"
    echo "- 项目数据存放目录：$storage_dir"
    echo "---------------------------------------------------------------"
    echo "已生成移动并连接${project_dir}下的upload目录到${storage_dir}的脚本文件： ${script_file}，请手动确认脚本内容并执行该脚本完成操作："
    echo "bash ${script_file}"
    echo "==============================================================="
fi