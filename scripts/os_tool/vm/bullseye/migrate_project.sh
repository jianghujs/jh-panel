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

# 定义存储迁移信息的json对象（如：migrate_info_project）
migrate_info_project='{"project_list": []}'

# 循环目录下的每个文件夹，获取git地址和所在提交点
for dir in $(ls -d ${project_dir}/*/); do
    pushd ${dir} > /dev/null
    if [ -d .git ]; then
        git_url=$(git remote -v | grep "origin" | grep "(push)" | awk '{print $2}')
        git_commit=$(git log -1 --pretty=format:%H)
        project_name=$(basename ${dir})
        project_info=$(jq -n --arg projectName "${project_name}" --arg path "${dir}" --arg gitUrl "${git_url}" --arg gitCommit "${git_commit}" '{projectName: $projectName, path: $path, gitUrl: $gitUrl, gitCommit: $gitCommit}')
        migrate_info_project=$(echo ${migrate_info_project} | jq --argjson project_info "${project_info}" '.project_list += [$project_info]')
        popd > /dev/null
    fi
done

# 将每个项目的整个目录（除了node_modules和logs）按 目录名称.zip 压缩存到 ${MIGRATE_DIR}/project_files/ 目录下
mkdir -p ${MIGRATE_DIR}/project_files/
for dir in $(ls -d ${project_dir}/*/); do
    pushd ${dir} > /dev/null
    project_name=$(basename ${dir})
    zip -r ${MIGRATE_DIR}/project_files/${project_name}.zip . -x *node_modules* *logs*
    popd > /dev/null
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

# 循环migrate_info_project文件的project_list
while read project_info; do
    project_name=\$(echo \${project_info} | jq -r '.projectName')
    git_url=\$(echo \${project_info} | jq -r '.gitUrl')
    git_commit=\$(echo \${project_info} | jq -r '.gitCommit')
    project_dir=\${deploy_dir}\${project_name}

    echo ">>>>>>>>>>>>>>>>>>> Start 部署\${git_url}到\${project_dir}"
    mkdir -p \$project_dir
    pushd \$project_dir > /dev/null
    git clone \${git_url} .
    popd > /dev/null
    echo "开始解压\${project_name}.zip到\${project_dir}"
    if [ -f "./project_files/\${project_name}.zip" ]; then
        unzip -o ./project_files/\${project_name}.zip -d \$project_dir
    fi
    echo ">>>>>>>>>>>>>>>>>>> End 部署\${git_url}到\${project_dir}"
done < <(jq -c '.project_list[]' ./migrate_info_project.json)

echo "导入项目数据成功✔!"

# 统一安装依赖

jq -c '.project_list[]' ./migrate_info_project.json | while read project_info; do
    project_name=\$(echo \${project_info} | jq -r '.projectName')
    project_dir=\${deploy_dir}\${project_name}

    echo "开始安装依赖：\${project_dir}"
    pushd \$project_dir > /dev/null
    npm i
    popd > /dev/null
done
echo "项目依赖安装完成✔!"

EOF
chmod +x ${MIGRATE_DIR}/deploy_project.sh

# 把migrate_info_project的内容写入到 ${MIGRATE_DIR}/migrate_info_project.json
echo ${migrate_info_project} > ${MIGRATE_DIR}/migrate_info_project.json
