# coding:utf-8

import sys
import io
import os
import re
import time
import shutil
from urllib.parse import unquote, urlparse
import dictdatabase as DDB

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


# https://github.com/mkrd/DictDataBase
def initDb():
    db_dir = getServerDir() + '/data/'
    if not os.path.exists(db_dir):
        mw.execShell('mkdir -p ' + db_dir)
    DDB.config.storage_directory = db_dir

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
    initDb()
    mw.restartWeb()
    return 'ok'

def stop():
    return '暂不支持'

def restart():
    cleanProjectStatus()
    return 'ok'

def reload():
    cleanProjectStatus()
    return 'ok'
    
def cleanProjectStatus():
    # 删除status文件
    scriptDir = getServerDir() + '/script'
    if os.path.exists(scriptDir):
        os.system('rm -f ' + scriptDir + '/*_status')


def projectScriptExcute():
    args = getArgs()
    data = checkArgs(args, ['id', 'scriptKey'])
    if not data[0]:
        return data[1]
    ids = args['id']
    scriptKey = args['scriptKey']
    for id in ids:
        data = getOne('project', id)
        if not data:
            return mw.returnJson(False, '项目不存在!')
        scriptFile = getServerDir() + '/script/' + data.get('echo', '') + "_" + scriptKey + ".sh"
        if not os.path.exists(scriptFile):
            return mw.returnJson(False, '脚本不存在!')
        logFile = getServerDir() + '/script/' + data.get('echo', '') + '.log'
        os.system('chmod +x ' + scriptFile)

        # data = mw.execShell('source /root/.bashrc && ' + scriptFile + ' >> ' + logFile )

        mw.addAndTriggerTask(
            name = '执行江湖管理器命令[' + scriptKey + ': ' + data.get('name', '') + ']',
            execstr = 'source /root/.bashrc && ' + scriptFile + ' >> ' + logFile
        )
        time.sleep(1)

    return mw.returnJson(True, '添加执行任务成功!')
    

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
    echo "更新项目成功"
    """ % path
    makeScriptFile('pullTemp.sh', cmd)

    scriptFile = getServerDir() + '/script/pullTemp.sh'
    os.system('chmod +x ' + scriptFile)

    mw.addAndTriggerTask(
        name = '执行江湖管理器命令[git pull: ' + path + ']',
        execstr = 'source /root/.bashrc && ' + scriptFile
    )

    # data = mw.execShell(cmd)
    return mw.returnJson(True, '添加更新任务成功!')

def projectList():
    data = getAll('project')
    echos = {item.get('echo', '') for item in data}
    paths = {item.get('path', '') for item in data}

    # autostartStatus
    autostartStatusCmd = "ls -R /etc/rc4.d"
    autostartStatusExec = mw.execShell(autostartStatusCmd)
    autostartStatusMap = {echo: ('start' if echo in autostartStatusExec[0] else 'stop') for echo in echos}

    # status
    statusCmd = """ps -ef | grep -v grep | grep -v python | grep 'jianghujs' | awk -F'baseDir":"' '{print $2}' | awk -F'","' '{print $1}'"""
    statusExec = mw.execShell(statusCmd)
    statusMap = {path: ('start' if path in statusExec[0] else 'stop') for path in paths}

    # loadingStatus
    server_dir = getServerDir()
    loadingStatusMap = {}
    for echo in echos:
        status_file = server_dir + '/script/' + echo + '_status'
        if os.path.isfile(status_file):
            with open(status_file, 'r') as f:
                loadingStatusMap[echo] = f.read()
        else:
            loadingStatusMap[echo] = ''

    for item in data:
        path = item.get('path', '') 
        echo = item.get('echo', '')
        item['autostartStatus'] = autostartStatusMap[echo]
        item['status'] = statusMap[path]
        item['loadingStatus'] = loadingStatusMap[echo]

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
    echo = 'jianghujs_' + project.get('echo', '')
    autostart_script = project['autostart_script']
    if autostart_script == '':
        return mw.returnJson(False, '请配置项目自启动脚本!')
    
    # 自动添加重试逻辑
    retry_logic = '''
attempt=0
until [ $attempt -ge 3 ]
do
    {} && break
    attempt=$[$attempt+1]
    sleep 5
done
    '''
    lines = autostart_script.split('\n')
    for i, line in enumerate(lines):
        if (line.strip().startswith("npm start") or line.strip().startswith("npm run start")) and "&& break" not in line:
            lines[i] = retry_logic.format(line.strip())
    autostart_script = '\n'.join(lines)


    # 创建自启动脚本文件
    autostartFile = '/etc/init.d/' + echo
    mw.writeFile(autostartFile, autostart_script)
    mw.execShell('chmod 755 ' + autostartFile)

    
    # 判断自启动脚本是否启用
    autostartStatusFile = '/etc/rc4.d/S01' + echo
    if os.path.exists(autostartStatusFile):
        mw.execShell('update-rc.d -f ' + echo + ' remove')
        return mw.returnJson(True, '已关闭自启动!')
    else:
        mw.execShell('update-rc.d ' + echo + ' defaults 80 80')
        return mw.returnJson(True, '已开启自启动!')


def projectAdd():
    args = getArgs()
    data = checkArgs(args, ['name', 'path', 'startScript', 'reloadScript', 'stopScript'])
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
    data = checkArgs(args, ['id', 'name', 'path', 'startScript', 'reloadScript', 'stopScript'])
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
    echo = project.get('echo', '')
    saveOne('project', id, {
        'name': name,
        'path': path,
        'start_script': startScript,
        'reload_script': reloadScript,
        'stop_script': stopScript,
        'autostart_script': autostartScript
    })
    statusFile = '%s/script/%s_status' % (getServerDir(), echo)
    makeScriptFile(echo + '_start.sh', 'echo "正在启动项目，请稍侯..."\ntouch %s\necho "启动中..." >> %s\n%s\nrm -f %s' % (statusFile, statusFile, startScript, statusFile))
    makeScriptFile(echo + '_reload.sh', 'echo "正在重启项目，请稍侯..."\ntouch %s\necho "重启中..." >> %s\n%s\nrm -f %s' % (statusFile, statusFile, reloadScript, statusFile))
    makeScriptFile(echo + '_stop.sh', 'echo "正在停止项目，请稍侯..."\ntouch %s\necho "停止中..." >> %s\n%s\nrm -f %s' % (statusFile, statusFile, stopScript, statusFile))
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
    echo = project.get('echo', '')
    logPath = getServerDir() + '/script'
    if not os.path.exists(logPath):
        os.system('mkdir -p ' + logPath)
    logFile = logPath + '/' + echo + '.log'
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
    echo = project.get('echo', '')
    logPath = getServerDir() + '/script'
    if not os.path.exists(logPath):
        os.system('mkdir -p ' + logPath)
    logFile = logPath + '/' + echo + '.log'
    if not os.path.exists(logFile):
        return mw.returnJson(False, '当前日志为空!')
    os.system('echo "" > ' + logFile)
    return mw.returnJson(True, '清空成功!')

def extractDomainFromGitUrl(url):
    if '@' in url:
        domain = url.split('@')[1]
    else:
        domain = url.split('//')[1]
    domain = domain.split('/')[0]
    if ':' in domain:
        domain = domain.split(':')[0]
    return domain

def getAddKnownHostsScript():
    args = getArgs()
    data = checkArgs(args, ['gitUrl'])

    if not data[0]:
        return data[1]
    git_url = unquote(args['gitUrl'], 'utf-8')
    host = extractDomainFromGitUrl(git_url)
    is_host_in_known_hosts = mw.checkExistHostInKnownHosts(host)
    cmd = ""
    if not is_host_in_known_hosts:
        cmd += """
        echo "正在添加git服务器到已知主机列表..."
        {
            echo "\n" >> ~/.ssh/known_hosts
            ssh-keyscan %(host)s >> ~/.ssh/known_hosts
            /etc/init.d/ssh restart
        } || echo "添加可信域名失败"
        """ % {'host': host}

    return cmd
    
def getCloneScript():
    args = getArgs()
    data = checkArgs(args, ['gitUrl', 'path'])

    if not data[0]:
        return data[1]

    git_url = unquote(args['gitUrl'], 'utf-8')
    path = unquote(args['path'], 'utf-8')
    
    exist_path = os.path.exists(path)
    
    cmd = ""
    if exist_path:
        cmd += """
        echo "正在删除旧项目文件..."
        rm -rf %(path)s
        """ % {'path': path}
    cmd += """
    echo "正在拉取项目文件..."
    export GIT_SSH_COMMAND='ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
    git clone --progress %(git_url)s %(path)s
    echo "拉取项目文件成功"
    """ % {'git_url': git_url, 'path': path}

    return cmd

def cloneProject():
    args = getArgs()
    data = checkArgs(args, ['gitUrl', 'path'])

    if not data[0]:
        return data[1]
    
    git_url = unquote(args['gitUrl'], 'utf-8')
    path = unquote(args['path'], 'utf-8')
    # host = extractDomainFromGitUrl(git_url)
    # mw.addHostToKnownHosts(host)
    
    log_file = mw.getRunDir() + '/tmp/plugin_jianghujs_clone_project.log'
    

    cmd = "set -e\n"
    if os.path.exists(path):
        cmd += """
        echo "正在删除旧项目文件..."
        rm -rf %(path)s
        """ % {'path': path}

    cmd += """
    echo "正在拉取项目文件..."
    git clone --progress %(git_url)s %(path)s
    echo "拉取项目文件成功"
    """ % {'git_url': git_url, 'path': path, 'log_file': log_file}

    # git clone --progress %(git_url)s %(path)s  2>&1 | tee %(log_file)s
    # git clone %(git_url)s %(path)s > %(log_file)s 2>&1

    # 写入临时文件用于执行
    tempFilePath = mw.getRunDir() + '/tmp/' +  str(time.time()) + '.sh'
    tempFileContent = """
    { 
        {
            %(cmd)s
            if [ $? -eq 0 ]; then
                true
            else
                false
            fi
        } && {
            echo "操作成功"
            rm -f %(tempFilePath)s
        }
    } || { 
        rm -f %(tempFilePath)s
        exit 1
    }
    """ % {'cmd': cmd, 'tempFilePath': tempFilePath}
    mw.writeFile(tempFilePath, tempFileContent)
    mw.execShell('chmod 750 ' + tempFilePath)
    
    # 使用os.system执行命令，不会返回结果
    data = mw.execShell('source /root/.bashrc && ' + tempFilePath + ' > ' + log_file + ' 2>&1')
    
    if data[2] != 0:
        return mw.returnJson(False, '执行失败' )
    return mw.returnJson(True, 'ok', )

def getProjectDeployFile():
    args = getArgs()
    data = checkArgs(args, ['path'])

    if not data[0]:
        return data[1]
    
    path = unquote(args['path'], 'utf-8')
    deployFile = path + '/deploy.sh'
    if os.path.exists(deployFile):
        return mw.readFile(deployFile)
    return ''

def checkProjectNameExist():
    args = getArgs()
    data = checkArgs(args, ['name'])

    if not data[0]:
        return data[1]
    
    name = unquote(args['name'], 'utf-8')
    for item in getAll('project'):
        if item['name'] == name:
            return mw.returnJson(True, 'ok', True)
    return mw.returnJson(True, 'ok', False)

if __name__ == "__main__":
    DDB.config.storage_directory = getServerDir() + '/data/'
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'reload':
        print(reload())
    elif func == 'restart':
        print(restart())
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
    elif func == 'get_add_known_hosts_script':
        print(getAddKnownHostsScript())
    elif func == 'get_clone_script':
        print(getCloneScript())
    elif func == 'clone_project':
        print(cloneProject())
    elif func == 'get_project_deploy_file':
        print(getProjectDeployFile())
    elif func == 'check_project_name_exist':
        print(checkProjectNameExist())
    else:
        print('error')
