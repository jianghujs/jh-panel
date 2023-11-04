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


def getPluginName():
    return 'frp'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def status():
    data = mw.execShell(
        "ps -ef|grep frp |grep -v grep | grep -v python | awk '{print $2}'")
    if data[0] == '':
        return 'stop'

    return 'start'


def contentReplace(content):
    service_path = mw.getServerDir()
    content = content.replace('{$ROOT_PATH}', mw.getRootDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$SERVER_APP}', service_path + '/frp')
    return content


def confClient():
    return getServerDir() + "/frpc.toml"


def confServer():
    return getServerDir() + "/frps.toml"


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


def ftOp(method):

    initDreplace()

    if mw.isAppleSystem():
        cmd = getServerDir() + '/init.d/frp ' + method + " &"
        data = mw.execShell(cmd)
        if data[1] != '':
            return 'fail'
        return 'ok'

    cmd = 'systemctl ' + method + ' frps'
    data = mw.execShell(cmd)
    if data[1] != '':
        return 'fail'

    cmd = 'systemctl ' + method + ' frpc'
    data = mw.execShell(cmd)
    if data[1] != '':
        return 'fail'

    return 'ok'


def start():
    return ftOp('start')


def stop():
    return ftOp('stop')


def restart():
    return ftOp('restart')


def reload():
    return ftOp('reload')


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
    return getServerDir() + "/frps.toml"


def frpServerCfgTpl():
    path = getPluginDir() + '/server_cfg'
    pathFile = os.listdir(path)
    tmp = []
    for one in pathFile:
        file = path + '/' + one
        tmp.append(file)
    return mw.getJson(tmp)


def frpClientCfg():
    return getServerDir() + "/frpc.toml"


def frpClientCfgTpl():
    path = getPluginDir() + '/client_cfg'
    pathFile = os.listdir(path)
    tmp = []
    for one in pathFile:
        file = path + '/' + one
        tmp.append(file)
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
        print(reload())
    elif func == 'initd_status':
        print(initdStatus())
    elif func == 'initd_install':
        print(initdInstall())
    elif func == 'initd_uninstall':
        print(initdUinstall())
    elif func == 'conf':
        print(conf())
    elif func == 'read_config_tpl':
        print(readConfigTpl())
    elif func == 'frp_server':
        print(frpServerCfg())
    elif func == 'frp_server_tpl':
        print(frpServerCfgTpl())
    elif func == 'frp_client':
        print(frpClientCfg())
    elif func == 'frp_client_tpl':
        print(frpClientCfgTpl())
    else:
        print('error')
