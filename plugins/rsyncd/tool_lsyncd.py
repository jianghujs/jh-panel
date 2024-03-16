# coding:utf-8

import sys
import io
import os
import time
import json

sys.path.append(os.getcwd() + "/class/core")
import mw
import crontab_api
crontabApi = crontab_api.crontab_api()

import index as rsyncdApi


app_debug = False
if mw.isAppleSystem():
    app_debug = True


def lsyncdModifyCron(args):
    name_reg = args['name_reg']
    data = rsyncdApi.getDefaultConf()
    slist = data['send']["list"]
    res = rsyncdApi.lsyncdListFindNameReg(slist, name_reg)
    retdata = {}

    if not res[0]:
      print(f"任务{name_reg}不存在")
      return
  
    list_index = res[1]
    realtime = args.get('realtime', 'false')
    period = args.get('period', 'day')
    hour = args.get('hour', '0')
    minute = args.get('minute', '0')
    minute_n = args.get('minute-n', '1')
    slist[list_index]["realtime"] = realtime
    slist[list_index]["period"] = period
    slist[list_index]["hour"] = hour
    slist[list_index]["minute"] = minute
    slist[list_index]["minute-n"] = minute_n

    data['send']["list"] = slist
    rsyncdApi.setDefaultConf(data)
    rsyncdApi.makeLsyncdConf(data)

    print("修改成功")

  
def lsyncdAddExclude(args):

    name_reg = args['name_reg']
    exclude = args['exclude']

    data = rsyncdApi.getDefaultConf()
    slist = data['send']["list"]
    res = rsyncdApi.lsyncdListFindNameReg(slist, name_reg)
    if not res[0]:
      print(f"任务{name_reg}不存在")
      return
    i = res[1]
    info = slist[i]

    exclude_list = info['exclude']
    if exclude in exclude_list:
        print(f"已经存在忽略项目{exclude}！")
        return
    exclude_list.append(exclude)

    data['send']["list"][i]['exclude'] = exclude_list
    rsyncdApi.setDefaultConf(data)
    rsyncdApi.makeLsyncdConf(data)
    print(f"添加忽略项{exclude}到{info['name']}成功")

def updateLsyncdLogCutShell():
    task_name = "[勿删]lsyncd实时日志切割"
    cronInfo = mw.M('crontab').where(
        'name=?', (task_name,)).field(crontabApi.field).find()
    if not cronInfo:
        print(f"{task_name}计划任务不存在")
        return
    print("cronInfo", cronInfo)
    cronInfo['sbody'] = f"""
#!/bin/bash
timestamp=$(date +%Y%m%d_%H%M%S)
cp /www/server/rsyncd/logs/lsyncd.status /www/server/rsyncd/logs/lsyncd_\${{timestamp}}.status
mv /www/server/rsyncd/logs/lsyncd.log /www/server/rsyncd/logs/lsyncd_\${{timestamp}}.log

python3 /www/server/jh-panel/scripts/clean.py /www/server/rsyncd/logs/ '{{"saveAllDay": "3", "saveOther": "1", "saveMaxDay": "30"}}'
  """
    addData = mw.M('crontab').where('id=?', (cronInfo['id'],)).save(
        'sbody', (cronInfo['sbody'],))
    crontabApi.removeCrond(cronInfo['echo'])
    crontabApi.syncToCrond(cronInfo)
    print(f"修改计划任务【{task_name}】成功!")

if __name__ == "__main__":
    type = sys.argv[1]

    if type == 'lsyncdModifyCron':
      """
      python3 /www/server/jh-panel/plugins/rsyncd/tool_lsyncd.py lsyncdModifyCron '{"name":"192.168.3.72@test","period":"minute-n","hour":"3","minute":"4","minute-n":"5"}'
      python3 /www/server/jh-panel/plugins/rsyncd/tool_lsyncd.py lsyncdModifyCron '{"name":".*test","period":"day","hour":"3","minute":"0"}'
      python3 /www/server/jh-panel/plugins/rsyncd/tool_lsyncd.py lsyncdModifyCron '{"name":".*test2","period":"minute-n","hour":"3","minute":"4","minute-n":"10"}'
      """
      cron_config = json.loads(sys.argv[2])
      lsyncdModifyCron(cron_config)
    elif type == 'lsyncdAddExclude':
      """
      python3 /www/server/jh-panel/plugins/rsyncd/tool_lsyncd.py lsyncdAddExclude '{"name_reg":".*wwwroot","exclude":"dababase3"}'
      """
      exclude_config = json.loads(sys.argv[2])
      lsyncdAddExclude(exclude_config)
    elif type == 'updateLsyncdLogCutShell':
      updateLsyncdLogCutShell()
