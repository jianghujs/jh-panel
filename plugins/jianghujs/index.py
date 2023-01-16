# coding:utf-8

import sys
import io
import os
import time
import shutil
from urllib.parse import unquote

sys.path.append(os.getcwd() + "/class/core")
import mw

try:
    import dictdatabase as DDB
except:
    mw.execShell("pip install dictdatabase")
    import dictdatabase as DDB

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():

    return 'jianghujs'


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


# https://github.com/mkrd/DictDataBase
def getDb(table):
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
    return 'start'

def start():
    mw.restartWeb()
    return 'ok'
    
def projectScriptExcute():
    args = getArgs()
    data = checkArgs(args, ['id', 'scriptKey'])
    if not data[0]:
        return data[1]
    id = args['id']
    scriptKey = args['scriptKey']
    data = getOne('project', id)
    if not data:
        return mw.returnJson(False, '项目不存在!')
    scriptFile = getServerDir() + '/script/' + data['echo'] + "_" + scriptKey + ".sh"
    if not os.path.exists(scriptFile):
        return mw.returnJson(False, '脚本不存在!')
    logFile = getServerDir() + '/script/' + data['echo'] + '.log'
    os.system('chmod +x ' + scriptFile)

    # os.system('nohup ' + scriptFile + ' >> ' + logFile + ' 2>&1 &')
    # os.system(scriptFile + ' >> ' + logFile + ' 2>&1')

    # data = mw.execShell('source /root/.bashrc && nohup ' + scriptFile + ' >> ' + logFile + ' 2>&1 &')
    
    data = mw.execShell('nohup ' + scriptFile + ' >> ' + logFile + ' 2>&1 &')

    return mw.returnJson(True, '执行成功!')
    

def projectStart():
    args = getArgs()
    data = checkArgs(args, ['path'])
    if not data[0]:
        return data[1]

    path = args['path']
    cmd = """
    cd %s
    npm i
    npm start
    """ % path
    data = mw.execShell(cmd)
    return mw.returnJson(True, '启动成功!')

def projectStop():
    args = getArgs()
    data = checkArgs(args, ['path'])
    if not data[0]:
        return data[1]

    path = args['path']
    cmd = """
    cd %s
    npm stop
    """ % path
    data = mw.execShell(cmd)
    return mw.returnJson(True, '停止成功!')

def projectRestart():
    args = getArgs()
    data = checkArgs(args, ['path'])
    if not data[0]:
        return data[1]

    path = args['path']
    cmd = """
    cd %s
    npm stop
    npm start
    """ % path
    data = mw.execShell(cmd)
    return mw.returnJson(True, '重启成功!')

    
def projectStatus():
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]

    name = args['name']
    cmd = "ps -ef|grep " + name + " |grep -v grep | grep -v python | awk '{print $2}'"
    data = mw.execShell(cmd)
    if data[0] == '':
        return 'stop'
    return 'start'

def projectUpdate():
    args = getArgs()
    data = checkArgs(args, ['path'])
    if not data[0]:
        return data[1]

    path = args['path']
    cmd = """
    cd %s
    git pull
    """ % path
    data = mw.execShell(cmd)
    return mw.returnJson(True, '更新成功!')

def projectList():
    data = getAll('project')
    for item in data:
        path = item['path']
        echo = item['echo']

        # autostartStatus
        autostartStatusCmd = "ls -R /etc/rc4.d | grep " + echo
        autostartStatusExec = mw.execShell(autostartStatusCmd)
        item['autostartStatus'] = 'stop' if autostartStatusExec[0] == '' else 'start'

        # status
        statusCmd = "ps -ef|grep " + path + " |grep -v grep | grep -v python | awk '{print $2}'"
        statusExec = mw.execShell(statusCmd)
        item['status'] = 'stop' if statusExec[0] == '' else 'start'

        # loadingStatus
        loadingStatusCmd = "ls -R %s/script | grep %s_status" % (getServerDir() , echo) 
        loadingStatusExec = mw.execShell(loadingStatusCmd)
        if loadingStatusExec[0] != '':
            item['loadingStatus'] = mw.readFile(getServerDir() + '/script/' + echo + '_status')

    return mw.returnJson(True, 'ok', data)

def projectToggleAutostart():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']
    project = getOne('project', id)
    if not project:
        return mw.returnJson(False, '项目不存在!')
    echo = project['echo']
    autostart_script = project['autostart_script']

    # 创建自启动脚本文件
    autostartFile = '/etc/init.d/' +  echo
    if not os.path.exists(autostartFile):
        mw.writeFile(autostartFile, autostart_script)
        mw.execShell('chmod 755 ' + autostartFile)
    
    # 判断自启动脚本是否启用
    autostartStatusFile = '/etc/rc4.d/S01' + echo
    if os.path.exists(autostartStatusFile):
        mw.execShell('update-rc.d -f ' + echo + ' remove')
        return mw.returnJson(True, '已关闭自启动!')
    else:
        mw.execShell('update-rc.d ' + echo + ' defaults')
        return mw.returnJson(True, '已开启自启动!')


def projectAdd():
    args = getArgs()
    data = checkArgs(args, ['name', 'path', 'startScript', 'reloadScript', 'stopScript', 'autostartScript'])
    if not data[0]:
        return data[1]
    name = args['name']
    path = unquote(args['path'], 'utf-8')
    startScript = getScriptArg('startScript')
    reloadScript = getScriptArg('reloadScript')
    stopScript = getScriptArg('stopScript')
    autostartScript = getScriptArg('autostartScript')
    echo =  mw.md5(str(time.time()) + '_jianghujs')
    id = int(time.time())
    saveOne('project', id, {
        'name': name,
        'path': path,
        'start_script': startScript,
        'reload_script': reloadScript,
        'stop_script': stopScript,
        'autostart_script': autostartScript,
        'create_time': int(time.time()),
        'echo': echo
    })
    statusFile = '%s/script/%s_status' % (getServerDir(), echo)
    makeScriptFile(echo + '_start.sh', 'touch %s\necho "启动中..." >> %s\n%s\nrm -f %s' % (statusFile, statusFile, startScript, statusFile))
    makeScriptFile(echo + '_reload.sh', 'touch %s\necho "重启中..." >> %s\n%s\nrm -f %s' % (statusFile, statusFile, reloadScript, statusFile))
    makeScriptFile(echo + '_stop.sh', 'touch %s\necho "停止中..." >> %s\n%s\nrm -f %s' % (statusFile, statusFile, stopScript, statusFile))
    
    return mw.returnJson(True, '添加成功!')

def projectEdit():
    args = getArgs()
    data = checkArgs(args, ['id', 'name', 'path', 'startScript', 'reloadScript', 'stopScript', 'autostartScript'])
    if not data[0]:
        return data[1]
    id = args['id']
    name = args['name']
    path = unquote(args['path'], 'utf-8')
    startScript = getScriptArg('startScript')
    reloadScript = getScriptArg('reloadScript')
    stopScript = getScriptArg('stopScript')
    autostartScript = getScriptArg('autostartScript')
    project = getOne('project', id)
    if not project:
        return mw.returnJson(False, '项目不存在!')
    echo = project['echo']
    saveOne('project', id, {
        'name': name,
        'path': path,
        'start_script': startScript,
        'reload_script': reloadScript,
        'stop_script': stopScript,
        'autostart_script': autostartScript
    })
    statusFile = '%s/script/%s_status' % (getServerDir(), echo)
    makeScriptFile(echo + '_start.sh', 'touch %s\necho "启动中..." >> %s\n%s\nrm -f %s' % (statusFile, statusFile, startScript, statusFile))
    makeScriptFile(echo + '_reload.sh', 'touch %s\necho "重启中..." >> %s\n%s\nrm -f %s' % (statusFile, statusFile, reloadScript, statusFile))
    makeScriptFile(echo + '_stop.sh', 'touch %s\necho "停止中..." >> %s\n%s\nrm -f %s' % (statusFile, statusFile, stopScript, statusFile))
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

def projectDelete():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]

    id = args['id']    
    deleteOne('project', id)
    return mw.returnJson(True, '删除成功!')

def projectLogs():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']
    project = getOne('project', id)
    if not project:
        return mw.returnJson(False, '项目不存在!')
    echo = project['echo']
    logPath = getServerDir() + '/script'
    if not os.path.exists(logPath):
        os.system('mkdir -p ' + logPath)
    logFile = logPath + '/' + echo['echo'] + '.log'
    if not os.path.exists(logFile):
        return mw.returnJson(False, '当前日志为空!')
    log = mw.getLastLine(logFile, 500)
    return mw.returnJson(True, log)

def projectLogsClear():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']  
    project = getOne('project', id)
    if not project:
        return mw.returnJson(False, '项目不存在!')
    echo = project['echo']
    logPath = getServerDir() + '/script'
    if not os.path.exists(logPath):
        os.system('mkdir -p ' + logPath)
    logFile = logPath + '/' + echo['echo'] + '.log'
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
    elif func == 'project_start':
        print(projectStart())
    elif func == 'project_stop':
        print(projectStop())
    elif func == 'project_restart':
        print(projectRestart())
    elif func == 'project_status':
        print(projectStatus())
    elif func == 'project_script_excute':
        print(projectScriptExcute())
    elif func == 'project_update':
        print(projectUpdate())
    elif func == 'project_list':
        print(projectList())
    elif func == 'project_toggle_autostart':
        print(projectToggleAutostart())
    elif func == 'project_add':
        print(projectAdd())
    elif func == 'project_edit':
        print(projectEdit())
    elif func == 'project_delete':
        print(projectDelete())
    elif func == 'project_logs':
        print(projectLogs())
    elif func == 'project_logs_clear':
        print(projectLogsClear())
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
