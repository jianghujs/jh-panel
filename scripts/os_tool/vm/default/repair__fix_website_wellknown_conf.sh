#!/bin/bash
source /www/server/jh-panel/scripts/util/apt.sh
source /www/server/jh-panel/scripts/util/msg.sh


prompt "需要更新所有网站的wellknown配置吗？（默认n）[y/n]: " confirm "n"
confirm=${confirm:-y}
if [[ $confirm != "y" && $confirm != "Y" ]]; then
  exit 0
fi


pushd /www/server/jh-panel > /dev/null
python3 /www/server/jh-panel/scripts/fix.py fixWebsiteWellknownConf
popd > /dev/null
