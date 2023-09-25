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
import common

if __name__ == "__main__":
    import cert_api
    api = cert_api.cert_api()
    api.createCertCron()
