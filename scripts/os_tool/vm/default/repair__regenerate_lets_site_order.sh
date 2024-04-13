#!/bin/bash
source /www/server/jh-panel/scripts/util/apt.sh
check_and_install "jq"

# 获取异常网站
pushd /www/server/jh-panel > /dev/null
lets_site_info=$(python3 /www/server/jh-panel/scripts/fix.py getLetsSiteInfo)
popd > /dev/null

site_list=$(echo "$lets_site_info" | jq -r '.letsSiteList')
site_name_str=$(echo "$lets_site_info" | jq -r '.letsSiteNameStr')

if [ -z "$site_name_str" ]; then
  echo "暂未发现使用lets证书的网站"
  exit 0
fi

read -p "存在【${site_name_str}】网站使用LetsEncrypt证书，确定要清空证书并重新申请吗？（默认y）[y/n]: " confirm
confirm=${confirm:-y}
if [[ $confirm != "y" && $confirm != "Y" ]]; then
  exit 0
fi

read -p "请输入域名管理员邮箱: " admin_email

# 修复异常网站
pushd /www/server/jh-panel > /dev/null
python3 /www/server/jh-panel/scripts/fix.py regenerateLetsSiteOrder "{\"email\": \"${admin_email}\"}"
popd > /dev/null
