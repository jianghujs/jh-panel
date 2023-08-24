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

# 获取环境变量中的MIGRATE_DIR值
MIGRATE_DIR=${MIGRATE_DIR:-"/www/migrate/"}

# 定义存储迁移信息的json对象（如：migrate_info_site）
migrate_info_site='{}'

# 执行 python3 /www/server/jh-panel/scripts/migrate.py exportSiteInfo，设置migrate_info_site.site_list为此列表
pushd /www/server/jh-panel > /dev/null
migrate_info_site=$(python3 /www/server/jh-panel/scripts/migrate.py exportSiteInfo)
popd > /dev/null

# 把migrate_info_site的内容写入到 迁移临时文件存放目录/migrate_info_site
echo ${migrate_info_site} > ${MIGRATE_DIR}/migrate_info_site.json

# 将/www/server/web_conf/压缩到 迁移临时文件存放目录/web_conf.zip

pushd /www/server/web_conf/ > /dev/null
zip -r ${MIGRATE_DIR}/web_conf.zip .
popd > /dev/null

# 在迁移临时文件存放目录生成deploy_site.sh，内容如下：
cat << EOF > ${MIGRATE_DIR}/deploy_site.sh
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

# 执行 python3 /www/server/jh-panel/scripts/migrate.py importSiteInfo，传入当前目录下的migrate_info_site文件路径恢复站点数据
python3 /www/server/jh-panel/scripts/migrate.py importSiteInfo \$(pwd)/migrate_info_site.json
echo "导入站点数据完成✔!"

# 解压覆盖当前目录下的web_conf.zip到/www/server/web_conf/
unzip -o ./web_conf.zip -d /www/server/web_conf/
echo "恢复网站配置完成✔!"

EOF
chmod +x ${MIGRATE_DIR}/deploy_site.sh
