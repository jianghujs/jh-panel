
  # 恢复插件数据
  echo "" >> $tmp_prepare_script_file
  prompt "需要恢复插件配置吗？（默认n）[y/n]: " plugin_setting_restore_choice "n"

  if [ $plugin_setting_restore_choice == "y" ]; then
    prerepre_online_opts+="- 恢复插件配置\n"
    echo "# 恢复插件配置" >> $tmp_prepare_script_file
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
    
    echo "plugin_setting_restore_tmp=/tmp/plugin_setting-restore" >> $tmp_prepare_script_file
    echo "unzip -o $plugin_setting_backup_dir/$plugin_setting_file -d \$plugin_setting_restore_tmp/ >> \$log_file" >> $tmp_prepare_script_file
    
    echo "pushd \$plugin_setting_restore_tmp > /dev/null" >> $tmp_prepare_script_file
    echo "for zipfile in *.zip; do" >> $tmp_prepare_script_file
    echo "    filename=\$(basename \"\$zipfile\" .zip)" >> $tmp_prepare_script_file
    echo "    server_dir=/www/server/\$filename" >> $tmp_prepare_script_file
    echo "    mkdir -p \$server_dir" >> $tmp_prepare_script_file
    echo "    echo \"正在解压 \$zipfile 到 \$server_dir\"" >> $tmp_prepare_script_file
    echo "    unzip -o \"\$zipfile\" -d \"\$server_dir\" >> \$log_file" >> $tmp_prepare_script_file
    echo "done" >> $tmp_prepare_script_file

    echo "popd > /dev/null" >> $tmp_prepare_script_file
    echo "show_info \"|- 恢复插件配置✅\"" >> $tmp_prepare_script_file
    echo "" >> $tmp_prepare_script_file
  fi
  echo "popd > /dev/null" >> $tmp_prepare_script_file
