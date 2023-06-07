# coding:utf-8

import sys
import io
import os
import time
import re
from urllib.parse import unquote

sys.path.append(os.getcwd() + "/class/core")
import mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True

def getPluginName():
    return 'xtrabackup'  

def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()

def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()

def runLog():
    return getServerDir() + '/xtrabackup.log'  

def initdInstall():
    updateCurrentMysqlPswInConf()
    return 'ok'


def updateCurrentMysqlPswInConf():
    try:
        mysqlConn = mw.M('config').dbPos(mw.getServerDir() + '/mysql-apt', 'mysql')
        password = mysqlConn.where(
            'id=?', (1,)).getField('mysql_root')
        file = getConf()
        content = mw.readFile(file)
        password_rep = '--password\s*=\s*(.*?) '
        content = re.sub(password_rep, '--password=' + password + ' ', content)
        mw.writeFile(file, content)
    except Exception as e:
        return str(e)

def status():
    return 'start'

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

def getXtrabackupCron():
    args = getArgs()
    data = checkArgs(args, ['xtrabackupCronName'])
    if not data[0]:
        return data[1]
    xtrabackupCronName = args['xtrabackupCronName']
    cronCount = mw.M('crontab').where('name=?', (xtrabackupCronName,)).count()
    cronList = mw.M('crontab').where('name=?', (xtrabackupCronName,)).field('id,name,type,where_hour,where_minute').select()
    if cronCount > 0:
        return mw.returnJson(True,  xtrabackupCronName + ' 已存在', { 
            'id': cronList[0]['id'],
            'name': cronList[0]['name'],
            'type': cronList[0]['type'],
            'hour': cronList[0]['where_hour'],
            'minute': cronList[0]['where_minute'],
        })
    return mw.returnJson(False, xtrabackupCronName + ' 不存在')    

def getSetting():
    file = getConf()
    content = mw.readFile(file)
    port_rep = '--port\s*=\s*(.*?) '
    port_tmp = re.search(port_rep, content).groups()[0].strip()
    user_rep = '--user\s*=\s*(.*?) '
    user_tmp = re.search(user_rep, content).groups()[0].strip()
    password_rep = '--password\s*=\s*(.*?) '
    password_tmp = re.search(password_rep, content).groups()[0].strip()
    return mw.returnJson(True, 'ok', {
        'port': port_tmp,
        'user': user_tmp,
        'password': password_tmp
    })

def changeSetting():
    args = getArgs()
    data = checkArgs(args, ['port', 'user', 'password'])
    if not data[0]:
        return data[1]

    port = args['port']
    user = args['user']
    password = args['password']
    file = getConf()
    content = mw.readFile(file)
    
    port_rep = '--port\s*=\s*(.*?) '
    content = re.sub(port_rep, '--port=' + port + ' ', content)
    user_rep = '--user\s*=\s*(.*?) '
    content = re.sub(user_rep, '--user=' + user + ' ', content)
    password_rep = '--password\s*=\s*(.*?) '
    content = re.sub(password_rep, '--password=' + password + ' ', content)
    mw.writeFile(file, content)
    return mw.returnJson(True, '编辑成功!')

def testSetting():
    args = getArgs()
    data = checkArgs(args, ['port', 'user', 'password'])
    if not data[0]:
        return data[1]

    port = args['port']
    user = args['user']
    password = args['password']
    db = mw.getMyORM()
    db.setPort(port)
    # db.setSocket(getSocketFile())
    db.setPwd(password)
    mysqlMsg = str(db.query('show databases'))
    if mysqlMsg != None:
        if "1045" in mysqlMsg:
            return mw.returnJson(False, '连接错误!')
    return mw.returnJson(True, '连接成功!')

def getBackupPathConf():
    return getServerDir() + '/backup-path.conf'

def getBackupPath():
    path = mw.readFile(getBackupPathConf())
    if(path == False):
        path = '/www/backup/xtrabackup_data'
    else:
        path = path.strip()

    return path


def executeScript(name, tempFileName, extraCommands = None):
    args = getArgs()
    content = mw.readFile(getConf())

    if args['content'] is not None:
        content = unquote(str(args['content']), 'utf-8').replace("\\n", "\n")

    # 写入临时文件用于执行
    tempFilePath = getServerDir() + '/' + tempFileName
    mw.writeFile(tempFilePath, '%(content)s\nrm -f %(tempFilePath)s\n%(extraCommands)s' % {'content': content, 'tempFilePath': tempFilePath, 'extraCommands': extraCommands or ''})
    mw.execShell('chmod 750 ' + tempFilePath)
    # 执行脚本
    log_file = runLog()
    mw.execShell('echo $(date "+%Y-%m-%d %H:%M:%S") "%(name)s开始" >> ' + log_file % {'name': name})
    
    # 运行指定的命令
    execstr = "sh %(tempFilePath)s >> %(logFile)s" % {'tempFilePath': tempFilePath, 'logFile': log_file }
    if name == '执行Xtrabackup命令[备份]':
        execstr = "BACKUP_PATH=%(backupPath)s " + execstr % {'backupPath': getBackupPath()}

    mw.addAndTriggerTask(
        name = name,
        execstr = execstr
    )
    
    execResult = mw.execShell("tail -n 1 " + log_file)
    return mw.returnJson(True, execResult[0])

def doMysqlBackup():
    # Tip: 兼容 老版本的 xtrabackup.sh; 未来可以删除
    # if os.path.exists(os.path.join(getBackupPath(), 'mysql')):
    #     return mw.returnJson(True, '备份成功')
        
    return executeScript('执行Xtrabackup命令[备份]', 'xtrabackup_temp.sh')


def backupList():
    result = []
    xtrabackup_data_history_path = '/www/backup/xtrabackup_data_history'
    for d_walk in os.walk(xtrabackup_data_history_path):
        for d_list in d_walk[2]:
            if mw.getFileSuffix(d_list) == 'zip': 
                filepath = '%s/%s' % (xtrabackup_data_history_path, d_list)
                result.append({
                    'filename': d_list,
                    'size': mw.getPathSize(filepath),
                    'sizeTxt': mw.toSize(mw.getPathSize(filepath)),
                    'createTime': os.path.getctime(filepath)
                })
    return mw.returnJson(True, 'ok', result)

def getRecoveryBackupScript():
    args = getArgs()
    data = checkArgs(args, ['filename'])
    if not data[0]:
        return data[1]
    filename = args['filename']

    # 获取的mysql目录
    mysqlDir = ''
    if os.path.exists('/www/server/mysql-apt'):
        mysqlDir = '/www/server/mysql-apt/data'
    elif os.path.exists('/www/server/mysql'):
        mysqlDir = '/www/server/mysql/data'
    else :
        return mw.returnJson(False, '未检测到安装的mysql插件!')

    recoveryScript = '#!/bin/bash\n'
    if os.path.exists('/www/server/mysql-apt'):
        recoveryScript += ('systemctl stop mysql-apt\n')
    elif os.path.exists('/www/server/mysql'):
        recoveryScript += ('systemctl stop mysql\n')
    recoveryScript += ('mv %s %s_%s\n' % (mysqlDir, mysqlDir, time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))))
    recoveryScript += ('rm -rf /www/backup/xtrabackup_data_restore\n')
    recoveryScript += ('unzip -d /www/backup/xtrabackup_data_restore /www/backup/xtrabackup_data_history/%s\n' % (filename))
    recoveryScript += ('xtrabackup --prepare --target-dir=/www/backup/xtrabackup_data_restore &>> /www/wwwlogs/xtrabackup.log\n')
    recoveryScript += ('xtrabackup --copy-back --target-dir=/www/backup/xtrabackup_data_restore &>> /www/wwwlogs/xtrabackup.log\n')
    recoveryScript += ('chown -R mysql:mysql %s \n' % (mysqlDir))
    recoveryScript += ('chmod -R 755 ' + mysqlDir + '\n')
    if os.path.exists('/www/server/mysql-apt'):
        recoveryScript += ('systemctl start mysql-apt\n')
    elif os.path.exists('/www/server/mysql'):
        recoveryScript += ('systemctl start mysql\n')
    return mw.returnJson(True, 'ok', recoveryScript)

def doRecoveryBackup():
    return executeScript('执行Xtrabackup命令[恢复]', 'recovery_temp.sh', 'echo 恢复成功')

def doDeleteBackup():
    args = getArgs()
    data = checkArgs(args, ['filename'])
    if not data[0]:
        return data[1]
    filename = args['filename']
    mw.execShell('rm -f /www/backup/xtrabackup_data_history/' + filename)
    return mw.returnJson(True, '删除成功!')

def getConf():
    path = getServerDir() + "/xtrabackup.sh"
    return path

def returnBackupPath():
    return mw.returnJson(True, 'ok',  getBackupPath())

def setBackupPath():
    args = getArgs()
    data = checkArgs(args, ['path'])
    if not data[0]:
        return data[1]

    path = args['path']
    mw.writeFile(getBackupPathConf(), path)
    return mw.returnJson(True, '修改成功!')

def getConfContent():
    return mw.returnJson(True, 'ok',  mw.readFile(getConf()))

if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'run_log':
        print(runLog())
    elif func == 'initd_install':
        print(initdInstall())
    elif func == 'conf':
        print(getConf()) 
    elif func == 'get_backup_path':
        print(returnBackupPath())
    elif func == 'set_backup_path':
        print(setBackupPath())
    elif func == 'conf_content':
        print(getConfContent())
    elif func == 'get_xtrabackup_cron':
        print(getXtrabackupCron())
    elif func == 'get_setting':
        print(getSetting())     
    elif func == 'change_setting':
        print(changeSetting())   
    elif func == 'test_setting':
        print(testSetting())     
    elif func == 'do_mysql_backup':
        print(doMysqlBackup())
    elif func == 'backup_list':
        print(backupList())
    elif func == 'get_recovery_backup_script':
        print(getRecoveryBackupScript())
    elif func == 'do_recovery_backup':
        print(doRecoveryBackup())
    elif func == 'do_delete_backup':
        print(doDeleteBackup())
    else:
        print('error')
