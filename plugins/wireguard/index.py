# coding:utf-8

import sys
import os
import time
import re
import json
import shutil
import shlex
import ipaddress
import glob
from urllib.parse import unquote

sys.path.append(os.getcwd() + "/class/core")
import mw

PLUGIN_PATH = os.path.dirname(__file__)
if PLUGIN_PATH not in sys.path:
    sys.path.append(PLUGIN_PATH)

app_debug = False
if mw.isAppleSystem():
    app_debug = True

WG_DIR = "/etc/wireguard"
DEFAULT_INTERFACE = "wg0"


def getPluginName():
    return 'wireguard'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getInitDFile():
    if app_debug:
        return '/tmp/' + getPluginName()
    return '/etc/init.d/' + getPluginName()


def getArgs():
    args = sys.argv[3:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        if t.strip() == '':
            tmp = {}
        else:
            t = t.split(':', 1)
            tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':', 1)
            tmp[t[0]] = t[1]
    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def getTextArg(arg, space_plus=True):
    args = getArgs()
    if arg not in args:
        return ''
    value = unquote(args[arg], 'utf-8')
    if space_plus:
        value = value.replace('+', ' ')
    return value.replace("\r\n", "\n").replace("\\n", "\n")


def _command_exists(cmd):
    return shutil.which(cmd) is not None


def _ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _safe_iface_name(name):
    if not name:
        return None
    if not re.match(r'^[A-Za-z0-9_.-]+$', name):
        return None
    return name


def _config_path(iface):
    safe = _safe_iface_name(iface)
    if not safe:
        return None
    return os.path.join(WG_DIR, safe + '.conf')


def _key_paths(iface):
    safe = _safe_iface_name(iface)
    if not safe:
        return (None, None)
    return (
        os.path.join(WG_DIR, safe + '.private'),
        os.path.join(WG_DIR, safe + '.public')
    )


def _fallback_key_paths():
    return (
        os.path.join(WG_DIR, 'privatekey'),
        os.path.join(WG_DIR, 'publickey')
    )


def _read_default_private_key(iface=None):
    private_path, _ = _fallback_key_paths()
    key = _read_key_file(private_path)
    if key:
        return key
    if iface:
        iface_private, _ = _key_paths(iface)
        return _read_key_file(iface_private)
    return ''


def _read_default_public_key(iface=None):
    _, public_path = _fallback_key_paths()
    key = _read_key_file(public_path)
    if key:
        return key
    if iface:
        _, iface_public = _key_paths(iface)
        return _read_key_file(iface_public)
    return ''


def _read_key_file(path):
    if not path or not os.path.exists(path):
        return ''
    return mw.readFile(path).strip()


def _write_key_file(path, value):
    _ensure_dir(os.path.dirname(path))
    mw.writeFile(path, value + "\n")
    os.chmod(path, 0o600)


def _backup_file(path):
    if not os.path.exists(path):
        return ''
    ts = time.strftime('%Y%m%d_%H%M%S')
    backup_path = path + '.bak.' + ts
    shutil.copy2(path, backup_path)
    try:
        backups = sorted(glob.glob(path + '.bak.*'), reverse=True)
        for old in backups[3:]:
            try:
                os.remove(old)
            except Exception:
                pass
    except Exception:
        pass
    return backup_path


def _normalize_config_content(content):
    if not isinstance(content, str):
        return content
    if '\n' not in content and '\\n' in content:
        content = content.replace('\\r\\n', '\n')
        content = content.replace('\\n', '\n')
    if '\r\n' in content:
        content = content.replace('\r\n', '\n')
    return content


def _interface_up(iface):
    if not iface:
        return False
    out, err, rc = mw.execShell('ip link show ' + iface)
    return rc == 0


def _service_enabled(iface):
    if not _command_exists('systemctl'):
        return False
    if not iface:
        return False
    out, err, rc = mw.execShell('systemctl is-enabled wg-quick@' + iface)
    return (out or '').strip() == 'enabled'


def _wg_quick_action(iface, action):
    if not iface:
        return '接口名为空'
    if not _command_exists('wg-quick'):
        if not _command_exists('systemctl'):
            return '未找到 wg-quick 命令'
        if action == 'start':
            out, err, rc = mw.execShell('systemctl start wg-quick@' + iface)
        elif action == 'stop':
            out, err, rc = mw.execShell('systemctl stop wg-quick@' + iface)
        else:
            out, err, rc = mw.execShell('systemctl stop wg-quick@' + iface + ' && systemctl start wg-quick@' + iface)
        if rc == 0:
            return 'ok'
        return (err or out or '执行失败').strip()
    if action == 'start':
        out, err, rc = mw.execShell('wg-quick up ' + iface)
    elif action == 'stop':
        out, err, rc = mw.execShell('wg-quick down ' + iface)
    else:
        out, err, rc = mw.execShell('wg-quick down ' + iface + ' && wg-quick up ' + iface)
    if rc == 0:
        return 'ok'
    return (err or out or '执行失败').strip()


def status():
    if not _command_exists('wg'):
        return 'stop'
    iface = DEFAULT_INTERFACE
    return 'start' if _interface_up(iface) else 'stop'


def start():
    return _wg_quick_action(DEFAULT_INTERFACE, 'start')


def stop():
    return _wg_quick_action(DEFAULT_INTERFACE, 'stop')


def restart():
    return _wg_quick_action(DEFAULT_INTERFACE, 'restart')


def reload():
    return restart()


def initdStatus():
    if mw.isAppleSystem():
        return "Apple Computer does not support"
    return 'ok' if _service_enabled(DEFAULT_INTERFACE) else 'fail'


def initdInstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"
    if _command_exists('systemctl'):
        mw.execShell('systemctl enable wg-quick@' + DEFAULT_INTERFACE)
    return 'ok'


def initdUinstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"
    if _command_exists('systemctl'):
        mw.execShell('systemctl disable wg-quick@' + DEFAULT_INTERFACE)
    return 'ok'


def installWireguard():
    script = os.path.join(getPluginDir(), 'install.sh')
    if not os.path.exists(script):
        return mw.returnJson(False, '未找到安装脚本')
    out, err, rc = mw.execShell('bash ' + script + ' install 1.0')
    msg = (out or err or '').strip() or 'ok'
    return mw.returnJson(rc == 0, msg)


def uninstallWireguard():
    script = os.path.join(getPluginDir(), 'install.sh')
    if not os.path.exists(script):
        return mw.returnJson(False, '未找到卸载脚本')
    out, err, rc = mw.execShell('bash ' + script + ' uninstall')
    msg = (out or err or '').strip() or 'ok'
    return mw.returnJson(rc == 0, msg)


def _validate_ip_interface(value, field_name):
    try:
        ipaddress.ip_interface(value)
        return None
    except Exception:
        return field_name + ' 格式错误'


def _validate_port(value, field_name):
    if value == '' or value is None:
        return None
    try:
        port = int(value)
        if port < 1 or port > 65535:
            return field_name + ' 超出范围'
    except Exception:
        return field_name + ' 格式错误'
    return None


def _split_allowed(value):
    if not value:
        return []
    parts = re.split(r'[\s,]+', value.strip())
    return [p for p in parts if p]


def _validate_allowed_ips(value, field_name):
    for item in _split_allowed(value):
        try:
            ipaddress.ip_network(item, strict=False)
        except Exception:
            return field_name + ' 包含无效网段: ' + item
    return None


def _validate_key(value, field_name):
    if not value:
        return field_name + ' 不能为空'
    if not re.match(r'^[A-Za-z0-9+/=]{42,64}$', value.strip()):
        return field_name + ' 格式不正确'
    return None


def _parse_conf(content):
    data = {
        'address': '',
        'listen_port': '',
        'private_key': '',
        'post_up': [],
        'post_down': [],
        'peers': []
    }
    section = ''
    current_peer = None
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue
        if line.startswith('[') and line.endswith(']'):
            section = line.strip('[]').strip().lower()
            if section == 'peer':
                current_peer = {}
                data['peers'].append(current_peer)
            else:
                current_peer = None
            continue
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip().lower()
        value = value.strip()
        if section == 'interface':
            if key == 'address':
                data['address'] = value
            elif key == 'listenport':
                data['listen_port'] = value
            elif key == 'privatekey':
                data['private_key'] = value
            elif key == 'postup':
                data['post_up'].append(value)
            elif key == 'postdown':
                data['post_down'].append(value)
        elif section == 'peer' and current_peer is not None:
            if key == 'publickey':
                current_peer['public_key'] = value
            elif key == 'allowedips':
                current_peer['allowed_ips'] = value
            elif key == 'endpoint':
                current_peer['endpoint'] = value
            elif key == 'persistentkeepalive':
                current_peer['persistent_keepalive'] = value
    return data


def _get_latest_handshake(iface):
    if not _command_exists('wg'):
        return ''
    out, err, rc = mw.execShell('wg show ' + iface + ' latest-handshakes')
    if rc != 0:
        return ''
    latest_ts = 0
    for line in (out or '').splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            ts = int(parts[1])
            if ts > latest_ts:
                latest_ts = ts
        except Exception:
            continue
    if latest_ts <= 0:
        return ''
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest_ts))


def listConfigs():
    items = []
    if not os.path.exists(WG_DIR):
        return mw.returnJson(True, 'ok', items)
    for file in sorted([f for f in os.listdir(WG_DIR) if f.endswith('.conf')]):
        path = os.path.join(WG_DIR, file)
        content = mw.readFile(path)
        parsed = _parse_conf(content)
        iface = file[:-5]
        items.append({
            'name': iface,
            'path': path,
            'address': parsed.get('address', ''),
            'listen_port': parsed.get('listen_port', ''),
            'peer_count': len(parsed.get('peers', [])),
            'interface_up': _interface_up(iface),
            'last_handshake': _get_latest_handshake(iface)
        })
    return mw.returnJson(True, 'ok', items)


def getConfig():
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]
    name = args['name'].strip()
    path = _config_path(name)
    if not path or not os.path.exists(path):
        return mw.returnJson(False, '配置文件不存在')
    return mw.returnJson(True, 'ok', mw.readFile(path))


def saveConfig():
    args = getArgs()
    data = checkArgs(args, ['name', 'content'])
    if not data[0]:
        return data[1]
    name = args['name'].strip()
    content = getTextArg('content', False)
    path = _config_path(name)
    if not path:
        return mw.returnJson(False, '接口名称不合法')
    if '[Interface]' not in content:
        return mw.returnJson(False, '配置必须包含 [Interface] 段')
    _ensure_dir(WG_DIR)
    backup = _backup_file(path)
    mw.writeFile(path, content)
    os.chmod(path, 0o600)
    return mw.returnJson(True, '保存成功', {'backup': backup})


def deleteConfig():
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]
    name = args['name'].strip()
    path = _config_path(name)
    if not path or not os.path.exists(path):
        return mw.returnJson(False, '配置文件不存在')
    backup = _backup_file(path)
    os.remove(path)
    return mw.returnJson(True, '删除成功', {'backup': backup})


def applyConfig():
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]
    name = args['name'].strip()
    path = _config_path(name)
    if not path or not os.path.exists(path):
        return mw.returnJson(False, '配置文件不存在')
    result = _wg_quick_action(name, 'restart')
    if result == 'ok':
        return mw.returnJson(True, '重启成功')
    return mw.returnJson(False, result)


def startConfig():
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]
    name = args['name'].strip()
    path = _config_path(name)
    if not path or not os.path.exists(path):
        return mw.returnJson(False, '配置文件不存在')
    result = _wg_quick_action(name, 'start')
    if result == 'ok':
        return mw.returnJson(True, '启用成功')
    return mw.returnJson(False, result)


def stopConfig():
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]
    name = args['name'].strip()
    path = _config_path(name)
    if not path or not os.path.exists(path):
        return mw.returnJson(False, '配置文件不存在')
    result = _wg_quick_action(name, 'stop')
    if result == 'ok':
        return mw.returnJson(True, '停用成功')
    return mw.returnJson(False, result)


def _generate_keypair():
    if not _command_exists('wg'):
        return ('', '', '未检测到 wg 命令')
    out, err, rc = mw.execShell('wg genkey')
    private_key = (out or '').strip()
    if rc != 0 or not private_key:
        return ('', '', '生成私钥失败')
    out, err, rc = mw.execShell("printf '%s' " + shlex.quote(private_key) + " | wg pubkey")
    public_key = (out or '').strip()
    if rc != 0 or not public_key:
        return ('', '', '生成公钥失败')
    return (private_key, public_key, '')


def generateKeypair():
    private_key, public_key, err = _generate_keypair()
    if err:
        return mw.returnJson(False, err)
    private_path, public_path = _fallback_key_paths()
    _write_key_file(private_path, private_key)
    _write_key_file(public_path, public_key)
    return mw.returnJson(True, '生成成功', {'public_key': public_key, 'private_key': private_key})


def getKeyInfo():
    private_key = _read_default_private_key(DEFAULT_INTERFACE)
    public_key = _read_default_public_key(DEFAULT_INTERFACE)
    data = {
        'public_key': public_key,
        'has_private': bool(private_key)
    }
    if private_key:
        data['private_key'] = private_key
    return mw.returnJson(True, 'ok', data)


def _build_config(interface, address, listen_port, private_key, post_up, post_down, peer):
    lines = ['[Interface]']
    lines.append('PrivateKey = ' + private_key)
    lines.append('Address = ' + address)
    if listen_port:
        lines.append('ListenPort = ' + str(listen_port))
    for item in post_up:
        lines.append('PostUp = ' + item)
    for item in post_down:
        lines.append('PostDown = ' + item)
    if peer:
        lines.append('')
        lines.append('[Peer]')
        lines.append('PublicKey = ' + peer['public_key'])
        if peer.get('allowed_ips'):
            lines.append('AllowedIPs = ' + peer['allowed_ips'])
        if peer.get('endpoint'):
            lines.append('Endpoint = ' + peer['endpoint'])
        if peer.get('persistent_keepalive'):
            lines.append('PersistentKeepalive = ' + str(peer['persistent_keepalive']))
    return "\n".join(lines) + "\n"


def _default_post_rules(iface):
    return (
        [
            'sysctl -w net.ipv4.ip_forward=1',
            'iptables -A FORWARD -i ' + iface + ' -j ACCEPT',
            'iptables -A FORWARD -o ' + iface + ' -j ACCEPT'
        ],
        [
            'iptables -D FORWARD -i ' + iface + ' -j ACCEPT',
            'iptables -D FORWARD -o ' + iface + ' -j ACCEPT'
        ]
    )


def createConfig():
    args = getArgs()
    required = ['iface', 'address', 'peer_public_key', 'peer_allowed_ips']
    data = checkArgs(args, required)
    if not data[0]:
        return data[1]
    iface = args['iface'].strip()
    address = args['address'].strip()
    listen_port = args.get('listen_port', '').strip()
    private_key = args.get('private_key', '').strip()
    auto_gen = str(args.get('auto_gen_key', '1')).lower() in ['1', 'true', 'yes', 'on']
    peer_public_key = args['peer_public_key'].strip()
    peer_allowed = args['peer_allowed_ips'].strip()
    peer_endpoint = args.get('peer_endpoint', '').strip()
    peer_keepalive = args.get('peer_keepalive', '').strip()
    enable_forward = str(args.get('enable_forward', '1')).lower() in ['1', 'true', 'yes', 'on']

    if not _safe_iface_name(iface):
        return mw.returnJson(False, '接口名称不合法')
    err = _validate_ip_interface(address, '接口地址')
    if err:
        return mw.returnJson(False, err)
    err = _validate_port(listen_port, '监听端口')
    if err:
        return mw.returnJson(False, err)
    err = _validate_key(peer_public_key, '对端公钥')
    if err:
        return mw.returnJson(False, err)
    err = _validate_allowed_ips(peer_allowed, 'AllowedIPs')
    if err:
        return mw.returnJson(False, err)

    if not private_key:
        private_key = _read_default_private_key(iface)
    if not private_key and auto_gen:
        private_key, public_key, err = _generate_keypair()
        if err:
            return mw.returnJson(False, err)
        private_path, public_path = _fallback_key_paths()
        _write_key_file(private_path, private_key)
        _write_key_file(public_path, public_key)
    if not private_key:
        return mw.returnJson(False, '未找到私钥，请先初始化密钥')

    post_up = []
    post_down = []
    if enable_forward:
        post_up, post_down = _default_post_rules(iface)

    if peer_endpoint and ':' not in peer_endpoint and listen_port:
        peer_endpoint = peer_endpoint + ':' + str(listen_port)

    peer = {
        'public_key': peer_public_key,
        'allowed_ips': ','.join(_split_allowed(peer_allowed)),
        'endpoint': peer_endpoint,
        'persistent_keepalive': peer_keepalive
    }

    content = _build_config(iface, address, listen_port, private_key, post_up, post_down, peer)

    path = _config_path(iface)
    if not path:
        return mw.returnJson(False, '接口名称不合法')
    _ensure_dir(WG_DIR)
    backup = _backup_file(path)
    mw.writeFile(path, content)
    os.chmod(path, 0o600)
    return mw.returnJson(True, '创建成功', {'backup': backup, 'path': path})


def getWizardDefaults():
    iface = DEFAULT_INTERFACE
    address = '10.0.0.1/24'
    listen_port = '51820'
    public_key = ''
    try:
        data = json.loads(getKeyInfo())
        public_key = data.get('data', {}).get('public_key', '')
    except Exception:
        public_key = ''
    data = {
        'interface': iface,
        'address': address,
        'listen_port': listen_port,
        'public_key': public_key
    }
    return mw.returnJson(True, 'ok', data)


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
    elif func == 'install_wireguard':
        print(installWireguard())
    elif func == 'uninstall_wireguard':
        print(uninstallWireguard())
    elif func == 'list_configs':
        print(listConfigs())
    elif func == 'get_config':
        print(getConfig())
    elif func == 'save_config':
        print(saveConfig())
    elif func == 'delete_config':
        print(deleteConfig())
    elif func == 'apply_config':
        print(applyConfig())
    elif func == 'start_config':
        print(startConfig())
    elif func == 'stop_config':
        print(stopConfig())
    elif func == 'generate_keypair':
        print(generateKeypair())
    elif func == 'get_key_info':
        print(getKeyInfo())
    elif func == 'create_config':
        print(createConfig())
    elif func == 'get_wizard_defaults':
        print(getWizardDefaults())
    else:
        print('error')
