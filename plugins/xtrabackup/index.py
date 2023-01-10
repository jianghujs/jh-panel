# coding:utf-8

import sys
import io
import os
import time
import re

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

def doMysqlBackup():
    log_file = runLog()
    xtrabackupScript = getServerDir() + '/xtrabackup.sh'
    mw.execShell('echo $(date "+%Y-%m-%d %H:%M:%S") "备份开始" >> ' + log_file)
    execResult = mw.execShell("sh %(xtrabackupScript)s >> %(logFile)s" % {'xtrabackupScript': xtrabackupScript, 'logFile': log_file })
    if execResult[1]:
        return mw.returnJson(False, '备份失败!' + execResult[1])
    mw.execShell('echo $(date "+%Y-%m-%d %H:%M:%S") "备份成功" >> ' + log_file)
    return mw.returnJson(True, '备份成功!')


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

def doRecoveryBackup():
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

    mw.execShell('mv %s %s_%s' % (mysqlDir, mysqlDir, time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))))
    mw.execShell('rm -rf /www/backup/xtrabackup_data_restore')
    mw.execShell('unzip -d /www/backup/xtrabackup_data_restore /www/backup/xtrabackup_data_history/%s' % (filename))
    mw.execShell('mv /www/backup/xtrabackup_data_restore/www/backup/xtrabackup_data %s' % (mysqlDir))
    mw.execShell('chown -R mysql:mysql %s' % (mysqlDir))
    mw.execShell('chmod -R 755 ' + mysqlDir)
    if os.path.exists('/www/server/mysql-apt'):
        mw.execShell('systemctl restart mysql-apt')
    elif os.path.exists('/www/server/mysql'):
        mw.execShell('systemctl restart mysql')

    return mw.returnJson(True, '恢复成功; 请前往Mysql插件 <br/>- "从服务器获取"  <br/>- 如果ROOT密码有变动👉"修复ROOT密码" <br/>Tip: 若无法找回密码, 可以使用无密码模式启动mysql, 然后再使用mysql的sql脚本设置密码。')
    # return mw.returnJson(True, '恢复成功\n \nt\t- 若root密码有 请到mysql插件的管理列表-点击【修复ROOT密码】更新ROOT密码!!')


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
    
if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'run_log':
        print(runLog())
    elif func == 'conf':
        print(getConf())     
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
    elif func == 'do_recovery_backup':
        print(doRecoveryBackup())
    elif func == 'do_delete_backup':
        print(doDeleteBackup())
    else:
        print('error')
