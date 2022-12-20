# coding:utf-8

import sys
import io
import os
import time
import shutil

sys.path.append(os.getcwd() + "/class/core")
import mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'nodejs'


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


def status():
    cmd = "ps -ef|grep nodejs |grep -v grep | grep -v python | awk '{print $2}'"
    data = mw.execShell(cmd)
    if data[0] == '':
        return 'stop'
    return 'start'


def rootDir():
    path = '/root'
    if mw.isAppleSystem():
        user = mw.execShell(
            "who | sed -n '2, 1p' |awk '{print $1}'")[0].strip()
        path = '/Users/' + user
    return path


def nodejsFNMDir():
    path = rootDir() + '/.local/share/fnm'
    return path

__SR = '''#!/bin/bash
PATH=%s:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
export HOME=%s
source %s/.bashrc
''' % (nodejsFNMDir(), rootDir(), rootDir())
__path = getServerDir() + '/list'


def nodejsLogDir():
    path = rootDir() + '/.nodejs'
    return path


def nodejsLog():
    path = nodejsLogDir() + '/nodejs.log'
    return path


def nodejsGetList():
    try:
        tmp = mw.execShell(__SR + "nodejs list|grep -v 'nodejs show'")
        t2 = tmp[0].replace("│", "").replace("└", "").replace(
            "─", "").replace("┴", "").replace("┘", "").strip().split("┤")
        if len(t2) == 1:
            return []
        tmpArr = t2[1].strip()
        if t2[1].find('App name') != -1:
            tmpArr = t2[2].strip()
        appList = tmpArr.split('\n')
        result = []
        tmp = mw.execShell('lsof -c node -P|grep LISTEN')
        plist = tmp[0].split('\n')
        for app in appList:
            if not app:
                continue

            tmp2 = app.strip().split()
            appInfo = {}
            appInfo['name'] = tmp2[0]
            appInfo['id'] = tmp2[1]
            appInfo['mode'] = tmp2[3]
            appInfo['pid'] = tmp2[4]
            appInfo['status'] = tmp2[5]
            appInfo['restart'] = tmp2[6]
            appInfo['uptime'] = tmp2[7]
            appInfo['cpu'] = tmp2[8]
            appInfo['mem'] = tmp2[9] + ' ' + tmp2[10]
            appInfo['user'] = tmp2[11]
            appInfo['watching'] = tmp2[12]
            appInfo['port'] = 'OFF'
            appInfo['path'] = 'OFF'
            for p in plist:
                ptmp = p.split()
                if len(ptmp) < 8:
                    continue
                if ptmp[1] == appInfo['pid']:
                    appInfo['port'] = ptmp[8].split(':')[1].split('->')[0]
            if os.path.exists(__path + '/' + appInfo['name']):
                appInfo['path'] = mw.readFile(
                    __path + '/' + appInfo['name'])
            result.append(appInfo)
        return result
    except Exception as e:
        return []


def nodejsList():
    result = nodejsGetList()
    return mw.returnJson(True, 'ok', result)


def nodejsAdd():
    args = getArgs()
    data = checkArgs(args, ['path', 'run', 'pname'])
    if not data[0]:
        return data[1]

    path = args['path']
    run = args['run']
    pname = args['pname']

    runFile = (path + '/' + run).replace('//', '/')
    if not os.path.exists(runFile):
        return mw.returnJson(False, '指定文件不存在!')

    nlist = nodejsGetList()
    for node in nlist:
        if pname == node['name']:
            return mw.returnJson(False, '指定项目名称已经存在!')
    if os.path.exists(path + '/package.json') and not os.path.exists(path + '/package-lock.json'):
        mw.execShell(__SR + "cd " + path + ' && npm install -s')
    mw.execShell(__SR + 'cd ' + path + ' && nodejs start ' +
                 runFile + ' --name "' + pname + '"|grep ' + pname)
    mw.execShell(__SR + 'nodejs save && nodejs startup')
    if not os.path.exists(__path):
        mw.execShell('mkdir -p ' + __path)
    mw.writeFile(__path + '/' + pname, path)
    return mw.returnJson(True, '添加成功!')


def nodejsDelete():
    args = getArgs()
    data = checkArgs(args, ['pname'])
    if not data[0]:
        return data[1]

    pname = args['pname']
    cmd = 'nodejs stop "' + pname + '" && nodejs delete "' + \
        pname + '" | grep "' + pname + '"'
    result = mw.execShell(__SR + cmd)[0]
    if result.find('✓') != -1:
        mw.execShell(__SR + 'nodejs save && nodejs startup')
        if os.path.exists(__path + '/' + pname):
            os.remove(__path + '/' + pname)
        return mw.returnJson(True, '删除成功!')
    return mw.returnJson(False, '删除失败!')


def nodejsStop():
    args = getArgs()
    data = checkArgs(args, ['pname'])
    if not data[0]:
        return data[1]

    pname = args['pname']
    result = mw.execShell(__SR + 'nodejs stop "' +
                          pname + '"|grep ' + pname)[0]
    if result.find('stoped') != -1:
        return mw.returnJson(True, '项目[' + pname + ']已停止!')
    return mw.returnJson(True, '项目[' + pname + ']停止失败!')


def nodejsStart():
    args = getArgs()
    data = checkArgs(args, ['pname'])
    if not data[0]:
        return data[1]

    pname = args['pname']
    result = mw.execShell(
        __SR + 'nodejs start "' + pname + '"|grep ' + pname)[0]
    if result.find('online') != -1:
        return mw.returnJson(True, '项目[' + pname + ']已启动!')
    return mw.returnJson(False, '项目[' + pname + ']启动失败!')


def nodejsVerList():
    # 获取Node版本列表
    import re
    result = {}
    rep = 'v\d+\.\d+\.\d+'

    cmd = __SR + ' fnm ls-remote|grep -v v0'
    # print cmd
    tmp = mw.execShell(cmd)
    result['list'] = re.findall(rep, tmp[0])
    tmp = mw.execShell(__SR + " node --version")
    result['version'] = tmp[0].strip()
    return mw.returnJson(True, 'ok', result)


def setNodeVersion():
    args = getArgs()
    data = checkArgs(args, ['version'])
    if not data[0]:
        return data[1]
    # 切换Node版本
    version = args['version'].replace('v', '')
    estr = '''
fnm install %s
fnm use %s
fnm default %s
npm install nodejs -g
''' % (version, version, version)
    cmd = __SR + estr
    mw.execShell(cmd)
    return mw.returnJson(True, '已切换至[' + version + ']')


def getMod():
    cmd = __SR + "npm list --depth=0 -global"
    tmp = mw.execShell(cmd)
    modList = tmp[0].replace("│", "").replace("└", "").replace(
        "─", "").replace("┴", "").replace("┘", "").strip().split()
    result = []
    for m in modList:
        mod = {}
        tmp = m.split('@')
        if len(tmp) < 2:
            continue
        mod['name'] = tmp[0]
        mod['version'] = tmp[1]
        result.append(mod)

    return mw.returnJson(True, 'OK', result)


# 安装库
def installMod():
    args = getArgs()
    data = checkArgs(args, ['mname'])
    if not data[0]:
        return data[1]

    mname = args['mname']
    mw.execShell(__SR + 'npm install ' + mname + ' -g')
    return mw.returnJson(True, '安装成功!')


def uninstallMod():
    args = getArgs()
    data = checkArgs(args, ['mname'])
    if not data[0]:
        return data[1]

    mname = args['mname']
    myNot = ['nodejs', 'npm']
    if mname in myNot:
        return mw.returnJson(False, '不能卸载[' + mname + ']')
    mw.execShell(__SR + 'npm uninstall ' + mname + ' -g')
    return mw.returnJson(True, '卸载成功!')


def nodeLogRun():
    args = getArgs()
    data = checkArgs(args, ['pname'])
    if not data[0]:
        return data[1]

    pname = args['pname']
    return nodejsLogDir() + '/logs/' + pname + '-out.log'


def nodeLogErr():
    args = getArgs()
    data = checkArgs(args, ['pname'])
    if not data[0]:
        return data[1]

    pname = args['pname']
    return nodejsLogDir() + '/logs/' + pname + '-error.log'


def nodeLogClearRun():
    args = getArgs()
    data = checkArgs(args, ['pname'])
    if not data[0]:
        return data[1]

    pname = args['pname']
    path = nodejsLogDir() + '/logs/' + pname + '-out.log'
    mw.execShell('rm -rf ' + path + '&& touch ' + path)
    return mw.returnJson(True, '清空运行成功')


def nodeLogClearErr():
    args = getArgs()
    data = checkArgs(args, ['pname'])
    if not data[0]:
        return data[1]
    pname = args['pname']
    path = nodejsLogDir() + '/logs/' + pname + '-error.log'
    mw.execShell('rm -rf ' + path + '&& touch ' + path)
    return mw.returnJson(True, '清空错误成功')

if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'list':
        print(nodejsList())
    elif func == 'add':
        print(nodejsAdd())
    elif func == 'delete':
        print(nodejsDelete())
    elif func == 'stop':
        print(nodejsStop())
    elif func == 'start':
        print(nodejsStart())
    elif func == 'get_logs':
        print(nodejsLog())
    elif func == 'node_log_run':
        print(nodeLogRun())
    elif func == 'node_log_err':
        print(nodeLogErr())
    elif func == 'node_log_clear_run':
        print(nodeLogClearRun())
    elif func == 'node_log_clear_err':
        print(nodeLogClearErr())
    elif func == 'versions':
        print(nodejsVerList())
    elif func == 'set_node_version':
        print(setNodeVersion())
    elif func == 'mod_list':
        print(getMod())
    elif func == 'install_mod':
        print(installMod())
    elif func == 'uninstall_mod':
        print(uninstallMod())
    else:
        print('error')
