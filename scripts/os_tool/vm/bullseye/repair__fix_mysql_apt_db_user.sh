#!/bin/bash

# read -p "确定重建mysql数据库未记录密码的用户吗？（默认y）[y/n]: " choice
# choice=${choice:-"y"}

# if [ $choice == "y" ]; then
    pushd /www/server/jh-panel > /dev/null
    python3 /www/server/jh-panel/plugins/mysql-apt/index.py sync_get_databases
    python3 /www/server/jh-panel/plugins/mysql-apt/index.py fix_all_db_user
    popd > /dev/null



    
    filename="/www/server/mysql-apt/mysql.db"
    # 提示是否rsync同步
    read -p "需要将数据库信息文件${filename}同步到其他服务器吗?(默认n)[y/n]" sync
    sync=${sync:-n}


    if [ $sync == "y" ]; then
        sync_file=""
        # 输入目标服务器IP
        read -p "请输入备用服务器IP: " remote_ip
        if [ -z "$remote_ip" ]; then
        echo "错误:未指定目标服务器IP"
        exit 1
        fi

        # 输入目标服务器SSH端口
        read -p "请输入备用服务器SSH端口(默认: 10022): " remote_port
        remote_port=${remote_port:-10022}

        read -p "确定要同步${filename}到${remote_ip}:${filename}吗?(默认n)[y/n]" confirm
        confirm=${confirm:-n}
        if [ $confirm == "y" ]; then
            rsync -avu -e "ssh -p ${remote_port}" --progress /www/server/mysql-apt/mysql.db root@${remote_ip}:/www/server/mysql-apt/mysql.db
        fi
    fi
# fi