#!/bin/bash

# read -p "确定重建mysql数据库未记录密码的用户吗？（默认y）[y/n]: " choice
# choice=${choice:-"y"}

# if [ $choice == "y" ]; then
    pushd /www/server/jh-panel > /dev/null
    if [ ! -d "/www/server/mysql-apt" ]; then
        echo "检测到未使用mysql-apt"
        exit 0
    fi
    mysql_status=$(python3 /www/server/jh-panel/plugins/mysql-apt/index.py status)
    if [ $mysql_status != 'start' ]; then
        echo "检测到mysql-apt已停用，请启用后重试"
        exit 0
    fi
    
    python3 /www/server/jh-panel/plugins/mysql-apt/index.py sync_get_databases
    python3 /www/server/jh-panel/plugins/mysql-apt/index.py fix_all_db_user
    popd > /dev/null



    
    filename="/www/server/mysql-apt/mysql.db"
    # 提示是否rsync同步
    read -p "需要将数据库信息文件${filename}同步到其他服务器吗?(默认n)[y/n]" sync
    sync=${sync:-n}


    if [ $sync == "y" ]; then
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
            rsync -avu -e "ssh -p ${remote_port}" --progress --delete "${filename}" "root@${remote_ip}:${filename}"
        fi
    fi
# fi