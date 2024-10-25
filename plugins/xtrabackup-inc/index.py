# coding:utf-8

import json
import sys
import io
import os
import time
import re
from urllib.parse import unquote
import configparser

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

def getConf():
    initConf()
    config = configparser.ConfigParser()
    file = getServerDir() + '/backup.ini'
    config.read(file)
    return config

def setConf(section, key, value):
    file = getServerDir() + '/backup.ini'
    config = getConf()
    
    if not config.has_section(section):
        config.add_section(section)
    
    config.set(section, key, value)
    
    with open(file, 'w') as configfile:
        config.write(configfile)

def initConf():
    # 验证 backup.ini 是否存在
    if not os.path.exists(getServerDir() + '/backup.ini'):
        file = getPluginDir() + '/conf/backup.ini'
        mw.writeFile(getServerDir() + '/backup.ini', mw.readFile(file))
        return

def getBackupConf():
    # 验证 backup.ini 是否存在
    if not os.path.exists(getServerDir() + '/backup.ini'):
        initConf()
    config = getConf()

    # 将 configparser 对象转换为字典
    config_dict = {s:dict(config.items(s)) for s in config.sections()}
    
    # 将字典转换为 JSON
    config_json = json.dumps(config_dict)
    return config_json

def setBackupConf():
    args = getArgs()
    data = checkArgs(args, ['section', 'key', 'value'])
    if not data[0]:
        return data[1]
    section = args['section']
    key = args['key']
    value = args['value']
    setConf(section, key, value)
    return mw.returnJson(True, '修改成功!')
    
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


def getShConf():
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

def getBackupPathConfig():
    config = getConf()
    path = '/www/backup/xtrabackup_inc_data'
    if config.has_option('backup', 'path'):
        path = config['backup']['path']
    return path

def getBaseBackupPath():
    return getBackupPathConfig() + '/base'

def getIncBackupPath():
    return getBackupPathConfig() + '/inc'

def getBackupShellDefineValue():
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
    
    config = getConf()
    backupZip = config['backup_inc']['backup_zip']
    backupCompress = config['backup_full']['backup_compress']

    return f"""
export BACKUP_PATH={getBackupPathConfig()}
export BACKUP_BASE_PATH={getBaseBackupPath()}
export BACKUP_INC_PATH={getIncBackupPath()}
export BACKUP_COMPRESS={backupCompress}
export BACKUP_ZIP={backupZip}
export LOCK_FILE_PATH={getLockFile()}
export MYSQL_NAME={mysqlName}
export MYSQL_DIR={mysqlDir}
    """

def doMysqlBackup():
    args = getArgs()
    content = mw.readFile(getShConf())

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

    mw.addAndTriggerTask(
        name='执行Xtrabackup命令[备份]',
        execstr='sh %(tempFilePath)s >> %(logFile)s' % {
            'tempFilePath': tempFilePath, 'logFile': log_file}
    )

    execResult = mw.execShell("tail -n 1 " + log_file)

    return mw.returnJson(True, execResult[0])


def getRecoveryBackupScript():
    recoveryScript = f'echo "开始增量恢复..." \n{getBackupShellDefineValue()}\nset -x\n{mw.readFile(getIncRecoveryScriptFile())}'
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
    return mw.returnJson(True, 'ok',  getBackupPathConfig())


def getFullBackupScript():
    backupScript = f'echo "开始全量备份..." \n{getBackupShellDefineValue()}\nset -x\n {mw.readFile(getFullScriptFile())}'
    return mw.returnJson(True, 'ok',  backupScript)


def getIncBackupScript():
    backupScript = f'echo "开始增量备份..." \n{getBackupShellDefineValue()}\nset -x\n { mw.readFile(getIncScriptFile())}'
    return mw.returnJson(True, 'ok',  backupScript)


def getFullBackupCronScript():
    backupCronScript = f'echo "开始全量备份..." \n{getBackupShellDefineValue()}\nset -x\n bash {getFullScriptFile()}'
    return mw.returnJson(True, 'ok',  backupCronScript)


def getIncBackupCronScript():
    backupCronScript = f'echo "开始增量备份..." \n{getBackupShellDefineValue()}\nset -x\n bash {getIncScriptFile()}' 
    return mw.returnJson(True, 'ok',  backupCronScript)

def getIncRecoveryCronScript():
    recoveryCronScript = f'echo "开始增量恢复..." \n{getBackupShellDefineValue()}\nset -x\nbash {getIncRecoveryScriptFile()}' 
    return mw.returnJson(True, 'ok',  recoveryCronScript)

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
        print(getBackupConf())
    elif func == 'set_conf':
        print(setBackupConf())
    elif func == 'get_backup_path':
        print(getBackupPath())
    elif func == 'full_backup_script':
        print(getFullBackupScript())
    elif func == 'full_backup_cron_script':
        print(getFullBackupCronScript())
    elif func == 'inc_backup_script':
        print(getIncBackupScript())
    elif func == 'inc_backup_cron_script':
        print(getIncBackupCronScript())
    elif func == 'get_setting':
        print(getSetting())
    elif func == 'change_setting':
        print(changeSetting())
    elif func == 'test_setting':
        print(testSetting())
    elif func == 'do_mysql_backup':
        print(doMysqlBackup())
    elif func == 'get_recovery_backup_script':
        print(getRecoveryBackupScript())
    elif func == 'get_inc_recovery_cron_script':
        print(getIncRecoveryCronScript())
    elif func == 'do_task_with_lock':
        print(doTaskWithLock())
    elif func == 'backup_callback':
        print(backupCallback())
    else:
        print('error')
