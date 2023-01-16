# coding:utf-8

import sys
import io
import os
import time
import shutil
from urllib.parse import unquote
import re

sys.path.append(os.getcwd() + "/class/core")
import mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'host'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getInitDFile():
    if app_debug:
        return '/tmp/' + getPluginName()
    return '/etc/init.d/' + getPluginName()


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = unquote(t[1], 'utf-8')
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = unquote(t[1], 'utf-8')
    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))

def status():
    return 'start'

def start():
    
    mw.restartWeb()
    return 'ok'

def createRsa():
    if os.path.exists('/root/.ssh/id_rsa.pub'):
        os.remove('/root/.ssh/id_rsa.pub')
    if os.path.exists('/root/.ssh/id_rsa'):
        os.remove('/root/.ssh/id_rsa')
    mw.execShell( 'echo y | ssh-keygen -q -t rsa -P "" -f /root/.ssh/id_rsa')
    mw.execShell('cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys')
    mw.execShell('chmod 600 /root/.ssh/authorized_keys')
    return mw.returnJson(True, '操作成功！')

def getRsa():
    if os.path.exists('/root/.ssh/id_rsa.pub'):
        return mw.returnJson(True, 'ok', mw.readFile('/root/.ssh/id_rsa.pub'))
    return mw.returnJson(True, 'ok', '')

if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'stop':
        print(stop())
    elif func == 'start':
        print(start())
    elif func == 'create_rsa':
        print(createRsa())
    elif func == 'get_rsa':
        print(getRsa())
    else:
        print('error')
