# coding: utf-8
#-----------------------------
# 文件夹清理工具
# python3 /www/server/jh-panel/scripts/clean.py /root/test '{"saveAllDay": "3", "saveOther": "1", "saveMaxDay": "30"}'
# python3 /www/server/jh-panel/scripts/clean.py /root/test '{"saveAllDay": "3", "saveOther": "1", "saveMaxDay": "30"} jianghujs.*.js'
#-----------------------------

import sys
import os

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')


chdir = os.getcwd()
sys.path.append(chdir + '/class/core')
sys.path.append(chdir + '/class/plugin')

# reload(sys)
# sys.setdefaultencoding('utf-8')


import mw
import db
import time
import json
import clean_tool

if __name__ == "__main__":
    path = sys.argv[1]
    save = {"saveAllDay": "3", "saveOther": "1", "saveMaxDay": "30"}
    if len(sys.argv) > 2:
        save = json.loads(sys.argv[2])
    pattern = "*"
    if len(sys.argv) > 3:
        pattern = sys.argv[3]
    clean_tool.cleanPath(path, save, pattern)
