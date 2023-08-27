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

# 从环境变量中获取PROJECT_DIR值
project_dir=${PROJECT_DIR:-""}
if [ -z "$project_dir" ]; then
    read -p "请输入jianghujs项目所在目录（默认/www/wwwroot/）: " project_dir
    project_dir=${project_dir:-"/www/wwwroot/"}
fi

# 定义存储迁移信息的json对象（如：migrate_info_plugin）
migrate_info_plugin='{"project_dir": "'${project_dir}'"}'

# 创建${MIGRATE_DIR}/plugin_files目录
mkdir -p ${MIGRATE_DIR}/plugin_files/

# 打包/www/server/jianghujs目录下的data和script目录到${MIGRATE_DIR}/jianghujs.zip
pushd /www/server/jianghujs/ > /dev/null
zip -r ${MIGRATE_DIR}/plugin_files/jianghujs.zip ./data ./script
popd > /dev/null

# 在${MIGRATE_DIR}生成deploy_plugin.sh
cat << EOF > ${MIGRATE_DIR}/deploy_plugin.sh
#!/bin/bash

read -p "恢复jianghujs管理器数据后原数据将丢失，确定要这样做吗？（默认y）[y/n]: " confirm
confirm=\${confirm:-"y"}

if [ "\$confirm" != "y" ]; then
    echo "操作已取消"
    exit 1
fi

# 删除/www/server/jianghujs目录
rm -rf /www/server/jianghujs

# 解压./plugin_files/jianghujs.zip到/www/server/jianghujs
unzip -o ./plugin_files/jianghujs.zip -d /www/server/jianghujs

# 在/www/server/jianghujs/目录下执行以下脚本替换项目目录
find . -type f -print0 | while read -d \$'\0' file
do
  echo "正在替换\${file}"
  sed -i "s|${project_dir}|/www/wwwroot/|g" "\$file"
done
EOF
chmod +x ${MIGRATE_DIR}/deploy_plugin.sh

# 将migrate_info_plugin的内容写入到 ${MIGRATE_DIR}/migrate_info_plugin.json
echo ${migrate_info_plugin} > ${MIGRATE_DIR}/migrate_info_plugin.json
