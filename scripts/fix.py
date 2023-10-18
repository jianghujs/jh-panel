# coding: utf-8
#-----------------------------
# 修复工具
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

class fixTools:

    def getNoOrderLetsSite(self):
        siteInfo = systemApi.getSiteInfo()
        siteInfo = {"site_list":[{"id":3,"name":"fintest.eggjs.tech","path":"/www/wwwroot/fintest.eggjs.tech","ps":"fintest.eggjs.tech","status":"1","addtime":"2023-09-19 14:39:26","http_to_https":True,"ssl_type":"custom","cert_data":{"issuer":"Sectigo RSA Domain Validation Secure Server CA","notAfter":"2024-03-09","notBefore":"2023-03-10","dns":["*.eggjs.tech","eggjs.tech"],"subject":"*.eggjs.tech","endtime":142}},{"id":1,"name":"hr.jianghujs.org","path":"/www/wwwroot/hr.jianghujs.org","ps":"hr.jianghujs.org","status":"1","addtime":"2023-09-19 14:39:26","http_to_https":True,"ssl_type":"lets","cert_data":{"issuer":"R3","notAfter":"2023-12-03","notBefore":"2023-09-04","dns":["hr.jianghujs.org"],"subject":"hr.jianghujs.org","endtime":45}}],"site_count":15,"active_count":15,"ssl_count":14}
        for site in siteInfo.get("site_list", []):
            print(site)
            siteApi.getLetsIndex(site.get(""))
        # print(mw.getJson(site))

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
                    result = json.loads(siteApi.add(json.dumps({"domain":importSite['name'],"domainlist":[],"count":1}), '80', importSite['ps'], '/www/wwwroot/' + importSite['name'], '00'))
                    if result['status'] == True:
                        print('创建站点%s成功' % importSite['name'])
                    else:
                        print('创建站点失败，' + result['msg'])

        
   
if __name__ == "__main__":
    fix = fixTools()
    type = sys.argv[1]

    if type == 'getNoOrderLetsSite':
        fix.getNoOrderLetsSite()
    elif type == 'importSiteInfo':
        siteInfoFile = sys.argv[2]
        migrate.importSiteInfo(siteInfoFile)
