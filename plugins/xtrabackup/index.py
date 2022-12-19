# coding:utf-8

import sys
import io
import os
import time
import re

sys.path.append(os.getcwd() + "/class/core")
import mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True

def getPluginName():
    return 'xtrabackup'  

def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()

def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()

def runLog():
    return getServerDir() + '/xtrabackup.log'  

def status():
    return 'start'

def doMysqlBackup():
    log_file = runLog()
    xtrabackupScript = getServerDir() + '/xtrabackup.sh'
    mw.execShell('echo $(date "+%Y-%m-%d %H:%M:%S") "备份开始" >> ' + log_file)
    mw.execShell("sh %(xtrabackupScript)s" % {'xtrabackupScript': xtrabackupScript, 'logFile': log_file })
    mw.execShell('echo $(date "+%Y-%m-%d %H:%M:%S") "备份成功" >> ' + log_file)
    return mw.returnJson(True, '备份成功!')
    
if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'run_log':
        print(runLog())
    elif func == 'do_mysql_backup':
        print(doMysqlBackup())
    else:
        print('error')
