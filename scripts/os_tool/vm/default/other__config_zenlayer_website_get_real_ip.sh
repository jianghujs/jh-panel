#!/bin/bash

source /www/server/jh-panel/scripts/util/msg.sh

# 配置网站代理协议
pushd /www/server/jh-panel > /dev/null

echo "-----------------------"
echo "说明："
echo "- 输入站点：www.xxx.com配置一个"
echo "- 输入all配置当前服务器全部站点"
echo "-----------------------"
read -p "请输入: " site_name

echo "-----------------------"
echo "- 站点: $site_name"
prompt "确认配置站点获取真实IP吗？（默认y）[y/n]: " confirm "y"
confirm=${confirm:-n}

case $confirm in
    [yY][eE][sS]|[yY])
        echo "开始配置..."
        ;;
    *)
        echo "已取消"
        exit 1
        ;;
esac



python3 /www/server/jh-panel/scripts/other.py config_zenlayer_website_get_real_ip "$site_name"

popd > /dev/null
