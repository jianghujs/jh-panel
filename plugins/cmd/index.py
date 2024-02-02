# coding:utf-8

import sys
import io
import os
import time
import shutil
from urllib.parse import unquote
import re
import dictdatabase as DDB

sys.path.append(os.getcwd() + "/class/core")
import mw


app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():

    return 'cmd'


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

# https://github.com/mkrd/DictDataBase
def initDb():
    db_dir = getServerDir() + '/data/'
    if not os.path.exists(db_dir):
        mw.execShell('mkdir -p ' + db_dir)
    DDB.config.storage_directory = db_dir

def getDb(table):
    DDB.config.storage_directory = getServerDir() + '/data/'
    if not DDB.at(table).exists():
        DDB.at(table).create({})
    return DDB.at(table)

def saveOne(table, id, data):
    if type(id) is not str:
        id = str(id)
    exist = getOne(table, id)
    if exist:
        data = {'id': id, **exist, **data}
    else:
        data = {'id': id, **data}
    with getDb(table).session() as (session, db):
        db[id] = data
        session.write()

def getAll(table):
    result = getDb(table).read()
    if result:
        return list(result.values())
    return []

def getOne(table, id):
    if type(id) is not str:
        id = str(id)
    for item in getAll(table):
        if item['id'] == id:
            return item
    return None

def deleteOne(table, id):
    if type(id) is not str:
        id = str(id)
    with getDb(table).session() as (session, db):
        del db[id]
        session.write()


def status():
    # status_exec = mw.execShell('systemctl status docker | grep running')
    return 'start'

def start():
    initDb()
    mw.restartWeb()
    return 'ok'

# 服务控制
def serviceCtl():
    args = getArgs()
    data = checkArgs(args, ['s_type'])
    if not data[0]:
        return data[1]
    s_type = args['s_type']
    if s_type not in ['start', 'stop', 'restart']:
        return mw.returnJson(False, '操作不正确')
    # exec_str = 'systemctl {} docker'.format(s_type)
    # print(exec_str)
    # mw.execShell(exec_str)
    return 'ok'

# 仓库列表
def repositoryList():
    data = getAll('repository')
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
        id = int(time.time())
        saveOne('script', id, {
            'user_name': user_name,
            'user_pass': user_pass,
            'registry': registry,
            'hub_name': hub_name,
            'namespace': namespace,
            'repository_name': repository_name,
            'create_time': int(time.time())
        })
        return mw.returnJson(True, '登陆成功')
    return mw.returnJson(False, '登陆失败')

# 删除仓库
def repositoryDelete():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]

    id = args['id']    
    deleteOne('repository', id)
    return mw.returnJson(True, '删除成功!')

# 脚本列表
def scriptList():
    data = getAll('script')
    for item in data:
        echo = item.get('echo', '')

        # loadingStatus
        loadingStatusCmd = "ls -R %s/script | grep %s_status" % (getServerDir() , echo) 
        loadingStatusExec = mw.execShell(loadingStatusCmd)
        if loadingStatusExec[0] != '':
            item['loadingStatus'] = mw.readFile(getServerDir() + '/script/' + echo + '_status')

    return mw.returnJson(True, 'ok', data)

def scriptAdd():
    args = getArgs()
    data = checkArgs(args, ['name', 'script'])
    if not data[0]:
        return data[1]
    name = args['name']
    script = getScriptArg('script')
    echo =  mw.md5(str(time.time()) + '_cmd')
    id = int(time.time())
    saveOne('script', id, {
        'name': name,
        'script': script,
        'create_time': int(time.time()),
        'echo': echo
    })
    statusFile = '%s/script/%s_status' % (getServerDir(), echo)
    finalScript = """
{ 
    touch %(statusFile)s\n
    echo "执行中..." >> %(statusFile)s\n
    cat /dev/null > %(statusFile)s\n
    {
        %(script)s\n
    } && {
        echo "执行成功" >> %(statusFile)s\n
    }
} || { 
    echo "执行失败" >> %(statusFile)s\n
}
    """ % {"statusFile": statusFile, "script": script}
    makeScriptFile(echo + '.sh', finalScript)
    return mw.returnJson(True, '添加成功!')

def scriptEdit():
    args = getArgs()
    data = checkArgs(args, ['id', 'name', 'script'])
    if not data[0]:
        return data[1]
    id = args['id']
    name = args['name']
    script = getScriptArg('script')
    scriptData = getOne('script', id)
    if not scriptData:
        return mw.returnJson(False, '脚本不存在!')
    echo = scriptData.get('echo', '')
    saveOne('script', id, {
        'name': name,
        'script': script
    })
    statusFile = '%s/script/%s_status' % (getServerDir(), echo)
    finalScript = """
{ 
    touch %(statusFile)s\n
    echo "执行中..." >> %(statusFile)s\n
    cat /dev/null > %(statusFile)s\n
    {
        %(script)s\n
    } && {
        echo "执行成功" >> %(statusFile)s\n
    }
} || { 
    echo "执行失败" >> %(statusFile)s\n
}
    """ % {"statusFile": statusFile, "script": script}
    makeScriptFile(echo + '.sh', finalScript)
    return mw.returnJson(True, '修改成功!')

def getScriptArg(arg):
    args = getArgs()
    return unquote(args[arg], 'utf-8').replace('+', ' ').replace("\r\n", "\n")

def makeScriptFile(filename, content):
    scriptPath = getServerDir() + '/script'
    if not os.path.exists(scriptPath):
        mw.execShell('mkdir -p ' + scriptPath)
    scriptFile = scriptPath + '/' + filename
    mw.writeFile(scriptFile, content)
    mw.execShell('chmod 750 ' + scriptFile)

def scriptDelete():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]

    id = args['id']    
    deleteOne('script', id)
    return mw.returnJson(True, '删除成功!')

def scriptExcute():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']
    data = getOne('script', id)
    if not data:
        return mw.returnJson(False, '脚本项不存在!')
    scriptFile = getServerDir() + '/script/' + data.get('echo', '') + ".sh"
    if not os.path.exists(scriptFile):
        return mw.returnJson(False, '脚本不存在!')
    logFile = getServerDir() + '/script/' + data.get('echo', '') + '.log'
    os.system('chmod +x ' + scriptFile)

    data = mw.execShell('source /root/.bashrc && nohup ' + scriptFile + ' >> ' + logFile + ' 2>&1')
    # data = mw.execShell('nohup ' + scriptFile + ' >> ' + logFile + ' 2>&1 &')

    return mw.returnJson(True, '执行成功!')
    
def scriptLogs():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']
    scriptData = getOne('script', id)
    if not scriptData:
        return mw.returnJson(False, '脚本不存在!')
    echo = scriptData.get('echo', '')
    logPath = getServerDir() + '/script'
    if not os.path.exists(logPath):
        os.system('mkdir -p ' + logPath)
    logFile = logPath + '/' + echo + '.log'
    if not os.path.exists(logFile):
        return mw.returnJson(False, '当前日志为空!')
    log = mw.getLastLine(logFile, 500)
    return mw.returnJson(True, log)

def scriptLogsClear():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']  
    scriptData = getOne('script', id)
    if not scriptData:
        return mw.returnJson(False, '脚本不存在!')
    echo = scriptData.get('echo', '')
    logPath = getServerDir() + '/script'
    if not os.path.exists(logPath):
        os.system('mkdir -p ' + logPath)
    logFile = logPath + '/' + echo + '.log'
    if not os.path.exists(logFile):
        return mw.returnJson(False, '当前日志为空!')
    os.system('echo "" > ' + logFile)
    return mw.returnJson(True, '清空成功!')

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
    elif func == 'repository_edit':
        print(repositoryEdit())
    elif func == 'script_list':
        print(scriptList())
    elif func == 'script_add':
        print(scriptAdd())
    elif func == 'script_edit':
        print(scriptEdit())
    elif func == 'script_delete':
        print(scriptDelete())
    elif func == 'script_excute':
        print(scriptExcute())
    elif func == 'script_logs':
        print(scriptLogs())
    elif func == 'script_logs_clear':
        print(scriptLogsClear())
    else:
        print('error')
