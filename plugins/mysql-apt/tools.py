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


def addAutoSaveSlaveStatusToMasterShell():
  iname = "[勿删]主从状态推送到[主]服务器"
  cron_type = "hour-n"
  week = ""
  hour = 0
  minute = 0
  where1 = 2
  saveAllDay = ""
  saveOther = ""
  saveMaxDay = ""
  backup_to = "localhost"
  stype = "toShell"
  sname = ""
  dumpType = ""
  sbody = f"""
#!/bin/bash
timestamp=$(date +%Y%m%d_%H%M%S)
cp /www/server/rsyncd/logs/lsyncd.status /www/server/rsyncd/logs/lsyncd_${{timestamp}}.status
mv /www/server/rsyncd/logs/lsyncd.log /www/server/rsyncd/logs/lsyncd_${{timestamp}}.log

python3 /www/server/jh-panel/scripts/clean.py /www/server/rsyncd/logs/ '{{"saveAllDay": "3", "saveOther": "1", "saveMaxDay": "30"}}'
  """
  urladdress = ""
  
  
  if stype == 'database':
    sbody = dumpType

  if len(iname) < 1:
      print("任务名称不能为空")
      return

  crontabList = mw.M('crontab').where('name=?', (iname,)).field('id').select()
  if len(crontabList) > 0:
      print("计划任务已经存在")
      return
  

  params = {
      'name': iname,
      'type': cron_type,
      'week': week,
      'where1': where1,
      'hour': hour,
      'minute': minute,
      'saveAllDay': saveAllDay,
      'saveOther': saveOther,
      'saveMaxDay': saveMaxDay,
      'backup_to': backup_to,
      'stype': stype,
      'sname': sname,
      'dumpType': dumpType,
      'sbody': sbody,
      'urladdress': urladdress,
  }

  is_check_pass, msg = crontabApi.cronCheck(params)
  if not is_check_pass:
      print(msg)
      return

  addData = crontabApi.add(params)
  if addData > 0:
      print("添加计划任务【" + iname + "】成功!")
  else:
      print("添加计划任务【" + iname + "】失败!")


if __name__ == "__main__":
    type = sys.argv[1]

    if type == 'addAutoSaveSlaveStatusToMasterShell':
      addAutoSaveSlaveStatusToMasterShell()
