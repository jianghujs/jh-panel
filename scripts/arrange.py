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

root_dir = '/www/wwwroot'
mysql_dir = '/www/server/mysql-apt'
mysql_cnf = os.path.join(mysql_dir, 'etc/my.cnf')


sys.path.append(chdir + '/plugins/mysql-apt')
from index import getDbPort, pMysqlDb, pSqliteDb

class arrangeTools:

    def findProjectUseDatabaseRootUser(self):
        if not os.path.exists(mysql_dir):
            print("未检测到mysql-apt插件目录")
            return
        
        db = pMysqlDb()
        psdb = pSqliteDb('databases')
        databases = psdb.field('id,pid,name,username,password,accept,rw,ps,addtime').select()
        databases_dict = {db['name']: {'user': db['username'], 'password': db['password']} for db in databases}

        host = '127.0.0.1'
        port = getDbPort()
        
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
                            print(f"当前文件{full_path}无法解析数据库名称。请手动处理。")
                            continue
                        db_name = db_name_match.group(1)
                        if db_name not in databases_dict:
                            print(f"在databases中不存在对应数据库名: {db_name}。请手动处理。")
                            continue
                        
                        # 解析用户名
                        user_match = re.search(r'[\'"]?user[\'"]?:\s*[\'"]?(\w+)[\'"]?', content)
                        if not user_match:
                            print(f"当前文件{full_path}无法解析用户名。请手动处理。")
                            continue
                            
                        user = user_match.group(1)
                        if user == 'root':
                            print(f"检测到配置文件{full_path}用户名为文件，正在修改配置文件信息为： host: {host}, port: {port}, user: {databases_dict[db_name]['user']}, password: {databases_dict[db_name]['password']}")
                            content = re.sub(r'([\'"]?host[\'"]?\s*:\s*)[\'"]\w+[\'"]', r'\1"' + host + '"', content)    
                            content = re.sub(r'([\'"]?port[\'"]?\s*:\s*)[\'"]\w+[\'"]', r'\1"' + port + '"', content)    
                            content = re.sub(r'([\'"]?user[\'"]?\s*:\s*)[\'"]\w+[\'"]', r'\1"' + databases_dict[db_name]['user'] + '"', content)
                            content = re.sub(r'([\'"]?password[\'"]?\s*:\s*)[\'"]\w+[\'"]', r'\1"' + databases_dict[db_name]['password'] + '"', content)
                            f.seek(0)
                            f.write(content)
                            print(f"|- 更新配置文件{full_path}完成✅")
                        else:
                            print(f"当前配置文件用户名为{user}，已跳过")
                            
                except Exception as e:
                    print(f"解析配置文件{full_path}异常！")






    def fixNoOrderLetsSite(self, params):
        email = params.get('email', None)
        siteInfo = systemApi.getSiteInfo()
        # 获取异常域名
        noOrderLetsSiteList = []
        for site in siteInfo.get("site_list", []):
            sslType = site.get("ssl_type", "")
            siteName = site.get("name", "")
            if sslType == 'lets':
                letsIndex = siteApi.getLetsIndex(siteName)
                if letsIndex == False:
                    noOrderLetsSiteList.append(site)
        if len(noOrderLetsSiteList) == 0:
            print("暂未发现异常网站订单")
            return

        for site in noOrderLetsSiteList:
            sslType = site.get("ssl_type", "")
            siteName = site.get("name", "")
            if sslType == 'lets':
                letsIndex = siteApi.getLetsIndex(siteName)
                if letsIndex == False:
                    print("|- 开始修复：%s" % siteName)
                    siteApi.closeSslConf(siteName)
                    print("|- 关闭%sSSL成功✅" % siteName)
                    siteApi.deleteSsl(siteName, "now")
                    print("|- 删除%sSSL配置成功✅" % siteName)
                    siteApi.deleteSsl(siteName, "lets")
                    print("|- 删除%sSSL证书成功✅" % siteName)
                    createLetForm = {
                        "siteName": siteName,
                        "domains": "[\"%s\"]" % siteName,
                        "force": True,
                        "email": email
                    }
                    siteApi.createLet(createLetForm)
                    print("|- 创建%sSSL证书成功✅" % siteName)
                    siteApi.deploySsl(siteName, "lets")
                    print("|- 部署%sSSL证书成功✅" % siteName)
   
if __name__ == "__main__":
    arrange = arrangeTools()
    type = sys.argv[1]

    if type == 'findProjectUseDatabaseRootUser':
        arrange.findProjectUseDatabaseRootUser()
    elif type == 'fixNoOrderLetsSite':
        params = json.loads(sys.argv[2])
        arrange.fixNoOrderLetsSite(params)
