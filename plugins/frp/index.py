# coding:utf-8

import sys
import os
import json
import re
import signal
import subprocess
from urllib.parse import unquote

PANEL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(PANEL_ROOT)
sys.path.append(PANEL_ROOT + "/class/core")
sys.path.append(PANEL_ROOT + "/class/plugin")
import mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True

ROLE_META = {
    'server': {
        'mode_key': 'server_mode',
        'single_name': 'frps.ini',
        'dir_name': 'frps.d',
        'tpl_dir': 'server_cfg',
        'binary': 'frps',
        'service_name': 'frps',
    },
    'client': {
        'mode_key': 'client_mode',
        'single_name': 'frpc.ini',
        'dir_name': 'frpc.d',
        'tpl_dir': 'client_cfg',
        'binary': 'frpc',
        'service_name': 'frpc',
    }
}

VALID_MODES = ['single', 'multi']


def getPluginName():
    return 'frp'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getModeFile():
    return getServerDir() + '/config_mode.json'


def getPidDir():
    return getServerDir() + '/run'


def getLogDir():
    return getServerDir() + '/logs'


def getWrapperPath():
    return getServerDir() + '/frp-wrapper.sh'


def getPluginIndexPath():
    return getPluginDir() + '/index.py'


def ensureDir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def getRoleMeta(role):
    return ROLE_META.get(role)


def roleSinglePath(role):
    meta = getRoleMeta(role)
    return getServerDir() + '/' + meta['single_name']


def roleMultiDir(role):
    meta = getRoleMeta(role)
    return getServerDir() + '/' + meta['dir_name']


def roleTemplateDir(role):
    meta = getRoleMeta(role)
    return getPluginDir() + '/' + meta['tpl_dir']


def getRoleBinary(role):
    meta = getRoleMeta(role)
    return getServerDir() + '/' + meta['binary']


def getRolePidPath(role, name):
    safe_name = safeConfigName(name)
    if safe_name is None:
        return ''
    return getPidDir() + '/' + role + '_' + safe_name + '.pid'


def getRoleLogPath(role, name):
    safe_name = safeConfigName(name)
    if safe_name is None:
        return ''
    return getLogDir() + '/' + role + '_' + safe_name + '.log'


def buildDefaultModes():
    return {'server_mode': 'single', 'client_mode': 'single'}


def ensureRuntimeLayout():
    ensureDir(getServerDir())
    ensureDir(getPidDir())
    ensureDir(getLogDir())
    ensureDir(roleMultiDir('server'))
    ensureDir(roleMultiDir('client'))
    mode_data = loadModeData()
    saveModeData(mode_data)


def loadModeData():
    mode_file = getModeFile()
    mode_data = buildDefaultModes()
    if os.path.exists(mode_file):
        try:
            file_data = json.loads(mw.readFile(mode_file))
            if isinstance(file_data, dict):
                for key in mode_data:
                    if file_data.get(key) in VALID_MODES:
                        mode_data[key] = file_data.get(key)
        except Exception:
            pass
    return mode_data


def saveModeData(data):
    mode_data = buildDefaultModes()
    for key in mode_data:
        if data.get(key) in VALID_MODES:
            mode_data[key] = data.get(key)
    mw.writeFile(getModeFile(), json.dumps(mode_data))


def getRoleMode(role):
    meta = getRoleMeta(role)
    return loadModeData().get(meta['mode_key'], 'single')


def setRoleMode(role, mode):
    if mode not in VALID_MODES:
        return False
    mode_data = loadModeData()
    mode_data[getRoleMeta(role)['mode_key']] = mode
    saveModeData(mode_data)
    return True


def safeConfigName(name):
    if name is None:
        return None
    safe_name = name.strip()
    if safe_name == '':
        return None
    if not safe_name.endswith('.ini'):
        safe_name += '.ini'
    if re.match(r'^[A-Za-z0-9_.-]+\.ini$', safe_name) is None:
        return None
    return safe_name


def normalizeText(content):
    if content is None:
        return ''
    if not isinstance(content, str):
        content = str(content)
    content = unquote(content, 'utf-8')
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    content = content.replace('\\n', '\n')
    return content


def getArgs():
    raw = ' '.join(sys.argv[2:]).strip()
    if raw == '':
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    tmp = {}
    args = sys.argv[2:]
    args_len = len(args)
    if args_len == 1:
        t = args[0].strip('{').strip('}')
        if t != '':
            parts = t.split(':', 1)
            if len(parts) == 2:
                tmp[parts[0]] = parts[1]
    elif args_len > 1:
        for i in range(args_len):
            parts = args[i].split(':', 1)
            if len(parts) == 2:
                tmp[parts[0]] = parts[1]
    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if ck[i] not in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def contentReplace(content):
    service_path = mw.getServerDir()
    content = content.replace('{$ROOT_PATH}', mw.getRootDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$SERVER_APP}', service_path + '/frp')
    content = content.replace('{$PLUGIN_PATH}', getPluginDir())
    content = content.replace('{$PYTHON_BIN}', '/usr/bin/python3')
    return content


def getTemplateList(role):
    path = roleTemplateDir(role)
    path_file = os.listdir(path)
    tmp = []
    for one in path_file:
        file = path + '/' + one
        tmp.append(file)
    return tmp


def readConfigTpl():
    args = getArgs()
    data = checkArgs(args, ['file'])
    if not data[0]:
        return data[1]

    content = mw.readFile(args['file'])
    content = contentReplace(content)
    return mw.returnJson(True, 'ok', content)


def readFile(path):
    if not os.path.exists(path):
        return ''
    return mw.readFile(path)


def writeFile(path, content):
    ensureDir(os.path.dirname(path))
    mw.writeFile(path, normalizeText(content))


def getConfigModes():
    ensureRuntimeLayout()
    data = {
        'server_mode': getRoleMode('server'),
        'client_mode': getRoleMode('client'),
        'server_single_path': roleSinglePath('server'),
        'client_single_path': roleSinglePath('client'),
        'server_multi_dir': roleMultiDir('server'),
        'client_multi_dir': roleMultiDir('client'),
    }
    return mw.returnJson(True, 'ok', data)


def setConfigMode():
    ensureRuntimeLayout()
    args = getArgs()
    data = checkArgs(args, ['role', 'mode'])
    if not data[0]:
        return data[1]

    role = args['role']
    mode = args['mode']
    if role not in ROLE_META:
        return mw.returnJson(False, '角色错误')
    if mode not in VALID_MODES:
        return mw.returnJson(False, '模式错误')

    setRoleMode(role, mode)
    return mw.returnJson(True, '切换成功', {
        'role': role,
        'mode': mode,
    })


def getRoleConfigPath(role, name=''):
    if role not in ROLE_META:
        return ''
    if getRoleMode(role) == 'single':
        return roleSinglePath(role)
    safe_name = safeConfigName(name)
    if safe_name is None:
        return ''
    return roleMultiDir(role) + '/' + safe_name


def listConfigFiles():
    ensureRuntimeLayout()
    args = getArgs()
    data = checkArgs(args, ['role'])
    if not data[0]:
        return data[1]

    role = args['role']
    if role not in ROLE_META:
        return mw.returnJson(False, '角色错误')

    mode = getRoleMode(role)
    result = {
        'role': role,
        'mode': mode,
        'single_path': roleSinglePath(role),
        'multi_dir': roleMultiDir(role),
        'items': []
    }

    if mode == 'single':
        path = roleSinglePath(role)
        result['items'].append({
            'name': os.path.basename(path),
            'path': path,
            'exists': os.path.exists(path),
            'active': True,
        })
    else:
        path = roleMultiDir(role)
        path_file = sorted(os.listdir(path))
        for one in path_file:
            if safeConfigName(one) is None:
                continue
            file_path = path + '/' + one
            if not os.path.isfile(file_path):
                continue
            result['items'].append({
                'name': one,
                'path': file_path,
                'exists': True,
                'active': True,
            })
    return mw.returnJson(True, 'ok', result)


def getConfigFile():
    ensureRuntimeLayout()
    args = getArgs()
    data = checkArgs(args, ['role'])
    if not data[0]:
        return data[1]

    role = args['role']
    name = args.get('name', '')
    if role not in ROLE_META:
        return mw.returnJson(False, '角色错误')

    path = getRoleConfigPath(role, name)
    if path == '':
        return mw.returnJson(False, '配置文件名错误')

    if not os.path.exists(path):
        if getRoleMode(role) == 'single':
            return mw.returnJson(True, 'ok', {
                'role': role,
                'mode': getRoleMode(role),
                'name': os.path.basename(path),
                'path': path,
                'content': '',
            })
        return mw.returnJson(False, '配置文件不存在')

    return mw.returnJson(True, 'ok', {
        'role': role,
        'mode': getRoleMode(role),
        'name': os.path.basename(path),
        'path': path,
        'content': readFile(path),
    })


def saveConfigFile():
    ensureRuntimeLayout()
    args = getArgs()
    data = checkArgs(args, ['role', 'content'])
    if not data[0]:
        return data[1]

    role = args['role']
    name = args.get('name', '')
    template_file = args.get('template', '')
    content = normalizeText(args['content'])

    if role not in ROLE_META:
        return mw.returnJson(False, '角色错误')

    mode = getRoleMode(role)
    if mode == 'single':
        path = roleSinglePath(role)
        writeFile(path, content)
        return mw.returnJson(True, '保存成功', {
            'path': path,
            'name': os.path.basename(path),
        })

    safe_name = safeConfigName(name)
    if safe_name is None:
        return mw.returnJson(False, '文件名不合法')

    if content.strip() == '' and template_file != '':
        content = normalizeText(readFile(template_file))
        content = contentReplace(content)

    if content.strip() == '':
        return mw.returnJson(False, '配置内容不能为空')

    path = roleMultiDir(role) + '/' + safe_name
    writeFile(path, content)
    return mw.returnJson(True, '保存成功', {
        'path': path,
        'name': safe_name,
    })


def createConfigFile():
    ensureRuntimeLayout()
    args = getArgs()
    data = checkArgs(args, ['role', 'name'])
    if not data[0]:
        return data[1]

    role = args['role']
    if role not in ROLE_META:
        return mw.returnJson(False, '角色错误')
    if getRoleMode(role) != 'multi':
        return mw.returnJson(False, '当前不是多配置模式')

    safe_name = safeConfigName(args['name'])
    if safe_name is None:
        return mw.returnJson(False, '文件名不合法')

    path = roleMultiDir(role) + '/' + safe_name
    if os.path.exists(path):
        return mw.returnJson(False, '配置文件已存在')

    content = normalizeText(args.get('content', ''))
    template_file = args.get('template', '')
    if content.strip() == '' and template_file != '':
        content = contentReplace(readFile(template_file))
    if content.strip() == '':
        content = '# new config\n'
    writeFile(path, content)
    return mw.returnJson(True, '创建成功', {
        'path': path,
        'name': safe_name,
    })


def deleteConfigFile():
    ensureRuntimeLayout()
    args = getArgs()
    data = checkArgs(args, ['role', 'name'])
    if not data[0]:
        return data[1]

    role = args['role']
    if role not in ROLE_META:
        return mw.returnJson(False, '角色错误')
    if getRoleMode(role) != 'multi':
        return mw.returnJson(False, '单配置模式下不允许删除主配置')

    safe_name = safeConfigName(args['name'])
    if safe_name is None:
        return mw.returnJson(False, '文件名不合法')

    path = roleMultiDir(role) + '/' + safe_name
    if not os.path.exists(path):
        return mw.returnJson(False, '配置文件不存在')

    os.remove(path)
    pid_path = getRolePidPath(role, safe_name)
    if pid_path != '' and os.path.exists(pid_path):
        os.remove(pid_path)
    return mw.returnJson(True, '删除成功')


def frpServerCfg():
    ensureRuntimeLayout()
    return roleSinglePath('server')


def frpServerCfgTpl():
    return mw.getJson(getTemplateList('server'))


def frpClientCfg():
    ensureRuntimeLayout()
    return roleSinglePath('client')


def frpClientCfgTpl():
    return mw.getJson(getTemplateList('client'))


def getRoleProcessIds(role):
    binary_name = getRoleMeta(role)['binary']
    cmd = "ps -ef|grep '{0}' |grep -v grep | grep '{1}' | awk '{{print $2}}'".format(
        binary_name,
        getServerDir() + '/'
    )
    data = mw.execShell(cmd)
    output = data[0].strip()
    if output == '':
        return []
    result = []
    for line in output.split('\n'):
        line = line.strip()
        if line != '':
            result.append(line)
    return result


def isRoleRunning(role):
    return len(getRoleProcessIds(role)) > 0


def status():
    if isRoleRunning('server') or isRoleRunning('client'):
        return 'start'
    return 'stop'


def stopRole(role):
    pids = getRoleProcessIds(role)
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except Exception:
            pass
    if len(pids) > 0:
        mw.execShell('sleep 1')
    pids = getRoleProcessIds(role)
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGKILL)
        except Exception:
            pass
    pid_path_dir = getPidDir()
    if os.path.exists(pid_path_dir):
        for one in os.listdir(pid_path_dir):
            if one.startswith(role + '_') and one.endswith('.pid'):
                try:
                    os.remove(pid_path_dir + '/' + one)
                except Exception:
                    pass
    return True


def writePidFile(role, config_name, pid):
    pid_path = getRolePidPath(role, config_name)
    if pid_path == '':
        return
    mw.writeFile(pid_path, str(pid))


def startSingleConfig(role, config_path):
    binary_path = getRoleBinary(role)
    if not os.path.exists(binary_path):
        return (False, '启动文件不存在: ' + binary_path)
    if not os.path.exists(config_path):
        return (False, '配置文件不存在: ' + config_path)

    config_name = os.path.basename(config_path)
    log_path = getRoleLogPath(role, config_name)
    log_fp = open(log_path, 'a')
    process = subprocess.Popen(
        [binary_path, '-c', config_path],
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        cwd=getServerDir(),
        preexec_fn=os.setsid
    )
    writePidFile(role, config_name, process.pid)
    return (True, '')


def getMultiConfigPaths(role):
    path = roleMultiDir(role)
    result = []
    if not os.path.exists(path):
        return result
    for one in sorted(os.listdir(path)):
        safe_name = safeConfigName(one)
        if safe_name is None:
            continue
        file_path = path + '/' + safe_name
        if os.path.isfile(file_path):
            result.append(file_path)
    return result


def startRole(role):
    ensureRuntimeLayout()
    mode = getRoleMode(role)
    stopRole(role)

    if mode == 'single':
        ok, msg = startSingleConfig(role, roleSinglePath(role))
        if not ok:
            return msg
        return 'ok'

    config_paths = getMultiConfigPaths(role)
    if len(config_paths) == 0:
        return '多配置目录为空，请先创建配置文件'

    for config_path in config_paths:
        ok, msg = startSingleConfig(role, config_path)
        if not ok:
            stopRole(role)
            return msg
    return 'ok'


def serviceRoleAction(role, action):
    if role not in ROLE_META:
        return '角色错误'
    if action == 'start':
        return startRole(role)
    if action == 'stop':
        stopRole(role)
        return 'ok'
    if action == 'restart' or action == 'reload':
        stopRole(role)
        return startRole(role)
    if action == 'status':
        return 'start' if isRoleRunning(role) else 'stop'
    return '操作错误'


def initDreplace():
    ensureRuntimeLayout()

    initD_path = getServerDir() + '/init.d'
    ensureDir(initD_path)

    file_bin = initD_path + '/' + getPluginName()
    file_tpl = getPluginDir() + "/init.d/frp.service.tpl"
    content = mw.readFile(file_tpl)
    content = contentReplace(content)
    mw.writeFile(file_bin, content)
    mw.execShell('chmod +x ' + file_bin)

    wrapper_path = getWrapperPath()
    wrapper_tpl = getPluginDir() + '/init.d/frp-wrapper.tpl'
    wrapper_content = mw.readFile(wrapper_tpl)
    wrapper_content = contentReplace(wrapper_content)
    mw.writeFile(wrapper_path, wrapper_content)
    mw.execShell('chmod +x ' + wrapper_path)

    systemDir = mw.systemdCfgDir()
    service_path = mw.getServerDir()
    if os.path.exists(systemDir):
        for role in ROLE_META:
            systemService = systemDir + '/' + getRoleMeta(role)['service_name'] + '.service'
            systemServiceTpl = getPluginDir() + '/init.d/' + getRoleMeta(role)['service_name'] + '.service.tpl'
            tpl = mw.readFile(systemServiceTpl)
            tpl = tpl.replace('{$SERVER_PATH}', service_path)
            tpl = tpl.replace('{$WRAPPER_PATH}', wrapper_path)
            mw.writeFile(systemService, tpl)
        mw.execShell('systemctl daemon-reload')


def ftOp(method):
    initDreplace()

    if mw.isAppleSystem():
        cmd = getServerDir() + '/init.d/frp ' + method + " &"
        data = mw.execShell(cmd)
        if len(data) > 1 and data[1] != '':
            return data[1]
        return 'ok'

    for role in ['server', 'client']:
        cmd = 'systemctl ' + method + ' ' + getRoleMeta(role)['service_name']
        data = mw.execShell(cmd)
        if len(data) > 1 and data[1] != '':
            err = data[1].strip()
            if err != '':
                return err
    return 'ok'


def start():
    return ftOp('start')


def stop():
    return ftOp('stop')


def restart():
    return ftOp('restart')


def reload():
    return ftOp('reload')


def initdStatus():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    for role in ['server', 'client']:
        cmd = 'systemctl status ' + getRoleMeta(role)['service_name'] + ' | grep loaded | grep "enabled;"'
        data = mw.execShell(cmd)
        if data[0] == '':
            return 'fail'
    return 'ok'


def initdInstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    initDreplace()
    for role in ['server', 'client']:
        mw.execShell('systemctl enable ' + getRoleMeta(role)['service_name'])
    return 'ok'


def initdUinstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    for role in ['server', 'client']:
        mw.execShell('systemctl disable ' + getRoleMeta(role)['service_name'])
    return 'ok'


def serviceRunner():
    role = sys.argv[2]
    action = sys.argv[3]
    result = serviceRoleAction(role, action)
    print(result)
    if action == 'status':
        if result in ['start', 'stop']:
            return
        sys.exit(1)
    if result != 'ok':
        sys.exit(1)


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
    elif func == 'read_config_tpl':
        print(readConfigTpl())
    elif func == 'frp_server':
        print(frpServerCfg())
    elif func == 'frp_server_tpl':
        print(frpServerCfgTpl())
    elif func == 'frp_client':
        print(frpClientCfg())
    elif func == 'frp_client_tpl':
        print(frpClientCfgTpl())
    elif func == 'get_config_modes':
        print(getConfigModes())
    elif func == 'set_config_mode':
        print(setConfigMode())
    elif func == 'list_config_files':
        print(listConfigFiles())
    elif func == 'get_config_file':
        print(getConfigFile())
    elif func == 'save_config_file':
        print(saveConfigFile())
    elif func == 'create_config_file':
        print(createConfigFile())
    elif func == 'delete_config_file':
        print(deleteConfigFile())
    elif func == 'service_runner':
        serviceRunner()
    else:
        print('error')
