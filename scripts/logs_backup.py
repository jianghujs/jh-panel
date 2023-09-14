#!/usr/bin/python
# coding: utf-8
#-----------------------------
# 网站日志切割脚本
#-----------------------------
import sys
import os
import shutil
import time
import glob
import json
# from clean import cleanTools

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')


chdir = os.getcwd()
sys.path.append(chdir + '/class/core')
sys.path.append(chdir + '/class/plugin')

# importlib.reload(sys)
# sys.setdefaultencoding('utf-8')

import mw
import clean_tool
print('==================================================================')
print('★[' + time.strftime("%Y/%m/%d %H:%M:%S") + ']，切割日志')
print('==================================================================')
logsPath = mw.getLogsDir()
px = '.log'


def split_logs(oldFileName, save):
    num = 3
    global logsPath
    if not os.path.exists(oldFileName):
        print('|---' + oldFileName + '文件不存在!')
        return

    newFileName = oldFileName + '_' + time.strftime("%Y-%m-%d_%H%M%S") + '.log'
    shutil.move(oldFileName, newFileName)
    print('|---已切割日志到:' + newFileName)
    clean_tool.cleanPath(logsPath, save, oldFileName.replace(logsPath + '/', "") + '_' + "*")


def split_all(save):
    sites = mw.M('sites').field('name').select()
    for site in sites:
        oldFileName = logsPath + site['name'] + px
        split_logs(oldFileName, save)

if __name__ == '__main__':
    save = {"saveAllDay": "3", "saveOther": "1", "saveMaxDay": "30"}
    if len(sys.argv) > 2:
        save = json.loads(sys.argv[2])
    if sys.argv[1].find('ALL') == 0:
        split_all(num)
    else:
        siteName = sys.argv[1]
        if siteName[-4:] == '.log':
            siteName = siteName[:-4]
        else:
            siteName = siteName.replace("-access_log", '')
        oldFileName = logsPath + '/' + sys.argv[1]
        errOldFileName = logsPath + '/' + \
            sys.argv[1].strip(".log") + ".error.log"
        split_logs(oldFileName, save)
        if os.path.exists(errOldFileName):
            split_logs(errOldFileName, save)
    path = mw.getServerDir()
    os.system("kill -USR1 `cat " + path + "/openresty/nginx/logs/nginx.pid`")
