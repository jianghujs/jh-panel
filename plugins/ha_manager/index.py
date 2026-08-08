# coding:utf-8

import hashlib
import hmac
import json
import os
import shlex
import sys
import time
import urllib.request

sys.path.append(os.getcwd() + '/class/core')
import mw


PLUGIN_NAME = 'ha_manager'
PLUGIN_DIR = os.path.join(mw.getPluginDir(), PLUGIN_NAME)
DATA_DIR = os.path.join(PLUGIN_DIR, 'data')
LOG_DIR = os.path.join(PLUGIN_DIR, 'logs')
SWITCH_LOG_DIR = os.path.join(LOG_DIR, 'switch')
PEER_LOG_DIR = os.path.join(LOG_DIR, 'peer')
CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')
STATE_PATH = os.path.join(DATA_DIR, 'state.json')
QUEUE_PATH = os.path.join(DATA_DIR, 'report_queue.json')
SEQ_PATH = os.path.join(DATA_DIR, 'seq.json')
LOCK_PATH = os.path.join(DATA_DIR, 'switch.lock')
SSH_PRIVATE_KEY_PATH = '/root/.ssh/id_rsa'
SSH_PUBLIC_KEY_PATH = '/root/.ssh/id_rsa.pub'


def _now():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


def _ensure_dirs():
    for path in (DATA_DIR, LOG_DIR, SWITCH_LOG_DIR, PEER_LOG_DIR):
        if not os.path.exists(path):
            os.makedirs(path, mode=0o700, exist_ok=True)


def _read_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as fp:
            return json.load(fp)
    except Exception:
        return default


def _write_json(path, data):
    _ensure_dirs()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def _args():
    if len(sys.argv) < 3:
        return {}
    raw = ' '.join(sys.argv[2:])
    try:
        return json.loads(raw)
    except Exception:
        result = {}
        for item in sys.argv[2:]:
            if ':' in item:
                key, value = item.split(':', 1)
                result[key.strip('{}')] = value.strip('{}')
        return result


def _return(status, msg, data=None):
    return mw.returnJson(status, msg, data)


def _host_id():
    host_file = '/www/server/jh-panel/data/ha_manager_host_id.pl'
    current = ''
    if os.path.exists(host_file):
        current = mw.readFile(host_file).strip()
    if not current:
        current = 'H_PANEL_' + hashlib.sha1((mw.getHostAddr() + str(time.time())).encode('utf-8')).hexdigest()[:8].upper()
        mw.writeFile(host_file, current)
    return current


def _default_config():
    return {
        'monitor_url': '',
        'pair_name': '生产面板主备',
        'pair_id': '',
        'api_secret': hashlib.sha256((str(time.time()) + mw.getRandomString(16)).encode('utf-8')).hexdigest(),
        'host_id': _host_id(),
        'host_name': os.uname().nodename,
        'host_ip': mw.getHostAddr(),
        'peer_host_id': '',
        'peer_public_ip': '',
        'peer_ssh_port': '22',
        'peer_ssh_user': 'root',
        'peer_public_key': '',
        'bind_test_status': 'untested',
        'role': 'standby',
        'desired_role': 'standby',
        'poll_interval': 10,
        'report_interval': 30,
        'last_report_at': '',
        'switch_run_id': '',
        'switch_status': 'idle',
        'log_path': '',
        'options': {
            'local_ip': mw.getHostAddr(),
            'remote_ip': '',
            'remote_ssh_port': '22',
            'run_checksum': True,
            'allow_checksum_diff': False,
            'sync_files': True,
            'sync_file_dirs': '/www/wwwroot,/www/wwwstorage',
            'sync_ignore_dirs': 'node_modules,logs,run',
            'restore_site_setting': False,
            'restore_plugin_setting': False,
            'run_xtrabackup_inc_restore': False,
            'promote_mysql': True
        }
    }


def _config():
    _ensure_dirs()
    cfg = _default_config()
    saved = _read_json(CONFIG_PATH, {})
    cfg.update(saved)
    cfg['options'].update(saved.get('options') or {})
    if not cfg.get('pair_id'):
        source = cfg.get('host_id', '') + '_' + cfg.get('peer_public_ip', '')
        cfg['pair_id'] = 'HA_' + hashlib.sha1(source.encode('utf-8')).hexdigest()[:12].upper()
    return cfg


def _save_config(cfg):
    _write_json(CONFIG_PATH, cfg)
    return cfg


def _health_snapshot(cfg):
    mysql = {'status': 'normal', 'text': 'MySQL 检查待接入'}
    if os.path.exists('/www/server/mysql') or os.path.exists('/www/server/mariadb'):
        mysql = {'status': 'normal', 'text': '数据库目录存在'}
    openresty_running = mw.execShell("ps -ef | grep openresty | grep -v grep | head -1")[0].strip() != ''
    rsync_running = mw.execShell("ps -ef | grep -E 'rsync|lsyncd' | grep -v grep | head -1")[0].strip() != ''
    return {
        'mysql': mysql,
        'rsync': {'status': 'normal' if rsync_running or cfg.get('role') == 'standby' else 'warning', 'text': 'rsync/lsyncd ' + ('运行中' if rsync_running else '未运行')},
        'openresty': {'status': 'normal' if openresty_running or cfg.get('role') == 'standby' else 'warning', 'text': 'OpenResty ' + ('运行中' if openresty_running else '未运行')},
        'ssh': {'status': 'normal' if cfg.get('bind_test_status') == 'success' else 'warning', 'text': 'SSH绑定' + ('已验证' if cfg.get('bind_test_status') == 'success' else '未验证')},
        'cloud': {'status': 'normal' if cfg.get('monitor_url') else 'warning', 'text': '云监控' + ('已配置' if cfg.get('monitor_url') else '未配置')},
        'lock': {'status': 'warning' if os.path.exists(LOCK_PATH) else 'normal', 'text': '本地切换锁' + ('存在' if os.path.exists(LOCK_PATH) else '空闲')}
    }


def _state(cfg=None):
    cfg = cfg or _config()
    state = _read_json(STATE_PATH, {})
    state.update({
        'pair_id': cfg.get('pair_id'),
        'pair_name': cfg.get('pair_name'),
        'host_id': cfg.get('host_id'),
        'host_name': cfg.get('host_name'),
        'host_ip': cfg.get('host_ip'),
        'role': cfg.get('role'),
        'desired_role': cfg.get('desired_role'),
        'online_status': 'online',
        'health_status': 'warning' if any([v.get('status') == 'warning' for v in _health_snapshot(cfg).values()]) else 'normal',
        'health_detail': _health_snapshot(cfg),
        'switch_run_id': cfg.get('switch_run_id'),
        'switch_status': cfg.get('switch_status'),
        'log_path': cfg.get('log_path'),
        'last_report_at': cfg.get('last_report_at'),
        'updated_at': _now()
    })
    _write_json(STATE_PATH, state)
    return state


def _seq():
    data = _read_json(SEQ_PATH, {'seq': 0})
    data['seq'] = int(data.get('seq') or 0) + 1
    _write_json(SEQ_PATH, data)
    return data['seq']


def _switch_log_path(switch_run_id):
    return os.path.join(SWITCH_LOG_DIR, switch_run_id + '.log')


def _append_switch_log(switch_run_id, phase, status, text):
    path = _switch_log_path(switch_run_id)
    seq = _seq()
    line = '[{0}] [{1}] [{2}] [{3}] {4}'.format(_now(), seq, phase, status, text)
    with open(path, 'a', encoding='utf-8') as fp:
        fp.write(line + '\n')
    return {'seq': seq, 'line': line, 'path': path}


def get_state():
    cfg = _config()
    data = cfg.copy()
    data['health'] = _health_snapshot(cfg)
    data['state'] = _state(cfg)
    data['log'] = read_latest_log_text()
    return _return(True, 'ok', data)


def save_binding():
    data = _args()
    cfg = _config()
    for key in ('peer_public_ip', 'peer_ssh_port', 'peer_ssh_user', 'peer_public_key', 'peer_host_id'):
        if key in data:
            cfg[key] = str(data.get(key) or '').strip()
    if not cfg.get('peer_public_ip') or not cfg.get('peer_public_key'):
        return _return(False, '请填写对方IP和对方公钥')
    if not cfg.get('peer_host_id'):
        cfg['peer_host_id'] = 'H_PEER_' + hashlib.sha1(cfg.get('peer_public_ip').encode('utf-8')).hexdigest()[:8].upper()
    cfg['options']['remote_ip'] = cfg.get('peer_public_ip')
    cfg['options']['remote_ssh_port'] = cfg.get('peer_ssh_port')
    _save_config(cfg)
    _state(cfg)
    return _return(True, '绑定已保存', cfg)


def get_local_public_key():
    info = _ssh_key_info()
    key = info.get('public_key') or ''
    if not key:
        return _return(False, '本机公钥为空')
    return _return(True, 'ok', {'public_key': key, 'path': SSH_PUBLIC_KEY_PATH})


def _ssh_key_info():
    public_key = ''
    private_key = ''
    private_exists = os.path.exists(SSH_PRIVATE_KEY_PATH)
    public_exists = os.path.exists(SSH_PUBLIC_KEY_PATH)
    if private_exists:
        private_key = mw.readFile(SSH_PRIVATE_KEY_PATH).strip()
    if public_exists:
        public_key = mw.readFile(SSH_PUBLIC_KEY_PATH).strip()
    return {
        'public_key': public_key,
        'private_key': private_key,
        'has_private': private_exists,
        'has_public': public_exists,
        'private_key_path': SSH_PRIVATE_KEY_PATH,
        'public_key_path': SSH_PUBLIC_KEY_PATH
    }


def get_key_info():
    return _return(True, 'ok', _ssh_key_info())


def generate_keypair():
    data = _args()
    force = str(data.get('force', '0')).lower() in ('1', 'true', 'yes', 'on')
    if (os.path.exists(SSH_PRIVATE_KEY_PATH) or os.path.exists(SSH_PUBLIC_KEY_PATH)) and not force:
        return _return(False, '本机 SSH 密钥已存在，如需覆盖请确认重新生成')
    ssh_dir = os.path.dirname(SSH_PRIVATE_KEY_PATH)
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
    if force:
        for path in (SSH_PRIVATE_KEY_PATH, SSH_PUBLIC_KEY_PATH):
            if os.path.exists(path):
                os.remove(path)
    cmd = 'ssh-keygen -t rsa -b 4096 -N "" -C {0} -f {1}'.format(
        shlex.quote('ha_manager@' + os.uname().nodename),
        shlex.quote(SSH_PRIVATE_KEY_PATH)
    )
    out, err, code = mw.execShell(cmd, timeout=20)
    if code != 0:
        return _return(False, '生成本机 SSH 密钥失败: ' + (err or out))
    try:
        os.chmod(SSH_PRIVATE_KEY_PATH, 0o600)
        os.chmod(SSH_PUBLIC_KEY_PATH, 0o644)
    except Exception:
        pass
    info = _ssh_key_info()
    if not info.get('public_key'):
        return _return(False, '密钥已生成但公钥读取失败')
    return _return(True, '生成成功', info)


def init_keypair():
    if os.path.exists(SSH_PRIVATE_KEY_PATH) and os.path.exists(SSH_PUBLIC_KEY_PATH):
        return _return(True, '密钥已存在', _ssh_key_info())
    return generate_keypair()


def test_peer_ssh():
    data = _args()
    cfg = _config()
    host = data.get('peer_public_ip') or cfg.get('peer_public_ip')
    port = data.get('peer_ssh_port') or cfg.get('peer_ssh_port') or '22'
    user = data.get('peer_ssh_user') or cfg.get('peer_ssh_user') or 'root'
    if not host:
        return _return(False, '请先填写对方IP')
    cmd = "ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p {0} {1}@{2} 'echo ok'".format(port, user, host)
    out, err, code = mw.execShell(cmd, timeout=8)
    cfg['bind_test_status'] = 'success' if code == 0 and out.strip() == 'ok' else 'failed'
    _save_config(cfg)
    if cfg['bind_test_status'] == 'success':
        return _return(True, 'SSH连接测试通过')
    return _return(False, 'SSH连接测试失败: ' + (err or out))


def save_monitor():
    data = _args()
    cfg = _config()
    for key in ('pair_name', 'monitor_url', 'poll_interval', 'report_interval'):
        if key in data:
            cfg[key] = data.get(key)
    cfg['poll_interval'] = int(cfg.get('poll_interval') or 10)
    cfg['report_interval'] = int(cfg.get('report_interval') or 30)
    _save_config(cfg)
    if not cfg.get('monitor_url'):
        return _return(True, '云监控地址为空，不上传状态', cfg)
    register = _register_monitor(cfg)
    return register


def clear_monitor():
    cfg = _config()
    cfg['monitor_url'] = ''
    _save_config(cfg)
    return _return(True, '已清空云监控地址', cfg)


def _sign(cfg, payload):
    timestamp = str(int(time.time()))
    nonce = hashlib.sha1((timestamp + mw.getRandomString(8)).encode('utf-8')).hexdigest()
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    sign_text = '\n'.join([timestamp, nonce, body_hash])
    signature = hmac.new(str(cfg.get('api_secret')).encode('utf-8'), sign_text.encode('utf-8'), hashlib.sha256).hexdigest()
    return {'X-JH-Timestamp': timestamp, 'X-JH-Nonce': nonce, 'X-JH-Body-Hash': body_hash, 'X-JH-Signature': signature, 'Content-Type': 'application/json'}


def _post_monitor(cfg, action, payload, signed=True):
    url = cfg.get('monitor_url', '').rstrip('/') + '/pub/' + action
    if not cfg.get('monitor_url'):
        return {'status': False, 'msg': '云监控地址为空'}
    headers = _sign(cfg, payload) if signed else {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='replace')
            return json.loads(text)
    except Exception as e:
        queue = _read_json(QUEUE_PATH, [])
        queue.append({'action': action, 'payload': payload, 'error': str(e), 'addtime': _now()})
        _write_json(QUEUE_PATH, queue[-200:])
        return {'status': False, 'msg': str(e)}


def _register_monitor(cfg):
    payload = {
        'pair_id': cfg.get('pair_id'),
        'pair_name': cfg.get('pair_name'),
        'api_secret': cfg.get('api_secret'),
        'desired_master_host_id': cfg.get('host_id') if cfg.get('role') == 'master' else cfg.get('peer_host_id'),
        'local_host': {'host_id': cfg.get('host_id'), 'host_name': cfg.get('host_name'), 'host_ip': cfg.get('host_ip'), 'role': cfg.get('role'), 'online_status': 'online'},
        'peer_host': {'host_id': cfg.get('peer_host_id'), 'host_name': '对端 ' + cfg.get('peer_public_ip', ''), 'host_ip': cfg.get('peer_public_ip'), 'role': 'standby' if cfg.get('role') == 'master' else 'master', 'online_status': 'unknown'}
    }
    res = _post_monitor(cfg, 'ha_register_pair', payload, signed=False)
    if res.get('status') and isinstance(res.get('data'), dict):
        cfg['pair_id'] = res['data'].get('pair_id') or cfg.get('pair_id')
        cfg['api_secret'] = res['data'].get('api_secret') or cfg.get('api_secret')
        cfg['last_report_at'] = _now()
        _save_config(cfg)
    return _return(bool(res.get('status')), res.get('msg') or '注册完成', cfg)


def report_state():
    cfg = _config()
    local_state = _state(cfg)
    peer_state = collect_peer_state_raw(cfg)
    hosts = [{
        'host_id': cfg.get('host_id'),
        'host_name': cfg.get('host_name'),
        'host_ip': cfg.get('host_ip'),
        'role': cfg.get('role'),
        'online_status': 'online',
        'health_status': local_state.get('health_status'),
        'health_detail': local_state.get('health_detail'),
        'collect_status': 'success',
        'collect_method': 'local',
        'report_host_id': cfg.get('host_id'),
        'switch_run_id': cfg.get('switch_run_id')
    }]
    if peer_state.get('status'):
        peer = peer_state.get('data') or {}
        peer_log_result = collect_peer_logs(cfg, peer)
        hosts.append({
            'host_id': peer.get('host_id') or cfg.get('peer_host_id'),
            'host_name': peer.get('host_name') or ('对端 ' + cfg.get('peer_public_ip', '')),
            'host_ip': peer.get('host_ip') or cfg.get('peer_public_ip'),
            'role': peer.get('role') or ('standby' if cfg.get('role') == 'master' else 'master'),
            'online_status': peer.get('online_status') or 'unknown',
            'health_status': peer.get('health_status') or 'unknown',
            'health_detail': peer.get('health_detail') or ({'summary': peer_log_result.get('msg')} if not peer_log_result.get('status') else {}),
            'collect_status': 'success' if peer_log_result.get('status') else 'partial',
            'collect_method': 'ssh_peer',
            'report_host_id': cfg.get('host_id'),
            'switch_run_id': peer.get('switch_run_id') or ''
        })
    elif cfg.get('peer_host_id'):
        hosts.append({'host_id': cfg.get('peer_host_id'), 'host_name': '对端 ' + cfg.get('peer_public_ip', ''), 'host_ip': cfg.get('peer_public_ip'), 'role': 'unknown', 'online_status': 'unknown', 'health_status': 'unknown', 'collect_status': 'failed', 'collect_method': 'ssh_peer', 'report_host_id': cfg.get('host_id'), 'health_detail': {'summary': peer_state.get('msg')}})
    payload = {'pair_id': cfg.get('pair_id'), 'hosts': hosts}
    res = _post_monitor(cfg, 'ha_report_state', payload, signed=True)
    if res.get('status'):
        cfg['last_report_at'] = _now()
        _save_config(cfg)
    return _return(bool(res.get('status')), res.get('msg') or '上报完成', {'hosts': hosts})


def collect_peer_state_raw(cfg):
    if not cfg.get('peer_public_ip') or cfg.get('bind_test_status') != 'success':
        return {'status': False, 'msg': 'SSH未绑定或未验证'}
    remote_path = os.path.join(PLUGIN_DIR, 'data/state.json')
    cmd = "ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p {0} {1}@{2} 'cat {3}'".format(cfg.get('peer_ssh_port'), cfg.get('peer_ssh_user'), cfg.get('peer_public_ip'), remote_path)
    out, err, code = mw.execShell(cmd, timeout=8)
    if code != 0:
        return {'status': False, 'msg': err or out or 'SSH采集失败'}
    try:
        return {'status': True, 'data': json.loads(out)}
    except Exception:
        return {'status': False, 'msg': '对端状态格式错误'}


def collect_peer_logs(cfg, peer_state):
    switch_run_id = peer_state.get('switch_run_id') or cfg.get('switch_run_id')
    peer_host_id = peer_state.get('host_id') or cfg.get('peer_host_id')
    if not switch_run_id or not peer_host_id or cfg.get('bind_test_status') != 'success':
        return {'status': False, 'msg': '缺少对端日志采集条件'}
    remote_path = os.path.join(PLUGIN_DIR, 'logs/switch', switch_run_id + '.log')
    cmd = "ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p {0} {1}@{2} 'cat {3}'".format(cfg.get('peer_ssh_port'), cfg.get('peer_ssh_user'), cfg.get('peer_public_ip'), remote_path)
    out, err, code = mw.execShell(cmd, timeout=8)
    if code != 0:
        return {'status': False, 'msg': err or out or '对端日志采集失败'}
    local_dir = os.path.join(PEER_LOG_DIR, peer_host_id)
    if not os.path.exists(local_dir):
        os.makedirs(local_dir, mode=0o700, exist_ok=True)
    local_path = os.path.join(local_dir, switch_run_id + '.log')
    old_lines = []
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8', errors='replace') as fp:
            old_lines = fp.read().splitlines()
    new_lines = out.splitlines()[len(old_lines):]
    if new_lines:
        with open(local_path, 'a', encoding='utf-8') as fp:
            for line in new_lines:
                fp.write(line + '\n')
        for index, line in enumerate(new_lines, start=len(old_lines) + 1):
            report_switch_event(cfg, 'peer_log', 'running', line, origin_host_id=peer_host_id, seq=index, collect_method='ssh_peer', switch_run_id=switch_run_id)
    return {'status': True, 'data': {'path': local_path, 'new_count': len(new_lines)}}


def poll_monitor():
    cfg = _config()
    payload = {'pair_id': cfg.get('pair_id'), 'host_id': cfg.get('host_id')}
    res = _post_monitor(cfg, 'ha_pull_desired_state', payload, signed=True)
    if res.get('status') and isinstance(res.get('data'), dict):
        run = res['data'].get('switch_run') or {}
        desired = res['data'].get('desired_master_host_id')
        cfg['desired_role'] = 'master' if desired == cfg.get('host_id') else 'standby'
        if run.get('switch_run_id'):
            cfg['switch_run_id'] = run.get('switch_run_id')
            cfg['switch_status'] = run.get('status') or cfg.get('switch_status')
            cfg['log_path'] = run.get('log_path') or cfg.get('log_path')
        _save_config(cfg)
    return _return(bool(res.get('status')), res.get('msg') or '轮询完成', cfg)


def read_latest_log_text():
    cfg = _config()
    path = _switch_log_path(cfg.get('switch_run_id') or 'latest')
    if not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8', errors='replace') as fp:
        return fp.read()[-200000:]


def read_log():
    return _return(True, 'ok', {'log': read_latest_log_text(), 'log_path': _config().get('log_path')})


def _lock():
    if os.path.exists(LOCK_PATH):
        return False
    mw.writeFile(LOCK_PATH, str(os.getpid()))
    return True


def _unlock():
    if os.path.exists(LOCK_PATH):
        os.remove(LOCK_PATH)


def local_switch():
    data = _args()
    cfg = _config()
    target_role = data.get('target_role') or ('standby' if cfg.get('role') == 'master' else 'master')
    if not _lock():
        return _return(False, '已有切换任务正在执行')
    try:
        switch_run_id = data.get('switch_run_id') or 'LOCAL_' + time.strftime('%Y%m%d%H%M%S')
        cfg['switch_run_id'] = switch_run_id
        cfg['switch_status'] = 'running'
        cfg['options'].update(data.get('options') or {})
        _save_config(cfg)
        phase = 'online' if target_role == 'master' else 'offline'
        _append_switch_log(switch_run_id, phase, 'start', '本机开始执行切换为' + ('主' if target_role == 'master' else '备'))
        _run_executor(phase, cfg)
        cfg['role'] = target_role
        cfg['desired_role'] = target_role
        cfg['switch_status'] = phase + '_done'
        _save_config(cfg)
        _append_switch_log(switch_run_id, phase, 'success', '本机切换完成')
        _state(cfg)
        report_switch_event(cfg, phase, 'success', '本机切换完成')
        return _return(True, '切换执行完成', cfg)
    except Exception as e:
        _append_switch_log(cfg.get('switch_run_id') or 'failed', 'switch', 'failed', str(e))
        cfg['switch_status'] = 'failed'
        _save_config(cfg)
        report_switch_event(cfg, 'switch', 'failed', str(e))
        return _return(False, '切换失败: ' + str(e))
    finally:
        _unlock()


def _run_executor(phase, cfg):
    script = '/www/server/jh-panel/scripts/os_tool/vm/default/switch__generate_' + phase + '.sh'
    if not os.path.exists(script):
        _append_switch_log(cfg.get('switch_run_id'), phase, 'warning', '原始脚本不存在，已记录模拟执行')
        return
    if phase == 'offline':
        steps = [
            '开启 xtrabackup、xtrabackup-inc、mysqldump 备份计划',
            '关闭网站/插件配置备份、lsyncd 同步、证书续签计划',
            '开启网站/插件配置恢复计划',
            '关闭主从同步异常提醒和 Rsync 状态异常提醒',
            '关闭 rsyncd/lsyncd 任务并清理 rsync 进程',
            '关闭 OpenResty',
            '写入备用角色状态快照'
        ]
    else:
        opts = cfg.get('options') or {}
        steps = [
            '按参数确认本机IP {0}、对端IP {1}、SSH端口 {2}'.format(opts.get('local_ip'), opts.get('remote_ip'), opts.get('remote_ssh_port')),
            '按需执行 xtrabackup 增量恢复' if opts.get('run_xtrabackup_inc_restore') else '跳过 xtrabackup 增量恢复',
            '按需执行 checksum 校验' if opts.get('run_checksum') else '跳过 checksum 校验',
            '按需同步文件目录 ' + str(opts.get('sync_file_dirs') or '') if opts.get('sync_files') else '跳过文件同步',
            '按需恢复网站和插件配置',
            '提升 MySQL 为主库' if opts.get('promote_mysql', True) else '跳过 MySQL 提升',
            '关闭备份计划并恢复主机侧同步计划',
            '启用 rsyncd/lsyncd 任务',
            '启动 OpenResty',
            '写入主机角色状态快照'
        ]
    for step in steps:
        _append_switch_log(cfg.get('switch_run_id'), phase, 'running', step)
        report_switch_event(cfg, phase, 'running', step)
        time.sleep(0.05)


def report_switch_event(cfg, phase, status, text, origin_host_id=None, seq=None, collect_method='local', switch_run_id=None):
    switch_run_id = switch_run_id or cfg.get('switch_run_id')
    if not cfg.get('monitor_url') or not switch_run_id or switch_run_id.startswith('LOCAL_'):
        return {'status': False, 'msg': '无需上报'}
    seq = seq or _seq()
    origin_host_id = origin_host_id or cfg.get('host_id')
    payload = {'pair_id': cfg.get('pair_id'), 'switch_run_id': switch_run_id, 'event_id': origin_host_id + '-' + str(seq), 'origin_host_id': origin_host_id, 'report_host_id': cfg.get('host_id'), 'collect_method': collect_method, 'seq': seq, 'phase': phase, 'step': text, 'status': status, 'log_text': text}
    return _post_monitor(cfg, 'ha_report_switch_event', payload, signed=True)


def main():
    _ensure_dirs()
    func = sys.argv[1] if len(sys.argv) > 1 else 'get_state'
    if func not in globals():
        print(_return(False, '方法不存在: ' + func))
        return
    result = globals()[func]()
    print(result)


if __name__ == '__main__':
    main()
