# coding:utf-8

import sys
import io
import os
import time
import re

sys.path.append(os.getcwd() + "/class/core")
import mw

PLUGIN_PATH = os.path.dirname(__file__)
if PLUGIN_PATH not in sys.path:
    sys.path.append(PLUGIN_PATH)
import config_util

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'keepalived'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getInitDFile():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return '/tmp/' + getPluginName()

    if current_os.startswith('freebsd'):
        return '/etc/rc.d/' + getPluginName()

    return '/etc/init.d/' + getPluginName()


def getConf():
    path = getServerDir() + "/etc/keepalived/keepalived.conf"
    return path


def getConfTpl():
    path = getPluginDir() + "/config/keepalived.conf"
    return path


def getInitDTpl():
    path = getPluginDir() + "/init.d/" + getPluginName() + ".tpl"
    return path


def getArgs():
    args = sys.argv[3:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        if t.strip() == '':
            tmp = []
        else:
            t = t.split(':')
            tmp[t[0]] = t[1]
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

def configTpl():
    path = getPluginDir() + '/tpl'
    pathFile = os.listdir(path)
    tmp = []
    for one in pathFile:
        file = path + '/' + one
        tmp.append(file)
    return mw.getJson(tmp)


def readConfigTpl():
    args = getArgs()
    data = checkArgs(args, ['file'])
    if not data[0]:
        return data[1]

    content = mw.readFile(args['file'])
    content = contentReplace(content)
    return mw.returnJson(True, 'ok', content)


def defaultScriptsTpl():
    path = getServerDir() + "/scripts/chk.sh"
    return path

def configScriptsTpl():
    path = getServerDir() + '/scripts'
    pathFile = os.listdir(path)
    tmp = []
    for one in pathFile:
        file = path + '/' + one
        tmp.append(file)
    return mw.getJson(tmp)



def getVrrpForm():
    conf = getConf()
    if not os.path.exists(conf):
        return mw.returnJson(False, '未找到配置文件!')

    tpl_content = ''
    tpl = getConfTpl()
    if os.path.exists(tpl):
        tpl_content = mw.readFile(tpl)

    content = mw.readFile(conf)
    try:
        data = config_util.get_vrrp_form_data(content, tpl_content)
    except config_util.KeepalivedConfigError as exc:
        return mw.returnJson(False, str(exc))
    return mw.returnJson(True, 'OK', data)


def saveVrrpForm():
    args = getArgs()
    required = ['interface', 'virtual_ipaddress', 'priority', 'auth_pass', 'unicast_enabled']
    data = checkArgs(args, required)
    if not data[0]:
        return data[1]

    interface = args['interface'].strip()
    vip = args['virtual_ipaddress'].strip()
    priority = args['priority'].strip()
    auth_pass = args['auth_pass'].strip()
    unicast_enabled = args['unicast_enabled'].lower() in ['1', 'true', 'yes', 'on']
    unicast_src_ip = config_util.normalize_arg(args.get('unicast_src_ip', '').strip())
    peer_raw = config_util.normalize_arg(args.get('unicast_peer_list', '').strip())
    peer_list = [p.strip() for p in peer_raw.splitlines() if p.strip() != '']

    if interface == '' or vip == '' or auth_pass == '':
        return mw.returnJson(False, '接口、虚拟IP和验证码不能为空!')

    try:
        priority_int = int(priority)
        if priority_int < 1:
            raise ValueError('priority < 1')
    except:
        return mw.returnJson(False, '优先级必须为正整数!')

    if unicast_enabled:
        if unicast_src_ip == '' or len(peer_list) == 0:
            return mw.returnJson(False, '单播模式开启时需要填写本地IP和对端IP!')

    conf = getConf()
    if not os.path.exists(conf):
        return mw.returnJson(False, '未找到配置文件!')

    content = mw.readFile(conf)
    values = {
        'interface': interface,
        'virtual_ipaddress': vip,
        'priority': priority_int,
        'auth_pass': auth_pass,
        'unicast_enabled': unicast_enabled,
        'unicast_src_ip': unicast_src_ip,
        'unicast_peer_list': peer_list
    }

    try:
        new_content = config_util.build_vrrp_content(content, values)
    except config_util.KeepalivedConfigError as exc:
        return mw.returnJson(False, str(exc))

    mw.writeFile(conf, new_content)
    return mw.returnJson(True, '保存成功!')


def status():
    data = mw.execShell(
        "ps aux|grep keepalived |grep -v grep | grep -v python | grep -v mdserver-web | awk '{print $2}'")

    if data[0] == '':
        return 'stop'
    return 'start'


def contentReplace(content):
    service_path = os.path.dirname(os.getcwd())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$PLUGIN_PATH}', getPluginDir())

    # 网络接口
    ethx = mw.execShell("route -n | grep ^0.0.0.0 | awk '{print $8}'")
    if ethx[1]!='':
        # 未找到
        content = content.replace('{$ETH_XX}', 'eth1')
    else:
        # 已找到
        content = content.replace('{$ETH_XX}', ethx[0])


    return content


def copyScripts():
    # 复制检查脚本
    src_scripts_path = getPluginDir() + '/scripts'
    dst_scripts_path = getServerDir() + '/scripts'
    if not os.path.exists(dst_scripts_path):
        mw.execShell('mkdir -p ' + dst_scripts_path)

    copied = False
    olist = os.listdir(src_scripts_path)
    for o in range(len(olist)):
        src_file = src_scripts_path + '/' + olist[o]
        dst_file = dst_scripts_path + '/' + olist[o]

        if os.path.exists(dst_file):
            continue

        content = mw.readFile(src_file)
        content = contentReplace(content)
        mw.writeFile(dst_file, content)

        cmd = 'chmod +x ' + dst_file
        mw.execShell(cmd)
        copied = True
    return copied


def getPromotionScriptPath():
    return getServerDir() + '/scripts/promote_slave_to_master.sh'


def getCheckMysqlScriptPath():
    return getServerDir() + '/scripts/chk_mysql.sh'


def shellQuote(value):
    if value is None:
        value = ''
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def parseMysqlConfValue(content, key):
    rep = r'^\s*' + re.escape(key) + r'\s*=\s*(.+)$'
    matches = re.findall(rep, content, re.M)
    if not matches:
        return ''
    return matches[-1].strip()


def detectMysqlInstance():
    server_path = mw.getServerDir()
    mysql_plugins = [
        {
            'name': 'mysql-apt',
            'path': server_path + '/mysql-apt',
            'client_bin': '/bin/usr/bin/mysql'
        },
        {
            'name': 'mysql-yum',
            'path': server_path + '/mysql-yum',
            'client_bin': '/bin/usr/bin/mysql'
        },
        {
            'name': 'mysql',
            'path': server_path + '/mysql',
            'client_bin': '/bin/mysql'
        },
        {
            'name': 'mariadb',
            'path': server_path + '/mariadb',
            'client_bin': '/bin/mysql'
        }
    ]

    for plugin in mysql_plugins:
        base_path = plugin['path']
        conf = base_path + '/etc/my.cnf'
        if not os.path.exists(conf):
            continue

        content = mw.readFile(conf)
        if not content:
            continue

        port = parseMysqlConfValue(content, 'port')
        socket_file = parseMysqlConfValue(content, 'socket')

        password = ''
        try:
            password = mw.M('config').dbPos(base_path, 'mysql').where(
                'id=?', (1,)).getField('mysql_root')
            if password is None:
                password = ''
        except Exception:
            password = ''

        client_bin = base_path + plugin['client_bin']
        if not os.path.exists(client_bin):
            client_bin = 'mysql'

        return {
            'user': 'root',
            'password': password,
            'port': port if port else '3306',
            'socket': socket_file if socket_file else '',
            'client_bin': client_bin
        }
    return None


def syncMysqlScriptsCredentials():
    mysql_info = detectMysqlInstance()
    if not mysql_info:
        return

    script_paths = [
        getPromotionScriptPath(),
        getCheckMysqlScriptPath()
    ]

    replacements = {
        'MYSQL_BIN': mysql_info['client_bin'],
        'MYSQL_USER': mysql_info['user'],
        'MYSQL_PASSWORD': mysql_info['password'],
        'MYSQL_PORT': mysql_info['port'],
        'MYSQL_SOCKET': mysql_info['socket']
    }

    for script_path in script_paths:
        if not os.path.exists(script_path):
            continue

        content = mw.readFile(script_path)
        if not content:
            continue

        changed = False
        for key, value in replacements.items():
            new_line = key + '=' + shellQuote(value)
            pattern = r'^' + key + r'=.*$'
            content, count = re.subn(pattern, new_line, content, flags=re.M)
            if count > 0:
                changed = True

        if changed:
            mw.writeFile(script_path, content)
        mw.execShell('chmod +x ' + script_path)

def initDreplace():

    file_tpl = getInitDTpl()
    service_path = os.path.dirname(os.getcwd())

    initD_path = getServerDir() + '/init.d'
    if not os.path.exists(initD_path):
        os.mkdir(initD_path)
    file_bin = initD_path + '/' + getPluginName()

    # initd replace
    if not os.path.exists(file_bin):
        content = mw.readFile(file_tpl)
        content = contentReplace(content)
        mw.writeFile(file_bin, content)
        mw.execShell('chmod +x ' + file_bin)

    # log
    dataLog = getServerDir() + '/data'
    if not os.path.exists(dataLog):
        mw.execShell('chmod +x ' + file_bin)

    # config replace
    dst_conf = getServerDir() + '/etc/keepalived/keepalived.conf'
    dst_conf_init = getServerDir() + '/init.pl'
    if not os.path.exists(dst_conf_init):
        content = mw.readFile(getConfTpl())
        content = contentReplace(content)
        mw.writeFile(dst_conf, content)
        mw.writeFile(dst_conf_init, 'ok')

    # 复制检查脚本并同步MySQL信息
    copyScripts()
    syncMysqlScriptsCredentials()

    # systemd
    systemDir = mw.systemdCfgDir()
    systemService = systemDir + '/' + getPluginName() + '.service'
    if os.path.exists(systemDir) and not os.path.exists(systemService):
        systemServiceTpl = getPluginDir() + '/init.d/' + getPluginName() + '.service.tpl'
        service_path = mw.getServerDir()
        content = mw.readFile(systemServiceTpl)
        content = contentReplace(content)
        mw.writeFile(systemService, content)
        mw.execShell('systemctl daemon-reload')

    return file_bin


def kpOp(method):
    file = initDreplace()

    current_os = mw.getOs()
    if current_os == "darwin":
        data = mw.execShell(file + ' ' + method)
        if data[1] == '':
            return 'ok'
        return data[1]

    if current_os.startswith("freebsd"):
        data = mw.execShell('service ' + getPluginName() + ' ' + method)
        if data[1] == '':
            return 'ok'
        return data[1]

    data = mw.execShell('systemctl ' + method + ' ' + getPluginName())
    if data[1] == '':
        return 'ok'
    return data[1]


def start():
    return kpOp('start')


def stop():
    return kpOp('stop')


def restart():
    status = kpOp('restart')

    log_file = runLog()
    mw.execShell("echo '' > " + log_file)
    return status


def reload():
    return kpOp('reload')


def getPort():
    conf = getServerDir() + '/keepalived.conf'
    content = mw.readFile(conf)

    rep = r"^(" + 'port' + r')\s*([.0-9A-Za-z_& ~]+)'
    tmp = re.search(rep, content, re.M)
    if tmp:
        return tmp.groups()[1]

    return '6379'


def initdStatus():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return "Apple Computer does not support"

    if current_os.startswith('freebsd'):
        initd_bin = getInitDFile()
        if os.path.exists(initd_bin):
            return 'ok'

    shell_cmd = 'systemctl status ' + \
        getPluginName() + ' | grep loaded | grep "enabled;"'
    data = mw.execShell(shell_cmd)
    if data[0] == '':
        return 'fail'
    return 'ok'


def initdInstall():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return "Apple Computer does not support"

    # freebsd initd install
    if current_os.startswith('freebsd'):
        import shutil
        source_bin = initDreplace()
        initd_bin = getInitDFile()
        shutil.copyfile(source_bin, initd_bin)
        mw.execShell('chmod +x ' + initd_bin)
        mw.execShell('sysrc ' + getPluginName() + '_enable="YES"')
        return 'ok'

    mw.execShell('systemctl enable ' + getPluginName())
    return 'ok'


def initdUinstall():
    current_os = mw.getOs()
    if current_os == 'darwin':
        return "Apple Computer does not support"

    if current_os.startswith('freebsd'):
        initd_bin = getInitDFile()
        os.remove(initd_bin)
        mw.execShell('sysrc ' + getPluginName() + '_enable="NO"')
        return 'ok'

    mw.execShell('systemctl disable ' + getPluginName())
    return 'ok'


def runLog():
    return getServerDir() + '/' + getPluginName() + '.log'


if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'initd_status':
        print(initdStatus())
    elif func == 'initd_install':
        print(initdInstall())
    elif func == 'initd_uninstall':
        print(initdUinstall())
    elif func == 'run_info':
        print(runInfo())
    elif func == 'conf':
        print(getConf())
    elif func == 'run_log':
        print(runLog())
    elif func == 'config_tpl':
        print(configTpl())
    elif func == 'default_scripts_tpl':
        print(defaultScriptsTpl())
    elif func == 'config_scripts_tpl':
        print(configScriptsTpl())
    elif func == 'read_config_tpl':
        print(readConfigTpl())
    elif func == 'get_vrrp_form':
        print(getVrrpForm())
    elif func == 'save_vrrp_form':
        print(saveVrrpForm())
    else:
        print('error')
