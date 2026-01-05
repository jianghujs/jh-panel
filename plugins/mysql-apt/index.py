# coding:utf-8

import sys
import io
import os
import time
import subprocess
import re
import json
import paramiko
from paramiko import RSAKey
import psutil


# reload(sys)
# sys.setdefaultencoding('utf-8')

sys.path.append(os.getcwd() + "/class/core")
import mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'mysql-apt'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


def getArgs():
    tmp = {}
    try:
      args = sys.argv[2:]
      args_len = len(args)

      if args_len == 1:
          t = args[0].strip('{').strip('}')
          t = t.split(':')
          tmp[t[0]] = t[1]
      elif args_len > 1:
          for i in range(len(args)):
              t = args[i].split(':')
              tmp[t[0]] = t[1]
    except:
      pass

    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def getConf():
    path = getServerDir() + '/etc/my.cnf'
    return path


def getSemiSyncPluginDir():
    return getServerDir() + '/bin/usr/lib/mysql/plugin'


SEMI_SYNC_REQUIRED_DIRECTIVES = [
    'plugin-load-add = semisync_master.so',
    'plugin-load-add = semisync_slave.so',
    'rpl-semi-sync-master-timeout = 5000',
    'rpl-semi-sync-master-wait-no-slave = ON',
    'rpl-semi-sync-master-wait-point = AFTER_SYNC',
    'rpl_semi_sync_master_enabled = 1',
    'rpl_semi_sync_slave_enabled = 1'
]


def _normalize_conf_line(line):
    return re.sub(r'\s+', '', line.strip().lower())


SEMI_SYNC_OPTIONAL_DIRECTIVES = [
    'plugin-dir = ' + getSemiSyncPluginDir()
]

SEMI_SYNC_REQUIRED_NORMALIZED = [_normalize_conf_line(item) for item in SEMI_SYNC_REQUIRED_DIRECTIVES]
SEMI_SYNC_REMOVE_NORMALIZED = [_normalize_conf_line(item) for item in (SEMI_SYNC_REQUIRED_DIRECTIVES + SEMI_SYNC_OPTIONAL_DIRECTIVES)]


def _is_semi_sync_line(line):
    stripped = line.strip()
    if stripped == '' or stripped.startswith('#'):
        return False
    return _normalize_conf_line(stripped) in SEMI_SYNC_REMOVE_NORMALIZED


def isSemiSyncConfigured(content=None):
    if content is None:
        content = mw.readFile(getConf())
    if content is None:
        return False
    pattern = _normalize_conf_line('rpl_semi_sync_master_enabled = 1')
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped == '' or stripped.startswith('#'):
            continue
        if _normalize_conf_line(stripped) == pattern:
            return True
    return False


def applySemiSyncConfigToFile(enable):
    conf_file = getConf()
    content = mw.readFile(conf_file)
    if content is None:
        return (False, '无法读取MySQL配置文件')
    current_enabled = isSemiSyncConfigured(content)
    plugin_dir_present = False
    plugin_dir_norm = None
    if len(SEMI_SYNC_OPTIONAL_DIRECTIVES) > 0:
        plugin_dir_norm = _normalize_conf_line(SEMI_SYNC_OPTIONAL_DIRECTIVES[0])
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped == '' or stripped.startswith('#'):
                continue
            if _normalize_conf_line(stripped) == plugin_dir_norm:
                plugin_dir_present = True
                break

    need_change = False
    if enable:
        if not current_enabled or not plugin_dir_present:
            need_change = True
    else:
        if current_enabled or plugin_dir_present:
            need_change = True

    if not need_change:
        return (False, '')

    lines = content.split('\n')
    filtered_lines = [line for line in lines if not _is_semi_sync_line(line)]

    if enable:
        insert_index = len(filtered_lines)
        for idx, line in enumerate(filtered_lines):
            if line.strip().lower() == '[mysqld]':
                insert_index = idx + 1
                break
        insert_lines = []
        insert_lines.extend(SEMI_SYNC_OPTIONAL_DIRECTIVES)
        insert_lines.extend(SEMI_SYNC_REQUIRED_DIRECTIVES)
        filtered_lines = filtered_lines[:insert_index] + insert_lines + filtered_lines[insert_index:]

    mw.writeFile(conf_file, '\n'.join(filtered_lines))
    return (True, '')


def getSemiSyncStatusSummary(db=None):
    info = {
        'enabled': isSemiSyncConfigured(),
        'master_runtime': False,
        'slave_runtime': False,
        'status_vars': {}
    }
    try:
        close_db = False
        if db is None:
            db = pMysqlDb()
            close_db = True
        master_var = db.query("SHOW GLOBAL VARIABLES LIKE 'rpl_semi_sync_master_enabled'")
        slave_var = db.query("SHOW GLOBAL VARIABLES LIKE 'rpl_semi_sync_slave_enabled'")

        if len(master_var) > 0:
            info['master_runtime'] = str(master_var[0].get('Value', '')).lower() in ('1', 'on', 'true')
        if len(slave_var) > 0:
            info['slave_runtime'] = str(slave_var[0].get('Value', '')).lower() in ('1', 'on', 'true')

        status_keys = [
            'Rpl_semi_sync_master_status',
            'Rpl_semi_sync_master_clients',
            'Rpl_semi_sync_master_yes_tx',
            'Rpl_semi_sync_master_no_tx',
            'Rpl_semi_sync_master_net_wait_time',
            'Rpl_semi_sync_master_net_waits',
            'Rpl_semi_sync_master_trx_newest_wait_time',
            'Rpl_semi_sync_master_net_avg_wait_time',
            'Rpl_semi_sync_master_timefunc_failures',
            'Rpl_semi_sync_slave_status',
            'Rpl_semi_sync_slave_clients',
            'Rpl_semi_sync_slave_yes_tx',
            'Rpl_semi_sync_slave_no_tx'
        ]

        for key in status_keys:
            rows = db.query("SHOW GLOBAL STATUS LIKE '{}'".format(key))
            if rows and len(rows) > 0:
                info['status_vars'][key] = rows[0].get('Value', '')

        if close_db:
            try:
                db.close()
            except Exception:
                pass
    except Exception:
        pass
    return info


def getDbPort():
    file = getConf()
    content = mw.readFile(file)
    rep = 'port\s*=\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()


def getSocketFile():
    file = getConf()
    content = mw.readFile(file)
    rep = 'socket\s*=\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()


def getErrorLogsFile():
    file = getConf()
    content = mw.readFile(file)
    rep = 'log-error\s*=\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()


def contentReplace(content):
    service_path = mw.getServerDir()
    content = content.replace('{$ROOT_PATH}', mw.getRootDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$SERVER_APP_PATH}',
                              service_path + '/' + getPluginName())
    return content


def pSqliteDb(dbname='databases'):
    file = getServerDir() + '/mysql.db'
    name = 'mysql'
    if not os.path.exists(file):
        conn = mw.M(dbname).dbPos(getServerDir(), name)
        csql = mw.readFile(getPluginDir() + '/conf/mysql.sql')
        csql_list = csql.split(';')
        for index in range(len(csql_list)):
            conn.execute(csql_list[index], ())
    else:
        # 现有run
        # conn = mw.M(dbname).dbPos(getServerDir(), name)
        # csql = mw.readFile(getPluginDir() + '/conf/mysql.sql')
        # csql_list = csql.split(';')
        # for index in range(len(csql_list)):
        #     conn.execute(csql_list[index], ())
        conn = mw.M(dbname).dbPos(getServerDir(), name)
    return conn


def pMysqlDb():
    # pymysql
    db = mw.getMyORM()
    # MySQLdb |
    # db = mw.getMyORMDb()

    db.setPort(getDbPort())
    db.setSocket(getSocketFile())
    # db.setCharset("utf8")
    db.setPwd(pSqliteDb('config').where('id=?', (1,)).getField('mysql_root'))
    return db


def initDreplace(version=''):

    my_dir = getServerDir() + '/etc'
    if not os.path.exists(my_dir):
        os.mkdir(my_dir)

    tmp_dir = getServerDir() + '/tmp'
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
        mw.execShell("chown -R mysql:mysql " + tmp_dir)
        mw.execShell("chmod 750 " + tmp_dir)

    mysql_conf = my_dir + '/my.cnf'
    if not os.path.exists(mysql_conf):
        mysql_conf_tpl = getPluginDir() + '/conf/my' + version + '.cnf'
        content = mw.readFile(mysql_conf_tpl)
        content = contentReplace(content)
        mw.writeFile(mysql_conf, content)

    # systemd
    systemDir = mw.systemdCfgDir()
    systemService = systemDir + '/mysql-apt.service'
    systemServiceTpl = getPluginDir() + '/init.d/mysql' + version + '.service.tpl'
    if os.path.exists(systemDir) and not os.path.exists(systemService):
        service_path = mw.getServerDir()
        se_content = mw.readFile(systemServiceTpl)
        se_content = se_content.replace('{$SERVER_PATH}', service_path)
        mw.writeFile(systemService, se_content)
        mw.execShell('systemctl daemon-reload')

    if mw.getOs() != 'darwin':
        mw.execShell('chown -R mysql mysql ' + getServerDir())
    return 'ok'


def status(version=''):
    pid = getPidFile()
    if not os.path.exists(pid):
        return 'stop'
    return 'start'


def getDataDir():
    file = getConf()
    content = mw.readFile(file)
    rep = 'datadir\s*=\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()


def getPidFile():
    file = getConf()
    content = mw.readFile(file)
    rep = 'pid-file\s*=\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()


def binLog():
    args = getArgs()
    conf = getConf()
    con = mw.readFile(conf)

    if con.find('#log-bin=mysql-bin') != -1:
        if 'status' in args:
            return mw.returnJson(False, '0')
        con = con.replace('#log-bin=mysql-bin', 'log-bin=mysql-bin')
        con = con.replace('#binlog_format=mixed', 'binlog_format=mixed')
        mw.execShell('sync')
        restart()
    else:
        path = getDataDir()
        if 'status' in args:
            dsize = 0
            for n in os.listdir(path):
                if len(n) < 9:
                    continue
                if n[0:9] == 'mysql-bin':
                    dsize += os.path.getsize(path + '/' + n)
            return mw.returnJson(True, dsize)
        con = con.replace('log-bin=mysql-bin', '#log-bin=mysql-bin')
        con = con.replace('binlog_format=mixed', '#binlog_format=mixed')
        mw.execShell('sync')
        restart()
        mw.execShell('rm -f ' + path + '/mysql-bin.*')

    mw.writeFile(conf, con)
    return mw.returnJson(True, '设置成功!')


def setSkipGrantTables(v):
    '''
    设置是否密码验证
    '''
    conf = getConf()
    con = mw.readFile(conf)
    if v:
        if con.find('#skip-grant-tables') != -1:
            con = con.replace('#skip-grant-tables', 'skip-grant-tables')
    else:
        con = con.replace('skip-grant-tables', '#skip-grant-tables')
    mw.writeFile(conf, con)
    return True


def getErrorLog():
    args = getArgs()
    filename = getErrorLogsFile()
    if not os.path.exists(filename):
        return mw.returnJson(False, '指定文件不存在!')
    if 'close' in args:
        mw.writeFile(filename, '')
        return mw.returnJson(False, '日志已清空')
    info = mw.getLastLine(filename, 18)
    return mw.returnJson(True, 'OK', info)


def getShowLogFile():
    file = getConf()
    content = mw.readFile(file)
    rep = 'slow-query-log-file\s*=\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()


def pGetDbUser():
    if mw.isAppleSystem():
        user = mw.execShell(
            "who | sed -n '2, 1p' |awk '{print $1}'")[0].strip()
        return user
    return 'mysql'


def initMysql57Data():
    datadir = getDataDir()
    if not os.path.exists(datadir + '/mysql'):
        serverdir = getServerDir()
        myconf = serverdir + "/etc/my.cnf"
        user = pGetDbUser()

        cmd = serverdir + '/bin/usr/sbin/mysqld --basedir=' + serverdir + '/bin/usr --datadir=' + \
            datadir + ' --initialize-insecure --explicit_defaults_for_timestamp'
        data = mw.execShell(cmd)
        # print(cmd)
        # print(data)

        if not mw.isAppleSystem():
            mw.execShell('chown -R mysql:mysql ' + datadir)
            mw.execShell('chmod -R 755 ' + datadir)
        return False
    return True


def initMysql8Data():
    '''
    chmod 644 /www/server/mysql-apt/etc/my.cnf
    try:
    mysqld --basedir=/usr  --datadir=/www/server/mysql-apt/data --initialize-insecure
    mysqld --defaults-file=/www/server/mysql-apt/etc/my.cnf --initialize-insecure
    mysqld --initialize-insecure
    select user, plugin from user;
    update user set authentication_string=password("123123"),plugin='mysql_native_password' where user='root';
    '''
    datadir = getDataDir()
    if not os.path.exists(datadir + '/mysql'):
        serverdir = getServerDir()
        user = pGetDbUser()

        cmd = serverdir + '/bin/usr/sbin/mysqld --basedir=' + serverdir + '/bin/usr --datadir=' + datadir + \
            ' --initialize-insecure --lower-case-table-names=1'
        data = mw.execShell(cmd)
        if data[1].find('ERROR') != -1:
            exit("Init MySQL{} Data Error".format(8))

        if not mw.isAppleSystem():
            mw.execShell('chown -R mysql:mysql ' + datadir)
            mw.execShell('chmod -R 755 ' + datadir)
        return False
    return True


def initMysql8Pwd():
    '''
    /usr/bin/mysql --defaults-file=/www/server/mysql-apt/etc/my.cnf -uroot -e"UPDATE mysql.user SET password=PASSWORD('BhIroUczczNVaKvw') WHERE user='root';flush privileges;"
    /usr/bin/mysql --defaults-file=/www/server/mysql-apt/etc/my.cnf -uroot -e"alter user 'root'@'localhost' identified by '123456';"
    '''
    time.sleep(5)

    serverdir = getServerDir()
    myconf = serverdir + "/etc/my.cnf"
    pwd = mw.getRandomString(16)

    cmd_my = serverdir + '/bin/usr/bin/mysql'

    cmd_pass = cmd_my + ' --defaults-file=' + myconf + ' -uroot -e'
    cmd_pass = cmd_pass + \
        '"alter user \'root\'@\'localhost\' identified by \'' + pwd + '\';'
    cmd_pass = cmd_pass + 'flush privileges;"'
    # print(cmd_pass)
    data = mw.execShell(cmd_pass)
    # print(data)

    # 删除空账户
    drop_empty_user = cmd_my + ' --defaults-file=' + myconf + ' -uroot -p' + \
        pwd + ' -e "use mysql;delete from user where USER=\'\'"'
    mw.execShell(drop_empty_user)

    # 删除测试数据库
    drop_test_db = cmd_my + ' --defaults-file=' + myconf + ' -uroot -p' + \
        pwd + ' -e "drop database test";'
    mw.execShell(drop_test_db)

    # 删除冗余账户
    hostname = mw.execShell('hostname')[0].strip()
    if hostname != 'localhost':
        drop_hostname = cmd_my + ' --defaults-file=' + \
            myconf + ' -uroot -p' + pwd + ' -e "drop user \'\'@\'' + hostname + '\'";'
        mw.execShell(drop_hostname)

        drop_root_hostname = cmd_my + ' --defaults-file=' + \
            myconf + ' -uroot -p' + pwd + ' -e "drop user \'root\'@\'' + hostname + '\'";'
        mw.execShell(drop_root_hostname)

        pSqliteDb('config').where('id=?', (1,)).save('mysql_root', (pwd,))
    return True


def my8cmd(version, method):
    initDreplace(version)
    # mysql 8.0  and 5.7
    try:
        if version == '5.7':
            isInited = initMysql57Data()
        elif version == '8.0':
            isInited = initMysql8Data()

        if not isInited:
            subprocess.run(["systemctl", "start", getPluginName()])
            initMysql8Pwd()
            subprocess.run(["systemctl", "stop", getPluginName()])

        result = subprocess.run(["systemctl", method, getPluginName()])
        if result.returncode == 0:
            return 'ok'
        else:
            return result.stderr if result.stderr else '启动失败'
    except Exception as e:
        return str(e)


def appCMD(version, action):
    return my8cmd(version, action)


def start(version=''):
    res = appCMD(version, 'start')
    return appCMD(version, 'start')


def stop(version=''):
    return appCMD(version, 'stop')


def restart(version=''):
    return appCMD(version, 'restart')


def reload(version=''):
    return appCMD(version, 'reload')


def initdStatus():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    shell_cmd = 'systemctl status ' + \
        getPluginName() + ' | grep loaded | grep "enabled;"'
    data = mw.execShell(shell_cmd)
    if data[0] == '':
        return 'fail'
    return 'ok'


def initdInstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    mw.execShell('systemctl enable ' + getPluginName())
    return 'ok'


def initdUinstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    mw.execShell('systemctl disable ' + getPluginName())
    return 'ok'


def getMyDbPos():
    file = getConf()
    content = mw.readFile(file)
    rep = 'datadir\s*=\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()


def setMyDbPos():
    args = getArgs()
    data = checkArgs(args, ['datadir'])
    if not data[0]:
        return data[1]

    s_datadir = getMyDbPos()
    t_datadir = args['datadir']
    if t_datadir == s_datadir:
        return mw.returnJson(False, '与当前存储目录相同，无法迁移文件!')

    if not os.path.exists(t_datadir):
        mw.execShell('mkdir -p ' + t_datadir)

    # mw.execShell('/etc/init.d/mysqld stop')
    stop()
    mw.execShell('cp -rf ' + s_datadir + '/* ' + t_datadir + '/')
    mw.execShell('chown -R mysql mysql ' + t_datadir)
    mw.execShell('chmod -R 755 ' + t_datadir)
    mw.execShell('rm -f ' + t_datadir + '/*.pid')
    mw.execShell('rm -f ' + t_datadir + '/*.err')

    path = getServerDir()
    myfile = path + '/etc/my.cnf'
    mycnf = mw.readFile(myfile)
    mw.writeFile(path + '/etc/my_backup.cnf', mycnf)

    mycnf = mycnf.replace(s_datadir, t_datadir)
    mw.writeFile(myfile, mycnf)
    start()

    result = mw.execShell(
        'ps aux|grep mysqld| grep -v grep|grep -v python')
    if len(result[0]) > 10:
        mw.writeFile('data/datadir.pl', t_datadir)
        return mw.returnJson(True, '存储目录迁移成功!')
    else:
        mw.execShell('pkill -9 mysqld')
        mw.writeFile(myfile, mw.readFile(path + '/etc/my_backup.cnf'))
        start()
        return mw.returnJson(False, '文件迁移失败!')


def getMyPort():
    file = getConf()
    content = mw.readFile(file)
    rep = 'port\s*=\s*(.*)'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()


def setMyPort():
    args = getArgs()
    data = checkArgs(args, ['port'])
    if not data[0]:
        return data[1]

    port = args['port']
    file = getConf()
    content = mw.readFile(file)
    rep = "port\s*=\s*([0-9]+)\s*\n"
    content = re.sub(rep, 'port = ' + port + '\n', content)
    mw.writeFile(file, content)
    restart()
    return mw.returnJson(True, '编辑成功!')


def runInfo(version):

    if status(version) == 'stop':
        return mw.returnJson(False, 'MySQL未启动', [])

    db = pMysqlDb()
    data = db.query('show global status')
    isError = isSqlError(data)
    if isError != None:
        return isError

    gets = ['Max_used_connections', 'Com_commit', 'Com_select', 'Com_rollback', 'Questions', 'Innodb_buffer_pool_reads', 'Innodb_buffer_pool_read_requests', 'Key_reads', 'Key_read_requests', 'Key_writes',
            'Key_write_requests', 'Qcache_hits', 'Qcache_inserts', 'Bytes_received', 'Bytes_sent', 'Aborted_clients', 'Aborted_connects',
            'Created_tmp_disk_tables', 'Created_tmp_tables', 'Innodb_buffer_pool_pages_dirty', 'Opened_files', 'Open_tables', 'Opened_tables', 'Select_full_join',
            'Select_range_check', 'Sort_merge_passes', 'Table_locks_waited', 'Threads_cached', 'Threads_connected', 'Threads_created', 'Threads_running', 'Connections', 'Uptime']

    result = {}
    # print(data)
    for d in data:
        vname = d["Variable_name"]
        for g in gets:
            if vname == g:
                result[g] = d["Value"]

    # print(result, int(result['Uptime']))
    result['Run'] = int(time.time()) - int(result['Uptime'])
    tmp = db.query('show master status')
    try:
        result['File'] = tmp[0]["File"]
        result['Position'] = tmp[0]["Position"]
    except:
        result['File'] = 'OFF'
        result['Position'] = 'OFF'
    return mw.getJson(result)


def myDbStatus(version):
    result = {}
    db = pMysqlDb()
    data = db.query('show variables')
    isError = isSqlError(data)
    if isError != None:
        return isError

    gets = ['table_open_cache', 'thread_cache_size', 'key_buffer_size', 'tmp_table_size', 'max_heap_table_size', 'innodb_buffer_pool_size',
            'innodb_additional_mem_pool_size', 'innodb_log_buffer_size', 'max_connections', 'sort_buffer_size', 'read_buffer_size', 'read_rnd_buffer_size', 'join_buffer_size', 'thread_stack', 'binlog_cache_size']

    if version != "8.0":
        gets.append('query_cache_size')

    result['mem'] = {}
    for d in data:
        vname = d['Variable_name']
        for g in gets:
            # print(g)
            if vname == g:
                result['mem'][g] = d["Value"]
    return mw.getJson(result)


def setDbStatusBySystemMemory(version):
    pc_mem = psutil.virtual_memory()
    div_gb_factor = (1024.0 ** 3)
    pc_mem_g = float('%.2f' % (pc_mem.total/div_gb_factor))
    args = {}
    if pc_mem_g > 16:
        args = {
            'key_buffer_size': 1024,
            'query_cache_size': 384,
            'tmp_table_size': 2048,
            'max_heap_table_size': 2048,
            'innodb_buffer_pool_size': 4096,
            'innodb_log_buffer_size': 32,
            'sort_buffer_size': 4096,
            'read_buffer_size': 4096,
            'read_rnd_buffer_size': 2048,
            'join_buffer_size': 8192,
            'thread_stack': 512,
            'binlog_cache_size': 256,
            'thread_cache_size': 256,
            'table_open_cache': 2048,
            'max_connections': 500,
        }
    elif pc_mem_g > 8:
        args = {
            'key_buffer_size': 512,
            'query_cache_size': 256,
            'tmp_table_size': 1024,
            'max_heap_table_size': 1024,
            'innodb_buffer_pool_size': 1024,
            'innodb_log_buffer_size': 32,
            'sort_buffer_size': 2048,
            'read_buffer_size': 2048,
            'read_rnd_buffer_size': 1024,
            'join_buffer_size': 4096,
            'thread_stack': 384,
            'binlog_cache_size': 192,
            'thread_cache_size': 192,
            'table_open_cache': 1024,
            'max_connections': 400,
        }
    elif pc_mem_g > 4:
        args = {
            'key_buffer_size': 384,
            'query_cache_size': 192,
            'tmp_table_size': 512,
            'max_heap_table_size': 512,
            'innodb_buffer_pool_size': 512,
            'innodb_log_buffer_size': 32,
            'sort_buffer_size': 1024,
            'read_buffer_size': 1024,
            'read_rnd_buffer_size': 768,
            'join_buffer_size': 2048,
            'thread_stack': 256,
            'binlog_cache_size': 128,
            'thread_cache_size': 128,
            'table_open_cache': 384,
            'max_connections': 300,
        }
    elif pc_mem_g > 1.7:
        args = {
            'key_buffer_size': 256,
            'query_cache_size': 128,
            'tmp_table_size': 384,
            'max_heap_table_size': 384,
            'innodb_buffer_pool_size': 384,
            'innodb_log_buffer_size': 32,
            'sort_buffer_size': 768,
            'read_buffer_size': 768,
            'read_rnd_buffer_size': 512,
            'join_buffer_size': 2048,
            'thread_stack': 256,
            'binlog_cache_size': 64,
            'thread_cache_size': 96,
            'table_open_cache': 192,
            'max_connections': 200,
        }
    elif pc_mem_g > 0.8:
        args = {
            'key_buffer_size': 128,
            'query_cache_size': 64,
            'tmp_table_size': 64,
            'max_heap_table_size': 64,
            'innodb_buffer_pool_size': 256,
            'innodb_log_buffer_size': 32,
            'sort_buffer_size': 768,
            'read_buffer_size': 768,
            'read_rnd_buffer_size': 512,
            'join_buffer_size': 1024,
            'thread_stack': 256,
            'binlog_cache_size': 64,
            'thread_cache_size': 64,
            'table_open_cache': 128,
            'max_connections': 100,
        }
    else:
        args = {
            'key_buffer_size': 8,
            'query_cache_size': 4,
            'tmp_table_size': 8,
            'max_heap_table_size': 8,
            'innodb_buffer_pool_size': 16,
            'innodb_log_buffer_size': 32,
            'sort_buffer_size': 256,
            'read_buffer_size': 256,
            'read_rnd_buffer_size': 128,
            'join_buffer_size': 128,
            'thread_stack': 256,
            'binlog_cache_size': 32,
            'thread_cache_size': 4,
            'table_open_cache': 32,
            'max_connections': 500,
        }

    gets = ['key_buffer_size', 'tmp_table_size', 'max_heap_table_size', 'innodb_buffer_pool_size', 'innodb_log_buffer_size', 'max_connections',
            'table_open_cache', 'thread_cache_size', 'sort_buffer_size', 'read_buffer_size', 'read_rnd_buffer_size', 'join_buffer_size', 'thread_stack', 'binlog_cache_size']

    if version != "8.0":
        # gets.append('query_cache_size')
        gets = ['key_buffer_size', 'query_cache_size', 'tmp_table_size', 'max_heap_table_size', 'innodb_buffer_pool_size', 'innodb_log_buffer_size', 'max_connections',
                'table_open_cache', 'thread_cache_size', 'sort_buffer_size', 'read_buffer_size', 'read_rnd_buffer_size', 'join_buffer_size', 'thread_stack', 'binlog_cache_size']

    # print(gets)
    emptys = ['max_connections', 'thread_cache_size', 'table_open_cache']
    # args = getArgs()
    conFile = getConf()
    print(conFile)
    content = mw.readFile(conFile)
    n = 0
    for g in gets:
        s = 'M'
        if n > 5:
            s = 'K'
        if g in emptys:
            s = ''
        rep = '\s*' + g + '\s*=\s*\d+(M|K|k|m|G)?\n'
        c = g + ' = ' + str(args[g]) + s + '\n'
        if content.find(g) != -1:
            content = re.sub(rep, '\n' + c, content, 1)
        else:
            content = content.replace('[mysqld]\n', '[mysqld]\n' + c)
        n += 1
    mw.writeFile(conFile, content)
    return mw.returnJson(True, '设置成功!')


def setDbStatus(version):
    gets = ['key_buffer_size', 'tmp_table_size', 'max_heap_table_size', 'innodb_buffer_pool_size', 'innodb_log_buffer_size', 'max_connections',
            'table_open_cache', 'thread_cache_size', 'sort_buffer_size', 'read_buffer_size', 'read_rnd_buffer_size', 'join_buffer_size', 'thread_stack', 'binlog_cache_size']

    if version != "8.0":
        # gets.append('query_cache_size')
        gets = ['key_buffer_size', 'query_cache_size', 'tmp_table_size', 'max_heap_table_size', 'innodb_buffer_pool_size', 'innodb_log_buffer_size', 'max_connections',
                'table_open_cache', 'thread_cache_size', 'sort_buffer_size', 'read_buffer_size', 'read_rnd_buffer_size', 'join_buffer_size', 'thread_stack', 'binlog_cache_size']

    # print(gets)
    emptys = ['max_connections', 'thread_cache_size', 'table_open_cache']
    args = getArgs()
    conFile = getConf()
    content = mw.readFile(conFile)
    n = 0
    for g in gets:
        s = 'M'
        if n > 5:
            s = 'K'
        if g in emptys:
            s = ''
        rep = '\s*' + g + '\s*=\s*\d+(M|K|k|m|G)?\n'
        c = g + ' = ' + args[g] + s + '\n'
        if content.find(g) != -1:
            content = re.sub(rep, '\n' + c, content, 1)
        else:
            content = content.replace('[mysqld]\n', '[mysqld]\n' + c)
        n += 1
    mw.writeFile(conFile, content)
    return mw.returnJson(True, '设置成功!')


def isSqlError(mysqlMsg):
    # 检测数据库执行错误
    mysqlMsg = str(mysqlMsg)
    if "MySQLdb" in mysqlMsg:
        return mw.returnJson(False, 'err:' + str(mysqlMsg) + "\n" + 'MySQLdb组件缺失! <br>进入SSH命令行输入: pip install mysql-python | pip install mysqlclient==2.0.3')
    if "2002," in mysqlMsg:
        return mw.returnJson(False, '数据库连接失败,请检查数据库服务是否启动!')
    if "2003," in mysqlMsg:
        return mw.returnJson(False, "Can't connect to MySQL server on '127.0.0.1' (61)")
    if "using password:" in mysqlMsg:
        return mw.returnJson(False, '数据库密码错误,在管理列表-点击【修复ROOT密码】!')
    if "1045" in mysqlMsg:
        return mw.returnJson(False, '连接错误!')
    if "SQL syntax" in mysqlMsg:
        return mw.returnJson(False, 'SQL语法错误!')
    if "Connection refused" in mysqlMsg:
        return mw.returnJson(False, '数据库连接失败,请检查数据库服务是否启动!')
    if "1133" in mysqlMsg:
        return mw.returnJson(False, '数据库用户不存在!')
    if "1007" in mysqlMsg:
        return mw.returnJson(False, '数据库已经存在!')
    return None


def __createUser(dbname, username, password, address):
    errmsg = ""

    pdb = pMysqlDb()
    if username == 'root':
        dbname = '*'

    t = pdb.execute(
        "CREATE USER `%s`@`localhost` IDENTIFIED BY '%s'" % (username, password))

    if t != 0:
        errmsg = str(t)

    pdb.execute(
        "grant all privileges on %s.* to `%s`@`localhost`" % (dbname, username))
    for a in address.split(','):
        pdb.execute(
            "CREATE USER `%s`@`%s` IDENTIFIED BY '%s'" % (username, a, password))
        pdb.execute(
            "grant all privileges on %s.* to `%s`@`%s`" % (dbname, username, a))
    pdb.execute("flush privileges")
    return errmsg


def getDbBackupListFunc(dbname=''):
    bkDir = mw.getRootDir() + '/backup/database'
    r = []
    if os.path.exists(bkDir):
      blist = os.listdir(bkDir)
      bname = 'db_' + dbname
      blen = len(bname)
      for x in blist:
          fbstr = x[0:blen]
          if fbstr == bname:
              r.append(x)
      r.sort(key=lambda fn: os.path.getmtime(bkDir + "/" + fn), reverse=True)
    return r


def setDbBackup():
    args = getArgs()
    data = checkArgs(args, ['name', 'exec_type'])
    if not data[0]:
        return data[1]

    exec_type = args['exec_type']
    name = args['name']
    script_dir = mw.getServerDir() + "/jh-panel/scripts"
    cmd = "python3 " + script_dir + "/backup.py database " + name + " " + ' \'{"saveAllDay":"3","saveOther":"1","saveMaxDay":"30"}\' ' + exec_type
    os.system(cmd)
    return mw.returnJson(True, 'ok')


def importDbExternal():
    args = getArgs()
    data = checkArgs(args, ['file', 'name'])
    if not data[0]:
        return data[1]

    file = args['file']
    name = args['name']

    import_dir = mw.getRootDir() + '/backup/import/'

    file_path = import_dir + file
    if not os.path.exists(file_path):
        return mw.returnJson(False, '文件突然消失?')

    exts = ['sql', 'gz', 'zip', 'zst']
    ext = mw.getFileSuffix(file)
    if ext not in exts:
        return mw.returnJson(False, '导入数据库格式不对!')

    pwd = pSqliteDb('config').where('id=?', (1,)).getField('mysql_root')
    port = getMyPort()

    # 按文件名区分类型
    if '.mydumper.tar.zst' in file:
        # mydumper 部分，使用 myloader
        # 先解 zst 和 tar
        mydumper_folder = import_dir + '/' + name
        mw.execShell('mkdir -p ' + mydumper_folder + ' && cd ' + mydumper_folder)
        mw.execShell('unzstd -c ' + file  + ' | tar -x')
        # 导入数据库
        mw.execShell('myloader -d ' + mydumper_folder + '/' + name + ' -u root -p ' + pwd + ' -h 127.0.0.1 -P ' + port + ' -B ' + name + ' -o')
        mw.execShell('rm -r ' + mydumper_folder)
    else:
        # mysqldump 部分，可以直接执行 mysql
        tmp = file.split('/')
        tmpFile = tmp[len(tmp) - 1]
        tmpFile = tmpFile.replace('.sql.' + ext, '.sql')
        tmpFile = tmpFile.replace('.' + ext, '.sql')
        tmpFile = tmpFile.replace('tar.', '')

        # print(tmpFile)
        import_sql = ""
        if file.find("sql.gz") > -1:
            cmd = 'cd ' + import_dir + ' && gzip -dc ' + \
                file + " > " + import_dir + tmpFile
            info = mw.execShell(cmd)
            if info[1] == "":
                import_sql = import_dir + tmpFile

        if file.find(".zst") > -1:
            cmd = 'cd ' + import_dir + ' && unzstd ' + file
            mw.execShell(cmd)
            import_sql = import_dir + tmpFile

        if file.find(".zip") > -1:
            cmd = 'cd ' + import_dir + ' && unzip -o ' + file
            mw.execShell(cmd)
            import_sql = import_dir + tmpFile

        if file.find("tar.gz") > -1:
            cmd = 'cd ' + import_dir + ' && tar -zxvf ' + file
            mw.execShell(cmd)
            import_sql = import_dir + tmpFile

        if file.find(".sql") > -1 and file.find(".sql.gz") == -1:
            import_sql = import_dir + file

        if import_sql == "":
            return mw.returnJson(False, '未找SQL文件')

        sock = getSocketFile()

        os.environ["MYSQL_PWD"] = pwd
        mysql_cmd = getServerDir() + '/bin/usr/bin/mysql -S ' + sock + ' -uroot -p' + \
            pwd + ' ' + name + ' < ' + import_sql

        # print(mysql_cmd)
        os.system(mysql_cmd)
        if ext != 'sql':
            os.remove(import_sql)

    return mw.returnJson(True, 'ok')


def getImportDbBackupScript():
    args = getArgs()
    data = checkArgs(args, ['file', 'name'])
    if not data[0]:
        return data[1]

    file = args['file']
    name = args['name']

    pwd = pSqliteDb('config').where('id=?', (1,)).getField('mysql_root')
    port = getMyPort()

    cmd = ''
    # 按文件名区分类型
    if '.mydumper.tar.zst' in file:
        # mydumper 部分
        # 先解 zst 和 tar
        mydumper_folder = mw.getRootDir() + '/backup/database/' + file.replace('.mydumper.tar.zst', '')
        cmd += 'mkdir -p ' + mydumper_folder + ' && cd ' + mydumper_folder + '\n'
        cmd += 'unzstd -c ' + mw.getRootDir() + '/backup/database/' + file  + ' | tar -x \n'
        # 导入数据库
        cmd += 'myloader -d ' + mydumper_folder + '/' + name + ' -u root -p ' + pwd + ' -h 127.0.0.1 -P ' + port + ' -B ' + name + ' -o\n'
        cmd += 'rm -r ' + mydumper_folder
    else:
        # mysqldump 部分
        file_path_sql = ''
        # 后缀 .zst 用 zstd 解压，其它用 gzip 解压
        if '.zst' in file:
            file_path_sql = mw.getRootDir() + '/backup/database/' + file.replace('.zst', '')
            if not os.path.exists(file_path_sql):
                cmd += 'cd ' + mw.getRootDir() + '/backup/database && unzstd ' + file + '\n'
        elif '.gz' in file:
            file_path_sql = mw.getRootDir() + '/backup/database/' + file.replace('.gz', '')
            if not os.path.exists(file_path_sql):
                cmd += 'cd ' + mw.getRootDir() + '/backup/database && gzip -d ' + file + '\n'
        elif '.sql' in file:
            file_path_sql = mw.getRootDir() + '/backup/database/' + file
        # 用 mysql 导入
        sock = getSocketFile()
        cmd += (getServerDir() + '/bin/usr/bin/mysql -S ' + sock + ' -uroot -p' + pwd +
                ' ' + name + ' < ' + file_path_sql + '\n')
        cmd += 'rm ' + file_path_sql

    # print(mysql_cmd)
    return mw.returnJson(True, 'ok', cmd)


def importDbBackup():
    args = getArgs()
    data = checkArgs(args, ['file', 'name'])
    if not data[0]:
        return data[1]

    file = args['file']
    name = args['name']

    file_path = mw.getRootDir() + '/backup/database/' + file
    file_path_sql = mw.getRootDir() + '/backup/database/' + file.replace('.gz', '')

    if not os.path.exists(file_path_sql):
        cmd = 'cd ' + mw.getRootDir() + '/backup/database && gzip -d ' + file
        mw.execShell(cmd)

    pwd = pSqliteDb('config').where('id=?', (1,)).getField('mysql_root')
    sock = getSocketFile()
    mysql_cmd = getServerDir() + '/bin/usr/bin/mysql -S ' + sock + ' -uroot -p' + pwd + \
        ' ' + name + ' < ' + file_path_sql

    # print(mysql_cmd)
    os.system(mysql_cmd)
    return mw.returnJson(True, 'ok')


def deleteDbBackup():
    args = getArgs()
    data = checkArgs(args, ['filename', 'path'])
    if not data[0]:
        return data[1]

    path = args['path']
    full_file = ""
    bkDir = mw.getRootDir() + '/backup/database'
    full_file = bkDir + '/' + args['filename']
    if path != "":
        full_file = path + "/" + args['filename']
    os.remove(full_file)
    return mw.returnJson(True, 'ok')


def getDbBackupList():
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]

    bkDir = mw.getRootDir() + '/backup/database'
    rr = []
    if os.path.exists(bkDir):
      r = getDbBackupListFunc(args['name'])
      for x in range(0, len(r)):
          p = bkDir + '/' + r[x]
          data = {}
          data['name'] = r[x]

          rsize = os.path.getsize(p)
          data['size'] = mw.toSize(rsize)

          t = os.path.getctime(p)
          t = time.localtime(t)

          data['time'] = time.strftime('%Y-%m-%d %H:%M:%S', t)
          rr.append(data)

          data['file'] = p

    return mw.returnJson(True, 'ok', rr)


def getDbBackupImportList():

    bkImportDir = mw.getRootDir() + '/backup/import'
    if not os.path.exists(bkImportDir):
        os.mkdir(bkImportDir)

    blist = os.listdir(bkImportDir)

    rr = []
    for x in range(0, len(blist)):
        name = blist[x]
        p = bkImportDir + '/' + name
        data = {}
        data['name'] = name

        rsize = os.path.getsize(p)
        data['size'] = mw.toSize(rsize)

        t = os.path.getctime(p)
        t = time.localtime(t)

        data['time'] = time.strftime('%Y-%m-%d %H:%M:%S', t)
        rr.append(data)

        data['file'] = p

    rdata = {
        "list": rr,
        "upload_dir": bkImportDir,
    }
    return mw.returnJson(True, 'ok', rdata)


def getMysqlInfo():
    mysql_info = {
        "status": status()
    }
    pdb = pMysqlDb()
    database_list = pSqliteDb('databases').field(
        'id,pid,name,username,password,accept,rw,ps,addtime').select()
    
    # 计算数据库大小
    total_bytes = 0
    # startTime = time.time()
    for database in database_list:

        # 计算大小
        sql = "select sum(DATA_LENGTH)+sum(INDEX_LENGTH) as sum_size from information_schema.tables  where table_schema='%s'" % database[
            'name']
        data_sum = pdb.query(sql)
        data = 0
        if data_sum[0]['sum_size'] != None:
            data = data_sum[0]['sum_size']
        database['size_bytes'] = float(data)
        database['size'] = mw.toSize(data)
        total_bytes += float(data)

    mysql_info['total_bytes'] = total_bytes
    mysql_info['total_size'] = mw.toSize(total_bytes)
    mysql_info['database_list'] = database_list

    # 主从状态
    mysql_dir = getServerDir()
    config_conn = mw.M('config').dbPos(mysql_dir, 'mysql')
    check_table_query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='slave_status';"
    table_exist = config_conn.originExecute(check_table_query)
    slave_status = None
    if table_exist.fetchone():
      slave_status_conn = mw.M('slave_status').dbPos(mysql_dir, 'mysql')
      slave_status = slave_status_conn.field('ip,user,log_file,io_running,sql_running,delay,error_msg,ps,addtime').select()
      slave_status_conn.close()
    mysql_info['slave_status'] = slave_status

    # finishTime = time.time() - startTime
    # print("查询数据库大小用时[" + str(round(finishTime, 2)) + "]秒")

    return mw.returnJson(True, 'ok', mysql_info)


def getDbListPage():
    args = getArgs()
    page = 1
    page_size = 10
    search = ''
    data = {}
    if 'page' in args:
        page = int(args['page'])

    if 'page_size' in args:
        page_size = int(args['page_size'])

    if 'search' in args:
        search = args['search']

    conn = pSqliteDb('databases')
    limit = str((page - 1) * page_size) + ',' + str(page_size)
    condition = ''
    if not search == '':
        condition = "name like '%" + search + "%'"
    field = 'id,pid,name,username,password,accept,rw,ps,addtime'
    clist = conn.where(condition, ()).field(
        field).limit(limit).order('id desc').select()

    backup_list = []
    if os.path.exists(mw.getRootDir() + '/backup/database'):
        backup_list = os.listdir(mw.getRootDir() + '/backup/database')
    
    for x in range(0, len(clist)):
        dbname = clist[x]['name']
        
        # 判断backup_list是否存在以"db_" + dbname开头的文件
        clist[x]['is_backup'] = False
        for backup in backup_list:
            if backup.startswith('db_' + dbname):
                clist[x]['is_backup'] = True
                break        

        # blist = getDbBackupListFunc(dbname)
        # # print(blist)
        # clist[x]['is_backup'] = False
        # if len(blist) > 0:
        #     clist[x]['is_backup'] = True

    count = conn.where(condition, ()).count()
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = 'dbList'
    data['page'] = mw.getPage(_page)
    data['data'] = clist

    info = {}
    info['root_pwd'] = pSqliteDb('config').where(
        'id=?', (1,)).getField('mysql_root')
    data['info'] = info

    return mw.getJson(data)


def syncGetDatabases():
    pdb = pMysqlDb()
    psdb = pSqliteDb('databases')
    # 测试代码
    # psdb.delete()

    data = pdb.query('show databases')
    isError = isSqlError(data)
    if isError != None:
        return isError
    users = pdb.query(
        "select User,Host from mysql.user where User!='root' AND Host!='localhost' AND Host!=''")
    nameArr = ['information_schema', 'performance_schema', 'mysql', 'sys']
    n = 0

    # print(users)
    for value in data:
        vdb_name = value["Database"]
        b = False
        for key in nameArr:
            if vdb_name == key:
                b = True
                break
        if b:
            continue
        if psdb.where("name=?", (vdb_name,)).count() > 0:
            continue
        host = '127.0.0.1'
        for user in users:
            if vdb_name == user["User"]:
                host = user["Host"]
                break

        ps = mw.getMsg('INPUT_PS')
        if vdb_name == 'test':
            ps = mw.getMsg('DATABASE_TEST')
        addTime = time.strftime('%Y-%m-%d %X', time.localtime())
        if psdb.add('name,username,password,accept,ps,addtime', (vdb_name, vdb_name, '', host, ps, addTime)):
            n += 1

    msg = mw.getInfo('本次共从服务器获取了{1}个数据库!', (str(n),))
    return mw.returnJson(True, msg)


def toDbBase(find):
    pdb = pMysqlDb()
    psdb = pSqliteDb('databases')
    if len(find['password']) < 3:
        find['username'] = find['name']
        find['password'] = mw.md5(str(time.time()) + find['name'])[0:10]
        psdb.where("id=?", (find['id'],)).save(
            'password,username', (find['password'], find['username']))

    result = pdb.execute("create database `" + find['name'] + "`")
    if "using password:" in str(result):
        return -1
    if "Connection refused" in str(result):
        return -1

    password = find['password']
    __createUser(find['name'], find['username'], password, find['accept'])
    return 1


def syncToDatabases():
    args = getArgs()
    data = checkArgs(args, ['type', 'ids'])
    if not data[0]:
        return data[1]

    pdb = pMysqlDb()
    result = pdb.execute("show databases")
    isError = isSqlError(result)
    if isError:
        return isError

    stype = int(args['type'])
    psdb = pSqliteDb('databases')
    n = 0

    if stype == 0:
        data = psdb.field('id,name,username,password,accept').select()
        for value in data:
            result = toDbBase(value)
            if result == 1:
                n += 1
    else:
        data = json.loads(args['ids'])
        for value in data:
            find = psdb.where("id=?", (value,)).field(
                'id,name,username,password,accept').find()
            # print find
            result = toDbBase(find)
            if result == 1:
                n += 1
    msg = mw.getInfo('本次共同步了{1}个数据库!', (str(n),))
    return mw.returnJson(True, msg)


def setRootPwd(version=''):
    args = getArgs()
    data = checkArgs(args, ['password'])
    if not data[0]:
        return data[1]

    password = args['password']
    try:
        pdb = pMysqlDb()
        result = pdb.query("show databases")
        isError = isSqlError(result)
        if isError != None:
            return isError

        if version.find('8.0') > -1:
            result = pdb.execute(
                "update mysql.user set password=password('" + password + "') where user='root'")
            # Old code
            # pdb.execute(
            #     "UPDATE mysql.user SET authentication_string='' WHERE user='root'")
            # pdb.execute(
            #     "ALTER USER 'root'@'localhost' IDENTIFIED BY '%s'" % password)
            # pdb.execute(
            #     "ALTER USER 'root'@'127.0.0.1' IDENTIFIED BY '%s'" % password)
        else:
            result = pdb.execute(
                "update mysql.user set authentication_string=password('" + password + "') where user='root'")
            # Old code
            # result = pdb.execute(
            #     "update mysql.user set Password=password('" + password + "') where User='root'")
        pdb.execute("flush privileges")
        pSqliteDb('config').where('id=?', (1,)).save('mysql_root', (password,))
        return mw.returnJson(True, '数据库root密码修改成功!')
    except Exception as ex:
        return mw.returnJson(False, '修改错误:' + str(ex))


def fixRootPwd(version=''):
    args = getArgs()
    data = checkArgs(args, ['password'])
    if not data[0]:
        return data[1]

    password = args['password']
    try:
        pdb = pMysqlDb()
        pdb.setPwd(password)
        result = pdb.query("show databases")
        isError = isSqlError(result)
        if isError != None:
            if "using password:" in str(result):
                return mw.returnJson(False, '请输入正确的ROOT密码!')
            else:
                return isError
        pSqliteDb('config').where('id=?', (1,)).save('mysql_root', (password,))
        return mw.returnJson(True, '数据库root密码修复成功!')
    except Exception as ex:
        return mw.returnJson(False, '修改错误:' + str(ex))


def setUserPwd(version=''):
    args = getArgs()
    data = checkArgs(args, ['password', 'name'])
    if not data[0]:
        return data[1]

    newpassword = args['password']
    username = args['name']
    uid = args['id']

    try:
        pdb = pMysqlDb()
        psdb = pSqliteDb('databases')
        name = psdb.where('id=?', (uid,)).getField('name')
        # if version.find('5.7') > -1 or version.find('8.0') > -1:

        accept = pdb.query(
            "select Host from mysql.user where User='" + name + "' AND Host!='localhost'")
        if len(accept) == 0:
            return mw.returnJson(False, "用户不存在，请点击数据库的“权限”按钮重新分配用户")
        t1 = pdb.execute(
            "update mysql.user set authentication_string='' where User='" + username + "'")
        # print(t1)
        result = pdb.execute(
            "ALTER USER `%s`@`localhost` IDENTIFIED BY '%s'" % (username, newpassword))
        # print(result)
        for my_host in accept:
            t2 = pdb.execute("ALTER USER `%s`@`%s` IDENTIFIED BY '%s'" % (
                username, my_host["Host"], newpassword))
            # print(t2)
        # else:
        #     result = pdb.execute("update mysql.user set Password=password('" +
        #                          newpassword + "') where User='" + username + "'")

        pdb.execute("flush privileges")
        psdb.where("id=?", (uid,)).setField('password', newpassword)
        return mw.returnJson(True, mw.getInfo('修改数据库[{1}]密码成功!', (name,)))
    except Exception as ex:
        return mw.returnJson(False, mw.getInfo('修改数据库[{1}]密码失败[{2}]!', (name, str(ex),)))


def setDbPs():
    args = getArgs()
    data = checkArgs(args, ['id', 'name', 'ps'])
    if not data[0]:
        return data[1]

    ps = args['ps']
    sid = args['id']
    name = args['name']
    try:
        psdb = pSqliteDb('databases')
        psdb.where("id=?", (sid,)).setField('ps', ps)
        return mw.returnJson(True, mw.getInfo('修改数据库[{1}]备注成功!', (name,)))
    except Exception as e:
        return mw.returnJson(True, mw.getInfo('修改数据库[{1}]备注失败!', (name,)))


def addDb():
    args = getArgs()
    data = checkArgs(args,
                     ['password', 'name', 'codeing', 'db_user', 'dataAccess', 'ps'])
    if not data[0]:
        return data[1]

    if not 'address' in args:
        address = ''
    else:
        address = args['address'].strip()

    dbname = args['name'].strip()
    dbuser = args['db_user'].strip()
    codeing = args['codeing'].strip()
    password = args['password'].strip()
    dataAccess = args['dataAccess'].strip()
    ps = args['ps'].strip()

    reg = "^[\w\.-]+$"
    if not re.match(reg, args['name']):
        return mw.returnJson(False, '数据库名称不能带有特殊符号!')
    checks = ['root', 'mysql', 'test', 'sys', 'panel_logs']
    if dbuser in checks or len(dbuser) < 1:
        return mw.returnJson(False, '数据库用户名不合法!')
    if dbname in checks or len(dbname) < 1:
        return mw.returnJson(False, '数据库名称不合法!')

    if len(password) < 1:
        password = mw.md5(time.time())[0:8]

    wheres = {
        'utf8':   'utf8_general_ci',
        'utf8mb4': 'utf8mb4_general_ci',
        'gbk':    'gbk_chinese_ci',
        'big5':   'big5_chinese_ci'
    }
    codeStr = wheres[codeing]

    pdb = pMysqlDb()
    psdb = pSqliteDb('databases')

    if psdb.where("name=? or username=?", (dbname, dbuser)).count():
        return mw.returnJson(False, '数据库已存在!')

    result = pdb.execute("create database `" + dbname +
                         "` DEFAULT CHARACTER SET " + codeing + " COLLATE " + codeStr)
    # print result
    isError = isSqlError(result)
    if isError != None:
        return isError

    pdb.execute("drop user '" + dbuser + "'@'localhost'")
    for a in address.split(','):
        pdb.execute("drop user '" + dbuser + "'@'" + a + "'")

    __createUser(dbname, dbuser, password, address)

    addTime = time.strftime('%Y-%m-%d %X', time.localtime())
    psdb.add('pid,name,username,password,accept,ps,addtime',
             (0, dbname, dbuser, password, address, ps, addTime))
    return mw.returnJson(True, '添加成功!')


def delDb():
    args = getArgs()
    data = checkArgs(args, ['id', 'name'])
    if not data[0]:
        return data[1]
    try:
        sid = args['id']
        name = args['name']
        psdb = pSqliteDb('databases')
        pdb = pMysqlDb()
        find = psdb.where("id=?", (sid,)).field(
            'id,pid,name,username,password,accept,ps,addtime').find()
        accept = find['accept']
        username = find['username']

        # 删除MYSQL
        result = pdb.execute("drop database `" + name + "`")

        users = pdb.query("select Host from mysql.user where User='" +
                          username + "' AND Host!='localhost'")
        pdb.execute("drop user '" + username + "'@'localhost'")
        for us in users:
            pdb.execute("drop user '" + username + "'@'" + us["Host"] + "'")
        pdb.execute("flush privileges")

        # 删除SQLITE
        psdb.where("id=?", (sid,)).delete()
        return mw.returnJson(True, '删除成功!')
    except Exception as ex:
        return mw.returnJson(False, '删除失败!' + str(ex))


def getDbAccess():
    args = getArgs()
    data = checkArgs(args, ['username'])
    if not data[0]:
        return data[1]
    username = args['username']
    pdb = pMysqlDb()

    users = pdb.query("select Host from mysql.user where User='" +
                      username + "' AND Host!='localhost'")

    isError = isSqlError(users)
    if isError != None:
        return isError

    if len(users) < 1:
        return mw.returnJson(True, "127.0.0.1")
    accs = []
    for c in users:
        accs.append(c["Host"])
    userStr = ','.join(accs)
    return mw.returnJson(True, userStr)


def setDbAccess():
    args = getArgs()
    data = checkArgs(args, ['username', 'access'])
    if not data[0]:
        return data[1]
    name = args['username']
    access = args['access']
    pdb = pMysqlDb()
    psdb = pSqliteDb('databases')

    dbname = psdb.where('username=?', (name,)).getField('name')

    if name == 'root':
        password = pSqliteDb('config').where(
            'id=?', (1,)).getField('mysql_root')
    else:
        password = psdb.where("username=?", (name,)).getField('password')

    users = pdb.query("select Host from mysql.user where User='" +
                      name + "' AND Host!='localhost'")

    for us in users:
        pdb.execute("drop user '" + name + "'@'" + us["Host"] + "'")

    __createUser(dbname, name, password, access)

    psdb.where('username=?', (name,)).save('accept,rw', (access, 'rw',))
    return mw.returnJson(True, '设置成功!')


def fixDbAccess(version):
    try:
        pdb = pMysqlDb()
        data = pdb.query('show databases')
        isError = isSqlError(data)
        if isError != None:
            appCMD(version, 'stop')
            # Error: 导致mysql挂了
            # mw.execShell("rm -rf " + getServerDir() + "/data")
            appCMD(version, 'start')
            return mw.returnJson(True, '修复成功!')
        return mw.returnJson(True, '正常无需修复!')
    except Exception as e:
        return mw.returnJson(False, '修复失败请重试!')


def setDbRw(version=''):
    args = getArgs()
    data = checkArgs(args, ['username', 'id', 'rw'])
    if not data[0]:
        return data[1]

    username = args['username']
    uid = args['id']
    rw = args['rw']

    pdb = pMysqlDb()
    psdb = pSqliteDb('databases')
    dbname = psdb.where("id=?", (uid,)).getField('name')
    users = pdb.query(
        "select Host from mysql.user where User='" + username + "'")

    # show grants for demo@"127.0.0.1";
    for x in users:
        # REVOKE ALL PRIVILEGES ON `imail`.* FROM 'imail'@'127.0.0.1';

        sql = "REVOKE ALL PRIVILEGES ON `" + dbname + \
            "`.* FROM '" + username + "'@'" + x["Host"] + "';"
        r = pdb.query(sql)
        # print(sql, r)

        if rw == 'rw':
            sql = "GRANT SELECT, INSERT, UPDATE, DELETE ON " + dbname + ".* TO " + \
                username + "@'" + x["Host"] + "'"
        elif rw == 'r':
            sql = "GRANT SELECT ON " + dbname + ".* TO " + \
                username + "@'" + x["Host"] + "'"
        else:
            sql = "GRANT all privileges ON " + dbname + ".* TO " + \
                username + "@'" + x["Host"] + "'"
        pdb.execute(sql)
    pdb.execute("flush privileges")
    r = psdb.where("id=?", (uid,)).setField('rw', rw)
    # print(r)
    return mw.returnJson(True, '切换成功!')


def getDbInfo():
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]

    db_name = args['name']
    pdb = pMysqlDb()
    # print 'show tables from `%s`' % db_name
    tables = pdb.query('show tables from `%s`' % db_name)

    ret = {}
    sql = "select sum(DATA_LENGTH)+sum(INDEX_LENGTH) as sum_size from information_schema.tables  where table_schema='%s'" % db_name
    data_sum = pdb.query(sql)

    data = 0
    if data_sum[0]['sum_size'] != None:
        data = data_sum[0]['sum_size']

    ret['data_size'] = mw.toSize(data)
    ret['database'] = db_name

    ret3 = []
    table_key = "Tables_in_" + db_name
    for i in tables:
        tb_sql = "show table status from `%s` where name = '%s'" % (db_name, i[
                                                                    table_key])
        table = pdb.query(tb_sql)

        tmp = {}
        tmp['type'] = table[0]["Engine"]
        tmp['rows_count'] = table[0]["Rows"]
        tmp['collation'] = table[0]["Collation"]

        data_size = 0
        if table[0]['Avg_row_length'] != None:
            data_size = table[0]['Avg_row_length']

        if table[0]['Data_length'] != None:
            data_size = table[0]['Data_length']

        tmp['data_byte'] = data_size
        tmp['data_size'] = mw.toSize(data_size)
        tmp['table_name'] = table[0]["Name"]
        ret3.append(tmp)

    ret['tables'] = (ret3)

    return mw.getJson(ret)


def repairTable():
    args = getArgs()
    data = checkArgs(args, ['db_name', 'tables'])
    if not data[0]:
        return data[1]

    db_name = args['db_name']
    tables = json.loads(args['tables'])
    pdb = pMysqlDb()
    mtable = pdb.query('show tables from `%s`' % db_name)

    ret = []
    key = "Tables_in_" + db_name
    for i in mtable:
        for tn in tables:
            if tn == i[key]:
                ret.append(tn)

    if len(ret) > 0:
        for i in ret:
            pdb.execute('REPAIR TABLE `%s`.`%s`' % (db_name, i))
        return mw.returnJson(True, "修复完成!")
    return mw.returnJson(False, "修复失败!")


def optTable():
    args = getArgs()
    data = checkArgs(args, ['db_name', 'tables'])
    if not data[0]:
        return data[1]

    db_name = args['db_name']
    tables = json.loads(args['tables'])
    pdb = pMysqlDb()
    mtable = pdb.query('show tables from `%s`' % db_name)
    ret = []
    key = "Tables_in_" + db_name
    for i in mtable:
        for tn in tables:
            if tn == i[key]:
                ret.append(tn)

    if len(ret) > 0:
        for i in ret:
            pdb.execute('OPTIMIZE TABLE `%s`.`%s`' % (db_name, i))
        return mw.returnJson(True, "优化成功!")
    return mw.returnJson(False, "优化失败或者已经优化过了!")


def alterTable():
    args = getArgs()
    data = checkArgs(args, ['db_name', 'tables'])
    if not data[0]:
        return data[1]

    db_name = args['db_name']
    tables = json.loads(args['tables'])
    table_type = args['table_type']
    pdb = pMysqlDb()
    mtable = pdb.query('show tables from `%s`' % db_name)

    ret = []
    key = "Tables_in_" + db_name
    for i in mtable:
        for tn in tables:
            if tn == i[key]:
                ret.append(tn)

    if len(ret) > 0:
        for i in ret:
            pdb.execute('alter table `%s`.`%s` ENGINE=`%s`' %
                        (db_name, i, table_type))
        return mw.returnJson(True, "更改成功!")
    return mw.returnJson(False, "更改失败!")


def getTotalStatistics():
    st = status()
    data = {}

    isInstall = os.path.exists(getServerDir() + '/version.pl')

    if st == 'start' and isInstall:
        data['status'] = True
        data['count'] = pSqliteDb('databases').count()
        data['ver'] = mw.readFile(getServerDir() + '/version.pl').strip()
        return mw.returnJson(True, 'ok', data)
    else:
        data['status'] = False
        data['count'] = 0
        return mw.returnJson(False, 'fail', data)


def recognizeDbMode():
    conf = getConf()
    con = mw.readFile(conf)
    rep = r"!include %s/(.*)?\.cnf" % (getServerDir() + "/etc/mode",)
    mode = 'none'
    try:
        data = re.findall(rep, con, re.M)
        mode = data[0]
    except Exception as e:
        pass
    return mode


def getDbrunMode(version=''):
    mode = recognizeDbMode()
    return mw.returnJson(True, "ok", {'mode': mode})


def setDbrunMode(version=''):
    if version == '5.5':
        return mw.returnJson(False, "不支持切换")

    args = getArgs()
    data = checkArgs(args, ['mode', 'reload'])
    if not data[0]:
        return data[1]

    mode = args['mode']
    dbreload = args['reload']

    if not mode in ['classic', 'gtid']:
        return mw.returnJson(False, "mode的值无效:" + mode)

    origin_mode = recognizeDbMode()
    path = getConf()
    con = mw.readFile(path)
    rep = r"!include %s/%s\.cnf" % (getServerDir() + "/etc/mode", origin_mode)
    rep_after = "!include %s/%s.cnf" % (getServerDir() + "/etc/mode", mode)
    con = re.sub(rep, rep_after, con)

    # 如果配置文件中 server-id = 1，则改成当前时间
    if re.search(r"server-id\s*?=\s*?1\n", con):
        con = re.sub(r"server-id\s*?=\s*?1", "server-id = " +
                     str(int(time.time())), con)

    mw.writeFile(path, con)

    # 保证配置文件存在
    cnf_file = getServerDir() + "/etc/mode/" + mode + ".cnf"
    if not os.path.exists(getServerDir() + "/etc/mode"):
        os.makedirs(getServerDir() + "/etc/mode", exist_ok=True)
    if not os.path.exists(cnf_file):
        origin_cnf_file = getPluginDir() + "/conf/" + mode + ".cnf"
        # 复制 origin_cnf_file
        mw.execShell("cp -f " + origin_cnf_file + " " + cnf_file)

    if version == '5.6':
        dbreload = 'yes'
    else:
        db = pMysqlDb()
        # The value of @@GLOBAL.GTID_MODE can only be changed one step at a
        # time: OFF <-> OFF_PERMISSIVE <-> ON_PERMISSIVE <-> ON. Also note that
        # this value must be stepped up or down simultaneously on all servers.
        # See the Manual for instructions.
        if mode == 'classic':
            db.query('set global enforce_gtid_consistency=off')
            db.query('set global gtid_mode=on')
            db.query('set global gtid_mode=on_permissive')
            db.query('set global gtid_mode=off_permissive')
            db.query('set global gtid_mode=off')
        elif mode == 'gtid':
            db.query('set global enforce_gtid_consistency=on')
            db.query('set global gtid_mode=off')
            db.query('set global gtid_mode=off_permissive')
            db.query('set global gtid_mode=on_permissive')
            db.query('set global gtid_mode=on')

    if dbreload == "yes":
        restart(version)

    return mw.returnJson(True, "切换成功!")


def findBinlogDoDb():
    dodb = None
    try:
      conf = getConf()
      con = mw.readFile(conf)
      rep = r"binlog-do-db\s*?=\s*?(.*)"
      dodb = re.findall(rep, con, re.M)
    except Exception as e:
      pass

    return dodb


def findBinlogSlaveDoDb():
    conf = getConf()
    con = mw.readFile(conf)
    rep = r"replicate-do-db\s*?=\s*?(.*)"
    dodb = re.findall(rep, con, re.M)
    return dodb


def setDbMasterAccess():
    args = getArgs()
    data = checkArgs(args, ['username', 'access'])
    if not data[0]:
        return data[1]
    username = args['username']
    access = args['access']
    pdb = pMysqlDb()
    psdb = pSqliteDb('master_replication_user')
    password = psdb.where("username=?", (username,)).getField('password')
    users = pdb.query("select Host from mysql.user where User='" +
                      username + "' AND Host!='localhost'")
    for us in users:
        pdb.execute("drop user '" + username + "'@'" + us["Host"] + "'")

    dbname = '*'
    for a in access.split(','):
        pdb.execute(
            "CREATE USER `%s`@`%s` IDENTIFIED BY '%s'" % (username, a, password))
        pdb.execute(
            "grant all privileges on %s.* to `%s`@`%s`" % (dbname, username, a))

    pdb.execute("flush privileges")
    psdb.where('username=?', (username,)).save('accept', (access,))
    return mw.returnJson(True, '设置成功!')


def getMasterDbList(version=''):
    try:
        args = getArgs()
        page = 1
        page_size = 10
        search = ''
        data = {}
        if 'page' in args:
            page = int(args['page'])

        if 'page_size' in args:
            page_size = int(args['page_size'])

        if 'search' in args:
            search = args['search']

        conn = pSqliteDb('databases')
        limit = str((page - 1) * page_size) + ',' + str(page_size)
        condition = ''
        dodb = findBinlogDoDb()
        data['dodb'] = dodb

        slave_dodb = findBinlogSlaveDoDb()

        if not search == '':
            condition = "name like '%" + search + "%'"
        field = 'id,pid,name,username,password,accept,ps,addtime'
        clist = conn.where(condition, ()).field(
            field).limit(limit).order('id desc').select()
        count = conn.where(condition, ()).count()

        for x in range(0, len(clist)):
            if clist[x]['name'] in dodb:
                clist[x]['master'] = 1
            else:
                clist[x]['master'] = 0

            if clist[x]['name'] in slave_dodb:
                clist[x]['slave'] = 1
            else:
                clist[x]['slave'] = 0

        _page = {}
        _page['count'] = count
        _page['p'] = page
        _page['row'] = page_size
        _page['tojs'] = 'dbList'
        data['page'] = mw.getPage(_page)
        data['data'] = clist
        return mw.getJson(data)
    except Exception as e:
        return mw.returnJson(False, "数据库密码错误,在管理列表-点击【修复】!")


def setDbMaster(version):
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]

    conf = getConf()
    con = mw.readFile(conf)
    rep = r"(binlog-do-db\s*?=\s*?(.*))"
    dodb = re.findall(rep, con, re.M)

    isHas = False
    for x in range(0, len(dodb)):

        if dodb[x][1] == args['name']:
            isHas = True

            con = con.replace(dodb[x][0] + "\n", '')
            mw.writeFile(conf, con)

    if not isHas:
        prefix = '#binlog-do-db'
        con = con.replace(
            prefix, prefix + "\nbinlog-do-db=" + args['name'])
        mw.writeFile(conf, con)

    restart(version)
    time.sleep(4)
    return mw.returnJson(True, '设置成功', [args, dodb])


def setDbSlave(version):
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]

    conf = getConf()
    con = mw.readFile(conf)
    rep = r"(replicate-do-db\s*?=\s*?(.*))"
    dodb = re.findall(rep, con, re.M)

    isHas = False
    for x in range(0, len(dodb)):
        if dodb[x][1] == args['name']:
            isHas = True

            con = con.replace(dodb[x][0] + "\n", '')
            mw.writeFile(conf, con)

    if not isHas:
        prefix = '#replicate-do-db'
        con = con.replace(
            prefix, prefix + "\nreplicate-do-db=" + args['name'])
        mw.writeFile(conf, con)

    restart(version)
    time.sleep(4)
    return mw.returnJson(True, '设置成功', [args, dodb])


def getMasterStatus(version=''):

    try:
        if status(version) == 'stop':
            return mw.returnJson(False, 'MySQL未启动,或正在启动中...!', [])

        conf = getConf()
        content = mw.readFile(conf)
        master_status = False
        if content.find('#log-bin') == -1 and content.find('log-bin') > 1:
            dodb = findBinlogDoDb()
            if dodb and len(dodb) > 0:
                master_status = True

        data = {}
        data['mode'] = recognizeDbMode()
        data['status'] = master_status

        db = pMysqlDb()
        dlist = db.query('show slave status')

        # print(dlist[0])
        try:
          if len(dlist) > 0 and (dlist[0]["Slave_IO_Running"] == 'Yes' or dlist[0]["Slave_SQL_Running"] == 'Yes'):
              data['slave_status'] = True
        except Exception as e:
            data['slave_status'] = False

        data['semi_sync'] = getSemiSyncStatusSummary(db)

        return mw.returnJson(master_status, '设置成功', data)
    except Exception as e:
        return mw.returnJson(False, "获取主从状态异常!" + str(e), 'pwd')


def setMasterStatus(version=''):

    conf = getConf()
    con = mw.readFile(conf)

    if con.find('#log-bin') != -1:
        return mw.returnJson(False, '必须开启二进制日志')

    restart(version)
    return mw.returnJson(True, '设置成功')


def setSemiSyncStatus(version=''):
    args = getArgs()
    data = checkArgs(args, ['enable'])
    if not data[0]:
        return data[1]

    enable_flag = str(args['enable']).lower()
    enable = enable_flag in ['1', 'true', 'on', 'yes']
    changed, err_msg = applySemiSyncConfigToFile(enable)
    if err_msg:
        return mw.returnJson(False, err_msg)

    if not changed:
        return mw.returnJson(True, '半同步配置已是目标状态', {'enabled': isSemiSyncConfigured()})

    ret = restart(version)
    if ret != 'ok':
        return mw.returnJson(False, '重启MySQL失败: ' + str(ret))
    time.sleep(3)
    return mw.returnJson(True, ('已启用' if enable else '已关闭') + '半同步复制', {'enabled': isSemiSyncConfigured()})


def getMasterRepSlaveList(version=''):
    args = getArgs()
    page = 1
    page_size = 10
    search = ''
    data = {}
    if 'page' in args:
        page = int(args['page'])

    if 'page_size' in args:
        page_size = int(args['page_size'])

    if 'search' in args:
        search = args['search']

    conn = pSqliteDb('master_replication_user')
    limit = str((page - 1) * page_size) + ',' + str(page_size)
    condition = ''

    if not search == '':
        condition = "name like '%" + search + "%'"
    field = 'id,username,password,accept,ps,addtime'
    clist = conn.where(condition, ()).field(
        field).limit(limit).order('id desc').select()
    count = conn.where(condition, ()).count()

    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = 'getMasterRepSlaveList'
    data['page'] = mw.getPage(_page)
    data['data'] = clist

    return mw.getJson(data)


def addMasterRepSlaveUser(version=''):
    args = getArgs()
    data = checkArgs(args, ['username', 'password'])
    if not data[0]:
        return data[1]

    if not 'address' in args:
        address = ''
    else:
        address = args['address'].strip()

    username = args['username'].strip()
    password = args['password'].strip()
    # ps = args['ps'].strip()
    # address = args['address'].strip()
    # dataAccess = args['dataAccess'].strip()

    reg = "^[\w\.-]+$"
    if not re.match(reg, username):
        return mw.returnJson(False, '用户名不能带有特殊符号!')
    checks = ['root', 'mysql', 'test', 'sys', 'panel_logs']
    if username in checks or len(username) < 1:
        return mw.returnJson(False, '用户名不合法!')
    if password in checks or len(password) < 1:
        return mw.returnJson(False, '密码不合法!')

    if len(password) < 1:
        password = mw.md5(time.time())[0:8]

    pdb = pMysqlDb()
    psdb = pSqliteDb('master_replication_user')

    if psdb.where("username=?", (username)).count() > 0:
        return mw.returnJson(False, '用户已存在!')

    if version == "8.0":
        sql = "CREATE USER '" + username + \
            "'  IDENTIFIED WITH mysql_native_password BY '" + password + "';"
        pdb.execute(sql)
        sql = "grant replication slave on *.* to '" + username + "'@'%';"
        result = pdb.execute(sql)
        isError = isSqlError(result)
        if isError != None:
            return isError

        sql = "FLUSH PRIVILEGES;"
        pdb.execute(sql)
    else:
        result = pdb.execute('SET sql_log_bin = 0;')
        sql = "GRANT REPLICATION SLAVE ON *.* TO  '" + username + \
            "'@'%' identified by '" + password + "';"
        result = pdb.execute(sql)
        result = pdb.execute('FLUSH PRIVILEGES;')
        result = pdb.execute('SET sql_log_bin = 1;')
        isError = isSqlError(result)
        if isError != None:
            return isError

    addTime = time.strftime('%Y-%m-%d %X', time.localtime())
    psdb.add('username,password,accept,ps,addtime',
             (username, password, '%', '', addTime))
    return mw.returnJson(True, '添加成功!')


def getMasterRepSlaveUserCmd(version):

    args = getArgs()
    data = checkArgs(args, ['username', 'db'])
    if not data[0]:
        return data[1]

    psdb = pSqliteDb('master_replication_user')
    f = 'username,password'
    username = args['username']
    if username == '':
        count = psdb.count()
        if count == 0:
            return mw.returnJson(False, '请添加同步账户!')

        clist = psdb.field(f).limit('1').order('id desc').select()
    else:
        clist = psdb.field(f).where("username=?", (username,)).limit(
            '1').order('id desc').select()

    ip = mw.getLocalIp()
    port = getMyPort()
    db = pMysqlDb()

    mstatus = db.query('show master status')
    if len(mstatus) == 0:
        return mw.returnJson(False, '未开启binlog日志!')

    mode = recognizeDbMode()

    if mode == "gtid":
        sql = "CHANGE MASTER TO MASTER_HOST='" + ip + "', MASTER_PORT=" + port + ", MASTER_USER='" + \
            clist[0]['username'] + "', MASTER_PASSWORD='" + \
            clist[0]['password'] + "', MASTER_AUTO_POSITION=1"
        if version == '8.0':
            sql = "CHANGE REPLICATION SOURCE TO SOURCE_HOST='" + ip + "', SOURCE_PORT=" + port + ", SOURCE_USER='" + \
                clist[0]['username'] + "', SOURCE_PASSWORD='" + \
                clist[0]['password'] + "', MASTER_AUTO_POSITION=1"
    else:
        sql = "CHANGE MASTER TO MASTER_HOST='" + ip + "', MASTER_PORT=" + port + ", MASTER_USER='" + \
            clist[0]['username'] + "', MASTER_PASSWORD='" + \
            clist[0]['password'] + \
            "', MASTER_LOG_FILE='" + mstatus[0]["File"] + \
            "',MASTER_LOG_POS=" + str(mstatus[0]["Position"])

        if version == "8.0":
            sql = "CHANGE REPLICATION SOURCE TO SOURCE_HOST='" + ip + "', SOURCE_PORT=" + port + ", SOURCE_USER='" + \
                clist[0]['username'] + "', SOURCE_PASSWORD='" + \
                clist[0]['password'] + \
                "', SOURCE_LOG_FILE='" + mstatus[0]["File"] + \
                "',SOURCE_LOG_POS=" + str(mstatus[0]["Position"])

    data = {}
    data['cmd'] = sql
    data["info"] = clist[0]
    data['mode'] = mode

    return mw.returnJson(True, 'ok!', data)


def delMasterRepSlaveUser(version=''):
    args = getArgs()
    data = checkArgs(args, ['username'])
    if not data[0]:
        return data[1]

    name = args['username']

    pdb = pMysqlDb()
    psdb = pSqliteDb('master_replication_user')
    pdb.execute("drop user '" + name + "'@'%'")
    pdb.execute("drop user '" + name + "'@'localhost'")

    users = pdb.query("select Host from mysql.user where User='" +
                      name + "' AND Host!='localhost'")
    for us in users:
        pdb.execute("drop user '" + name + "'@'" + us["Host"] + "'")

    psdb.where("username=?", (args['username'],)).delete()

    return mw.returnJson(True, '删除成功!')


def updateMasterRepSlaveUser(version=''):
    args = getArgs()
    data = checkArgs(args, ['username', 'password'])
    if not data[0]:
        return data[1]

    pdb = pMysqlDb()
    psdb = pSqliteDb('master_replication_user')
    pdb.execute("drop user '" + args['username'] + "'@'%'")
    pdb.execute("GRANT REPLICATION SLAVE ON *.* TO  '" +
                args['username'] + "'@'%' identified by '" + args['password'] + "'")

    # 更新db文件中的密码
    psdb.where("username=?", (args['username'],)).save('password', (args['password'],))
    

    return mw.returnJson(True, '更新成功!')


def getSlaveSSHList(version=''):
    args = getArgs()
    data = checkArgs(args, ['page', 'page_size'])
    if not data[0]:
        return data[1]

    page = int(args['page'])
    page_size = int(args['page_size'])

    conn = pSqliteDb('slave_id_rsa')
    limit = str((page - 1) * page_size) + ',' + str(page_size)

    field = 'id,ip,port,db_user,id_rsa,ps,addtime'
    clist = conn.field(field).limit(limit).order('id desc').select()
    count = conn.count()

    data = {}
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = args['tojs']
    data['page'] = mw.getPage(_page)
    data['data'] = clist

    return mw.getJson(data)


def getSlaveSSHByIp(version=''):
    args = getArgs()
    data = checkArgs(args, ['ip'])
    if not data[0]:
        return data[1]

    ip = args['ip']

    conn = pSqliteDb('slave_id_rsa')
    data = conn.field('ip,port,db_user,id_rsa').where("ip=?", (ip,)).select()
    return mw.returnJson(True, 'ok', data)


def addSlaveSSH(version=''):
    import base64

    args = getArgs()
    data = checkArgs(args, ['ip'])
    if not data[0]:
        return data[1]

    ip = args['ip']
    if ip == "":
        return mw.returnJson(True, 'ok')

    data = checkArgs(args, ['port', 'id_rsa', 'db_user'])
    if not data[0]:
        return data[1]

    id_rsa = args['id_rsa'].replace('\\n', '\n')
    port = args['port']
    db_user = args['db_user']
    user = 'root'
    addTime = time.strftime('%Y-%m-%d %X', time.localtime())

    conn = pSqliteDb('slave_id_rsa')
    data = conn.field('ip,id_rsa').where("ip=?", (ip,)).select()
    if len(data) > 0:
        res = conn.where("ip=?", (ip,)).save(
            'port,id_rsa,db_user', (port, id_rsa, db_user))
    else:
        conn.add('ip,port,user,id_rsa,db_user,ps,addtime',
                 (ip, port, user, id_rsa, db_user, '', addTime))

    return mw.returnJson(True, '设置成功!')


def delSlaveSSH(version=''):
    args = getArgs()
    data = checkArgs(args, ['ip'])
    if not data[0]:
        return data[1]

    ip = args['ip']

    conn = pSqliteDb('slave_id_rsa')
    conn.where("ip=?", (ip,)).delete()
    return mw.returnJson(True, 'ok')


def updateSlaveSSH(version=''):
    args = getArgs()
    data = checkArgs(args, ['ip', 'id_rsa'])
    if not data[0]:
        return data[1]

    ip = args['ip']
    id_rsa = args['id_rsa']
    conn = pSqliteDb('slave_id_rsa')
    conn.where("ip=?", (ip,)).save('id_rsa', (id_rsa,))
    return mw.returnJson(True, 'ok')

def testSSH():
    args = getArgs()
    data = checkArgs(args, ['ip', 'port', 'id_rsa'])
    if not data[0]:
        return data[1]
    
    SSH_PRIVATE_KEY = "/root/.ssh/id_rsa"
    # 如果args['id_rsa']的内容不是一个路径，而是证书内容（包含BEGIN OPENSSH PRIVATE KEY）
    if args['id_rsa'] and args['id_rsa'].find('BEGIN OPENSSH PRIVATE KEY') > -1:
        SSH_PRIVATE_KEY = "/tmp/t_ssh.txt"
        mw.writeFile(SSH_PRIVATE_KEY, args['id_rsa'].replace('\\n', '\n'))


    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 自动添加主机名和主机密钥
    try:
        ssh.connect(hostname=args['ip'], port=args['port'], username='root', pkey=RSAKey(filename=SSH_PRIVATE_KEY), timeout=2)  # 你的主机名，用户名和密码
        return mw.returnJson(True, '连接成功')
    except Exception as e:
        return mw.returnJson(False, str(e))

def getSlaveList(version=''):

    db = pMysqlDb()
    dlist = db.query('show slave status')
    ret = []
    for x in range(0, len(dlist)):
        tmp = {}
        tmp['Master_User'] = dlist[x]["Master_User"]
        tmp['Master_Host'] = dlist[x]["Master_Host"]
        tmp['Master_Port'] = dlist[x]["Master_Port"]
        tmp['Master_Log_File'] = dlist[x]["Master_Log_File"]
        tmp['Slave_IO_Running'] = dlist[x]["Slave_IO_Running"]
        tmp['Slave_SQL_Running'] = dlist[x]["Slave_SQL_Running"]
        tmp['Seconds_Behind_Master'] = dlist[x]["Seconds_Behind_Master"] if dlist[x]["Seconds_Behind_Master"] != None else '异常'
        tmp['Last_Error'] = dlist[x]["Last_Error"] 
        tmp['Last_IO_Error'] = dlist[x]["Last_IO_Error"]
        ret.append(tmp)
    data = {}
    data['data'] = ret

    return mw.getJson(data)


def getSlaveSyncCmd(version=''):

    root = mw.getRunDir()
    cmd = 'cd ' + root + ' && python3 ' + root + \
        '/plugins/mysql-apt/index.py do_full_sync {"db":"all"}'
    return mw.returnJson(True, 'ok', cmd)



class master_ssh_client:
    def __init__(self):
        self._client = None
        self._ssh_private_key = None

    def connect(self, ip, port, id_rsa):
        SSH_PRIVATE_KEY = "/root/.ssh/id_rsa"
        # 如果args['id_rsa']的内容不是一个路径，而是证书内容（包含BEGIN OPENSSH PRIVATE KEY）
        if id_rsa and id_rsa.find('BEGIN OPENSSH PRIVATE KEY') > -1:
          SSH_PRIVATE_KEY = "/tmp/t_ssh.txt"
          mw.writeFile(SSH_PRIVATE_KEY, id_rsa.replace('\\n', '\n'))
        self._ssh_private_key = SSH_PRIVATE_KEY 

        import paramiko
        paramiko.util.log_to_file('paramiko.log')
        ssh = paramiko.SSHClient()

        mw.execShell("chmod 600 " + SSH_PRIVATE_KEY)
        key = paramiko.RSAKey.from_private_key_file(SSH_PRIVATE_KEY)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, port=int(port),
                    username='root', pkey=key)
        self._client = ssh
        return ssh

    def close(self):
        # 如果是tmp下的证书，删除证书
        if self._ssh_private_key == "/tmp/t_ssh.txt":
          os.system("rm -rf " + self._ssh_private_key)
        if self._client:
          self._client.close()
        return True


def initSlaveStatus(version=''):
    args = getArgs()
    log_file = args.get('log_file', '')
    log_pos = args.get('log_pos', '')
    gtid_purged = args.get('gtid_purged', '')
    
    db = pMysqlDb()
    try:
      dlist = db.query('show slave status')
      if len(dlist) > 0:
        return mw.returnJson(False, '已经初始化好了zz...')
    except Exception as e:
        return mw.returnJson(False, '主从状态异常，请尝试手动修复主从状态...')

    conn = pSqliteDb('slave_id_rsa')
    data = conn.field('ip,port,id_rsa').find()

    if len(data) < 1:
        return mw.returnJson(False, '需要先配置【[主]SSH配置】!')

    ip = data['ip']
    master_port = data['port']
    id_rsa = data['id_rsa']

    ssh_client = master_ssh_client()
    try:
        ssh = ssh_client.connect(ip, master_port, id_rsa)

        # todo 修复使用指定账号
        cmd = 'cd /www/server/jh-panel && python3 plugins/mysql-apt/index.py get_master_rep_slave_user_cmd {"username":"","db":""}'
        # print("cmd", cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        result = stdout.read()
        # print("result", result)
        result = result.decode('utf-8')
        # print("result", result)
        cmd_data = json.loads(result)

        if not cmd_data['status']:
            return mw.returnJson(False, '[主]:' + cmd_data['msg'])

        local_mode = recognizeDbMode()
        if local_mode != cmd_data['data']['mode']:
            return mw.returnJson(False, '主【{}】从【{}】,运行模式不一致!'.format(cmd_data['data']['mode'], local_mode))

        u = cmd_data['data']['info']
        ps = u['username'] + "|" + u['password']
        conn.where('ip=?', (ip,)).setField('ps', ps)
        db.query('stop slave')

        # 保证同步IP一致
        cmd = cmd_data['data']['cmd']
        if cmd.find('SOURCE_HOST') > -1:
            cmd = re.sub(r"SOURCE_HOST='([^']*)'",
                         "SOURCE_HOST='" + ip + "'", cmd, 1)

        if cmd.find('MASTER_HOST') > -1:
            cmd = re.sub(r"MASTER_HOST='([^']*)'",
                         "MASTER_HOST='" + ip + "'", cmd, 1)

        # 指定位置启动从库
        if log_file != '' and log_pos != '':
            cmd = re.sub(r", MASTER_AUTO_POSITION=1", "", cmd, 1)
            cmd = cmd + " ,MASTER_LOG_FILE='" + log_file + \
               "',MASTER_LOG_POS=" + log_pos
        if gtid_purged != '':
            # print("gtid集合：", gtid_purged)
            gtid_purged = gtid_purged.replace('：', ':')
            # print(gtid_purged)
            # 使用 reset master 清空 GTID_EXECUTED，否则 gtid_purged 设置会报错
            db.query("RESET MASTER")
            db.query("RESET SLAVE ALL")
            db.query("SET GLOBAL gtid_purged='" + gtid_purged + "'")
        # print('cmd', cmd)
        db.query(cmd)
        db.query("start slave user='{}' password='{}';".format(
            u['username'], u['password']))
        
        # 开始只读
        db.query('SET GLOBAL read_only = on')
        db.query('SET GLOBAL super_read_only = on')
        mw.execShell(f'source {getPluginDir()}/readonly.sh && enable_readonly')

    except Exception as e:
        return mw.returnJson(False, 'SSH认证配置连接失败!' + str(e))
    ssh_client.close()
    return mw.returnJson(True, '初始化成功!')

def setDbReadOnly(version=''):
    db = pMysqlDb()
    db.query('SET GLOBAL read_only = on')
    db.query('SET GLOBAL super_read_only = on')
    mw.execShell(f'source {getPluginDir()}/readonly.sh && enable_readonly')
    return mw.returnJson(True, '设置成功!')

def setDbReadWrite(version=''):
    db = pMysqlDb()
    db.query('SET GLOBAL read_only = off')
    db.query('SET GLOBAL super_read_only = off')
    mw.execShell(f'source {getPluginDir()}/readonly.sh && disable_readonly')
    return mw.returnJson(True, '设置成功!')


def setSlaveStatus(version=''):

    db = pMysqlDb()
    dlist = db.query('show slave status')
    if len(dlist) == 0:
        return mw.returnJson(False, '需要手动添加主服务命令或者执行[初始化]!')

    if len(dlist) > 0 and (dlist[0]["Slave_IO_Running"] == 'Yes' or dlist[0]["Slave_SQL_Running"] == 'Yes'):
        db.query('stop slave')
    else:
        ip = dlist[0]['Master_Host']
        conn = pSqliteDb('slave_id_rsa')
        data = conn.field('ip,ps').where("ip=?", (ip,)).find()
        if len(data) == 0:
            return mw.returnJson(False, '没有数据无法重启!')
        u = data['ps'].split("|")
        db.query("start slave user='{}' password='{}';".format(u[0], u[1]))

    return mw.returnJson(True, '设置成功!')


def waitRelayLogApplied(db, max_wait=30):
    """
    等待 Relay Log 回放完成，确保切换主库前数据已全部执行。
    """
    try:
        db.query('STOP SLAVE IO_THREAD')
    except Exception as e:
        mw.writeLog('mysql-apt', '停止IO线程失败: {}'.format(e))

    start_time = time.time()
    while True:
        try:
            status = db.query('SHOW SLAVE STATUS')
        except Exception as e:
            mw.writeLog('mysql-apt', '读取从库状态失败: {}'.format(e))
            break

        if not status:
            mw.writeLog('mysql-apt', '未检测到从库状态，跳过 Relay Log 检查')
            break

        row = status[0]
        relay_master_file = str(row.get('Relay_Master_Log_File', '') or '')
        master_log_file = str(row.get('Master_Log_File', '') or '')
        read_pos = str(row.get('Read_Master_Log_Pos', '0') or '0')
        exec_pos = str(row.get('Exec_Master_Log_Pos', '0') or '0')

        if relay_master_file == master_log_file and read_pos == exec_pos:
            mw.writeLog('mysql-apt', 'Relay Log 已完全回放 (Pos: {0})'.format(exec_pos))
            break

        elapsed = int(time.time() - start_time)
        mw.writeLog('mysql-apt',
                    '等待 Relay Log 回放中: Read={0}, Exec={1}, 已等待 {2}s'.format(read_pos, exec_pos, elapsed))

        if elapsed >= max_wait:
            mw.writeLog('mysql-apt', '等待 Relay Log 回放超过 {0}s，强制进入主库模式'.format(max_wait))
            break

        time.sleep(1)


def deleteSlave(version=''):
    db = pMysqlDb()
    waitRelayLogApplied(db, 30)
    db.query('STOP SLAVE')
    db.query('RESET SLAVE ALL')
    db.query('SET GLOBAL read_only = off')
    db.query('SET GLOBAL super_read_only = off')
    mw.execShell(f'source {getPluginDir()}/readonly.sh && disable_readonly')
    return mw.returnJson(True, '删除成功!')

def saveSlaveStatus(version=''):
    args = getArgs()
    ip = args.get('ip', '')
    user = args.get('user', '')
    log_file = args.get('log_file', '')
    io_running = args.get('io_running', '')
    sql_running = args.get('sql_running', '')
    delay = args.get('delay', '')
    error_msg = args.get('error_msg', '')
    ps = args.get('ps', '')
    addtime = int(time.time())

    # 创建表
    config_conn = pSqliteDb('config')
    check_table_query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='slave_status';"
    table_exist = config_conn.originExecute(check_table_query)
    if not table_exist.fetchone():
        config_conn.originExecute("CREATE TABLE IF NOT EXISTS slave_status (id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT, user TEXT, log_file TEXT, io_running TEXT, sql_running TEXT, delay TEXT, `error_msg` TEXT, ps TEXT, addtime TEXT)")

    # 保存数据  
    slave_status_conn = pSqliteDb('slave_status')
    slave_status_conn.execute('DELETE FROM slave_status')
    slave_status_conn.add('ip,user,log_file,io_running,sql_running,delay,error_msg,ps,addtime', (ip, user, log_file, io_running, sql_running, delay, error_msg, ps, addtime))

    # # 判断是否存在指定的ip，如果存在则更新，不存在则新增
    # data = slave_status_conn.field('id').where('ip=?', (ip,)).select()
    # if len(data) > 0:
    #     slave_status_conn.where('ip=?', (ip,)).save('user,log_file,io_running,sql_running,delay,error_msg,ps,addtime', (user, log_file, io_running, sql_running, delay, error_msg, ps, addtime))
    # else:
    #     slave_status_conn.add('ip,user,log_file,io_running,sql_running,delay,error_msg,ps,addtime', (ip, user, log_file, io_running, sql_running, delay, error_msg, ps, addtime))
  
    return mw.returnJson(True, '保存成功!')
    

def saveSlaveStatusToMaster(version=''):
    db = pMysqlDb()
    dlist = db.query('show slave status')

    ip = mw.getLocalIp()
    
    for x in range(0, len(dlist)):

        # 报错从库状态
        conn = pSqliteDb('slave_id_rsa')
        data = conn.field('ip,port,id_rsa').where('ip=?', (dlist[x]["Master_Host"],)).find()
        if len(data) < 1:
          print('未找到【[主]SSH配置】!')
          continue
            
        master_ip = data['ip']
        master_port = data['port']
        id_rsa = data['id_rsa']
        user = dlist[x]["Master_User"]
        log_file = dlist[x]["Master_Log_File"]
        io_running = dlist[x]["Slave_IO_Running"]
        sql_running = dlist[x]["Slave_SQL_Running"]
        delay = dlist[x]["Seconds_Behind_Master"]
        error_msg = dlist[x]["Last_Error"] if dlist[x]["Last_Error"] else dlist[x]["Last_IO_Error"]
        ps = ""

        ssh_client = master_ssh_client()
        try:
            print(f"|- 开始连接{user}@{master_ip}")
            ssh = ssh_client.connect(master_ip, master_port, id_rsa)
            cmd = f'cd /www/server/jh-panel && python3 /www/server/jh-panel/plugins/mysql-apt/index.py save_slave_status {{ip:{ip},user:{user},log_file:{log_file},io_running:{io_running},sql_running:{sql_running},delay:{delay},error_msg:"{error_msg}",ps:{ps}}}'
            print("|- cmd：", cmd)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            result = stdout.read()
            result = result.decode('utf-8')
            print("|- result：", result)

        except Exception as e:
            return mw.returnJson(False, 'SSH认证配置连接失败!' + str(e))
        ssh_client.close()
    return mw.returnJson(True, '保存成功!')

def dumpMysqlData(version=''):
    args = getArgs()
    data = checkArgs(args, ['db'])
    if not data[0]:
        return data[1]

    pwd = pSqliteDb('config').where('id=?', (1,)).getField('mysql_root')
    mysql_dir = getServerDir()
    myconf = mysql_dir + "/etc/my.cnf"

    option = ''
    mode = recognizeDbMode()
    if mode == 'gtid':
        option = ' --set-gtid-purged=off '

    if args['db'].lower() == 'all':
        dlist = findBinlogDoDb()
        cmd = mysql_dir + "/bin/usr/bin/mysqldump --defaults-file=" + myconf + " " + option + " -uroot -p" + \
            pwd + " --databases " + \
            ' '.join(dlist) + " | gzip > /tmp/dump.sql.gz"
    else:
        cmd = mysql_dir + "/bin/usr/bin/mysqldump --defaults-file=" + myconf + " " + option + " -uroot -p" + \
            pwd + " --databases " + args['db'] + " | gzip > /tmp/dump.sql.gz"

    ret = mw.execShell(cmd)
    if ret[0] == '':
        return 'ok'
    return 'fail'


############### --- 重要 同步---- ###########

def writeDbSyncStatus(data):
    path = '/tmp/db_async_status.txt'
    # status_data['code'] = 1
    # status_data['msg'] = '主服务器备份完成...'
    # status_data['progress'] = 30
    mw.writeFile(path, json.dumps(data))


def doFullSync(version=''):

    args = getArgs()
    data = checkArgs(args, ['db'])
    if not data[0]:
        return data[1]

    db = pMysqlDb()

    id_rsa_conn = pSqliteDb('slave_id_rsa')
    data = id_rsa_conn.field('ip,port,db_user,id_rsa').find()

    SSH_PRIVATE_KEY = "/tmp/mysql_sync_id_rsa.txt"
    id_rsa = data['id_rsa'].replace('\\n', '\n')
    mw.writeFile(SSH_PRIVATE_KEY, id_rsa)

    ip = data["ip"]
    master_port = data['port']
    db_user = data['db_user']
    print("master ip:", ip)

    writeDbSyncStatus({'code': 0, 'msg': '开始同步...', 'progress': 0})

    import paramiko
    paramiko.util.log_to_file('paramiko.log')
    ssh = paramiko.SSHClient()

    print(SSH_PRIVATE_KEY)
    if not os.path.exists(SSH_PRIVATE_KEY):
        writeDbSyncStatus({'code': 0, 'msg': '需要配置SSH......', 'progress': 0})
        return 'fail'

    try:
        # ssh.load_system_host_keys()
        mw.execShell("chmod 600 " + SSH_PRIVATE_KEY)
        key = paramiko.RSAKey.from_private_key_file(SSH_PRIVATE_KEY)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(ip, master_port)

        # pkey=key
        # key_filename=SSH_PRIVATE_KEY
        ssh.connect(hostname=ip, port=int(master_port),
                    username='root', pkey=key)
    except Exception as e:
        print(str(e))
        writeDbSyncStatus(
            {'code': 0, 'msg': 'SSH配置错误:' + str(e), 'progress': 0})
        return 'fail'

    writeDbSyncStatus({'code': 0, 'msg': '登录Master成功...', 'progress': 5})

    dbname = args['db']
    cmd = "cd /www/server/jh-panel && python3 plugins/mysql-apt/index.py dump_mysql_data {\"db\":\"" + dbname + "\"}"
    print(cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    result = stdout.read()
    result = result.decode('utf-8')
    if result.strip() == 'ok':
        writeDbSyncStatus({'code': 1, 'msg': '主服务器备份完成...', 'progress': 30})
    else:
        writeDbSyncStatus(
            {'code': 1, 'msg': '主服务器备份失败...:' + str(result), 'progress': 100})
        return 'fail'

    print("同步文件", "start")
    # cmd = 'scp -P' + str(master_port) + ' -i ' + SSH_PRIVATE_KEY + \
    #     ' root@' + ip + ':/tmp/dump.sql.gz /tmp'
    t = ssh.get_transport()
    sftp = paramiko.SFTPClient.from_transport(t)
    copy_status = sftp.get("/tmp/dump.sql.gz", "/tmp/dump.sql.gz")
    print("同步信息:", copy_status)
    print("同步文件", "end")
    if copy_status == None:
        writeDbSyncStatus({'code': 2, 'msg': '数据同步本地完成...', 'progress': 40})

    cmd = 'cd /www/server/jh-panel && python3 plugins/mysql-apt/index.py get_master_rep_slave_user_cmd {"username":"' + db_user + '","db":""}'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    result = stdout.read()
    result = result.decode('utf-8')
    cmd_data = json.loads(result)

    db.query('stop slave')
    writeDbSyncStatus({'code': 3, 'msg': '停止从库完成...', 'progress': 45})

    cmd = cmd_data['data']['cmd']
    # 保证同步IP一致
    if cmd.find('SOURCE_HOST') > -1:
        cmd = re.sub(r"SOURCE_HOST='(.*)'", "SOURCE_HOST='" + ip + "'", cmd, 1)

    if cmd.find('MASTER_HOST') > -1:
        cmd = re.sub(r"MASTER_HOST='(.*)'", "SOURCE_HOST='" + ip + "'", cmd, 1)

    db.query(cmd)
    uinfo = cmd_data['data']['info']
    ps = uinfo['username'] + "|" + uinfo['password']
    id_rsa_conn.where('ip=?', (ip,)).setField('ps', ps)
    writeDbSyncStatus({'code': 4, 'msg': '刷新从库同步信息完成...', 'progress': 50})

    pwd = pSqliteDb('config').where('id=?', (1,)).getField('mysql_root')
    root_dir = getServerDir()
    msock = root_dir + "/mysql.sock"
    mw.execShell("cd /tmp && gzip -d dump.sql.gz")
    cmd = root_dir + "/bin/usr/bin/mysql -S " + msock + \
        " -uroot -p" + pwd + " < /tmp/dump.sql"
    import_data = mw.execShell(cmd)
    if import_data[0] == '':
        print(import_data[1])
        writeDbSyncStatus({'code': 5, 'msg': '导入数据完成...', 'progress': 90})
    else:
        print(import_data[0])
        writeDbSyncStatus({'code': 5, 'msg': '导入数据失败...', 'progress': 100})
        return 'fail'

    db.query("start slave user='{}' password='{}';".format(
        uinfo['username'], uinfo['password']))
    writeDbSyncStatus({'code': 6, 'msg': '从库重启完成...', 'progress': 100})

    os.system("rm -rf " + SSH_PRIVATE_KEY)
    os.system("rm -rf /tmp/dump.sql")
    return True


def fullSync(version=''):
    args = getArgs()
    data = checkArgs(args, ['db', 'begin'])
    if not data[0]:
        return data[1]

    status_file = '/tmp/db_async_status.txt'
    if args['begin'] == '1':
        cmd = 'cd ' + mw.getRunDir() + ' && python3 ' + \
            getPluginDir() + \
            '/index.py do_full_sync {"db":"' + args['db'] + '"} &'
        print(cmd)
        mw.execShell(cmd)
        return json.dumps({'code': 0, 'msg': '同步数据中!', 'progress': 0})

    if os.path.exists(status_file):
        c = mw.readFile(status_file)
        tmp = json.loads(c)
        if tmp['code'] == 1:
            sys_dump_sql = "/tmp/dump.sql"
            if os.path.exists(sys_dump_sql):
                dump_size = os.path.getsize(sys_dump_sql)
                tmp['msg'] = tmp['msg'] + ":" + "同步文件:" + mw.toSize(dump_size)
            c = json.dumps(tmp)

        # if tmp['code'] == 6:
        #     os.remove(status_file)
        return c

    return json.dumps({'code': 0, 'msg': '点击开始,开始同步!', 'progress': 0})


def installPreInspection(version):

    sys = mw.execShell(
        "cat /etc/*-release | grep PRETTY_NAME |awk -F = '{print $2}' | awk -F '\"' '{print $2}'| awk '{print $1}'")

    if sys[1] != '':
        return '不支持改系统'

    sys_id = mw.execShell(
        "cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F '\"' '{print $2}'")

    sysName = sys[0].strip().lower()
    sysId = sys_id[0].strip()

    if not sysName in ('debian', 'ubuntu'):
        return '仅支持debian,ubuntu'

    if (sysName == 'debian' and not sysId in ('11', '10')):
        return 'debian支持10,11'

    if (sysName == 'ubuntu' and version == '5.7' and not sysId in ('18.04')):
        return "Ubuntu Apt MySQL[" + version + "] 仅支持18.04"

    if (sysName == 'ubuntu' and version == '8.0' and not sysId in ('18.04', '20.04', '22.04')):
        return 'Ubuntu Apt MySQL[' + version + '] 仅支持18.04,20.04,22.04'
    return 'ok'


class checksum_logger:
    def __init__(self):
        self._log_file = 'logs/mysql_checksum_opt.log'

    def clear(self):
        if os.path.exists(self._log_file):
            os.remove(self._log_file)
        return True

    def info(self, log_str, mode="ab+"):
        f = open(self._log_file, mode)
        log_str += "\n"
        f.write(log_str.encode('utf-8'))
        f.close()
        return True


def getChecksumReport(version):
    pdb = pMysqlDb()
    databasesData = pdb.query('show databases')
    isError = isSqlError(databasesData)
    if isError != None:
        return isError

    pdb.setDbName("information_schema")

    checksums = {}
    checksum_total = 0
    checksumLogger = checksum_logger()
    checksumLogger.clear()
    checksumReportFile = 'tmp/mysql_checksum_report.txt'

    ignoreDatabases = ['information_schema',
                       'performance_schema', 'mysql', 'sys']
    n = 0
    checksumLogger.info('正在计算checksum...')
    mw.writeFile(checksumReportFile, '', 'w')
    for databaaseValue in databasesData:
        database = databaaseValue["Database"]
        current_database_checksum = 0

        if database in ignoreDatabases:
            continue

        mw.writeFile(checksumReportFile, '|------------------ ' +
                     database + ' ---------------\n', 'a+')

        tablesData = pdb.query(
            f"SELECT * FROM TABLES WHERE TABLE_SCHEMA='{database}' AND TABLE_COMMENT!='VIEW'")
        for tableValue in tablesData:
            table = tableValue["TABLE_NAME"]
            checksumData = pdb.query(f"CHECKSUM TABLE `{database}`.`{table}`")
            checksum = checksumData[0]['Checksum']
            mw.writeFile(checksumReportFile,
                         f"|- {database}.{table}: {checksum}\n", 'a+')
            checksums[database] = {table: checksum}
            current_database_checksum += (int(checksum)
                                          if checksum != None else 0)

        checksum_total += current_database_checksum
        mw.writeFile(checksumReportFile,
                     f'|- Total: {current_database_checksum}\n', 'a+')
        # mw.writeFile(checksumReportFile, f'|----------------------------------------------------------\n', 'a+')
        checksumLogger.info(f'|- {database}: {current_database_checksum}')

    title = mw.getConfig('title')
    mw.writeFile(checksumReportFile,
                 f'\n----------------------------------------------------------\n', 'a+')
    mw.writeFile(checksumReportFile, f'- Name：{title}\n', 'a+')
    mw.writeFile(checksumReportFile,
                 f'- Database Count：{len(databasesData) - len(ignoreDatabases)}\n', 'a+')
    mw.writeFile(checksumReportFile,
                 f'- All Database Total：{checksum_total}\n', 'a+')
    mw.writeFile(checksumReportFile,
                 f'----------------------------------------------------------\n', 'a+')

    checksumLogger.info(f'|- All Database Total：{checksum_total}')
    return mw.returnJson(True, 'ok',  '')


def uninstallPreInspection(version):
    stop(version)
    if mw.isDebugMode():
        return 'ok'

    return "请手动删除MySQL[{}]<br/> rm -rf {}".format(version, getServerDir())


def fixAllDbUser(version):
    pdb = pMysqlDb()
    psdb = pSqliteDb('databases')
    databases = psdb.field(
        'id,pid,name,username,password,accept,rw,ps,addtime').select()

    print("开始检查数据库用户信息...")
    fixDatabases = []
    for databaseIndex in range(0, len(databases)):
        db = databases[databaseIndex]
        dbname = db['username']
        dbpsw = db['password']
        print(f'|- 开始检查：{dbname}...')
        db_users = pdb.query(
            "select Host from mysql.user where User='" + dbname + "'")
        # 密码为空
        if dbpsw is None or dbpsw == '':
            # 删除旧用户
            for us in db_users:
                pdb.execute("drop user '" + dbname + "'@'" + us["Host"] + "'")
        # 查询用户
        db_users = pdb.query(
            "select Host from mysql.user where User='" + dbname + "'")
        if len(db_users) == 0:
            fixDatabases.append(db)

    if len(fixDatabases) == 0:
        print('暂无需要修复的数据库用户!')
        return
    confirm = input(
        f"检测到异常数据库用户：{','.join(db.get('name', '') for db in fixDatabases)}，要重建这些用户吗？（默认y）[y/n] ")
    confirm = confirm if confirm else 'y'
    if confirm.lower() == 'y':
        defaultAccess = '127.0.0.1'
        addTime = time.strftime('%Y-%m-%d %X', time.localtime())

        for databaseIndex in range(0, len(fixDatabases)):
            db = fixDatabases[databaseIndex]
            dbname = db['name']
            dbpsw = db['password']
            print(f"|- 开始重建用户：{dbname}...")
            password = dbpsw if dbpsw else mw.getRandomString(16)
            createResult = __createUser(
                dbname, dbname, password, defaultAccess)
            if createResult:
                print(f"|- 重建用户{dbname}失败❌：{createResult}")
                continue
            psdb.where('username=?', (dbname,)).save(
                'password,accept,rw', (password, defaultAccess, 'rw',))
            print(f"|- 重建用户{dbname}成功✅，当前密码为{password}")
        print("全部数据库用户修复完成!✅")
    else:
        print("取消执行")
    return ''


if __name__ == "__main__":

    func = sys.argv[1]

    version = "5.6"
    version_pl = getServerDir() + "/version.pl"
    if os.path.exists(version_pl):
        version = mw.readFile(version_pl).strip()

    # if (len(sys.argv) > 2):
    #     version = sys.argv[2]

    if func == 'status':
        print(status(version))
    elif func == 'start':
        print(start(version))
    elif func == 'stop':
        print(stop(version))
    elif func == 'restart':
        print(restart(version))
    elif func == 'reload':
        print(reload(version))
    elif func == 'initd_status':
        print(initdStatus())
    elif func == 'set_db_status_by_system_memory':
        print(setDbStatusBySystemMemory(version))
    elif func == 'initd_install':
        print(initdInstall())
    elif func == 'initd_uninstall':
        print(initdUinstall())
    elif func == 'install_pre_inspection':
        print(installPreInspection(version))
    elif func == 'uninstall_pre_inspection':
        print(uninstallPreInspection(version))
    elif func == 'run_info':
        print(runInfo(version))
    elif func == 'db_status':
        print(myDbStatus(version))
    elif func == 'set_db_status':
        print(setDbStatus(version))
    elif func == 'conf':
        print(getConf())
    elif func == 'bin_log':
        print(binLog())
    elif func == 'clean_bin_log':
        print(cleanBinLog())
    elif func == 'error_log':
        print(getErrorLog())
    elif func == 'show_log':
        print(getShowLogFile())
    elif func == 'my_db_pos':
        print(getMyDbPos())
    elif func == 'set_db_pos':
        print(setMyDbPos())
    elif func == 'my_port':
        print(getMyPort())
    elif func == 'set_my_port':
        print(setMyPort())
    elif func == 'init_pwd':
        print(initMysqlPwd())
    elif func == 'get_mysql_info':
        print(getMysqlInfo())
    elif func == 'get_db_list_page':
        print(getDbListPage())
    elif func == 'set_db_backup':
        print(setDbBackup())
    elif func == 'get_import_db_backup_script':
        print(getImportDbBackupScript())
    elif func == 'import_db_backup':
        print(importDbBackup())
    elif func == 'import_db_external':
        print(importDbExternal())
    elif func == 'delete_db_backup':
        print(deleteDbBackup())
    elif func == 'get_db_backup_list':
        print(getDbBackupList())
    elif func == 'get_db_backup_import_list':
        print(getDbBackupImportList())
    elif func == 'add_db':
        print(addDb())
    elif func == 'del_db':
        print(delDb())
    elif func == 'sync_get_databases':
        print(syncGetDatabases())
    elif func == 'sync_to_databases':
        print(syncToDatabases())
    elif func == 'set_root_pwd':
        print(setRootPwd(version))
    elif func == 'fix_root_pwd':
        print(fixRootPwd(version))
    elif func == 'set_user_pwd':
        print(setUserPwd(version))
    elif func == 'get_db_access':
        print(getDbAccess())
    elif func == 'set_db_access':
        print(setDbAccess())
    elif func == 'fix_db_access':
        print(fixDbAccess(version))
    elif func == 'set_db_rw':
        print(setDbRw(version))
    elif func == 'set_db_ps':
        print(setDbPs())
    elif func == 'get_db_info':
        print(getDbInfo())
    elif func == 'repair_table':
        print(repairTable())
    elif func == 'opt_table':
        print(optTable())
    elif func == 'alter_table':
        print(alterTable())
    elif func == 'get_total_statistics':
        print(getTotalStatistics())
    elif func == 'get_dbrun_mode':
        print(getDbrunMode(version))
    elif func == 'set_dbrun_mode':
        print(setDbrunMode(version))
    elif func == 'get_masterdb_list':
        print(getMasterDbList(version))
    elif func == 'get_master_status':
        print(getMasterStatus(version))
    elif func == 'set_master_status':
        print(setMasterStatus(version))
    elif func == 'set_semi_sync_status':
        print(setSemiSyncStatus(version))
    elif func == 'set_db_master':
        print(setDbMaster(version))
    elif func == 'set_db_slave':
        print(setDbSlave(version))
    elif func == 'set_dbmaster_access':
        print(setDbMasterAccess())
    elif func == 'get_master_rep_slave_list':
        print(getMasterRepSlaveList(version))
    elif func == 'add_master_rep_slave_user':
        print(addMasterRepSlaveUser(version))
    elif func == 'del_master_rep_slave_user':
        print(delMasterRepSlaveUser(version))
    elif func == 'update_master_rep_slave_user':
        print(updateMasterRepSlaveUser(version))
    elif func == 'get_master_rep_slave_user_cmd':
        print(getMasterRepSlaveUserCmd(version))
    elif func == 'get_slave_list':
        print(getSlaveList(version))
    elif func == 'get_slave_sync_cmd':
        print(getSlaveSyncCmd(version))
    elif func == 'get_slave_ssh_list':
        print(getSlaveSSHList(version))
    elif func == 'get_slave_ssh_by_ip':
        print(getSlaveSSHByIp(version))
    elif func == 'add_slave_ssh':
        print(addSlaveSSH(version))
    elif func == 'del_slave_ssh':
        print(delSlaveSSH(version))
    elif func == 'update_slave_ssh':
        print(updateSlaveSSH(version))
    elif func == 'test_ssh':
        print(testSSH())
    elif func == 'init_slave_status':
        print(initSlaveStatus(version))
    elif func == 'set_slave_status':
        print(setSlaveStatus(version))
    elif func == 'set_db_read_only':
        print(setDbReadOnly(version))
    elif func == 'set_db_read_write':
        print(setDbReadWrite(version))
    elif func == 'delete_slave':
        print(deleteSlave(version))
    elif func == 'save_slave_status':
        print(saveSlaveStatus(version))
    elif func == 'save_slave_status_to_master':
        print(saveSlaveStatusToMaster(version))
    elif func == 'full_sync':
        print(fullSync(version))
    elif func == 'do_full_sync':
        print(doFullSync(version))
    elif func == 'dump_mysql_data':
        print(dumpMysqlData(version))
    elif func == 'get_checksum_report':
        print(getChecksumReport(version))
    elif func == 'fix_all_db_user':
        fixAllDbUser(version)
    else:
        print('error')
