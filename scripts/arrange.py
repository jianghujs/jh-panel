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
import crontab_api
systemApi = system_api.system_api()
siteApi = site_api.site_api()
crontabApi = crontab_api.crontab_api()

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
            if 'node_modules' in dirpath:
                continue
            for filename in filenames:
                if filename != 'config.prod.js':
                    continue
                full_path = os.path.join(dirpath, filename)
                print(f"|- 正在检查配置文件：{full_path}")
                try:
                    with open(full_path, 'r+') as f:
                        content = f.read()
                        # 解析数据库名
                        db_name_match = re.search(r'[\'"]?database[\'"]?:\s*[\'"]?([\w.-]+)[\'"]?', content)
                        if not db_name_match:
                            print(f"|--\033[31m当前文件{full_path}无法解析数据库名称。请手动处理。\033[0m")
                            continue

                        db_name = db_name_match.group(1)
                        if db_name not in databases_dict:
                            print(f"|--\033[31m在databases中不存在对应数据库名: {db_name}。请手动处理。\033[0m")
                            continue

                        if 'data_repository' in db_name:
                            print(f"|--数据库名: {db_name}包含data_repository。已跳过。")
                            continue
                            
                        # 解析地址
                        host_match = re.search(r'[\'"]?host[\'"]?:\s*[\'"]?([\w.-]+)[\'"]?', content)
                        if not host_match:
                            print(f"|-- \033[31m当前文件{full_path}无法解析地址。请手动处理。\033[0m")
                            continue
                        host = host_match.group(1)
                        if host != '127.0.0.1' and host != 'localhost' and host != 'process.env.DB_HOST':
                            print(f"|-- 当前文件地址地址为{host}。已跳过。")
                            continue
                        
                        # 解析用户名
                        user_match = re.search(r'[\'"]?user[\'"]?:\s*[\'"]?([\w.-]+)[\'"]?', content)
                        if not user_match:
                            print(f"|-- \033[31m当前文件{full_path}无法解析用户名。请手动处理。\033[0m")
                            continue
                        user = user_match.group(1)

                        print(f"|-- \033[36m检测到配置文件{full_path}用户名为{user}\033[0m")
                        fixConfigs.append({
                            "path": full_path,
                            "db_name": db_name,
                            "user": user
                        })
                            
                except Exception as e:
                    print(f"\033[31m解析配置文件{full_path}异常！\033[0m")
                    print(e)
        
        print(f'------------------------------------------------------------------------------')
        # 修改配置文件
        if len(fixConfigs) == 0:
            print('暂未检测到使用非本数据库账号的项目配置文件!')
            return 
        confirm = input(f"检测到使用非本数据库账号的项目配置文件：{','.join(c.get('path', '') for c in fixConfigs)}，要更新这些配置文件，改为使用数据库本身的用户吗？（默认y）[y/n] ")
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
                    content = re.sub(r'([\'"]?host[\'"]?\s*:\s*)[\'"]?[\w.-]+[\'"]?', r'\1"' + host + '"', content)    
                    content = re.sub(r'([\'"]?port[\'"]?\s*:\s*)[\'"]?[\w.-]+[\'"]?', r'\1"' + port + '"', content)    
                    content = re.sub(r'([\'"]?user[\'"]?\s*:\s*)[\'"]?[\w.-]+[\'"]?', r'\1"' + databases_dict[db_name]['user'] + '"', content)
                    content = re.sub(r'([\'"]?password[\'"]?\s*:\s*)[\'"]?[\w.-]+[\'"]?', r'\1"' + databases_dict[db_name]['password'] + '"', content)
                    f.seek(0)
                    mw.writeFile(config_path, content)
                    print(f"|- 更新配置文件{full_path}完成✅")
            print("全部配置文件更新完成!✅")
        else:
            print("已取消")
    
    def cleanSysCrontab(self):
        print("|- 正在检测系统crontab...")
        
        crontab_list = mw.M('crontab').field(crontabApi.field).order('id desc').select()
        crontab_echo_list = [item['echo'] for item in crontab_list]
        
        # 待清理的crontab列表
        sys_crontab_clean_list = []
        sys_crontab_clean_index_list = []

        # 获取系统crontab列表
        sys_crontab_list = mw.execShell('crontab -l')[0]
        sys_crontab_list = sys_crontab_list.split("\n")
        sys_crontab_result_list = []
        sys_crontab_repeat_echo_list = []
        for index,item in enumerate(sys_crontab_list):
            if not item:
                sys_crontab_result_list.append(item)
                continue
            sys_echo_result = re.search(r'\/www\/server\/cron\/([\w.-]+)', item)
            if not sys_echo_result:
                sys_crontab_result_list.append(item)
                continue
            sys_echo = sys_echo_result.group(1)
            
            # 检查任务是否存在或者是否重复
            if sys_echo not in crontab_echo_list or sys_echo in sys_crontab_repeat_echo_list:
                sys_crontab_clean_list.append(item)
                sys_crontab_clean_index_list.append(index)
            else:
                sys_crontab_result_list.append(item)

            if sys_echo not in sys_crontab_repeat_echo_list:
                sys_crontab_repeat_echo_list.append(sys_echo)
        
        if len(sys_crontab_clean_list) == 0:
            print('暂无需要清理的crontab任务')
            return

        # # 检查crontab_list中存在但是sys_crontab_list不存在的任务
        # for item in crontab_list:
        #     if item['echo'] not in sys_crontab_repeat_echo_list:
        #         print(f"\033[31m检测到crontab任务{item['echo']}在数据库中存在，但是系统中不存在。\033[0m")
                
        try:
          print(f"\033[31m检测到需要清理的crontab任务（{len(sys_crontab_clean_list)}）：") 
          # 用红色字体打印换行的sys_crontab_clean_list
          print("\n".join(sys_crontab_clean_list) + "\033[0m")
          print(f"即将重建crontab为（{len(sys_crontab_result_list)}）：")
          print("\n".join(sys_crontab_result_list))
          confirm = input(f"确定要这样做吗？（默认y）[y/n] ")
          confirm = confirm if confirm else 'y'
          if confirm.lower() == 'y':
              # 重新使用sys_crontab_result_list生成crontab
              mw.writeFile('/tmp/crontab.tmp', "\n".join(sys_crontab_result_list) + "\n")
              mw.execShell(f"crontab /tmp/crontab.tmp")
              print("重建crontab完成！✅") 
        except KeyboardInterrupt as e:
          print("已取消")
        except Exception as e:
          print(e)

    
    def getCustomSSLSiteInfo(self):
        siteInfo = systemApi.getSiteInfo()
        customSSLSiteList = []
        for site in siteInfo.get("site_list", []):
            sslType = site.get("ssl_type", "")
            siteName = site.get("name", "")
            if sslType == 'custom':
                customSSLSiteList.append(site)
        print(mw.getJson({
            "customSSLSiteList": customSSLSiteList,
            "customSSLSiteNameStr": ','.join([site['name'] for site in customSSLSiteList])
        }))
    
    def fixCustomSSLSite(self, params):
        email = params.get('email', None)
        optSiteNames = params.get('optSiteNames', "all")
        excludeSiteNames = params.get('excludeSiteNames', "")
        if not email:
            print("请传入email参数")
            return
        siteInfo = systemApi.getSiteInfo()
        customSSLSiteList = []
        for site in siteInfo.get("site_list", []):
            sslType = site.get("ssl_type", "")
            siteName = site.get("name", "")
            if sslType == 'custom' and (optSiteNames == 'all' or siteName in optSiteNames):
              if excludeSiteNames and siteName in excludeSiteNames:
                print('跳过：%s' % siteName)
                continue
              customSSLSiteList.append(site)

        if len(customSSLSiteList) == 0:
            print('暂未发现自定义SSL网站')
            return

        for site in customSSLSiteList:
            sslType = site.get("ssl_type", "")
            siteName = site.get("name", "")
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

    if type == 'fixProjectConfigUseDatabaseRootUser':
        arrange.fixProjectConfigUseDatabaseRootUser()
    elif type == 'cleanSysCrontab':
        arrange.cleanSysCrontab()
    elif type == 'getCustomSSLSiteInfo':
        arrange.getCustomSSLSiteInfo()
    elif type == 'fixCustomSSLSite':
        params = json.loads(sys.argv[2])
        arrange.fixCustomSSLSite(params)
    else:
        print("无效参数")