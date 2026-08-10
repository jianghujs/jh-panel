# coding:utf-8

import sys

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'status':
    print('start')
    sys.exit(0)

import hashlib
import hmac
import json
import os
import shlex
import shutil
import signal
import subprocess
import time
import urllib.request

PANEL_DIR = '/www/server/jh-panel'
sys.path.append(os.path.join(PANEL_DIR, 'class/core'))
import mw


PLUGIN_NAME = 'ha_manager'
PLUGIN_DIR = os.path.join(mw.getPluginDir(), PLUGIN_NAME)
RUNTIME_DIR = '/www/server/ha_manager'
VERSION_PATH = os.path.join(RUNTIME_DIR, 'version.pl')
DATA_DIR = os.path.join(RUNTIME_DIR, 'data')
LOG_DIR = os.path.join(RUNTIME_DIR, 'logs')
SWITCH_LOG_DIR = os.path.join(LOG_DIR, 'switch')
PEER_LOG_DIR = os.path.join(LOG_DIR, 'peer')
CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')
STATE_PATH = os.path.join(DATA_DIR, 'state.json')
QUEUE_PATH = os.path.join(DATA_DIR, 'report_queue.json')
SEQ_PATH = os.path.join(DATA_DIR, 'seq.json')
LOCK_PATH = os.path.join(DATA_DIR, 'switch.lock')
SSH_PRIVATE_KEY_PATH = '/root/.ssh/id_rsa'
SSH_PUBLIC_KEY_PATH = '/root/.ssh/id_rsa.pub'
LEGACY_DATA_DIR = os.path.join(PLUGIN_DIR, 'data')
LEGACY_LOG_DIR = os.path.join(PLUGIN_DIR, 'logs')
REMOTE_STATE_PATH = '/www/server/ha_manager/data/state.json'
REMOTE_SWITCH_LOG_DIR = '/www/server/ha_manager/logs/switch'


def _now():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


def _ensure_dirs():
    for path in (RUNTIME_DIR, DATA_DIR, LOG_DIR, SWITCH_LOG_DIR, PEER_LOG_DIR):
        if not os.path.exists(path):
            os.makedirs(path, mode=0o700, exist_ok=True)
    if not os.path.exists(VERSION_PATH) or not mw.readFile(VERSION_PATH).strip():
        mw.writeFile(VERSION_PATH, '1.0')
    _migrate_runtime_data()


def _copy_if_missing(src, dst):
    if os.path.exists(dst) or not os.path.exists(src):
        return
    parent = os.path.dirname(dst)
    if not os.path.exists(parent):
        os.makedirs(parent, mode=0o700, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_tree_if_missing(src_dir, dst_dir):
    if not os.path.exists(src_dir):
        return
    for root, dirs, files in os.walk(src_dir):
        rel_root = os.path.relpath(root, src_dir)
        target_root = dst_dir if rel_root == '.' else os.path.join(dst_dir, rel_root)
        for dirname in dirs:
            target_dir = os.path.join(target_root, dirname)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, mode=0o700, exist_ok=True)
        for filename in files:
            _copy_if_missing(os.path.join(root, filename), os.path.join(target_root, filename))


def _migrate_runtime_data():
    legacy_files = ('config.json', 'state.json', 'report_queue.json', 'seq.json')
    for filename in legacy_files:
        _copy_if_missing(os.path.join(LEGACY_DATA_DIR, filename), os.path.join(DATA_DIR, filename))
    if os.path.exists(os.path.join(LEGACY_LOG_DIR, 'switch')):
        for filename in os.listdir(os.path.join(LEGACY_LOG_DIR, 'switch')):
            _copy_if_missing(os.path.join(LEGACY_LOG_DIR, 'switch', filename), os.path.join(SWITCH_LOG_DIR, filename))
    _copy_tree_if_missing(os.path.join(LEGACY_LOG_DIR, 'peer'), PEER_LOG_DIR)
    legacy_host_file = '/www/server/jh-panel/data/ha_manager_host_id.pl'
    _copy_if_missing(legacy_host_file, os.path.join(RUNTIME_DIR, 'host_id.pl'))


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
        data = json.loads(raw)
        if isinstance(data, str):
            data = json.loads(data)
        return data if isinstance(data, dict) else {}
    except Exception:
        result = {}
        for item in sys.argv[2:]:
            if ':' in item:
                key, value = item.split(':', 1)
                key = key.strip('{}')
                value = value.strip('{}')
                if key.startswith('options:'):
                    options = result.setdefault('options', {})
                    option_key = key.split(':', 1)[1]
                    if value in ('true', 'false'):
                        value = value == 'true'
                    options[option_key] = value
                else:
                    result[key] = value
        return result


def _dict_value(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _return(status, msg, data=None):
    return mw.returnJson(status, msg, data)


def _host_id():
    _ensure_dirs()
    host_file = os.path.join(RUNTIME_DIR, 'host_id.pl')
    current = ''
    if os.path.exists(host_file):
        current = mw.readFile(host_file).strip()
    if not current:
        current = 'H_PANEL_' + hashlib.sha1((mw.getHostAddr() + str(time.time())).encode('utf-8')).hexdigest()[:8].upper()
        mw.writeFile(host_file, current)
    return current


def _panel_title():
    try:
        title = mw.getConfig('title')
        if title:
            return str(title).strip()
    except Exception:
        pass
    title_path = '/www/server/jh-panel/data/title.pl'
    if os.path.exists(title_path):
        title = mw.readFile(title_path).strip()
        if title:
            return title
    return '江湖面板'


def _default_monitor_url():
    port = ''
    port_path = '/www/server/jh-monitor/data/port.pl'
    if os.path.exists(port_path):
        port = mw.readFile(port_path).strip()
    port = port or '10844'
    return 'http://{0}:{1}'.format(mw.getHostAddr(), port)


def _default_config():
    return {
        'monitor_url': _default_monitor_url(),
        'monitor_disabled': False,
        'pair_name': '生产面板主备',
        'pair_id': '',
        'api_secret': hashlib.sha256((str(time.time()) + mw.getRandomString(16)).encode('utf-8')).hexdigest(),
        'host_id': _host_id(),
        'host_name': _panel_title(),
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
            'run_checksum': False,
            'allow_checksum_diff': False,
            'sync_files': False,
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
    cfg['options'].update(_dict_value(saved.get('options')))
    cfg['host_name'] = _panel_title()
    if not cfg.get('monitor_disabled') and not cfg.get('monitor_url'):
        cfg['monitor_url'] = _default_monitor_url()
    if not cfg.get('pair_id'):
        source = cfg.get('host_id', '') + '_' + cfg.get('peer_public_ip', '')
        cfg['pair_id'] = 'HA_' + hashlib.sha1(source.encode('utf-8')).hexdigest()[:12].upper()
    return cfg


def _save_config(cfg):
    _write_json(CONFIG_PATH, cfg)
    return cfg


HA_CHECK_DEFS = [
    {'group': '计划任务', 'name': '备份数据库', 'type': 'crontab', 'target': '备份数据库[backupAll]', 'master': 'disabled', 'standby': 'enabled'},
    {'group': '计划任务', 'name': 'xtrabackup', 'type': 'crontab', 'target': '[勿删]xtrabackup-cron', 'master': 'disabled', 'standby': 'enabled'},
    {'group': '计划任务', 'name': 'xtrabackup-inc 全量备份', 'type': 'crontab', 'target': '[勿删]xtrabackup-inc全量备份', 'master': 'disabled', 'standby': 'enabled'},
    {'group': '计划任务', 'name': 'xtrabackup-inc 增量备份', 'type': 'crontab', 'target': '[勿删]xtrabackup-inc增量备份', 'master': 'disabled', 'standby': 'enabled'},
    {'group': '计划任务', 'name': '备份网站配置', 'type': 'crontab', 'target': '备份网站配置[backupAll]', 'master': 'enabled', 'standby': 'disabled'},
    {'group': '计划任务', 'name': '备份插件配置', 'type': 'crontab', 'target': ['备份插件配置[所有]', '备份插件配置[backupAll]'], 'master': 'enabled', 'standby': 'disabled'},
    {'group': '计划任务', 'name': '证书续签任务', 'type': 'crontab', 'target': "[勿删]续签Let's Encrypt证书", 'master': 'enabled', 'standby': 'disabled'},
    {'group': '计划任务', 'name': '恢复网站配置', 'type': 'crontab', 'target': '恢复网站配置[所有]', 'master': 'disabled', 'standby': 'enabled'},
    {'group': '计划任务', 'name': '恢复插件配置', 'type': 'crontab', 'target': '恢复插件配置[所有]', 'master': 'disabled', 'standby': 'enabled'},
    {'group': 'SSH 同步', 'name': 'authorized_keys 同步公钥', 'type': 'authorized_key', 'master': 'disabled', 'standby': 'enabled'},
    {'group': 'rsync', 'name': 'rsyncd 任务', 'type': 'rsyncd_tasks', 'master': 'enabled', 'standby': 'disabled'},
    {'group': 'rsync', 'name': 'lsyncd 服务', 'type': 'lsyncd_service', 'master': 'running', 'standby': 'stopped'},
    {'group': 'Web 服务', 'name': 'OpenResty', 'type': 'process', 'target': 'openresty', 'master': 'running', 'standby': 'stopped'},
    {'group': '监控提醒', 'name': '主从同步异常提醒', 'type': 'notify', 'target': 'mysql_slave_status_notice', 'master': 'enabled', 'standby': 'disabled'},
    {'group': '监控提醒', 'name': 'Rsync 状态异常提醒', 'type': 'notify', 'target': 'rsync_status_notice', 'master': 'enabled', 'standby': 'disabled'}
]


def _expected_text(value):
    return {
        'enabled': '应启用',
        'disabled': '应停用',
        'running': '应运行',
        'stopped': '应停止',
        'authorized': '应授权',
        'unauthorized': '应未授权'
    }.get(value, value)


def _actual_text(value):
    return {
        'enabled': '已启用',
        'disabled': '已停用',
        'missing': '不存在',
        'running': '运行中',
        'stopped': '已停止',
        'authorized': '已授权',
        'unauthorized': '未授权',
        'unknown': '未知'
    }.get(value, value)


def _check_crontab(name):
    names = name if isinstance(name, list) else [name]
    info = None
    for item in names:
        info = mw.M('crontab').where('name=?', (item,)).field('id,name,status').find()
        if info:
            break
    if not info:
        return 'missing'
    return 'enabled' if int(info.get('status') or 0) == 1 else 'disabled'


def _check_process(name):
    out = mw.execShell("ps -ef | grep -E '{0}' | grep -v grep | head -1".format(name))[0].strip()
    return 'running' if out else 'stopped'


def _rsyncd_tasks():
    data = _read_json('/www/server/rsyncd/config.json', {})
    return ((data.get('send') or {}).get('list') or [])


def _check_rsyncd_tasks(expected):
    tasks = _rsyncd_tasks()
    total = len(tasks)
    enabled_count = len([item for item in tasks if item.get('status', 'enabled') == 'enabled'])
    if total == 0:
        return 'skip', '无同步任务'
    if expected == 'enabled':
        return ('enabled' if enabled_count > 0 else 'disabled'), '同步任务 {0} 个，已启用 {1} 个'.format(total, enabled_count)
    return ('disabled' if enabled_count == 0 else 'enabled'), '同步任务 {0} 个，已启用 {1} 个'.format(total, enabled_count)


def _check_lsyncd_service(expected):
    tasks = _rsyncd_tasks()
    realtime_tasks = [item for item in tasks if item.get('realtime') == 'true']
    if len(realtime_tasks) == 0:
        return 'skip', '无实时同步任务'
    service_status = _check_process('lsyncd')
    return service_status, '实时任务 {0} 个，lsyncd {1}'.format(len(realtime_tasks), _actual_text(service_status))


def _check_notify(name):
    data = mw.getControlNotifyConfig()
    return 'enabled' if int(data.get(name) or 0) == 1 else 'disabled'


def _check_authorized_key():
    pub_path = '/root/.ssh/standby_sync.pub'
    auth_path = '/root/.ssh/authorized_keys'
    if not os.path.exists(pub_path) or not os.path.exists(auth_path):
        return 'unauthorized'
    pub = mw.readFile(pub_path).strip()
    auth = mw.readFile(auth_path)
    return 'authorized' if pub and pub in auth else 'unauthorized'


def _script_health_checks(cfg):
    role = cfg.get('role') if cfg.get('role') in ('master', 'standby') else 'standby'
    checks = []
    for item in HA_CHECK_DEFS:
        expected = item.get(role)
        actual_text = ''
        if item.get('type') == 'crontab':
            actual = _check_crontab(item.get('target'))
            ok = actual == expected or (expected == 'disabled' and actual == 'missing')
        elif item.get('type') == 'process':
            actual = _check_process(item.get('target'))
            ok = actual == expected
        elif item.get('type') == 'rsyncd_tasks':
            actual, actual_text = _check_rsyncd_tasks(expected)
            ok = actual == expected or actual == 'skip'
        elif item.get('type') == 'lsyncd_service':
            actual, actual_text = _check_lsyncd_service(expected)
            ok = actual == expected or actual == 'skip'
        elif item.get('type') == 'notify':
            actual = _check_notify(item.get('target'))
            ok = actual == expected
        elif item.get('type') == 'authorized_key':
            actual = _check_authorized_key()
            expected = 'authorized' if expected == 'enabled' else 'unauthorized'
            ok = actual == expected
        else:
            actual = 'unknown'
            ok = False
        checks.append({
            'group': item.get('group'),
            'name': item.get('name'),
            'expected': _expected_text(expected),
            'actual': actual_text or _actual_text(actual),
            'status': 'pass' if ok else 'fail'
        })
    return checks


def _health_snapshot(cfg):
    checks = _script_health_checks(cfg)
    mysql = {'status': 'normal', 'text': 'MySQL 检查待接入'}
    if os.path.exists('/www/server/mysql') or os.path.exists('/www/server/mariadb'):
        mysql = {'status': 'normal', 'text': '数据库目录存在'}
    openresty_failed = any([item.get('name') == 'OpenResty' and item.get('status') == 'fail' for item in checks])
    rsync_failed = any([item.get('group') == 'rsync' and item.get('status') == 'fail' for item in checks])
    return {
        'mysql': mysql,
        'rsync': {'status': 'warning' if rsync_failed else 'normal', 'text': 'rsync/lsyncd 状态' + ('不符合当前角色' if rsync_failed else '正常')},
        'openresty': {'status': 'warning' if openresty_failed else 'normal', 'text': 'OpenResty ' + ('不符合当前角色' if openresty_failed else '正常')},
        'ssh': {'status': 'normal' if cfg.get('bind_test_status') == 'success' else 'warning', 'text': 'SSH绑定' + ('已验证' if cfg.get('bind_test_status') == 'success' else '未验证')},
        'cloud': {'status': 'normal' if cfg.get('monitor_url') else 'warning', 'text': '云监控' + ('已配置' if cfg.get('monitor_url') else '未配置')},
        'lock': {'status': 'warning' if os.path.exists(LOCK_PATH) else 'normal', 'text': '本地切换锁' + ('存在' if os.path.exists(LOCK_PATH) else '空闲')},
        'script_checks': checks
    }


def _plugin_health_status(cfg, health_detail):
    return 'normal', '正常'


def _state(cfg=None):
    cfg = cfg or _config()
    state = _read_json(STATE_PATH, {})
    health_detail = _health_snapshot(cfg)
    health_status, health_text = _plugin_health_status(cfg, health_detail)
    state.update({
        'pair_id': cfg.get('pair_id'),
        'pair_name': cfg.get('pair_name'),
        'host_id': cfg.get('host_id'),
        'host_name': cfg.get('host_name'),
        'host_ip': cfg.get('host_ip'),
        'role': cfg.get('role'),
        'desired_role': cfg.get('desired_role'),
        'online_status': 'online',
        'health_status': health_status,
        'health_text': health_text,
        'health_detail': health_detail,
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
    switch_run_id = switch_run_id or 'latest'
    path = _switch_log_path(switch_run_id)
    seq = _seq()
    line = '[{0}] [{1}] [{2}] [{3}] {4}'.format(_now(), seq, phase, status, text)
    with open(path, 'a', encoding='utf-8') as fp:
        fp.write(line + '\n')
    return {'seq': seq, 'line': line, 'path': path}


def status():
    return 'start'


def get_state():
    cfg = _config()
    peer_state = collect_peer_state_raw(cfg)
    data = cfg.copy()
    data['health'] = _health_snapshot(cfg)
    data['state'] = _state(cfg)
    data['health_status'] = data['state'].get('health_status')
    data['health_text'] = data['state'].get('health_text')
    data['peer_state'] = peer_state.get('data') if peer_state.get('status') else None
    data['peer_collect_status'] = 'success' if peer_state.get('status') else 'failed'
    data['peer_collect_msg'] = peer_state.get('msg', '')
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
    for key in ('peer_public_ip', 'peer_ssh_port', 'peer_ssh_user', 'peer_public_key', 'peer_host_id'):
        if key in data:
            cfg[key] = str(data.get(key) or '').strip()
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
        return _return(True, 'SSH连接测试通过', cfg)
    return _return(False, 'SSH连接测试失败: ' + (err or out), cfg)


def save_monitor():
    data = _args()
    cfg = _config()
    for key in ('pair_name', 'monitor_url', 'poll_interval', 'report_interval'):
        if key in data:
            cfg[key] = data.get(key)
    cfg['monitor_disabled'] = False if cfg.get('monitor_url') else True
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
    cfg['monitor_disabled'] = True
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
    remote_path = REMOTE_STATE_PATH
    marker = '__HA_MANAGER_PANEL_TITLE__'
    title_cmd = "cd /www/server/jh-panel && python3 -c 'import sys; sys.path.append(\"/www/server/jh-panel/class/core\"); import mw; print(mw.getConfig(\"title\"))' 2>/dev/null || cat /www/server/jh-panel/data/title.pl 2>/dev/null || true"
    remote_cmd = "cat {0}; printf '\\n{1}\\n'; {2}".format(remote_path, marker, title_cmd)
    cmd = "ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p {0} {1}@{2} {3}".format(cfg.get('peer_ssh_port'), cfg.get('peer_ssh_user'), cfg.get('peer_public_ip'), shlex.quote(remote_cmd))
    out, err, code = mw.execShell(cmd, timeout=8)
    if code != 0:
        return {'status': False, 'msg': err or out or 'SSH采集失败'}
    try:
        state_text = out
        panel_title = ''
        if marker in out:
            state_text, panel_title = out.split(marker, 1)
            panel_title = panel_title.strip()
        state = json.loads(state_text.strip())
        if panel_title:
            state['host_name'] = panel_title
        return {'status': True, 'data': state}
    except Exception:
        return {'status': False, 'msg': '对端状态格式错误'}


def collect_peer_logs(cfg, peer_state):
    switch_run_id = peer_state.get('switch_run_id') or cfg.get('switch_run_id')
    peer_host_id = peer_state.get('host_id') or cfg.get('peer_host_id')
    if not switch_run_id or not peer_host_id or cfg.get('bind_test_status') != 'success':
        return {'status': False, 'msg': '缺少对端日志采集条件'}
    remote_path = os.path.join(REMOTE_SWITCH_LOG_DIR, switch_run_id + '.log')
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


def read_latest_log_text(switch_run_id=None):
    cfg = _config()
    path = _switch_log_path(switch_run_id or cfg.get('switch_run_id') or 'latest')
    if not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8', errors='replace') as fp:
        return fp.read()[-200000:]


def read_log():
    data = _args()
    cfg = _config()
    switch_run_id = data.get('switch_run_id') or cfg.get('switch_run_id')
    return _return(True, 'ok', {'log': read_latest_log_text(switch_run_id), 'log_path': cfg.get('log_path'), 'switch_run_id': switch_run_id, 'switch_status': cfg.get('switch_status')})


def _read_lock_pid():
    if not os.path.exists(LOCK_PATH):
        return 0
    try:
        return int((mw.readFile(LOCK_PATH) or '').strip())
    except Exception:
        return 0


def _pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _pid_cmdline(pid):
    try:
        with open('/proc/{0}/cmdline'.format(pid), 'rb') as fp:
            return fp.read().replace(b'\x00', b' ').decode('utf-8', errors='replace').strip()
    except Exception:
        return ''


def _is_ha_switch_process(pid):
    cmdline = _pid_cmdline(pid)
    return 'plugins/ha_manager/index.py' in cmdline and (' local_switch' in cmdline or ' switch_phase' in cmdline)


def _process_children(pid):
    children = []
    for name in os.listdir('/proc'):
        if not name.isdigit():
            continue
        child_pid = int(name)
        try:
            with open('/proc/{0}/stat'.format(child_pid), 'r') as fp:
                parts = fp.read().split()
            if len(parts) > 3 and int(parts[3]) == pid:
                children.append(child_pid)
        except Exception:
            continue
    result = []
    for child_pid in children:
        result.extend(_process_children(child_pid))
        result.append(child_pid)
    return result


def _terminate_pid_tree(pid):
    targets = _process_children(pid) + [pid]
    for target in targets:
        try:
            if target != pid:
                os.killpg(os.getpgid(target), signal.SIGTERM)
            os.kill(target, signal.SIGTERM)
        except Exception:
            pass
    time.sleep(2)
    for target in targets:
        if _pid_alive(target):
            try:
                if target != pid:
                    os.killpg(os.getpgid(target), signal.SIGKILL)
                os.kill(target, signal.SIGKILL)
            except Exception:
                pass


def _switch_lock_status_data():
    pid = _read_lock_pid()
    alive = _pid_alive(pid)
    return {'locked': os.path.exists(LOCK_PATH), 'pid': pid, 'alive': alive, 'cmdline': _pid_cmdline(pid) if alive else '', 'can_force_stop': alive and _is_ha_switch_process(pid)}


def switch_lock_status():
    return _return(True, 'ok', _switch_lock_status_data())


def force_stop_switch():
    cfg = _config()
    pid = _read_lock_pid()
    if not os.path.exists(LOCK_PATH):
        return _return(True, '当前没有正在执行的切换任务', _switch_lock_status_data())
    if not pid or not _pid_alive(pid):
        _unlock()
        cfg['switch_status'] = 'failed'
        _save_config(cfg)
        _append_switch_log(cfg.get('switch_run_id') or 'latest', 'switch', 'failed', '清理陈旧切换锁，原进程已不存在')
        return _return(True, '已清理陈旧切换锁', _switch_lock_status_data())
    if not _is_ha_switch_process(pid):
        return _return(False, '锁定进程不是 ha_manager 切换任务，已拒绝强制结束: ' + _pid_cmdline(pid))
    _append_switch_log(cfg.get('switch_run_id') or 'latest', 'switch', 'failed', '用户确认强制结束正在执行的切换任务，PID: ' + str(pid))
    _terminate_pid_tree(pid)
    _unlock()
    cfg['switch_status'] = 'failed'
    _save_config(cfg)
    _append_switch_log(cfg.get('switch_run_id') or 'latest', 'switch', 'failed', '已强制结束切换任务并清理锁，PID: ' + str(pid))
    return _return(True, '已强制结束切换任务', _switch_lock_status_data())


def _lock():
    if os.path.exists(LOCK_PATH):
        return False
    mw.writeFile(LOCK_PATH, str(os.getpid()))
    return True


def _unlock():
    if os.path.exists(LOCK_PATH):
        os.remove(LOCK_PATH)


def _remote_phase_options(cfg, phase):
    options = dict(cfg.get('options') or {})
    if phase in ('prepare_online', 'online'):
        options['local_ip'] = cfg.get('peer_public_ip')
        options['remote_ip'] = cfg.get('host_ip')
        options['remote_ssh_port'] = options.get('local_ssh_port') or '22'
    return options


def _phase_text(phase):
    if phase == 'prepare_online':
        return '预上线'
    if phase == 'online':
        return '正式上线'
    if phase == 'offline':
        return '下线'
    return phase


def _run_local_switch_phase(cfg, phase, role, switch_run_id, options=None, label='本机'):
    cfg['switch_run_id'] = switch_run_id
    cfg['switch_status'] = phase + '_running'
    cfg['options'].update(_dict_value(options))
    _save_config(cfg)
    _append_switch_log(switch_run_id, phase, 'start', label + '开始执行' + _phase_text(phase) + '脚本，目标角色：' + ('主' if role == 'master' else '备'))
    _run_executor(phase, cfg)
    if phase != 'prepare_online':
        cfg['role'] = role
        cfg['desired_role'] = role
    cfg['switch_status'] = phase + '_done'
    _save_config(cfg)
    _append_switch_log(switch_run_id, phase, 'success', label + _phase_text(phase) + '脚本执行完成')
    _state(cfg)
    report_switch_event(cfg, phase, 'success', label + _phase_text(phase) + '脚本执行完成')
    return cfg


def _run_remote_switch_phase(cfg, phase, role, switch_run_id, options=None):
    if not cfg.get('peer_public_ip') or cfg.get('bind_test_status') != 'success':
        raise RuntimeError('SSH未绑定或未验证，无法在对端执行切换脚本')
    payload = {
        'phase': phase,
        'role': role,
        'switch_run_id': switch_run_id,
        'options': options or {},
        'orchestrated': True
    }
    args = shlex.quote(json.dumps(payload, ensure_ascii=False))
    remote_cmd = 'cd /www/server/jh-panel && python3 /www/server/jh-panel/plugins/ha_manager/index.py switch_phase {0}'.format(args)
    cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=no', '-p', str(cfg.get('peer_ssh_port')), cfg.get('peer_ssh_user') + '@' + cfg.get('peer_public_ip'), remote_cmd]
    _append_switch_log(switch_run_id, phase, 'start', '开始通过 SSH 在对端执行' + _phase_text(phase) + '脚本')
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, preexec_fn=os.setsid)
    output_lines = []
    start_time = time.time()
    for line in iter(proc.stdout.readline, ''):
        if time.time() - start_time > 1800:
            proc.kill()
            raise RuntimeError('对端' + _phase_text(phase) + '脚本执行超时')
        line = line.strip()
        if not line:
            continue
        output_lines.append(line)
        output_lines = output_lines[-300:]
        if not line.startswith('{'):
            _append_switch_log(switch_run_id, phase, 'running', '对端: ' + line)
    code = proc.wait()
    out = '\n'.join(output_lines)
    if code != 0:
        raise RuntimeError('对端' + _phase_text(phase) + '脚本执行失败: ' + out[-2000:])
    try:
        result = json.loads(out.strip().split('\n')[-1])
    except Exception:
        raise RuntimeError('对端切换返回格式错误: ' + out[-1000:])
    if not result.get('status'):
        raise RuntimeError(result.get('msg') or '对端切换失败')
    _append_switch_log(switch_run_id, phase, 'success', '对端' + _phase_text(phase) + '脚本执行完成')
    return result.get('data') or {}


def switch_phase():
    data = _args()
    cfg = _config()
    phase = data.get('phase')
    role = data.get('role') or ('master' if phase in ('prepare_online', 'online') else 'standby')
    if phase not in ('offline', 'prepare_online', 'online'):
        return _return(False, '切换阶段无效')
    if role not in ('master', 'standby'):
        return _return(False, '目标角色无效')
    if not _lock():
        return _return(False, '已有切换任务正在执行')
    try:
        switch_run_id = data.get('switch_run_id') or 'LOCAL_' + time.strftime('%Y%m%d%H%M%S')
        cfg = _run_local_switch_phase(cfg, phase, role, switch_run_id, _dict_value(data.get('options')), '本机')
        return _return(True, '阶段执行完成', cfg)
    except Exception as e:
        _append_switch_log(cfg.get('switch_run_id') or data.get('switch_run_id') or 'failed', phase or 'switch', 'failed', str(e))
        cfg['switch_status'] = 'failed'
        _save_config(cfg)
        return _return(False, '阶段执行失败: ' + str(e))
    finally:
        _unlock()


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
        request_options = _dict_value(data.get('options'))
        switch_options = dict(_default_config().get('options') or {})
        switch_options.update(_dict_value(cfg.get('options')))
        switch_options.update(request_options)
        for key in ('run_checksum', 'allow_checksum_diff', 'sync_files', 'restore_site_setting', 'restore_plugin_setting', 'run_xtrabackup_inc_restore'):
            if key not in request_options:
                switch_options[key] = False
        if 'promote_mysql' not in request_options:
            switch_options['promote_mysql'] = True
        cfg['options'].update(switch_options)
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'switch', 'running', '本次预上线选项：sync_files={0}, run_checksum={1}, promote_mysql={2}'.format(str(switch_options.get('sync_files')).lower(), str(switch_options.get('run_checksum')).lower(), str(switch_options.get('promote_mysql')).lower()))
        if target_role == 'master':
            _append_switch_log(switch_run_id, 'switch', 'start', '切换主备开始：先在目标主机（本机）执行预上线，再在目标备用机（对端）执行下线，最后在目标主机（本机）执行正式上线')
            cfg = _run_local_switch_phase(cfg, 'prepare_online', 'master', switch_run_id, switch_options, '本机')
            _run_remote_switch_phase(cfg, 'offline', 'standby', switch_run_id, _remote_phase_options(cfg, 'offline'))
            cfg = _run_local_switch_phase(cfg, 'online', 'master', switch_run_id, switch_options, '本机')
        else:
            _append_switch_log(switch_run_id, 'switch', 'start', '切换主备开始：先在目标主机（对端）执行预上线，再在目标备用机（本机）执行下线，最后在目标主机（对端）执行正式上线')
            _run_remote_switch_phase(cfg, 'prepare_online', 'master', switch_run_id, _remote_phase_options(cfg, 'prepare_online'))
            cfg = _run_local_switch_phase(cfg, 'offline', 'standby', switch_run_id, switch_options, '本机')
            _run_remote_switch_phase(cfg, 'online', 'master', switch_run_id, _remote_phase_options(cfg, 'online'))
        cfg['desired_role'] = target_role
        cfg['switch_status'] = 'switch_done'
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'switch', 'success', '切换主备完成')
        _state(cfg)
        report_switch_event(cfg, 'switch', 'success', '切换主备完成')
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
    script_phase = 'online' if phase == 'prepare_online' else phase
    script = '/www/server/jh-panel/scripts/os_tool/vm/default/switch__generate_' + script_phase + '.sh'
    if not os.path.exists(script):
        raise RuntimeError('切换脚本不存在: ' + script)
    args = json.dumps(cfg.get('options') or {}, ensure_ascii=False)
    cmd = ['bash', script, '--plugin-run', '--args', args]
    env = os.environ.copy()
    if phase == 'prepare_online':
        env['HA_MANAGER_SWITCH_PHASE'] = 'prepare_online'
    _append_switch_log(cfg.get('switch_run_id'), phase, 'running', '执行真实切换脚本: ' + script + '，阶段：' + _phase_text(phase))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, preexec_fn=os.setsid, env=env)
    output_lines = []
    start_time = time.time()
    for line in iter(proc.stdout.readline, ''):
        if time.time() - start_time > 1800:
            proc.kill()
            raise RuntimeError(_phase_text(phase) + '脚本执行超时')
        if line.strip():
            output_lines.append(line.strip())
            output_lines = output_lines[-200:]
            _append_switch_log(cfg.get('switch_run_id'), phase, 'running', line.strip())
            print(line.strip())
            sys.stdout.flush()
            report_switch_event(cfg, phase, 'running', line.strip())
    code = proc.wait()
    if code != 0:
        output = '\n'.join(output_lines)
        raise RuntimeError(_phase_text(phase) + '脚本执行失败 exit_code={0}: {1}'.format(code, output[-2000:]))


def report_switch_event(cfg, phase, status, text, origin_host_id=None, seq=None, collect_method='local', switch_run_id=None):
    switch_run_id = switch_run_id or cfg.get('switch_run_id')
    if not cfg.get('monitor_url') or not switch_run_id or switch_run_id.startswith('LOCAL_'):
        return {'status': False, 'msg': '无需上报'}
    seq = seq or _seq()
    origin_host_id = origin_host_id or cfg.get('host_id')
    payload = {'pair_id': cfg.get('pair_id'), 'switch_run_id': switch_run_id, 'event_id': origin_host_id + '-' + str(seq), 'origin_host_id': origin_host_id, 'report_host_id': cfg.get('host_id'), 'collect_method': collect_method, 'seq': seq, 'phase': phase, 'step': text, 'status': status, 'log_text': text}
    return _post_monitor(cfg, 'ha_report_switch_event', payload, signed=True)


if __name__ == '__main__':
    _ensure_dirs()
    func = sys.argv[1] if len(sys.argv) > 1 else ''
    if func == 'status':
        print(status())
    elif func == 'get_state':
        print(get_state())
    elif func == 'save_binding':
        print(save_binding())
    elif func == 'get_local_public_key':
        print(get_local_public_key())
    elif func == 'get_key_info':
        print(get_key_info())
    elif func == 'generate_keypair':
        print(generate_keypair())
    elif func == 'init_keypair':
        print(init_keypair())
    elif func == 'test_peer_ssh':
        print(test_peer_ssh())
    elif func == 'save_monitor':
        print(save_monitor())
    elif func == 'clear_monitor':
        print(clear_monitor())
    elif func == 'report_state':
        print(report_state())
    elif func == 'poll_monitor':
        print(poll_monitor())
    elif func == 'read_log':
        print(read_log())
    elif func == 'switch_lock_status':
        print(switch_lock_status())
    elif func == 'force_stop_switch':
        print(force_stop_switch())
    elif func == 'switch_phase':
        print(switch_phase())
    elif func == 'local_switch':
        print(local_switch())
    else:
        print('error')
