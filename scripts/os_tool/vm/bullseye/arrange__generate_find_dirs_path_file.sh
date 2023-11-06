#!/bin/bash

default_find_dir="/www/wwwroot/"
read -p "输入查找的根目录（默认为：${default_find_dir}）: " find_dir
find_dir=${find_dir:-${default_find_dir}}

path_file="find_dirs_path.txt"

read -p "请输入需要查找目录（多个用英文逗号隔开，默认为 .git）: " dirs_input
dirs_input=${dirs_input:-".git"}

# 将逗号替换为管道，以便在find命令中使用
IFS=',' read -ra dirs <<< "$dirs_input"

echo "" > $path_file

for cur_dir in "${dirs[@]}"; do
  # 搜索所有目录，排除"node_modules"、"logs"、"run"目录
  find "$find_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" \) -prune -o -name "$cur_dir" -type d -print | while read dir
  do
    echo "${dir#$find_dir}/" >> $path_file

    echo "|-- 添加${dir}成功✅"
  done
done

echo ""
echo "===========================生成脚本完成✅=========================="
echo "- 根目录：$find_dir"
echo "- 查找目录名：$dirs_input"
echo "---------------------------------------------------------------"
echo "已生成${find_dir}下的全部${dirs_input}目录路径文件：${path_file}"
echo "你可以使用这个文件作为rsync辅助文件，例如："
echo "- 同步这些目录到其他服务器：rsync -avz -e \"ssh -p 10022\" --files-from="${path_file}" ${find_dir} root@x.x.x.x:${find_dir}"
echo "- 同步除了这些目录以外的目录到其他服务器：rsync -avz -e \"ssh -p 10022\" --exclude-from="${path_file}" ${find_dir} root@x.x.x.x:${find_dir}"
echo "==============================================================="
