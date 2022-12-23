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
    return 'start'

def start():
    
    mw.restartWeb()
    return 'ok'

def hostList():
    hostsFile = open("/etc/hosts")
    hostsArr = []
    try:
        while 1:
            line = hostsFile.readline().replace('\t', ' ')
            if(not line):
                break
            if(line != "\n" and line[0] != "#"):
                hostsArr.append({"ip":line.split(" ", 1)[0].strip(), "domain":line.split(" ", 1)[1].strip(), "original":line.strip("\n")})
    except:
        return mw.returnJson(False, 'hosts文件存在语法错误！请手动修复错误！')
    return mw.returnJson(True, 'ok', hostsArr)

def hostAdd():
    args = getArgs()
    data = checkArgs(args, ['ip', 'domain'])
    if not data[0]:
        return data[1]
    ip = args['ip']
    domain = args['domain'].replace("+", " ")
    hostsFile = open("/etc/hosts", "a+")
    hostsFile.write("\r\n%s %s"%(ip, domain))
    hostsFile.close()
    return mw.returnJson(True, '添加成功！')

def hostEdit():
    args = getArgs()
    data = checkArgs(args, ['original', 'ip', 'domain'])
    if not data[0]:
        return data[1]
    original = args['original']
    ip = args['ip']
    domain = args['domain'].replace("+", " ")
    hostsFileOld = open("/etc/hosts")
    hostsNew = ''
    while(1):
        line = hostsFileOld.readline()
        if(not line):
            break
        if(not line == '\n'):
            if(original.strip() != line.strip()):
                hostsNew = hostsNew + ip + ' ' + domain + '\r\n'
            else:
                hostsNew = hostsNew + line
    hostsFileOld.close()
    with open("/etc/hosts", 'w') as f:
        f.write(hostsNew)
    return mw.returnJson(True, '修改成功！')

def hostDelete():
    args = getArgs()
    data = checkArgs(args, ['original'])
    if not data[0]:
        return data[1]
    original = args['original']
    hostsFileOld = open("/etc/hosts")
    hostsNew = ''
    while(1):
        line = hostsFileOld.readline()
        if(not line):
            break
        if(not line == '\n'):
            if(original.strip() != line.strip()):
                hostsNew = hostsNew + line
    hostsFileOld.close()
    with open("/etc/hosts", 'w') as f:
        f.write(hostsNew)
    return mw.returnJson(True, '成功删除此条hosts')

def getHostFile():
    return mw.returnJson(True, 'ok', open("/etc/hosts").read())

def saveHostFile():
    content = sys.argv[2:][0].strip('{content:').strip("}")
    os.system("cp /etc/hosts /etc/hosts.bak")
    with open('/etc/hosts', 'w') as hostsFile:
        hostsFile.write(unquote(content.replace('\\n', '\r\n'), 'utf-8').replace('+', ' '))
    return mw.returnJson(True, '编辑hosts成功！')

if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'host_list':
        print(hostList())
    elif func == 'host_add':
        print(hostAdd())
    elif func == 'host_edit':
        print(hostEdit())
    elif func == 'host_delete':
        print(hostDelete())
    elif func == 'get_host_file':
        print(getHostFile())
    elif func == 'save_host_file':
        print(saveHostFile())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'stop':
        print(pm2Stop())
    elif func == 'start':
        print(start())
    else:
        print('error')
