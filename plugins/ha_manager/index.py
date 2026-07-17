# coding:utf-8

import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
import ipaddress

sys.path.append(os.getcwd() + "/class/core")
import mw

PLUGIN_NAME = 'ha_manager'
SERVER_DIR_NAME = 'ha_manager'
DATA_DIR = mw.getServerDir() + '/' + SERVER_DIR_NAME
CONFIG_PATH = DATA_DIR + '/config.json'
SSH_DIR = '/root/.ssh'
PRIVATE_KEY_PATH = SSH_DIR + '/ha_manager'
PUBLIC_KEY_PATH = SSH_DIR + '/ha_manager.pub'
AUTHORIZED_KEYS_PATH = SSH_DIR + '/authorized_keys'
MYSQL_APT_INDEX = '/www/server/jh-panel/plugins/mysql-apt/index.py'
DEFAULT_SSH_USER = 'root'
DEFAULT_SSH_PORT = 22


def getPluginName():
    return PLUGIN_NAME


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return DATA_DIR


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    for item in args:
        item = item.strip()
        if not item:
            continue
        if item.startswith('{') and item.endswith('}'):
            item = item[1:-1]
        if ':' not in item:
            continue
        key, value = item.split(':', 1)
        tmp[key] = value
    return tmp


def checkArgs(data, ck=[]):
    for item in ck:
        if item not in data:
            return (False, mw.returnJson(False, '参数:(' + item + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def _ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _default_config():
    now = int(time.time())
    return {
        'relation_id': '',
        'peer_ip': '',
        'ssh_user': DEFAULT_SSH_USER,
        'ssh_port': DEFAULT_SSH_PORT,
        'peer_ssh_public_key': '',
        'configured_role': '',
        'connection_status': 'pending',
        'connection_checked_at': 0,
        'connection_msg': '',
        'switch_state': 'normal',
        'switch_started_at': 0,
        'switch_failed_at': 0,
        'last_peer_result': {},
        'checks': {},
        'updated_at': now,
        'created_at': now,
    }


def _normalize_config(data):
    base = _default_config()
    if not isinstance(data, dict):
        return base
    base.update({
        'relation_id': str(data.get('relation_id', '') or '').strip(),
        'peer_ip': str(data.get('peer_ip', '') or '').strip(),
        'ssh_user': str(data.get('ssh_user', DEFAULT_SSH_USER) or DEFAULT_SSH_USER).strip() or DEFAULT_SSH_USER,
        'ssh_port': _safe_int(data.get('ssh_port', DEFAULT_SSH_PORT), DEFAULT_SSH_PORT),
        'peer_ssh_public_key': str(data.get('peer_ssh_public_key', '') or '').strip(),
        'configured_role': str(data.get('configured_role', '') or '').strip(),
        'connection_status': str(data.get('connection_status', 'pending') or 'pending').strip(),
        'connection_checked_at': _safe_int(data.get('connection_checked_at', 0), 0),
        'connection_msg': str(data.get('connection_msg', '') or '').strip(),
        'switch_state': str(data.get('switch_state', 'normal') or 'normal').strip(),
        'switch_started_at': _safe_int(data.get('switch_started_at', 0), 0),
        'switch_failed_at': _safe_int(data.get('switch_failed_at', 0), 0),
        'last_peer_result': data.get('last_peer_result') or {},
        'checks': data.get('checks') or {},
    })
    if 'updated_at' in data:
        base['updated_at'] = _safe_int(data.get('updated_at'), base['updated_at'])
    if 'created_at' in data:
        base['created_at'] = _safe_int(data.get('created_at'), base['created_at'])
    return base


def _safe_int(value, default=0):
    try:
        if value is None or value == '':
            return default
        return int(value)
    except Exception:
        return default


def _load_config():
    _ensure_dir(getServerDir())
    if not os.path.exists(CONFIG_PATH):
        config = _default_config()
        _write_config(config)
        return config
    content = mw.readFile(CONFIG_PATH)
    if not content:
        config = _default_config()
        _write_config(config)
        return config
    try:
        data = json.loads(content)
    except Exception:
        data = {}
    return _normalize_config(data)


def _write_config(config):
    _ensure_dir(getServerDir())
    config = _normalize_config(config)
    config['updated_at'] = int(time.time())
    mw.writeFile(CONFIG_PATH, json.dumps(config, ensure_ascii=False, indent=2))
    return config


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['1', 'true', 'yes', 'on']
    return bool(value)


def _validate_config_fields(data):
    relation_id = str(data.get('relation_id', '') or '').strip()
    peer_ip = str(data.get('peer_ip', '') or '').strip()
    ssh_user = str(data.get('ssh_user', DEFAULT_SSH_USER) or DEFAULT_SSH_USER).strip()
    ssh_port = _safe_int(data.get('ssh_port', DEFAULT_SSH_PORT), DEFAULT_SSH_PORT)
    peer_ssh_public_key = str(data.get('peer_ssh_public_key', '') or '').strip()
    configured_role = str(data.get('configured_role', '') or '').strip()

    if not relation_id:
        return False, 'relation_id 不能为空'
    if not peer_ip:
        return False, 'peer_ip 不能为空'
    try:
        ipaddress.ip_address(peer_ip)
    except Exception:
        return False, 'peer_ip 格式错误'
    if not ssh_user:
        return False, 'ssh_user 不能为空'
    if ssh_port < 1 or ssh_port > 65535:
        return False, 'ssh_port 格式错误'
    if not peer_ssh_public_key:
        return False, 'peer_ssh_public_key 不能为空'
    if configured_role not in ['primary', 'standby']:
        return False, 'configured_role 只能是 primary 或 standby'
    return True, {
        'relation_id': relation_id,
        'peer_ip': peer_ip,
        'ssh_user': ssh_user,
        'ssh_port': ssh_port,
        'peer_ssh_public_key': peer_ssh_public_key,
        'configured_role': configured_role,
    }


def _command_exists(cmd):
    from shutil import which
    return which(cmd) is not None


def _run_shell(command, timeout=20):
    try:
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or '').strip(), (proc.stderr or '').strip()
    except subprocess.TimeoutExpired:
        return 124, '', 'timeout'
    except Exception as exc:
        return 1, '', str(exc)


def _ensure_ssh_dir():
    _ensure_dir(SSH_DIR)
    try:
        os.chmod(SSH_DIR, 0o700)
    except Exception:
        pass


def _ensure_keypair():
    _ensure_ssh_dir()
    if os.path.exists(PRIVATE_KEY_PATH) and os.path.exists(PUBLIC_KEY_PATH):
        return True, ''
    if not _command_exists('ssh-keygen'):
        return False, '未找到 ssh-keygen 命令'
    cmd = 'ssh-keygen -t rsa -b 2048 -N "" -f ' + shlex.quote(PRIVATE_KEY_PATH) + ' >/dev/null 2>&1'
    rc, out, err = _run_shell(cmd, timeout=60)
    if rc != 0:
        return False, err or out or '生成密钥失败'
    try:
        os.chmod(PRIVATE_KEY_PATH, 0o600)
    except Exception:
        pass
    return True, ''


def _read_public_key():
    ok, msg = _ensure_keypair()
    if not ok:
        return ''
    if not os.path.exists(PUBLIC_KEY_PATH):
        return ''
    return (mw.readFile(PUBLIC_KEY_PATH) or '').strip()


def _append_authorized_key(public_key):
    _ensure_ssh_dir()
    existing = mw.readFile(AUTHORIZED_KEYS_PATH) or ''
    lines = [line.strip() for line in existing.splitlines() if line.strip()]
    if public_key.strip() in lines:
        return True, '已存在'
    if existing and not existing.endswith('\n'):
        existing += '\n'
    existing += public_key.strip() + '\n'
    mw.writeFile(AUTHORIZED_KEYS_PATH, existing)
    try:
        os.chmod(AUTHORIZED_KEYS_PATH, 0o600)
    except Exception:
        pass
    return True, 'ok'


def _mysql_apt_status():
    if not os.path.exists(MYSQL_APT_INDEX):
        return {
            'status': 'warning',
            'reason': 'mysql_apt_missing',
            'detail': 'mysql-apt 插件不存在',
            'data': None,
        }
    cmd = 'cd /www/server/jh-panel && python3 plugins/mysql-apt/index.py get_master_status'
    rc, out, err = _run_shell(cmd, timeout=30)
    if rc != 0 or not out:
        return {
            'status': 'warning',
            'reason': 'mysql_status_error',
            'detail': err or out or '读取 MySQL 状态失败',
            'data': None,
        }
    try:
        payload = json.loads(out)
    except Exception:
        return {
            'status': 'warning',
            'reason': 'mysql_status_parse_error',
            'detail': out,
            'data': None,
        }
    data = payload.get('data') or {}
    if isinstance(data, dict):
        data.setdefault('status', bool(payload.get('status', False)))
    if payload.get('data') == 'pwd':
        return {
            'status': 'warning',
            'reason': 'mysql_status_error',
            'detail': payload.get('msg', 'mysql 状态异常'),
            'data': {},
        }
    return {
        'status': 'normal',
        'reason': '',
        'detail': '',
        'data': data,
    }


def _actual_role_from_mysql(mysql_payload):
    data = mysql_payload.get('data') or {}
    if data.get('slave_status'):
        return 'standby'
    if data.get('status'):
        return 'primary'
    return 'unknown'


def _local_check_results(config):
    checks = {}
    mysql_payload = _mysql_apt_status()
    actual_role = _actual_role_from_mysql(mysql_payload)
    configured_role = config.get('configured_role', '')
    role_status = 'normal'
    role_msg = ''
    if configured_role and actual_role != 'unknown' and configured_role != actual_role:
        role_status = 'warning'
        role_msg = 'role_mismatch'
    if not config.get('relation_id'):
        checks['config'] = {
            'status': 'warning',
            'reason': 'ha_config_missing',
            'detail': '尚未配置主备关系',
        }
    else:
        checks['config'] = {
            'status': 'normal',
            'reason': '',
            'detail': '',
        }
    checks['mysql'] = mysql_payload
    checks['role'] = {
        'status': role_status,
        'reason': role_msg,
        'detail': '' if not role_msg else '配置角色与 MySQL 状态不一致',
    }
    switch_state = config.get('switch_state', 'normal')
    if switch_state == 'switching':
        started_at = _safe_int(config.get('switch_started_at', 0), 0)
        elapsed = int(time.time()) - started_at if started_at > 0 else 0
        if elapsed > 3600:
            checks['switching'] = {
                'status': 'warning',
                'reason': 'switching_timeout',
                'detail': '切换已超过 1 小时',
            }
        else:
            checks['switching'] = {
                'status': 'warning',
                'reason': 'switching',
                'detail': '切换中',
            }
    elif switch_state == 'failed':
        checks['switching'] = {
            'status': 'error',
            'reason': 'switch_failed',
            'detail': '最近一次切换失败',
        }
    else:
        checks['switching'] = {
            'status': 'normal',
            'reason': '',
            'detail': '',
        }
    summary_status = 'normal'
    summary_msgs = []
    for item in checks.values():
        if item.get('status') == 'error':
            summary_status = 'error'
        elif item.get('status') == 'warning' and summary_status != 'error':
            summary_status = 'warning'
        if item.get('reason'):
            summary_msgs.append(item.get('reason'))
    actual_role = actual_role if actual_role != 'unknown' else ('primary' if configured_role == 'primary' else 'standby' if configured_role == 'standby' else 'unknown')
    return checks, actual_role, summary_status, ','.join(summary_msgs)


def getConfig():
    return mw.returnJson(True, 'ok', _load_config())


def saveConfig():
    args = getArgs()
    ok, result = _validate_config_fields(args)
    if not ok:
        return mw.returnJson(False, result)
    config = _load_config()
    config.update(result)
    config['peer_ssh_public_key'] = result['peer_ssh_public_key']
    config['connection_status'] = 'pending' if config.get('connection_status') == 'pending' else config.get('connection_status', 'pending')
    config['connection_checked_at'] = config.get('connection_checked_at', 0)
    config['connection_msg'] = config.get('connection_msg', '')
    config['last_peer_result'] = config.get('last_peer_result', {})
    config['checks'] = config.get('checks', {})
    _append_authorized_key(result['peer_ssh_public_key'])
    _write_config(config)
    return mw.returnJson(True, '保存成功', config)


def getLocalPublicKey():
    key = _read_public_key()
    if not key:
        return mw.returnJson(False, '未能生成或读取公钥')
    return mw.returnJson(True, 'ok', {'public_key': key, 'private_key_path': PRIVATE_KEY_PATH, 'public_key_path': PUBLIC_KEY_PATH})


def ensureKeypair():
    ok, msg = _ensure_keypair()
    if not ok:
        return mw.returnJson(False, msg)
    return mw.returnJson(True, 'ok', {'public_key': _read_public_key()})


def getStatus(local_only=False):
    config = _load_config()
    checks, actual_role, summary_status, summary_msg = _local_check_results(config)
    peer = {
        'status': 'not_checked',
        'reason': '',
        'detail': '',
        'relation_id': '',
        'peer_role': '',
        'raw': None,
    }
    if not local_only and config.get('peer_ip'):
        peer = _check_peer(config, checks)
        _apply_peer_connection(config, peer)
        peer_status = peer.get('status', 'warning')
        if peer_status == 'error':
            summary_status = 'error'
        elif peer_status == 'warning' and summary_status != 'error':
            summary_status = 'warning'
    result = {
        'relation_id': config.get('relation_id', ''),
        'local_ip': _detect_local_ip(),
        'configured_role': config.get('configured_role', ''),
        'actual_role': actual_role,
        'switch_state': config.get('switch_state', 'normal'),
        'peer': peer,
        'checks': checks,
        'summary_status': summary_status,
        'summary_msg': summary_msg,
        'connection_status': config.get('connection_status', 'pending'),
        'connection_checked_at': config.get('connection_checked_at', 0),
        'connection_msg': config.get('connection_msg', ''),
        'local_only': bool(local_only),
    }
    config['checks'] = checks
    config['last_peer_result'] = peer
    config['summary_status'] = summary_status
    config['summary_msg'] = summary_msg
    _write_config(config)
    return mw.returnJson(True, 'ok', result)


def _detect_local_ip():
    config = _load_config()
    peer_ip = config.get('peer_ip', '')
    try:
        if peer_ip:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.connect((peer_ip, 80))
            return sock.getsockname()[0]
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception:
        return ''


def _check_peer(config, local_checks):
    peer_ip = config.get('peer_ip', '')
    ssh_user = config.get('ssh_user', DEFAULT_SSH_USER)
    ssh_port = _safe_int(config.get('ssh_port', DEFAULT_SSH_PORT), DEFAULT_SSH_PORT)
    cmd = [
        'ssh',
        '-i', PRIVATE_KEY_PATH,
        '-o', 'BatchMode=yes',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=8',
        '-p', str(ssh_port),
        f'{ssh_user}@{peer_ip}',
        'cd /www/server/jh-panel && python3 plugins/ha_manager/index.py get_status --local-only'
    ]
    rc, out, err = _run_shell(' '.join(shlex.quote(part) for part in cmd), timeout=20)
    if rc != 0:
        reason = 'peer_plugin_missing'
        status = 'warning'
        detail = err or out or '对端检查失败'
        if 'timed out' in detail.lower() or 'timeout' in detail.lower() or rc == 124:
            reason = 'ssh_timeout'
        elif 'permission denied' in detail.lower() or 'auth' in detail.lower():
            reason = 'ssh_auth_failed'
        return {
            'status': status,
            'reason': reason,
            'detail': detail,
            'relation_id': '',
            'peer_role': '',
            'raw': None,
        }
    try:
        payload = json.loads(out)
    except Exception:
        return {
            'status': 'warning',
            'reason': 'peer_plugin_missing',
            'detail': out,
            'relation_id': '',
            'peer_role': '',
            'raw': None,
        }
    peer_data = payload.get('data') or {}
    peer_relation = peer_data.get('relation_id', '')
    if peer_relation and peer_relation != config.get('relation_id', ''):
        return {
            'status': 'warning',
            'reason': 'relation_id_mismatch',
            'detail': '对端 relation_id 不一致',
            'relation_id': peer_relation,
            'peer_role': peer_data.get('configured_role', ''),
            'raw': peer_data,
        }
    if peer_data.get('switch_state') == 'switching':
        return {
            'status': 'warning',
            'reason': 'switching',
            'detail': '对端切换中',
            'relation_id': peer_relation,
            'peer_role': peer_data.get('configured_role', ''),
            'raw': peer_data,
        }
    local_role = config.get('configured_role', '')
    peer_role = peer_data.get('configured_role', '')
    if local_role and peer_role and local_role == peer_role:
        return {
            'status': 'error',
            'reason': 'ha_role_conflict',
            'detail': '两端角色冲突',
            'relation_id': peer_relation,
            'peer_role': peer_role,
            'raw': peer_data,
        }
    peer_state = 'normal'
    if peer_role not in ['primary', 'standby']:
        peer_state = 'warning'
    return {
        'status': peer_state,
        'reason': '' if peer_state == 'normal' else 'peer_status_warning',
        'detail': '',
        'relation_id': peer_relation,
        'peer_role': peer_role,
        'raw': peer_data,
    }


def _apply_peer_connection(config, peer):
    reason = peer.get('reason', '')
    status = peer.get('status', '')
    if status == 'normal':
        config['connection_status'] = 'connected'
    elif reason in ['ssh_timeout', 'ssh_auth_failed', 'peer_plugin_missing', 'relation_id_mismatch']:
        config['connection_status'] = reason
    else:
        config['connection_status'] = status or 'pending'
    config['connection_checked_at'] = int(time.time())
    config['connection_msg'] = peer.get('detail') or reason or status
    config['last_peer_result'] = peer
    return config


def testPeer():
    config = _load_config()
    if not config.get('peer_ip'):
        return mw.returnJson(False, '尚未配置对端 IP')
    checks, actual_role, summary_status, summary_msg = _local_check_results(config)
    peer = _check_peer(config, checks)
    _apply_peer_connection(config, peer)
    _write_config(config)
    return mw.returnJson(peer.get('status') == 'normal', config.get('connection_msg', '测试完成'), peer)


def selfCheck():
    config = _load_config()
    checks, actual_role, summary_status, summary_msg = _local_check_results(config)
    result = {
        'relation_id': config.get('relation_id', ''),
        'actual_role': actual_role,
        'summary_status': summary_status,
        'summary_msg': summary_msg,
        'checks': checks,
    }
    config['checks'] = checks
    config['summary_status'] = summary_status
    config['summary_msg'] = summary_msg
    _write_config(config)
    return mw.returnJson(True, 'ok', result)


def switchRole():
    args = getArgs()
    role = str(args.get('role', '') or '').strip()
    if not role and len(sys.argv) > 2:
        raw = str(sys.argv[2] or '').strip()
        if raw in ['switching', 'primary', 'standby', 'failed']:
            role = raw
    config = _load_config()
    if role not in ['switching', 'primary', 'standby', 'failed']:
        return mw.returnJson(False, '非法切换参数')
    now = int(time.time())
    if role == 'switching':
        config['switch_state'] = 'switching'
        config['switch_started_at'] = now
    elif role in ['primary', 'standby']:
        config['configured_role'] = role
        config['switch_state'] = 'normal'
        config['switch_started_at'] = 0
        config['switch_failed_at'] = 0
    elif role == 'failed':
        config['switch_state'] = 'failed'
        config['switch_failed_at'] = now
    _write_config(config)
    return mw.returnJson(True, 'ok', config)


def getStatusPanel():
    config = _load_config()
    checks, actual_role, summary_status, summary_msg = _local_check_results(config)
    peer = config.get('last_peer_result', {}) or {}
    data = {
        'config': config,
        'checks': checks,
        'actual_role': actual_role,
        'summary_status': summary_status,
        'summary_msg': summary_msg,
        'peer': peer,
        'public_key': _read_public_key(),
    }
    return mw.returnJson(True, 'ok', data)


def status():
    return 'start'


def start():
    return 'ok'


def stop():
    return 'ok'


def restart():
    return 'ok'


def reload():
    return 'ok'


def initdStatus():
    return 'ok'


def initdInstall():
    return 'ok'


def initdUinstall():
    return 'ok'


def runLog():
    return getServerDir() + '/ha_manager.log'


def installPlugin():
    _ensure_dir(getServerDir())
    config = _load_config()
    _write_config(config)
    ok, msg = _ensure_keypair()
    if not ok:
        return mw.returnJson(False, msg)
    return mw.returnJson(True, 'ok', config)


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
    elif func == 'run_log':
        print(runLog())
    elif func == 'install_plugin':
        print(installPlugin())
    elif func == 'get_config':
        print(getConfig())
    elif func == 'save_config':
        print(saveConfig())
    elif func == 'get_local_public_key':
        print(getLocalPublicKey())
    elif func == 'ensure_keypair':
        print(ensureKeypair())
    elif func == 'get_status':
        local_only = False
        for arg in sys.argv[2:]:
            if arg in ['--local-only', 'local-only:1', 'local_only:1']:
                local_only = True
        print(getStatus(local_only))
    elif func == 'test_peer':
        print(testPeer())
    elif func == 'self_check':
        print(selfCheck())
    elif func == 'switch_role':
        print(switchRole())
    elif func == 'get_status_panel':
        print(getStatusPanel())
    else:
        print('error')
