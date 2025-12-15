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

VRRP_INSTANCE_NAME = 'VI_MYSQL'
VRRP_PANEL_UNICAST_TAG = '# panel_unicast_disabled'


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


def _leadingSpaces(line):
    match = re.match(r'^(\s*)', line)
    if not match:
        return ''
    return match.group(1)


def _findVrrpInstanceBlock(content):
    lines = content.splitlines()
    block_lines = []
    start = -1
    depth = 0
    seen_brace = False
    target = re.compile(r'^\s*vrrp_instance\s+' + VRRP_INSTANCE_NAME + r'\b')

    for idx, line in enumerate(lines):
        if start == -1:
            if target.search(line):
                start = idx
        if start != -1:
            block_lines.append(line)
            brace_delta = line.count('{') - line.count('}')
            if brace_delta > 0:
                seen_brace = True
            depth += brace_delta
            if seen_brace and depth == 0:
                end = idx
                return {'start': start, 'end': end, 'lines': block_lines}
    return None


def _extractBlock(lines, start_idx):
    block = []
    depth = 0
    seen_brace = False
    idx = start_idx
    total = len(lines)
    while idx < total:
        line = lines[idx]
        block.append(line)
        brace_delta = line.count('{') - line.count('}')
        if brace_delta > 0:
            seen_brace = True
        depth += brace_delta
        if seen_brace and depth == 0:
            break
        idx += 1
    return block, idx


def _parseVrrpBlock(block_text):
    data = {
        'interface': '',
        'virtual_ipaddress': '',
        'unicast_src_ip': '',
        'unicast_peer_list': [],
        'priority': '',
        'auth_pass': '',
        'panel_unicast_disabled': VRRP_PANEL_UNICAST_TAG in block_text
    }

    match_interface = re.search(r'^\s*interface\s+([^\s]+)', block_text, re.M)
    if match_interface:
        data['interface'] = match_interface.group(1).strip()

    match_priority = re.search(r'^\s*priority\s+([^\s]+)', block_text, re.M)
    if match_priority:
        data['priority'] = match_priority.group(1).strip()

    match_auth = re.search(r'^\s*auth_pass\s+([^\s]+)', block_text, re.M)
    if match_auth:
        data['auth_pass'] = match_auth.group(1).strip()

    match_vip = re.search(r'virtual_ipaddress\s*{([^}]*)}', block_text, re.S)
    if match_vip:
        lines = match_vip.group(1).splitlines()
        ips = [ip.strip() for ip in lines if ip.strip() != '']
        if ips:
            data['virtual_ipaddress'] = ips[0]

    match_unicast_src = re.search(r'^\s*unicast_src_ip\s+([^\s]+)', block_text, re.M)
    if match_unicast_src:
        data['unicast_src_ip'] = match_unicast_src.group(1).strip()

    match_unicast_peer = re.search(r'unicast_peer\s*{([^}]*)}', block_text, re.S)
    if match_unicast_peer:
        peers = match_unicast_peer.group(1).splitlines()
        peers = [p.strip() for p in peers if p.strip() != '']
        data['unicast_peer_list'] = peers

    data['unicast_enabled'] = (len(data['unicast_peer_list']) > 0 or data['unicast_src_ip'] != '')
    if data['panel_unicast_disabled']:
        data['unicast_enabled'] = False
    return data


def _getVrrpDefaults():
    tpl = getConfTpl()
    if os.path.exists(tpl):
        content = mw.readFile(tpl)
        block = _findVrrpInstanceBlock(content)
        if block:
            block_text = "\n".join(block['lines'])
            return _parseVrrpBlock(block_text)
    return {
        'interface': '',
        'virtual_ipaddress': '',
        'unicast_src_ip': '',
        'unicast_peer_list': [],
        'priority': '',
        'auth_pass': '',
        'unicast_enabled': True,
        'panel_unicast_disabled': False
    }


def _buildPeerBlock(indent, peers):
    block = [indent + 'unicast_peer {']
    inner_indent = indent + '    '
    for peer in peers:
        block.append(inner_indent + peer)
    block.append(indent + '}')
    return block


def _rewriteVrrpBlock(block_lines, values):
    lines = list(block_lines)
    result = []
    i = 0
    interface_index = None
    interface_indent = '    '
    unicast_src_present = False
    unicast_src_index = None
    unicast_peer_present = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith(VRRP_PANEL_UNICAST_TAG):
            i += 1
            continue

        if stripped.startswith('interface '):
            indent = _leadingSpaces(line)
            interface_indent = indent if indent != '' else '    '
            interface_index = len(result)
            result.append(indent + 'interface ' + values['interface'])
            i += 1
            continue

        if stripped.startswith('priority '):
            indent = _leadingSpaces(line)
            result.append(indent + 'priority ' + str(values['priority']))
            i += 1
            continue

        if stripped.startswith('unicast_src_ip'):
            if values['unicast_enabled']:
                indent = _leadingSpaces(line)
                unicast_line = indent + 'unicast_src_ip ' + values['unicast_src_ip']
                result.append(unicast_line)
                unicast_src_present = True
                unicast_src_index = len(result) - 1
            i += 1
            continue

        if stripped.startswith('unicast_peer'):
            block, block_end = _extractBlock(lines, i)
            if values['unicast_enabled']:
                indent = _leadingSpaces(block[0])
                peers_block = _buildPeerBlock(indent, values['unicast_peer_list'])
                result.extend(peers_block)
                unicast_peer_present = True
            i = block_end + 1
            continue

        if stripped.startswith('virtual_ipaddress'):
            block, block_end = _extractBlock(lines, i)
            indent = _leadingSpaces(block[0])
            vip_block = [indent + 'virtual_ipaddress {']
            inner_indent = indent + '    '
            vip_value = values['virtual_ipaddress']
            if vip_value != '':
                vip_block.append(inner_indent + vip_value)
            vip_block.append(indent + '}')
            result.extend(vip_block)
            i = block_end + 1
            continue

        if stripped.startswith('authentication'):
            block, block_end = _extractBlock(lines, i)
            replaced = False
            for idx in range(len(block)):
                if re.match(r'^\s*auth_pass\b', block[idx].strip()):
                    indent = _leadingSpaces(block[idx])
                    block[idx] = indent + 'auth_pass ' + values['auth_pass']
                    replaced = True
                    break
            if not replaced:
                indent = _leadingSpaces(block[0]) + '    '
                block.insert(len(block) - 1, indent + 'auth_pass ' + values['auth_pass'])
            result.extend(block)
            i = block_end + 1
            continue

        result.append(line)
        i += 1

    if values['unicast_enabled']:
        if not unicast_src_present:
            indent = interface_indent
            insert_line = indent + 'unicast_src_ip ' + values['unicast_src_ip']
            insert_pos = interface_index + 1 if interface_index is not None else len(result)
            result.insert(insert_pos, insert_line)
            unicast_src_index = insert_pos

        if not unicast_peer_present:
            indent = interface_indent
            peers_block = _buildPeerBlock(indent, values['unicast_peer_list'])
            if unicast_src_index is not None:
                insert_pos = unicast_src_index + 1
            elif interface_index is not None:
                insert_pos = interface_index + 1
            else:
                insert_pos = len(result)
            for offset, peer_line in enumerate(peers_block):
                result.insert(insert_pos + offset, peer_line)
    else:
        existing_tag = any(VRRP_PANEL_UNICAST_TAG in line for line in result)
        if not existing_tag:
            indent = interface_indent
            insert_pos = interface_index + 1 if interface_index is not None else len(result)
            result.insert(insert_pos, indent + VRRP_PANEL_UNICAST_TAG)

    return result


def _normalizeArg(value):
    if value is None:
        return ''
    return value.replace('\\n', '\n').replace('\\r', '\r')


def _mergeVrrpValues(current, defaults):
    merged = defaults.copy()
    merged['interface'] = current['interface'] or defaults.get('interface', '')
    merged['virtual_ipaddress'] = current['virtual_ipaddress'] or defaults.get('virtual_ipaddress', '')
    merged['unicast_src_ip'] = current['unicast_src_ip'] or ''
    merged['unicast_peer_list'] = current['unicast_peer_list'] if len(current['unicast_peer_list']) > 0 else []
    merged['priority'] = current['priority'] or defaults.get('priority', '')
    merged['auth_pass'] = current['auth_pass'] or defaults.get('auth_pass', '')

    merged['unicast_enabled'] = current['unicast_enabled']
    return merged


def getVrrpForm():
    conf = getConf()
    if not os.path.exists(conf):
        return mw.returnJson(False, '未找到配置文件!')

    content = mw.readFile(conf)
    block = _findVrrpInstanceBlock(content)
    if not block:
        return mw.returnJson(False, '未找到 vrrp_instance ' + VRRP_INSTANCE_NAME + ' 配置块!')

    block_text = "\n".join(block['lines'])
    current = _parseVrrpBlock(block_text)
    defaults = _getVrrpDefaults()
    merged = _mergeVrrpValues(current, defaults)

    data = {
        'interface': merged['interface'],
        'virtual_ipaddress': merged['virtual_ipaddress'],
        'unicast_enabled': True if merged['unicast_enabled'] else False,
        'unicast_src_ip': merged['unicast_src_ip'],
        'unicast_peer_list': "\n".join(merged['unicast_peer_list']),
        'priority': merged['priority'],
        'auth_pass': merged['auth_pass']
    }
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
    unicast_src_ip = _normalizeArg(args.get('unicast_src_ip', '').strip())
    peer_raw = _normalizeArg(args.get('unicast_peer_list', '').strip())
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
    block = _findVrrpInstanceBlock(content)
    if not block:
        return mw.returnJson(False, '未找到 vrrp_instance ' + VRRP_INSTANCE_NAME + ' 配置块!')

    values = {
        'interface': interface,
        'virtual_ipaddress': vip,
        'priority': priority_int,
        'auth_pass': auth_pass,
        'unicast_enabled': unicast_enabled,
        'unicast_src_ip': unicast_src_ip,
        'unicast_peer_list': peer_list
    }

    new_block_lines = _rewriteVrrpBlock(block['lines'], values)
    lines = content.splitlines()
    new_lines = lines[:block['start']] + new_block_lines + lines[block['end'] + 1:]
    new_content = "\n".join(new_lines)
    if content.endswith("\n"):
        new_content += "\n"
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
