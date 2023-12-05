#!/bin/bash

# read -p "确定重建mysql数据库未记录密码的用户吗？（默认y）[y/n]: " choice
# choice=${choice:-"y"}

# if [ $choice == "y" ]; then
    pushd /www/server/jh-panel > /dev/null
    python3 /www/server/jh-panel/scripts/arrange.py fixProjectConfigUseDatabaseRootUser
    popd > /dev/null
# fi