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

    return 'docker'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getInitDFile():
    if app_debug:
        return '/tmp/' + getPluginName()
    return '/etc/init.d/' + getPluginName()


# def getArgs():
#     args = sys.argv[2:]
#     tmp = {}
#     args_len = len(args)

#     if args_len == 1:
#         t = args[0].strip('{').strip('}')
#         t = t.split(':')
#         tmp[t[0]] = unquote(t[1], 'utf-8')
#     elif args_len > 1:
#         for i in range(len(args)):
#             t = args[i].split(':')
#             tmp[t[0]] = unquote(t[1], 'utf-8')
#     return tmp

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

def getSqliteDb(tablename='tablename'):
    name = "docker"
    db_dir = getServerDir() + '/data/'

    if not os.path.exists(db_dir):
        mw.execShell('mkdir -p ' + db_dir)

    file = db_dir + name + '.db'
    if not os.path.exists(file):
        conn = mw.M(tablename).dbPos(db_dir, name)
        sql = mw.readFile(getPluginDir() + '/init.sql')
        sql_list = sql.split(';')
        for index in range(len(sql_list)):
            conn.execute(sql_list[index])
    else:
        conn = mw.M(tablename).dbPos(db_dir, name)
    return conn

def status():
    status_exec = mw.execShell('systemctl status docker | grep running')
    return 'stop' if status_exec[0] == '' else 'start'

def start():
    getSqliteDb()

    mw.restartWeb()
    return 'ok'

def serviceCtl():
    args = getArgs()
    data = checkArgs(args, ['s_type'])
    if not data[0]:
        return data[1]
    s_type = args['s_type']
    if s_type not in ['start', 'stop', 'restart']:
        return mw.returnJson(False, '操作不正确')
    exec_str = 'systemctl {} docker'.format(s_type)
    print(exec_str)
    mw.execShell(exec_str)
    return 'ok'

# 仓库列表
def repositoryList():
    conn = getSqliteDb('repository')
    data = conn.field('id,hub_name,registry,namespace,repository_name,create_time').select()
    return mw.returnJson(True, 'ok', data)

# 检查仓库连接
def checkRepositoryLogin(user_name, user_pass, registry):
    login_test = mw.execShell('docker login -u=%s -p %s %s' % (user_name, user_pass, registry))
    ret = 'required$|Error|未找到命令'
    ret2 = re.findall(ret, login_test[-1])
    if len(ret2) == 0:
        return True
    else:
        return False

# 添加仓库
def repositoryAdd():
    args = getArgs()
    # data = checkArgs(args, ['user_name', 'user_pass', 'registry', 'hub_name', 'namespace'])
    # if not data[0]:
    #     return data[1]
    user_name = args['user_name']
    user_pass = args['user_pass']
    registry = args['registry']
    hub_name = args['hub_name']
    namespace = args['namespace']
    repository_name = args['repository_name']
    if not registry:
        registry = "docker.io"
    checkResult = checkRepositoryLogin(user_name, user_pass, registry)
    if checkResult:
        conn = getSqliteDb('repository')
        data = conn.add('user_name,user_pass,registry,hub_name,namespace,repository_name,create_time',
            (user_name, user_pass, registry, hub_name, namespace, repository_name, int(time.time()))
        )
        return mw.returnJson(True, '登陆成功')
    return mw.returnJson(False, '登陆失败')

# 删除仓库
def repositoryDelete():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]

    id = args['id']    
    conn = getSqliteDb('repository')
    conn.delete(id)
    return mw.returnJson(True, '删除成功!')



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
        print(pm2Stop())
    elif func == 'service_ctl':
        print(serviceCtl())
    elif func == 'repository_list':
        print(repositoryList())
    elif func == 'repository_add':
        print(repositoryAdd())
    elif func == 'repository_delete':
        print(repositoryDelete())
    else:
        print('error')
