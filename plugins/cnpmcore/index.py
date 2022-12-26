# coding:utf-8

import sys
import io
import os
import time
import re
import string
import subprocess


sys.path.append(os.getcwd() + "/class/core")
import mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True

def rootDir():
    path = '/root'
    if mw.isAppleSystem():
        user = mw.execShell(
            "who | sed -n '2, 1p' |awk '{print $1}'")[0].strip()
        path = '/Users/' + user
    return path

__SR = '''#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
export HOME=%s
source %s/.bashrc
''' % (rootDir(), rootDir())

def getPluginName():
    return 'cnpmcore'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def status():
    data = mw.execShell(
        "ps -ef|grep cnpmcore |grep -v grep | grep -v python | awk '{print $2}'")
    if data[0] == '':
        return 'stop'

    return 'start'


def contentReplace(content):
    service_path = mw.getServerDir()
    content = content.replace('{$ROOT_PATH}', mw.getRootDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$SERVER_APP}', service_path + '/cnpmcore')
    return content


def confCnpmcore():
    return getServerDir() + "/cnpmcore/config/config.default.ts"


def confPackage():
    return getServerDir() + "/package/package.json"


def initDreplace():

    initD_path = getServerDir() + '/init.d'
    if not os.path.exists(initD_path):
        os.mkdir(initD_path)
    file_bin = initD_path + '/' + getPluginName()

    # initd replace
    if not os.path.exists(file_bin):
        file_tpl = getPluginDir() + "/init.d/frp.service.tpl"
        content = mw.readFile(file_tpl)
        content = contentReplace(content)
        mw.writeFile(file_bin, content)
        mw.execShell('chmod +x ' + file_bin)

    # systemd
    systemDir = mw.systemdCfgDir()
    service_path = mw.getServerDir()
    systemService = systemDir + '/frpc.service'
    systemServiceTpl = getPluginDir() + '/init.d/frpc.service.tpl'
    if os.path.exists(systemDir) and not os.path.exists(systemService):
        tpl = mw.readFile(systemServiceTpl)
        tpl = tpl.replace('{$SERVER_PATH}', service_path)
        mw.writeFile(systemService, tpl)
        mw.execShell('systemctl daemon-reload')

    systemService = systemDir + '/frps.service'
    systemServiceTpl = getPluginDir() + '/init.d/frps.service.tpl'
    if os.path.exists(systemDir) and not os.path.exists(systemService):
        tpl = mw.readFile(systemServiceTpl)
        tpl = tpl.replace('{$SERVER_PATH}', service_path)
        mw.writeFile(systemService, tpl)
        mw.execShell('systemctl daemon-reload')


def startAndRestart(method):
    cmd = __SR + 'cd ' + getServerDir() + '/cnpmcore' + ' && npm run tsc && npm run ' + method
    data = mw.execShell(cmd)
    if data[1] != '':
        return 'fail'
    return 'ok'

    return 'ok'

def start():
    return startAndRestart('start')


def stop():
    cmd = __SR + 'cd ' + getServerDir() + '/cnpmcore' + ' && npm run stop'
    data = mw.execShell(cmd)
    if data[1] != '':
        return 'fail'
    return 'ok'


def restart():
    return startAndRestart('restart')


def initdStatus():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    cmd = 'systemctl status frpc | grep loaded | grep "enabled;"'
    data = mw.execShell(cmd)
    if data[0] == '':
        return 'fail'
    return 'ok'


def initdInstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    mw.execShell('systemctl enable frpc')
    return 'ok'


def initdUinstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    mw.execShell('systemctl disable frpc')
    return 'ok'


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]
    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def readConfigTpl():
    args = getArgs()
    data = checkArgs(args, ['file'])
    if not data[0]:
        return data[1]

    content = mw.readFile(args['file'])
    content = contentReplace(content)
    return mw.returnJson(True, 'ok', content)


def frpServerCfg():
    return getServerDir() + "/frps.ini"


def packageJsonTpl():
    # path = getPluginDir() + '/source/package.json'
    # pathFile = os.listdir(path)
    tmp = []
    # tmp.append(path)
    # for one in pathFile:
    #     file = path + '/' + one
    #     tmp.append(file)
    return mw.getJson(tmp)


# def frpClientCfg():
#     return getServerDir() + "/frpc.ini"


def configCnpmcore():
    # path = getPluginDir() + '/client_cfg'
    # pathFile = os.listdir(path)
    tmp = []
    # for one in pathFile:
    #     file = path + '/' + one
    #     tmp.append(file)
    return mw.getJson(tmp)

if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(restart())
    # elif func == 'initd_status':
    #     print(initdStatus())
    # elif func == 'initd_install':
    #     print(initdInstall())
    # elif func == 'initd_uninstall':
    #     print(initdUinstall())
    elif func == 'conf':
        print(conf())
    elif func == 'read_config_tpl':
        print(readConfigTpl())
    elif func == 'cnpmcore_config':
        print(confCnpmcore())
    elif func == 'cnpmcore_package_tpl':
        print(packageJsonTpl())
    elif func == 'cnpmcore_package':
        print(confPackage())
    elif func == 'cnpmcore_config_tpl':
        print(configCnpmcore())
    else:
        print('error')