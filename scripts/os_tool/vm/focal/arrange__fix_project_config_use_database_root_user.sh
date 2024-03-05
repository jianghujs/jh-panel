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
    python3 /www/server/jh-panel/scripts/arrange.py fixProjectConfigUseDatabaseRootUser
    popd > /dev/null
# fi