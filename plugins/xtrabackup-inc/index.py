# coding:utf-8

import sys
import io
import os
import time
import re
from urllib.parse import unquote

sys.path.append(os.getcwd() + "/class/core")
import mw

ddb = None

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'xtrabackup-inc'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def runLog():
    return getServerDir() + '/xtrabackup.log'


def initdInstall():
    updateCurrentMysqlPswInScript()
    return 'ok'

# 更新脚本中的配置
def updateScriptConfig(config):
    port = config.get('port', None)
    user = config.get('user', None)
    password = config.get('password', None)
    port_rep = '--port\s*=\s*(.*?) '
    user_rep = '--user\s*=\s*(.*?) '
    password_rep = '--password\s*=\s*(.*?) '
    # 更新全量备份脚本
    full_script_file = getFullScriptFile()
    full_script_content = mw.readFile(full_script_file)
    if port is not None:
        full_script_content = re.sub(
            port_rep, '--port=' + port + ' ', full_script_content)
    if user is not None:
        full_script_content = re.sub(
            user_rep, '--user=' + user + ' ', full_script_content)
    if password is not None:
        full_script_content = re.sub(
            password_rep, '--password=' + password + ' ', full_script_content)

    mw.writeFile(full_script_file, full_script_content)

    # 更新增量备份脚本
    inc_script_file = getIncScriptFile()
    inc_script_content = mw.readFile(inc_script_file)
    password_rep = '--password\s*=\s*(.*?) '
    if port is not None:
        inc_script_content = re.sub(
            port_rep, '--port=' + port + ' ', inc_script_content)
    if user is not None:
        inc_script_content = re.sub(
            user_rep, '--user=' + user + ' ', inc_script_content)
    if password is not None:
        inc_script_content = re.sub(
            password_rep, '--password=' + password + ' ', inc_script_content)
    mw.writeFile(inc_script_file, inc_script_content)


def updateCurrentMysqlPswInScript():
    try:
        mysqlConn = mw.M('config').dbPos(
            mw.getServerDir() + '/mysql-apt', 'mysql')
        password = mysqlConn.where(
            'id=?', (1,)).getField('mysql_root')
        updateScriptConfig({
            "password": password
        })
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


def getConf():
    path = getServerDir() + "/xtrabackup.sh"
    return path


def getFullScriptFile():
    path = getServerDir() + "/xtrabackup-full.sh"
    return path


def getIncScriptFile():
    path = getServerDir() + "/xtrabackup-inc.sh"
    return path


def getIncRecoveryScriptFile():
    path = getServerDir() + "/xtrabackup-inc-recovery.sh"
    return path

def getLockFile():
    path = getServerDir() + "/inc_task_lock"
    return path

def getSetting():
    file = getFullScriptFile()
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
    data = checkArgs(args, ['password'])
    if not data[0]:
        return data[1]

    updateScriptConfig(args)
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


def getBaseBackupPathConf():
    return getServerDir() + '/base-backup-path.conf'


def getBaseBackupPath():
    path = mw.readFile(getBaseBackupPathConf())
    if (path == False):
        path = '/www/backup/xtrabackup_data_base'
    else:
        path = path.strip()
    return path


def getIncBackupPathConf():
    return getServerDir() + '/inc-backup-path.conf'


def getIncBackupPath():
    path = mw.readFile(getIncBackupPathConf())
    if (path == False):
        path = '/www/backup/xtrabackup_data_incremental'
    else:
        path = path.strip()
    return path


def doMysqlBackup():
    args = getArgs()
    content = mw.readFile(getConf())

    if args['content'] is not None:
        content = unquote(str(args['content']), 'utf-8').replace("\\n", "\n")

    # 写入临时文件用于执行
    tempFilePath = getServerDir() + '/xtrabackup_temp.sh'
    mw.writeFile(tempFilePath, '%(content)s\nrm -f %(tempFilePath)s' %
                 {'content': content, 'tempFilePath': tempFilePath})
    mw.execShell('chmod 750 ' + tempFilePath)
    # 执行脚本
    log_file = runLog()
    mw.execShell('echo $(date "+%Y-%m-%d %H:%M:%S") "备份开始" >> ' + log_file)

    # sync the backup path to the backup script
    # mw.execShell("BACKUP_PATH=%(backupPath)s sh %(tempFilePath)s >> %(logFile)s" % {'backupPath':getBackupPath(), 'tempFilePath': tempFilePath, 'logFile': log_file })
    mw.addAndTriggerTask(
        name='执行Xtrabackup命令[备份]',
        execstr='sh %(tempFilePath)s >> %(logFile)s' % {
            'tempFilePath': tempFilePath, 'logFile': log_file}
    )

    execResult = mw.execShell("tail -n 1 " + log_file)

    # if "备份成功" in execResult[0]:
    #     return mw.returnJson(True, execResult[0])

    # Tip: 兼容 老版本的 xtrabackup.sh; 未来可以删除
    if os.path.exists(os.path.join(getBackupPath(), 'mysql')):
        return mw.returnJson(True, '备份成功')

    return mw.returnJson(True, execResult[0])


def getRecoveryBackupScript():

    # 获取的mysql目录
    mysqlDir = ''
    mysqlName = ''
    if os.path.exists('/www/server/mysql-apt'):
        mysqlDir = '/www/server/mysql-apt'
        mysqlName = 'mysql-apt'
    elif os.path.exists('/www/server/mysql'):
        mysqlDir = '/www/server/mysql'
        mysqlName = 'mysql'
    else:
        return mw.returnJson(False, '未检测到安装的mysql插件!')
    recoveryScript = 'echo "开始全量恢复..." \nBACKUP_BASE_PATH=%(baseBackupPath)s\nBACKUP_INC_PATH=%(incBackupPath)s\nMYSQL_NAME=%(mysqlName)s\nMYSQL_DIR=%(mysqlDir)s\nset -x\n%(script)s' % {
        'baseBackupPath': getBaseBackupPath(), 'incBackupPath': getIncBackupPath(), 'mysqlName': mysqlName, 'mysqlDir': mysqlDir, 'script': mw.readFile(getIncRecoveryScriptFile())}
    return mw.returnJson(True, 'ok', recoveryScript)


def doTaskWithLock():
    args = getArgs()
    name = args['name'].strip()
    content = unquote(str(args['content']), 'utf-8').replace("\\n", "\n")

    # 加锁
    execTime = time.time()
    lockFile = getLockFile()
    if os.path.exists(lockFile):
        lock_date = mw.readFile(lockFile)
        # 30 分钟未解锁则失效
        if (execTime - float(lock_date)) < 60 * 30:
            return mw.returnJson(False, '已有任务在执行中，请等待任务执行结束...')

    # 写入临时文件用于执行
    tempFilePath = getServerDir() + '/xtrabackup_inc_temp.sh'
    mw.writeFile(tempFilePath, 'LOCK_FILE_PATH=%(lockFile)s\n%(content)s\nrm -f %(tempFilePath)s\necho %(name)s成功' %
                 {'name': name, 'content': content, 'lockFile': lockFile, 'tempFilePath': tempFilePath})
    mw.execShell('chmod 750 ' + tempFilePath)
    # 执行脚本
    log_file = runLog()
    mw.execShell('echo $(date "+%Y-%m-%d %H:%M:%S") "' +
                 name + '开始" >> ' + log_file)

    # mw.execShell("sh %(tempFilePath)s >> %(logFile)s" % {'tempFilePath': tempFilePath, 'logFile': log_file })
    mw.addAndTriggerTask(
        name='执行Xtrabackup命令[' + name + ']',
        execstr="sh %(tempFilePath)s >> %(logFile)s" % {
            'tempFilePath': tempFilePath, 'logFile': log_file}
    )

    execResult = mw.execShell("tail -n 1 " + log_file)

    # if "恢复成功" in execResult[0]:
    #     return mw.returnJson(True, '恢复成功; 请前往Mysql插件 <br/>- "从服务器获取"  <br/>- 如果ROOT密码有变动👉"修复ROOT密码" <br/>Tip: 若无法找回密码, 可以使用无密码模式启动mysql, 然后再使用mysql的sql脚本设置密码。')

    return mw.returnJson(True, execResult[0])


def getBackupPath():
    return mw.returnJson(True, 'ok',  {
        "base": getBaseBackupPath(),
        "inc": getIncBackupPath()
    })


def setBackupPath():
    args = getArgs()
    data = checkArgs(args, ['base', 'inc'])
    if not data[0]:
        return data[1]

    base = args['base']
    inc = args['inc']
    mw.writeFile(getBaseBackupPathConf(), base)
    mw.writeFile(getIncBackupPathConf(), inc)
    return mw.returnJson(True, '修改成功!')


def getFullBackupScript():
    backupScript = 'echo "开始全量备份..." \nBACKUP_BASE_PATH=%(baseBackupPath)s\nBACKUP_INC_PATH=%(incBackupPath)s\nset -x\n %(script)s' % {
        'baseBackupPath': getBaseBackupPath(), 'incBackupPath': getIncBackupPath(), 'script': mw.readFile(getFullScriptFile())}
    return mw.returnJson(True, 'ok',  backupScript)


def getIncBackupScript():
    backupScript = 'echo "开始增量备份..." \nBACKUP_BASE_PATH=%(baseBackupPath)s\nBACKUP_INC_PATH=%(incBackupPath)s\nset -x\n %(script)s' % {
        'baseBackupPath': getBaseBackupPath(), 'incBackupPath': getIncBackupPath(), 'script': mw.readFile(getIncScriptFile())}
    return mw.returnJson(True, 'ok',  backupScript)


def getFullBackupCronScript():
    # cron中直接执行脚本文件
    backupCronScript = 'echo "开始全量备份..." \nexport BACKUP_BASE_PATH=%(baseBackupPath)s\nexport BACKUP_INC_PATH=%(incBackupPath)s\nexport LOCK_FILE_PATH=%(lockFilePath)s\nset -x\n bash %(scriptFile)s' % {
        'baseBackupPath': getBaseBackupPath(), 'incBackupPath': getIncBackupPath(), 'lockFilePath': getLockFile(), 'scriptFile': getFullScriptFile()}
    return mw.returnJson(True, 'ok',  backupCronScript)


def getIncBackupCronScript():
    # cron中直接执行脚本文件
    backupCronScript = 'echo "开始增量备份..." \nexport BACKUP_BASE_PATH=%(baseBackupPath)s\nexport BACKUP_INC_PATH=%(incBackupPath)s\nexport LOCK_FILE_PATH=%(lockFilePath)s\nset -x\n bash %(scriptFile)s' % {
        'baseBackupPath': getBaseBackupPath(), 'incBackupPath': getIncBackupPath(), 'lockFilePath': getLockFile(), 'scriptFile': getIncScriptFile()}
    return mw.returnJson(True, 'ok',  backupCronScript)


def backupCallback():
    args = getArgs()
    data = checkArgs(args, ['backup_type'])
    if not data[0]:
        return data[1]
    backup_type = args['backup_type']
    backup_path = getBaseBackupPath() if backup_type == 'full' else getIncBackupPath()
    if os.path.exists(backup_path):
        # 获取文件大小、时间
        backup = {}
        file_size = mw.getDirSize(backup_path)
        file_create_time = os.path.getctime(backup_path)
        backup['size_bytes'] = float(file_size)
        backup['size'] = mw.toSize(file_size)
        backup['add_timestamp'] = file_create_time
        backup['add_time'] = mw.toTime(file_create_time)
        backup['backup_type'] = backup_type
        print('backup', backup)
        ddb.saveOne('backup_history', time.time(), backup)
    return 'ok'


if __name__ == "__main__":
    ddb = mw.getDDB(getServerDir() + '/data/')
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
        print(getBackupPath())
    elif func == 'set_backup_path':
        print(setBackupPath())
    elif func == 'full_backup_script':
        print(getFullBackupScript())
    elif func == 'full_backup_cron_script':
        print(getFullBackupCronScript())
    elif func == 'inc_backup_script':
        print(getIncBackupScript())
    elif func == 'inc_backup_cron_script':
        print(getIncBackupCronScript())
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
    elif func == 'do_delete_backup':
        print(doDeleteBackup())
    elif func == 'do_task_with_lock':
        print(doTaskWithLock())
    elif func == 'backup_callback':
        print(backupCallback())
    else:
        print('error')
