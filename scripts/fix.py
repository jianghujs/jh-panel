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

    def getNoOrderLetsSiteInfo(self):
        siteInfo = systemApi.getSiteInfo()
        siteInfo = {"site_list":[{"id":3,"name":"fintest.eggjs.tech","path":"/www/wwwroot/fintest.eggjs.tech","ps":"fintest.eggjs.tech","status":"1","addtime":"2023-09-19 14:39:26","http_to_https":True,"ssl_type":"custom","cert_data":{"issuer":"Sectigo RSA Domain Validation Secure Server CA","notAfter":"2024-03-09","notBefore":"2023-03-10","dns":["*.eggjs.tech","eggjs.tech"],"subject":"*.eggjs.tech","endtime":142}},{"id":1,"name":"hr.jianghujs.org","path":"/www/wwwroot/hr.jianghujs.org","ps":"hr.jianghujs.org","status":"1","addtime":"2023-09-19 14:39:26","http_to_https":True,"ssl_type":"lets","cert_data":{"issuer":"R3","notAfter":"2023-12-03","notBefore":"2023-09-04","dns":["hr.jianghujs.org"],"subject":"hr.jianghujs.org","endtime":45}}],"site_count":15,"active_count":15,"ssl_count":14}
        noOrderLetsSiteList = []
        for site in siteInfo.get("site_list", []):
            sslType = site.get("ssl_type", "")
            siteName = site.get("name", "")
            if sslType == 'lets':
                letsIndex = siteApi.getLetsIndex(siteName)
                if letsIndex == False:
                    noOrderLetsSiteList.append(site)
        print(mw.getJson({
            "noOrderLetsSiteList": noOrderLetsSiteList,
            "noOrderLetsSiteNameStr": ','.join([site['name'] for site in noOrderLetsSiteList])
        }))

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
   
if __name__ == "__main__":
    fix = fixTools()
    type = sys.argv[1]

    if type == 'getNoOrderLetsSiteInfo':
        fix.getNoOrderLetsSiteInfo()
    elif type == 'fixNoOrderLetsSite':
        params = json.loads(sys.argv[2])
        fix.fixNoOrderLetsSite(params)
