#!/bin/bash

# 检查/usr/bin/jq是否存在
if ! [ -x "/usr/bin/jq" ]; then
    echo "/usr/bin/jq不存在，正在尝试自动安装..."
    apt-get update
    apt-get install jq -y
    hash -r
    if ! [ -x "/usr/bin/jq" ]; then
        echo "安装jq失败，请手动安装后再运行脚本。"
        exit 1
    fi
fi

# 从环境变量中获取MIGRATE_DIR值
MIGRATE_DIR=${MIGRATE_DIR:-"/www/migrate/"}

# 当前系统如果存在/appdata/wwwroot/则默认为/appdata/wwwroot/否则为/www/wwwroot/
default_project_dir="/www/wwwroot/"
if [ -d "/appdata/wwwroot/" ]; then
    default_project_dir="/appdata/wwwroot/"
fi

# 提示”输入项目所在目录（默认/www/wwwroot/）”
read -p "输入项目所在目录（默认为：${default_project_dir}）: " project_dir
project_dir=${project_dir:-${default_project_dir}}
export PROJECT_DIR=$project_dir

# 提示"请输入需要忽略的目录（多个用英文逗号隔开，默认为：node_modules,logs,run）:"
read -p "请输入需要忽略的目录（多个用英文逗号隔开，默认为：node_modules,logs,run）: " ignore_dirs_input
ignore_dirs_input=${ignore_dirs_input:-"node_modules,logs,run"}
IFS=',' read -ra ignore_dirs <<< "$ignore_dirs_input"

# 定义存储迁移信息的json对象（如：migrate_info_project）
migrate_info_project='{"project_list": []}'

# 循环目录下的每个文件夹，获取git地址和所在提交点
for dir in $(ls -d ${project_dir}/*/); do
    pushd ${dir} > /dev/null
    git_url=""
    git_commit=""
    if [ -d .git ]; then
        git_url=$(git remote -v | grep "origin" | grep "(push)" | awk '{print $2}')
        git_commit=$(git log -1 --pretty=format:%H)
    fi
    project_name=$(basename ${dir})
    project_info=$(jq -n --arg projectName "${project_name}" --arg path "${dir}" --arg gitUrl "${git_url}" --arg gitCommit "${git_commit}" '{projectName: $projectName, path: $path, gitUrl: $gitUrl, gitCommit: $gitCommit}')
    migrate_info_project=$(echo ${migrate_info_project} | jq --argjson project_info "${project_info}" '.project_list += [$project_info]')
    popd > /dev/null
done

# 将每个项目的整个目录（除了忽略的目录）按 目录名称.zip 压缩存到 ${MIGRATE_DIR}/project_files/ 目录下
mkdir -p ${MIGRATE_DIR}/project_files/
for dir in $(ls -d ${project_dir}/*/); do
    pushd ${dir} > /dev/null
    project_name=$(basename ${dir})
    zip_command="zip --symlinks -r ${MIGRATE_DIR}/project_files/${project_name}.zip ."
    for ignore_dir in "${ignore_dirs[@]}"; do
        zip_command+=" -x '${ignore_dir}/*' '*/${ignore_dir}/*'"
    done
    zip_command+=" &>> ${MIGRATE_DIR}/pack_project_files.log"
    eval $zip_command
    popd > /dev/null
done

# 将目录下的软链提取到脚本
symbolic_links_file="${MIGRATE_DIR}/project_files/symbolic_links_origin.sh"
echo "" >  $symbolic_links_file

# 使用find命令搜索所有目录，排除忽略的目录
find_command="find \"$project_dir\" -type d \( "
for ignore_dir in "${ignore_dirs[@]}"; do
    find_command+="-name '${ignore_dir}' -o "
done
find_command+="-name '.git' \) -prune -o -print"
eval $find_command | while read dir
do
    echo "Processing directory: $dir" >> ${MIGRATE_DIR}/project_link.log

    # 如果目录是符号链接，则跳过
    if [ -L "$dir" ]; then
        echo "$dir is a symbolic link, skipping." >> ${MIGRATE_DIR}/project_link.log
        continue
    fi

    # 在每个目录中，查找所有的符号链接
    ls -l "$dir" | grep "^l" | while read line
    do
        # 提取软链接文件名和目标文件名
        link=$(echo $line | awk '{print $9}')
        target=$(echo $line | awk '{print $11}')

        # 获取软链接和目标文件的绝对路径
        abs_link=$(readlink -f "$dir/$link")
        abs_target=$(readlink -f "$dir/$target")

        # 生成进入目录和创建相同软链接的命令，并将其追加到links.sh文件中
        echo "cd $dir" >> $symbolic_links_file
        echo "unlink $link" >> $symbolic_links_file
        echo "ln -s $abs_target $abs_link" >> $symbolic_links_file
    done
done


# 在${MIGRATE_DIR}目录生成deploy_project.sh，内容如下：
cat << EOF > ${MIGRATE_DIR}/deploy_project.sh
#!/bin/bash

# 检查/usr/bin/jq是否存在
if ! [ -x "/usr/bin/jq" ]; then
    echo "/usr/bin/jq不存在，正在尝试自动安装..."
    apt-get update
    apt-get install jq -y
    hash -r
    if ! [ -x "/usr/bin/jq" ]; then
        echo "安装jq失败，请手动安装后再运行脚本。"
        exit 1
    fi
fi

# 提示“输入部署项目目录（默认/www/wwwroot/）”
read -p "请输入部署项目目录（默认/www/wwwroot/）: " deploy_dir
deploy_dir=\${deploy_dir:-"/www/wwwroot/"}
export DEPLOY_DIR=\$deploy_dir

# 循环migrate_info_project文件的project_list
while read project_info; do
    project_name=\$(echo \${project_info} | jq -r '.projectName')
    git_url=\$(echo \${project_info} | jq -r '.gitUrl')
    git_commit=\$(echo \${project_info} | jq -r '.gitCommit')
    project_dir=\${deploy_dir}\${project_name}

    echo "创建项目目录：\${project_dir}"
    mkdir -p \$project_dir

    echo "开始解压\${project_name}.zip到\${project_dir}"
    if [ -f "./project_files/\${project_name}.zip" ]; then
        unzip -o ./project_files/\${project_name}.zip -d \$project_dir
    fi


    pushd \$project_dir > /dev/null
    if [ -z "\${git_url}" ]; then  
        git config --global --add safe.directory \$project_dir
    fi
    popd > /dev/null
done < <(jq -c '.project_list[]' ./migrate_info_project.json)

# 部署软链
cp ./project_files/symbolic_links_origin.sh ./project_files/symbolic_links.sh 
# 在文件中替换字符串"${project_dir}"为"\${deploy_dir}"
sed -i 's|${project_dir}|\${deploy_dir}|g'./project_files/symbolic_links.sh 

echo "导入项目数据成功✔!"

# 统一配置root权限、安装依赖

jq -c '.project_list[]' ./migrate_info_project.json | while read project_info; do
    project_name=\$(echo \${project_info} | jq -r '.projectName')
    project_dir=\${deploy_dir}\${project_name}

    echo "开始安装依赖：\${project_dir}"
    pushd \$project_dir > /dev/null
    chown -R root:root .
    npm i
    popd > /dev/null
done
echo "项目依赖安装完成✔!"

EOF
chmod +x ${MIGRATE_DIR}/deploy_project.sh

# 把migrate_info_project的内容写入到 ${MIGRATE_DIR}/migrate_info_project.json
echo ${migrate_info_project} > ${MIGRATE_DIR}/migrate_info_project.json


