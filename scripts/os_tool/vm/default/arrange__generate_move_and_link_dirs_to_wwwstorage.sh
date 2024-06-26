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
script_file="/tmp/move_and_link_dirs_to_wwwstorage.sh"

read -p "请输入需要移动并链接的目录（多个用英文逗号隔开，默认为 upload: " dirs_input
dirs_input=${dirs_input:-"upload"}

# 将逗号替换为管道，以便在find命令中使用
IFS=',' read -ra dirs <<< "$dirs_input"

echo "" > $script_file

# 搜索所有目录，排除"node_modules"、"logs"、"run"目录
for cur_dir in "${dirs[@]}"; do
    find "$project_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" -o -name ".git" \) -prune -o -name "$cur_dir" -type d -print | while read dir
    do
        if [[ $dir != *"/app/"* ]]; then
            # 获取相对路径
            relative_path="${dir#$project_dir}"

            # 构建目标目录路径
            target_dir="$storage_dir$relative_path"

            # 创建目标目录及其父目录
            echo "# 移动 ${dir} 到 ${target_dir}" >> $script_file
            echo "mkdir -p \"$target_dir\"" >> $script_file
            
            # 使用 rsync 命令将 upload 目录复制到目标目录
            echo "rsync -a --delete \"$dir/\" \"$target_dir/\"" >> $script_file

            # 删除原始 upload 目录
            echo "rm -rf \"$dir\"" >> $script_file
            
            echo "|-- 添加 移动${dir} 到 ${target_dir}命令成功✅"
            

            # 创建软链接
            echo "# 链接 ${dir} 到 ${target_dir}" >> $script_file
            echo "ln -s \"$target_dir\" \"$dir\"" >> $script_file

            echo "|-- 添加 链接${dir} 到 ${target_dir}命令成功✅"

            # 如果是upload，则再增加一个创建multipartTmp目录并软链的命令
            if [[ $cur_dir == "upload" ]]; then
                echo "# 创建multipartTmp目录" >> $script_file
                echo "mkdir -p \"${target_dir/upload/multipartTmp}\"" >> $script_file
                # 判断是否存在multipartTmp目录
                if [ -d "${dir/upload/multipartTmp}" ]; then
                    echo "rsync -a --delete \"${dir/upload/multipartTmp}/\" \"${target_dir/upload/multipartTmp}/\"" >> $script_file
                fi
                echo "rm -rf \"${dir/upload/multipartTmp}\"" >> $script_file
                echo "ln -sf \"${target_dir/upload/multipartTmp}\" \"${dir/upload/multipartTmp}\""  >> $script_file
                echo "|-- 添加 链接${dir/upload/multipartTmp} 到 ${target_dir/upload/multipartTmp} 命令成功✅"
            fi
        fi
    done
done

echo ""
echo "===========================整理完成✅=========================="
echo "- 项目所在目录：$project_dir"
echo "- 项目数据存放目录：$storage_dir"
echo "---------------------------------------------------------------"
echo "已生成移动并连接${project_dir}下的${dirs_input}目录到${storage_dir}的脚本文件： ${script_file}，请手动确认脚本内容并执行该脚本完成操作："
echo "vi ${script_file}"
echo "bash ${script_file}"
echo "==============================================================="
