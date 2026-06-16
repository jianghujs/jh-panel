
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
plugin_setting_file=${plugin_setting_file_input:-$plugin_setting_file}

plugin_setting_file_path="${plugin_setting_backup_dir}/${plugin_setting_file}"
if [ ! -f "$plugin_setting_file_path" ]; then
  show_error "错误:插件配置备份文件不存在：$plugin_setting_file_path"
  exit 1
fi

plugin_setting_restore_tmp=/tmp/plugin_setting-restore
rm -rf "$plugin_setting_restore_tmp"
mkdir -p "$plugin_setting_restore_tmp"
unzip -o "$plugin_setting_file_path" -d "$plugin_setting_restore_tmp/" > /dev/null

mapfile -t plugin_zip_files < <(find "$plugin_setting_restore_tmp" -maxdepth 1 -type f -name '*.zip' -printf '%f\n' | sort)
if [ ${#plugin_zip_files[@]} -eq 0 ]; then
  show_error "错误:备份文件中未找到插件配置zip文件"
  exit 1
fi

echo "可恢复的插件配置："
for i in "${!plugin_zip_files[@]}"; do
  plugin_name="${plugin_zip_files[$i]%.zip}"
  echo "$((i + 1)). ${plugin_name}"
done
prompt "请输入要恢复的插件序号或名称，多个用英文逗号分隔（默认全部）: " selected_plugins "all"

declare -A selected_map
if [ "$selected_plugins" = "all" ] || [ -z "$selected_plugins" ]; then
  for zipfile in "${plugin_zip_files[@]}"; do
    selected_map["${zipfile%.zip}"]=1
  done
else
  selected_plugins=${selected_plugins//，/,}
  IFS=',' read -ra selected_items <<< "$selected_plugins"
  for item in "${selected_items[@]}"; do
    item=$(echo "$item" | xargs)
    if [[ "$item" =~ ^[0-9]+$ ]]; then
      index=$((item - 1))
      if [ "$index" -ge 0 ] && [ "$index" -lt "${#plugin_zip_files[@]}" ]; then
        selected_map["${plugin_zip_files[$index]%.zip}"]=1
      else
        show_error "错误:插件序号超出范围：$item"
        exit 1
      fi
    elif [ -n "$item" ]; then
      selected_map["$item"]=1
    fi
  done
fi

if [ ${#selected_map[@]} -eq 0 ]; then
  show_error "错误:未选择任何插件"
  exit 1
fi

pushd $plugin_setting_restore_tmp > /dev/null
for zipfile in *.zip; do
    filename=$(basename "$zipfile" .zip)
    if [ -z "${selected_map[$filename]}" ]; then
        echo "跳过插件配置：$filename"
        continue
    fi
    server_dir=/www/server/$filename
    mkdir -p $server_dir
    echo "正在解压 $zipfile 到 $server_dir"
    unzip -o "$zipfile" -d "$server_dir"
done

popd > /dev/null
rm -rf "$plugin_setting_restore_tmp"
show_info "|- 恢复插件配置完成✅"
