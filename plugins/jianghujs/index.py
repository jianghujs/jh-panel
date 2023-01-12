# coding:utf-8

import sys
import io
import os
import time
import shutil
from urllib.parse import unquote

sys.path.append(os.getcwd() + "/class/core")
import mw

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


def getSqliteDb(tablename='tablename'):
    name = "jianghujs"
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
    return 'start'

def start():
    getSqliteDb()
    
    mw.restartWeb()
    return 'ok'
    
def projectScriptExcute():
    args = getArgs()
    data = checkArgs(args, ['id', 'scriptKey'])
    if not data[0]:
        return data[1]
    id = args['id']
    scriptKey = args['scriptKey']
    conn = getSqliteDb('project')
    data = conn.where('id=?', (id,)).field('id,name,path,start_script,reload_script,stop_script,create_time,echo').find()
    if not data:
        return mw.returnJson(False, '项目不存在!')
    scriptFile = getServerDir() + '/script/' + data['echo'] + "_" + scriptKey + ".sh"
    if not os.path.exists(scriptFile):
        return mw.returnJson(False, '脚本不存在!')
    logFile = getServerDir() + '/script/' + data['echo'] + '.log'
    os.system('chmod +x ' + scriptFile)

    # os.system('nohup ' + scriptFile + ' >> ' + logFile + ' 2>&1 &')
    # os.system(scriptFile + ' >> ' + logFile + ' 2>&1')
    data = mw.execShell('source /root/.bashrc && nohup ' + scriptFile + ' >> ' + logFile + ' 2>&1 &')

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
    conn = getSqliteDb('project')
    data = conn.field('id,name,path,start_script,reload_script,stop_script,autostart_script,echo,create_time').select()
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
    return mw.returnJson(True, 'ok', data)

def projectToggleAutostart():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']
    conn = getSqliteDb('project')
    project = conn.where('id=?', (id,)).field('id,name,path,start_script,reload_script,stop_script,autostart_script,create_time,echo').find()
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
    conn = getSqliteDb('project')
    data = conn.add(
        'name,path,start_script,reload_script,stop_script,autostart_script,create_time,echo',
        ( name, path, startScript, reloadScript, stopScript, autostartScript, int(time.time()), echo )
    )
    makeScriptFile(echo + '_start.sh', startScript)
    makeScriptFile(echo + '_reload.sh', reloadScript)
    makeScriptFile(echo + '_stop.sh', stopScript)
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
    conn = getSqliteDb('project')
    conn.where('id=?', (id,)).update({
        'name': name,
        'path': path,
        'start_script': startScript,
        'reload_script': reloadScript,
        'stop_script': stopScript,
        'autostart_script': autostartScript
    })
    makeScriptFile(echo + '_start.sh', startScript)
    makeScriptFile(echo + '_reload.sh', reloadScript)
    makeScriptFile(echo + '_stop.sh', stopScript)
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
    conn = getSqliteDb('project')
    conn.delete(id)
    return mw.returnJson(True, '删除成功!')

def projectLogs():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']
    conn = getSqliteDb('project')
    echo = conn.where('id=?', (id,)).field('echo').find()  
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
    conn = getSqliteDb('project')
    echo = conn.where('id=?', (id,)).field('echo').find()
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
