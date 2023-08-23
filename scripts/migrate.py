# coding: utf-8
#-----------------------------
# 迁移工具
#-----------------------------

import sys
import os
import json
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

class migrateTools:

    def exportSiteInfo(self):
        siteInfo = systemApi.getSiteInfo()
        print(mw.getJson(siteInfo))

    def importSiteInfo(self, siteInfoFile):
        currentSiteInfo = systemApi.getSiteInfo()
        currentSiteList = currentSiteInfo['site_list']
        # 读取siteInfoFile文件内容并转为json
        with open(siteInfoFile, 'r') as f:
            importSiteInfo = json.load(f)
            importSiteList = importSiteInfo['site_list']
            print(importSiteList)
            # 循环对比currentSiteList每个对象的name值和importSiteList的name值，找出不存在的site并创建
            for importSite in importSiteList:
                if any(curentSite.get('name', None) == importSite.get('name', None) for curentSite in currentSiteList) == False:
                    print('开始创建站点：' + importSite['name'])
                    result = json.loads(siteApi.add(json.dumps({"domain":importSite['name'],"domainlist":[],"count":1}), '80', importSite['ps'], '/www/wwwroot/', '00'))
                    if result['status'] == True:
                        print('创建站点%s成功' % importSite['name'])
                    else:
                        print('创建站点失败，' + result['msg'])

        
   
if __name__ == "__main__":
    migrate = migrateTools()
    type = sys.argv[1]

    if type == 'exportSiteInfo':
        migrate.exportSiteInfo()
    elif type == 'importSiteInfo':
        siteInfoFile = sys.argv[2]
        migrate.importSiteInfo(siteInfoFile)
