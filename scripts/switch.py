# coding: utf-8
#-----------------------------
# 切换工具
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
import crontab_api
systemApi = system_api.system_api()
siteApi = site_api.site_api()
crontabApi = crontab_api.crontab_api()

class switchTools:

    def openCrontab(self, name):
        cronInfo = mw.M('crontab').where(
            'name=?', (name,)).field(crontabApi.field).find()
        if cronInfo is None:
            print("计划任务不存在")

        mw.M('crontab').where('id=?', (cronInfo['id'],)).setField('status', 1)
        crontabApi.syncToCrond(cronInfo)
        print("启用定时任务" + name + "成功!")
            
    def closeCrontab(self, name):
        cronInfo = mw.M('crontab').where(
            'name=?', (name,)).field(crontabApi.field).find()
        if cronInfo is None:
            print("计划任务不存在")

        mw.M('crontab').where('id=?', (cronInfo['id'],)).setField('status', 0)
        crontabApi.removeCrond(cronInfo['echo'])
        print("停用定时任务" + name + "成功!")
            
    def openEmailNotify(self):
        data = mw.getNotifyData(False)
        data['email']['enable'] = True
        mw.writeNotify(data)
        print("启用邮件通知成功!")

    def closeEmailNotify(self):
        data = mw.getNotifyData(False)
        data['email']['enable'] = False
        mw.writeNotify(data)
        print("关闭邮件通知成功!")
        
   
if __name__ == "__main__":
    st = switchTools()
    type = sys.argv[1]

    if type == 'openCrontab':
      name = sys.argv[2]
      st.openCrontab(name)
    elif type == 'closeCrontab':
      name = sys.argv[2]
      st.closeCrontab(name)
    elif type == 'openEmailNotify':
      st.openEmailNotify()
    elif type == 'closeEmailNotify':
      st.closeEmailNotify()
