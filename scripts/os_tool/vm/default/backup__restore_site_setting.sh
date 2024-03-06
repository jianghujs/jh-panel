
source /www/server/jh-panel/scripts/util/msg.sh

default_site_setting_backup_dir="/www/backup/site_setting"
prompt "请输入网站配置备份文件所在目录（默认为：${default_site_setting_backup_dir}）: " site_setting_backup_dir $default_site_setting_backup_dir
# 获取最近的一个网站配置all文件
site_setting_file_path=$(ls -t ${site_setting_backup_dir}/all_*.zip | head -n 1)
if [ -z "$site_setting_file_path" ]; then
  show_error "错误:未找到网站配置备份文件"
  exit 1
fi
site_setting_file=$(basename ${site_setting_file_path})
prompt "请输入网站配置备份文件名称（默认为：${site_setting_file}）: " site_setting_file_input $site_setting_file

site_setting_restore_tmp=/tmp/site_setting-restore
unzip -o $site_setting_backup_dir/$site_setting_file -d $site_setting_restore_tmp/

pushd $site_setting_restore_tmp > /dev/null
python3 /www/server/jh-panel/scripts/migrate.py importSiteInfo $(pwd)/site_info.json
echo "导入站点数据完成✅!"

# 合并letsencrypt.json
python3 /www/server/jh-panel/scripts/migrate.py importLetsencryptOrder $(pwd)/letsencrypt.json
echo "合并letsencrypt.json完成✅!"

# 解压合并当前目录下的web_conf.zip到/www/server/web_conf/
unzip -o ./web_conf.zip -d /www/server/web_conf/
echo "恢复网站配置完成✅!"
popd > /dev/null

# 重启openresty
pushd /www/server/jh-panel > /dev/null
python3 /www/server/jh-panel/plugins/openresty/index.py restart
popd > /dev/null
echo "重启openresty完成✅!"

show_info "|- 恢复网站配置✅"
