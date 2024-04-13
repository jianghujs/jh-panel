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
                    siteApi.deploySsl(siteName, "lets")
                    print("|- 部署%sSSL证书成功✅" % siteName)
   
    def getLetsSiteInfo(self):
        siteInfo = systemApi.getSiteInfo()
        letsSiteList = []
        for site in siteInfo.get("site_list", []):
            sslType = site.get("ssl_type", "")
            siteName = site.get("name", "")
            if sslType == 'lets':
                letsSiteList.append(site)
        print(mw.getJson({
            "letsSiteList": letsSiteList,
            "letsSiteNameStr": ','.join([site['name'] for site in letsSiteList])
        }))

    def regenerateLetsSiteOrder(self, params):
        email = params.get('email', None)
        siteInfo = systemApi.getSiteInfo()
        # 获取异常域名
        letsSiteList = []
        for site in siteInfo.get("site_list", []):
            sslType = site.get("ssl_type", "")
            siteName = site.get("name", "")
            if sslType == 'lets':
                letsSiteList.append(site)
        if len(letsSiteList) == 0:
            print("暂未发现使用lets证书的网站")
            return

        for site in letsSiteList:
            sslType = site.get("ssl_type", "")
            siteName = site.get("name", "")
            if sslType == 'lets':
                print("|- 开始重建：%s" % siteName)
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
    fix = fixTools()
    type = sys.argv[1]

    if type == 'getNoOrderLetsSiteInfo':
        fix.getNoOrderLetsSiteInfo()
    elif type == 'fixNoOrderLetsSite':
        params = json.loads(sys.argv[2])
        fix.fixNoOrderLetsSite(params)
    elif type == 'getLetsSiteInfo':
        fix.getLetsSiteInfo()
    elif type == 'regenerateLetsSiteOrder':
        params = json.loads(sys.argv[2])
        fix.regenerateLetsSiteOrder(params)
