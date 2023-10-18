#!/bin/bash

# 获取异常网站
pushd /www/server/jh-panel > /dev/null
no_order_lets_site_info=$(python3 /www/server/jh-panel/scripts/fix.py getNoOrderLetsSiteInfo)
popd > /dev/null

site_list=$(echo "$no_order_lets_site_info" | jq -r '.noOrderLetsSiteList')
site_name_str=$(echo "$no_order_lets_site_info" | jq -r '.noOrderLetsSiteNameStr')

echo $site_list
echo $site_name_str

if [ -z "$site_name_str" ]; then
  echo "暂未发现异常网站订单"
  exit 0
fi

read -p "存在【${site_name_str}】网站不存在订单数据，确定要清空证书并重新申请吗？（默认y）[y/n]: " confirm
confirm=${confirm:-y}
if [[ $confirm != "y" && $confirm != "Y" ]]; then
  exit 0
fi

read -p "请输入域名管理员邮箱: " admin_email

# 修复异常网站
pushd /www/server/jh-panel > /dev/null
python3 /www/server/jh-panel/scripts/fix.py fixNoOrderLetsSite "{\"email\": \"${admin_email}\"}"
popd > /dev/null
