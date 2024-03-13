# coding: utf-8
#-----------------------------
# 切换工具
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

class switchTools:

    def openCrontab(self, name):
        cronInfo = mw.M('crontab').where(
            'name=?', (name,)).field(crontabApi.field).find()
        if not cronInfo:
            print("计划任务不存在")
            return
        if cronInfo['status'] == 1:
            print("计划任务已经启用了")
            return

        mw.M('crontab').where('id=?', (cronInfo['id'],)).setField('status', 1)
        cronInfo['status'] = 1
        crontabApi.syncToCrond(cronInfo)
        print("启用定时任务" + name + "成功!")
            
    def closeCrontab(self, name):
        cronInfo = mw.M('crontab').where(
            'name=?', (name,)).field(crontabApi.field).find()
        if not cronInfo:
            print("计划任务不存在")
            return
        if cronInfo['status'] == 0:
            print("计划任务已经停用了")
            return

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

    def modifyCrontabCron(self, cron_config):
        iname = cron_config.get('name', '')
        iname_reg_str = cron_config.get('name_reg', '').replace("[", "\\[").replace("]", "\\]")
        cron_type = cron_config.get('type', '')
        week = cron_config.get('week', '')
        hour = cron_config.get('hour', '')
        minute = cron_config.get('minute', '')
        where1 = cron_config.get('where1', '')

        params = {
            'name': iname,
            'type': cron_type,
            'week': week,
            'where1': where1,
            'hour': hour,
            'minute': minute
        }

        
        is_check_pass, msg = crontabApi.cronCheck(params)
        if not is_check_pass:
            print(msg)
            return

        cuonConfig, get, name = crontabApi.getCrondCycle(params)
        crontabList = mw.M('crontab').field(crontabApi.field).select()
        cronInfo = None
        iname_reg = re.compile("^" + iname_reg_str + "$")
        for cron in crontabList:
            if re.match(iname_reg, cron["name"]):
              cronInfo = cron

        if cronInfo is None:
            print("计划任务【" + iname_reg_str + "】不存在")
            return
        
        sid = cronInfo['id']
        name = cronInfo['name']
        cronInfo['type'] = get['type']
        cronInfo['where1'] = get['where1']
        cronInfo['where_hour'] = get['hour']
        cronInfo['where_minute'] = get['minute']
        
        addData = mw.M('crontab').where('id=?', (sid,)).save('type,where1,where_hour,where_minute', (cronInfo['type'], cronInfo['where1'], cronInfo['where_hour'], cronInfo['where_minute']))
        crontabApi.removeCrond(cronInfo['echo'])
        crontabApi.syncToCrond(cronInfo)
        print("修改计划任务【" + name + "】成功!")

        
   
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
    elif type == 'modifyCrontabCron':
      """
      python3 /www/server/jh-panel/scripts/switch.py modifyCrontabCron '{"name":"[勿删]同步插件定时任务[113.197.36.162@wwwroot]","type":"day","hour":1,"minute":34}'
      """
      cron_config = json.loads(sys.argv[2])
      st.modifyCrontabCron(cron_config)
