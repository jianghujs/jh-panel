#!/bin/bash

project_dir=${PROJECT_DIR:-"/www/wwwroot/"}
storage_dir=${STORAGE_DIR:-"/www/wwwstorage/"}
script_file="copy_upload_to_wwwstorage.sh"

read -p "确定生成复制${project_dir}下的upload目录到${storage_dir}的脚本文件吗？（默认y）[y/n]: " choice
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
        mkdir -p "$target_dir"

        # 生成复制命令
        cmd="rsync -a \"$dir/\" \"$target_dir\"" 
        echo $cmd >> $script_file

        echo "|-- 添加 复制${dir} 到 ${target_dir}命令成功✅"
    done

    echo ""
    echo "===========================生成脚本完成✅=========================="
    echo "- 项目所在目录：$project_dir"
    echo "- 项目数据存放目录：$storage_dir"
    echo "---------------------------------------------------------------"
	echo "已生成复制${project_dir}下的upload目录到${storage_dir}的脚本文件： ${script_file}，请手动确认脚本内容并执行该脚本完成操作："
    echo "bash ${script_file}"
    echo "==============================================================="
fi
