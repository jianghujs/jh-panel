# coding: utf-8
#-----------------------------
# 整理工具
#-----------------------------

import sys
import os
import json
import re
import datetime

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')


chdir = os.getcwd()
sys.path.append(chdir + '/class/core')

# reload(sys)
# sys.setdefaultencoding('utf-8')


import mw
import db
import time
import system_api
import site_api
systemApi = system_api.system_api()
siteApi = site_api.site_api()

mysql_dir = '/www/server/mysql-apt'
mysql_cnf = os.path.join(mysql_dir, 'etc/my.cnf')

sys.path.append(chdir + '/plugins/mysql-apt')
from index import getDbPort, pMysqlDb, pSqliteDb

class arrangeTools:

    def fixProjectConfigUseDatabaseRootUser(self):
        if not os.path.exists(mysql_dir):
            print("未检测到mysql-apt插件目录")
            return
        
        db = pMysqlDb()
        psdb = pSqliteDb('databases')
        databases = psdb.field('id,pid,name,username,password,accept,rw,ps,addtime').select()
        databases_dict = {db['name']: {'user': db['username'], 'password': db['password']} for db in databases}
        
        root_dir_input = input(f"请输入项目所在目录（默认为：/www/wwwroot）：")
        root_dir = root_dir_input if root_dir_input else '/www/wwwroot'
        fixConfigs = []
        
        print(f'-----------开始检测{root_dir}目录下的使用root账号的项目配置文件-------------')
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename != 'config.prod.js':
                    continue
                full_path = os.path.join(dirpath, filename)
                print(f"|- 正在检查配置文件：{full_path}")
                try:
                    with open(full_path, 'r+') as f:
                        content = f.read()
                        # 解析数据库名
                        db_name_match = re.search(r'[\'"]?database[\'"]?:\s*[\'"]?(\w+)[\'"]?', content)
                        if not db_name_match:
                            print(f"|--\033[31m当前文件{full_path}无法解析数据库名称。请手动处理。\033[0m")
                            continue

                        db_name = db_name_match.group(1)
                        if db_name not in databases_dict:
                            print(f"|--\033[31m在databases中不存在对应数据库名: {db_name}。请手动处理。\033[0m")
                            continue

                        if 'data_repository' in db_name:
                            print(f"|--\033[31m数据库名: {db_name}包含data_repository。已跳过。\033[0m")
                            continue
                            
                        # 解析地址
                        host_match = re.search(r'[\'"]?host[\'"]?:\s*[\'"]?([\w.]+)[\'"]?', content)
                        if not host_match:
                            print(f"|-- \033[31m当前文件{full_path}无法解析地址。请手动处理。\033[0m")
                            continue
                        host = host_match.group(1)
                        if host != '127.0.0.1' and host != 'localhost' and host != 'process.env.DB_HOST':
                            print(f"|-- \033[31m当前文件地址不是使用本地地址，实际地址为{host}。请手动处理。\033[0m")
                            continue
                        
                        # 解析用户名
                        user_match = re.search(r'[\'"]?user[\'"]?:\s*[\'"]?(\w+)[\'"]?', content)
                        if not user_match:
                            print(f"|-- \033[31m当前文件{full_path}无法解析用户名。请手动处理。\033[0m")
                            continue
                        user = user_match.group(1)

                        if user == 'root':
                            print(f"|-- 检测到配置文件{full_path}用户名为root")
                            fixConfigs.append({
                                "path": full_path,
                                "db_name": db_name,
                                "user": user
                            })
                        else:
                            print(f"|-- 当前配置文件用户名为{user}，已跳过")
                            
                except Exception as e:
                    print(e)
                    print(f"解析配置文件{full_path}异常！")
        
        print(f'------------------------------------------------------------------------------')
        # 修改配置文件
        if len(fixConfigs) == 0:
            print('暂未检测到使用root账号的项目配置文件!')
            return 
        confirm = input(f"检测到使用root账号的项目配置文件：{','.join(c.get('path', '') for c in fixConfigs)}，要更新这些配置文件，改为使用数据库本身的用户吗？（默认y）[y/n] ")
        confirm = confirm if confirm else 'y'
        if confirm.lower() == 'y':
            host = '127.0.0.1'
            port = getDbPort()
            for fixConfig in fixConfigs:
                config_path = fixConfig.get('path', '')
                db_name = fixConfig.get('db_name', '')
                with open(config_path, 'r+') as f:
                    print(f"|- 正在更新配置文件{full_path}... 数据库连接信息为： host: {host}, port: {port}, user: {databases_dict[db_name]['user']}, password: {databases_dict[db_name]['password']}")
                    content = f.read()
                    content = re.sub(r'([\'"]?host[\'"]?\s*:\s*)[\'"]\w+[\'"]', r'\1"' + host + '"', content)    
                    content = re.sub(r'([\'"]?port[\'"]?\s*:\s*)[\'"]\w+[\'"]', r'\1"' + port + '"', content)    
                    content = re.sub(r'([\'"]?user[\'"]?\s*:\s*)[\'"]\w+[\'"]', r'\1"' + databases_dict[db_name]['user'] + '"', content)
                    content = re.sub(r'([\'"]?password[\'"]?\s*:\s*)[\'"]\w+[\'"]', r'\1"' + databases_dict[db_name]['password'] + '"', content)
                    f.seek(0)
                    f.write(content)
                    print(f"|- 更新配置文件{full_path}完成✅")
            print("全部配置文件更新完成!✅")
        else:
            print("已取消")
   
if __name__ == "__main__":
    arrange = arrangeTools()
    type = sys.argv[1]

    if type == 'fixProjectConfigUseDatabaseRootUser':
        arrange.fixProjectConfigUseDatabaseRootUser()
    else:
        print("无效参数")