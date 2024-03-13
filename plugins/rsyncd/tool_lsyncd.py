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
    name = args['name']
    data = rsyncdApi.getDefaultConf()
    slist = data['send']["list"]
    res = rsyncdApi.lsyncdListFindNameReg(slist, name)
    retdata = {}

    if not res[0]:
      print("任务不存在")
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




if __name__ == "__main__":
    type = sys.argv[1]

    if type == 'lsyncdModifyCron':
      """
      python3 /www/server/jh-panel/plugins/rsyncd/tool_lsyncd.py lsyncdModifyCron '{"name":"192.168.3.72@test","period":"minute-n","hour":"3","minute":"4","minute-n":"5"}'
      """
      cron_config = json.loads(sys.argv[2])
      lsyncdModifyCron(cron_config)