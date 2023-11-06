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
project_dir_exist_dirs=()
script_file="link_dirs_to_wwwstorage.sh"

read -p "确定要生成链接${project_dir}下的目录到${storage_dir}的脚本文件吗？（默认y）[y/n]: " choice
choice=${choice:-"y"}

read -p "请输入需要移动并链接的目录（多个用英文逗号隔开，默认为 upload: " dirs_input
dirs_input=${dirs_input:-"upload"}

# 将逗号替换为管道，以便在find命令中使用
IFS=',' read -ra dirs <<< "$dirs_input"

echo "" > $script_file

if [ $choice == "y" ]; then

  # 搜索所有目录，排除"node_modules"、"logs"、"run"目录
  for cur_dir in "${dirs[@]}"; do
    # 查找project_dir下已存在的目录
    echo "|- 正在查找项目目录下已存在的目录..."
    while IFS= read -r -d '' dir; do
      if [[ $dir != *"/app/"* ]]; then
              # 获取相对路径
              relative_path="${dir#$storage_dir}"

              # 构建目标目录路径
              target_dir="$project_dir$relative_path"    
              
              if [ -d "$target_dir" ]; then
                  project_dir_exist_dirs+=("$target_dir")
              fi
          fi
    done < <(find "$storage_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" -o -name ".git" \) -prune -o -name "$cur_dir"  -type d -print0)
      

    if [ ${#project_dir_exist_dirs[@]} -gt 0 ]; then
          echo "检测到${project_dir}下存在以下与${storage_dir}同名的目录："
          for dir in "${project_dir_exist_dirs[@]}"
          do
              echo "- $dir"
          done

          read -p "要生成删除这些目录的脚本吗？(默认y) [y/n]: " delete_choice
          delete_choice=${delete_choice:-"y"}
          if [ $delete_choice == "y" ]; then
            for dir in "${project_dir_exist_dirs[@]}"
            do
          
              echo "rm -rf \"$dir\""  >> $script_file
          echo "|-- 添加 删除${dir}命令成功✅"
            done
          fi
      
      fi

      # 搜索所有目录，排除"node_modules"、"logs"、"run"目录
      find "$storage_dir" -type d \( -name "node_modules" -o -name "logs" -o -name "run" -o -name ".git" \) -prune -o -name "$cur_dir"  -type d -print | while read dir
      do
      if [[ $dir != *"/app/"* ]]; then
              # 获取相对路径
              relative_path="${dir#$storage_dir}"

              # 构建目标目录路径
              target_dir="$project_dir$relative_path"
      
              # 创建软链接
              echo "ln -s \"$dir\" \"$target_dir\"" >> $script_file

              echo "|-- 添加 链接${target_dir} 到 ${dir}命令成功✅"

              # 如果是upload，则再增加一个创建multipartTmp目录并软链的命令
              if [[ $cur_dir == "upload" ]]; then
                  echo "mkdir -p \"${dir/upload/multipartTmp}\"" >> $script_file
                  echo "rm -rf \"${target_dir/upload/multipartTmp}\"" >> $script_file
                  echo "ln -sf \"${dir/upload/multipartTmp}\" \"${target_dir/upload/multipartTmp}\""  >> $script_file
                  echo "|-- 添加 链接${target_dir/upload/multipartTmp} 到 ${dir/upload/multipartTmp} 命令成功✅"
              fi
          fi
      done

      
      echo ""
      echo "===========================生成脚本完成✅=========================="
      echo "- 项目所在目录：$project_dir"
      echo "- 项目数据存放目录：$storage_dir"
      echo "---------------------------------------------------------------"
    echo "已生成链接${project_dir}下的目录到${storage_dir}的脚本文件： ${script_file}，请手动确认脚本内容并执行该脚本完成操作："
      echo "bash ${script_file}"
      echo "==============================================================="
  done
fi