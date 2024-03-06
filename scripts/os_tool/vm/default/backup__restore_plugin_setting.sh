
source /www/server/jh-panel/scripts/util/msg.sh

default_plugin_setting_backup_dir="/www/backup/plugin_setting"
prompt "请输入插件配置备份文件所在目录（默认为：${default_plugin_setting_backup_dir}）: " plugin_setting_backup_dir $default_plugin_setting_backup_dir
# 获取最近的一个插件配置all文件
plugin_setting_file_path=$(ls -t ${plugin_setting_backup_dir}/all_*.zip | head -n 1)
if [ -z "$plugin_setting_file_path" ]; then
  show_error "错误:未找到插件配置备份文件"
  exit 1
fi
plugin_setting_file=$(basename ${plugin_setting_file_path})
prompt "请输入插件配置备份文件名称（默认为：${plugin_setting_file}）: " plugin_setting_file_input $plugin_setting_file

plugin_setting_restore_tmp=/tmp/plugin_setting-restore
unzip -o $plugin_setting_backup_dir/$plugin_setting_file -d $plugin_setting_restore_tmp/

pushd $plugin_setting_restore_tmp > /dev/null
for zipfile in *.zip; do
    filename=$(basename "$zipfile" .zip)
    server_dir=/www/server/$filename
    mkdir -p $server_dir
    echo "正在解压 $zipfile 到 $server_dir"
    unzip -o "$zipfile" -d "$server_dir"
done

popd > /dev/null
show_info "|- 恢复插件配置✅"

