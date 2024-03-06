#!/bin/bash

# 获取异常网站
pushd /www/server/jh-panel > /dev/null
custom_ssl_site_info=$(python3 /www/server/jh-panel/scripts/arrange.py getCustomSSLSiteInfo)
popd > /dev/null

site_list=$(echo "$custom_ssl_site_info" | jq -r '.customSSLSiteList')
site_name_str=$(echo "$custom_ssl_site_info" | jq -r '.customSSLSiteNameStr')

if [ -z "$site_name_str" ]; then
  echo "暂无自定义证书网站"
  exit 0
fi


echo "存在【${site_name_str}】网站使用自定义证书"
# 输入要清空的域名
read -p "请输入要清空的域名（默认全部，多个用英文逗号隔开）: " opt_site_names
opt_site_names=${opt_site_names:-$site_list}

read -p "确定要清空【${opt_site_names}】的证书并重新申请为lets证书吗？（默认y）[y/n]: " confirm
confirm=${confirm:-y}
if [[ $confirm != "y" && $confirm != "Y" ]]; then
  echo "已取消操作"
  exit 0
fi

read -p "请输入域名管理员邮箱: " admin_email

pushd /www/server/jh-panel > /dev/null
python3 /www/server/jh-panel/scripts/arrange.py fixCustomSSLSite "{\"email\": \"${admin_email}\", \"optSiteNames\": \"${opt_site_names}\"}"
popd > /dev/null
