# coding:utf-8

import sys
import io
import os
import time
import json
import re

sys.path.append(os.getcwd() + "/class/core")
import mw
import crontab_api
crontabApi = crontab_api.crontab_api()

import index as rsyncdApi


app_debug = False
if mw.isAppleSystem():
    app_debug = True


UUID_GTID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}:")


def stripGtidPurged(sql_file):
  if not os.path.exists(sql_file):
    print('SQL文件不存在: ' + sql_file)
    return 1

  with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

  new_lines = []
  skip_until_semicolon = False
  skip_gtid_comment_block = False
  removed = 0

  for line in lines:
    stripped = line.strip()

    if skip_until_semicolon:
      removed += 1
      if stripped.endswith(';') or stripped.endswith("';"):
        skip_until_semicolon = False
      continue

    if '@@GLOBAL.GTID_PURGED' in line:
      removed += 1
      if not (stripped.endswith(';') or stripped.endswith("';")):
        skip_until_semicolon = True
      continue

    if stripped == '-- GTID state at the end of the backup':
      removed += 1
      skip_gtid_comment_block = True
      continue

    if skip_gtid_comment_block:
      removed += 1
      if UUID_GTID_RE.match(stripped):
        if stripped.endswith(';') or stripped.endswith("';"):
          skip_gtid_comment_block = False
        else:
          skip_until_semicolon = True
          skip_gtid_comment_block = False
        continue
      if stripped == '--' or stripped == '':
        continue
      skip_gtid_comment_block = False

    new_lines.append(line)

  if removed > 0:
    with open(sql_file, 'w', encoding='utf-8') as f:
      f.writelines(new_lines)
    print('已清理GTID_PURGED语句: ' + str(removed) + '行')
  else:
    print('未发现GTID_PURGED语句')
  return 0


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
pushd /www/server/jh-panel > /dev/null  
python3 /www/server/jh-panel/plugins/mysql-apt/index.py save_slave_status_to_master
popd > /dev/null
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
    elif type == 'stripGtidPurged':
      if len(sys.argv) < 3:
        print('用法: python3 plugins/mysql-apt/tools.py stripGtidPurged <sql_file>')
        sys.exit(1)
      sys.exit(stripGtidPurged(sys.argv[2]))
