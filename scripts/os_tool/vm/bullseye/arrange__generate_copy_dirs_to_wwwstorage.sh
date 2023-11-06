#!/bin/bash
default_project_dir="/www/wwwroot/"
default_storage_dir="/www/wwwstorage/"

read -p "输入项目所在目录（默认为：${default_project_dir}）: " project_dir
project_dir=${project_dir:-${default_project_dir}}
export PROJECT_DIR=$project_dir

read -p "输入项目数据存放目录（默认为：${default_storage_dir}）: " storage_dir
storage_dir=${storage_dir:-${default_storage_dir}}
export STORAGE_DIR=$storage_dir

project_dir=${PROJECT_DIR:-"/www/wwwroot/"}
storage_dir=${STORAGE_DIR:-"/www/wwwstorage/"}
script_file="copy_dirs_to_wwwstorage.sh"

read -p "请输入需要迁移的目录（多个用英文逗号隔开，默认为 upload,multipartTmp）: " dirs_input
dirs_input=${dirs_input:-"upload,multipartTmp"}

# 将逗号替换为管道，以便在find命令中使用
IFS=',' read -ra dirs <<< "$dirs_input"

echo "" > $script_file

for cur_dir in "${dirs[@]}"; do
  # 搜索所有目录，排除"node_modules"、"logs"、"run"目录
  find "$project_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" \) -prune -o -name "$cur_dir" -type d -print | while read dir
  do
    if [[ $dir != *"/app/"* ]]; then
        # 获取相对路径
        relative_path="${dir#$project_dir}"

        # 构建目标目录路径
        target_dir="$storage_dir$relative_path"

        # 创建目标目录及其父目录
        echo "mkdir -p \"$target_dir\"" >> $script_file

        # 生成复制命令
        cmd="rsync -a --delete \"$dir/\" \"$target_dir/\"" 
        echo $cmd >> $script_file

        echo "|-- 添加 复制${dir} 到 ${target_dir}命令成功✅"
    fi
  done
done

echo ""
echo "===========================生成脚本完成✅=========================="
echo "- 项目所在目录：$project_dir"
echo "- 项目数据存放目录：$storage_dir"
echo "---------------------------------------------------------------"
echo "已生成复制${project_dir}下的指定目录到${storage_dir}的脚本文件： ${script_file}，请手动确认脚本内容并执行该脚本完成操作："
echo "bash ${script_file}"
echo "==============================================================="
