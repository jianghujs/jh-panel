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
import urllib.parse
import urllib.request

PANEL_DIR = '/www/server/jh-panel'
sys.path.append(os.path.join(PANEL_DIR, 'class/core'))
import mw


PLUGIN_NAME = 'ha_manager'
PLUGIN_DIR = os.path.join(PANEL_DIR, 'plugins', PLUGIN_NAME)
RUNTIME_DIR = '/www/server/ha_manager'
SERVER_LOG_DIR = '/www/server/logs'
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
FAILOVER_STATE_PATH = os.path.join(DATA_DIR, 'failover_state.json')
RECOVERY_LOCK_PATH = os.path.join(DATA_DIR, 'recovery.lock')
CLOUD_TASK_CLAIMS_PATH = os.path.join(DATA_DIR, 'cloud_task_claims.json')
CLOUD_TASK_LAUNCHER_LOG_PATH = os.path.join(LOG_DIR, 'cloud_task_launcher.log')
CLOUD_INTERACTION_LOG_PATH = os.path.join(SERVER_LOG_DIR, 'ha_manager_cloud.log')
DRY_RUN = os.environ.get('HA_MANAGER_SWITCH_DRY_RUN') == '1'
SSH_PRIVATE_KEY_PATH = '/root/.ssh/id_rsa'
SSH_PUBLIC_KEY_PATH = '/root/.ssh/id_rsa.pub'
LEGACY_DATA_DIR = os.path.join(PLUGIN_DIR, 'data')
LEGACY_LOG_DIR = os.path.join(PLUGIN_DIR, 'logs')
REMOTE_STATE_PATH = '/www/server/ha_manager/data/state.json'
REMOTE_SWITCH_LOG_DIR = '/www/server/ha_manager/logs/switch'
PANEL_TITLE_STATE_PATH = '/www/server/jh-panel/data/ha_manager_title_state.json'


def _now():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


def _ensure_dirs():
    for path in (RUNTIME_DIR, DATA_DIR, LOG_DIR, SWITCH_LOG_DIR, PEER_LOG_DIR, SERVER_LOG_DIR):
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


def _read_failover_state():
    data = _read_json(FAILOVER_STATE_PATH, {})
    return data if isinstance(data, dict) else {}


def _write_failover_state(data):
    if not isinstance(data, dict):
        data = {}
    data['update_time'] = _now()
    _write_json(FAILOVER_STATE_PATH, data)
    return data


def _clear_failover_state():
    if os.path.exists(FAILOVER_STATE_PATH):
        os.remove(FAILOVER_STATE_PATH)


def _switch_state_fields():
    state = _read_failover_state()
    if not state:
        return {}
    keys = (
        'mode', 'current_master_host_id', 'pending_switch_required', 'pending_switch_host_id',
        'pending_switch_role', 'unreachable_host_id', 'coordinator_host_id', 'failover_run_id',
        'failover_time', 'reason', 'recovery_mode', 'recovery_status', 'recovery_required',
        'recovery_notified_at', 'recovery_run_id', 'recovery_error', 'update_time'
    )
    return dict([(key, state.get(key)) for key in keys if key in state])


def _coordination_state_data(cfg=None):
    cfg = cfg or _config()
    switch_state = _switch_state_fields()
    data = {
        'host_id': cfg.get('host_id'),
        'host_name': cfg.get('host_name'),
        'host_ip': cfg.get('host_ip'),
        'role': cfg.get('role'),
        'desired_role': cfg.get('desired_role'),
        'switch_status': cfg.get('switch_status') or 'idle',
        'switch_lock': _switch_lock_status_data(),
        'failover': switch_state,
        'mode': switch_state.get('mode') or 'normal',
        'pending_switch_required': bool(switch_state.get('pending_switch_required')),
        'pending_switch_host_id': switch_state.get('pending_switch_host_id') or '',
        'pending_switch_role': switch_state.get('pending_switch_role') or '',
        'recovery_status': switch_state.get('recovery_status') or '',
        'updated_at': _now()
    }
    return data


def get_coordination_state():
    cfg = _config()
    return _return(True, 'ok', _coordination_state_data(cfg))


def _write_panel_title_state(cfg):
    data = {
        'installed': True,
        'role': cfg.get('role') or 'unknown',
        'desired_role': cfg.get('desired_role') or cfg.get('role') or 'unknown',
        'switch_status': cfg.get('switch_status') or 'idle',
        'host_name': cfg.get('host_name') or _panel_title(),
        'updated_at': _now()
    }
    parent = os.path.dirname(PANEL_TITLE_STATE_PATH)
    if not os.path.exists(parent):
        os.makedirs(parent, mode=0o700, exist_ok=True)
    tmp = PANEL_TITLE_STATE_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    os.replace(tmp, PANEL_TITLE_STATE_PATH)
    try:
        os.chmod(PANEL_TITLE_STATE_PATH, 0o600)
    except Exception:
        pass
    return data


def _args():
    if len(sys.argv) < 3:
        return {}
    raw = ' '.join(sys.argv[2:])
    if '%' in raw:
        raw = urllib.parse.unquote(raw)
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


def _return_data(result):
    if isinstance(result, dict):
        return result
    try:
        data = json.loads(result or '{}')
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _host_id():
    _ensure_dirs()
    host_file = os.path.join(RUNTIME_DIR, 'host_id.pl')
    current = ''
    if os.path.exists(host_file):
        current = mw.readFile(host_file).strip()
    if not current:
        current = _new_host_id()
        mw.writeFile(host_file, current)
    return current


def _new_host_id(prefix='H_PANEL'):
    timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime())
    return prefix + '_' + timestamp + '_' + mw.getRandomString(8).upper()


def _is_legacy_host_id(host_id):
    text = str(host_id or '').strip()
    if not text.startswith('H_PANEL_'):
        return False
    suffix = text[len('H_PANEL_'):]
    return len(suffix) == 8 and all(ch in '0123456789ABCDEFabcdef' for ch in suffix)


def _set_host_id(cfg, host_id):
    host_id = str(host_id or '').strip()
    if not host_id:
        return cfg
    cfg['host_id'] = host_id
    mw.writeFile(os.path.join(RUNTIME_DIR, 'host_id.pl'), host_id)
    try:
        mw.writeFile('/www/server/jh-panel/data/ha_manager_host_id.pl', host_id)
    except Exception:
        pass
    return cfg


def _sync_host_id_file(cfg):
    changed = False
    current_ip = str(mw.getHostAddr() or cfg.get('host_ip') or '').strip()
    host_file = os.path.join(RUNTIME_DIR, 'host_id.pl')
    file_host_id = mw.readFile(host_file).strip() if os.path.exists(host_file) else ''
    host_id = str(cfg.get('host_id') or file_host_id or '').strip()
    if not host_id or _is_legacy_host_id(host_id):
        host_id = _new_host_id()
        cfg = _set_host_id(cfg, host_id)
        changed = True
    if str(cfg.get('host_ip') or '').strip() != current_ip:
        cfg['host_ip'] = current_ip
        changed = True
    if str(cfg.get('host_id') or '').strip() != host_id:
        cfg = _set_host_id(cfg, host_id)
        changed = True
    if file_host_id != host_id:
        mw.writeFile(host_file, host_id)
    return cfg, changed


def _repair_duplicate_host_id(cfg, peer):
    peer_id = str((peer or {}).get('host_id') or '').strip()
    peer_ip = str((peer or {}).get('host_ip') or cfg.get('peer_public_ip') or '').strip()
    local_id = str(cfg.get('host_id') or '').strip()
    local_ip = str(cfg.get('host_ip') or '').strip()
    if peer_id and local_id and peer_id == local_id:
        cfg = _set_host_id(cfg, _new_host_id())
        _save_config(cfg)
    return cfg


def _sync_binding_options(cfg):
    options = cfg.setdefault('options', {})
    changed = False
    local_ip = str(options.get('local_ip') or '').strip()
    if local_ip != str(cfg.get('host_ip') or mw.getHostAddr()).strip():
        options['local_ip'] = cfg.get('host_ip') or mw.getHostAddr()
        changed = True
    remote_ip = str(options.get('remote_ip') or '').strip()
    if remote_ip != str(cfg.get('peer_public_ip') or '').strip():
        options['remote_ip'] = cfg.get('peer_public_ip') or ''
        changed = True
    remote_ssh_port = str(options.get('remote_ssh_port') or '').strip()
    if remote_ssh_port != str(cfg.get('peer_ssh_port') or '22').strip():
        options['remote_ssh_port'] = cfg.get('peer_ssh_port') or '22'
        changed = True
    return changed


def _peer_host_id(ip):
    return _new_host_id('H_PEER')


def _report_peer_host_id(cfg, peer):
    peer_ip = str(peer.get('host_ip') or cfg.get('peer_public_ip') or '').strip()
    peer_id = str(peer.get('host_id') or '').strip()
    local_id = str(cfg.get('host_id') or '').strip()
    local_ip = str(cfg.get('host_ip') or '').strip()
    if peer_id and peer_id != local_id:
        return peer_id
    if peer_id == local_id and peer_ip and peer_ip != local_ip:
        return cfg.get('peer_host_id') or _peer_host_id(peer_ip)
    return peer_id or cfg.get('peer_host_id') or _peer_host_id(peer_ip)


def _peer_report_host(cfg, peer=None, report_time=None):
    peer = peer or {}
    has_peer_state = bool(peer)
    host = {
        'host_id': _report_peer_host_id(cfg, peer),
        'host_name': peer.get('host_name') or ('对端 ' + cfg.get('peer_public_ip', '')),
        'host_ip': peer.get('host_ip') or cfg.get('peer_public_ip'),
        'role': peer.get('role') or ('standby' if cfg.get('role') == 'master' else 'master'),
        'online_status': peer.get('online_status') or ('online' if has_peer_state else 'unknown'),
        'health_status': peer.get('health_status') or 'unknown',
        'health_detail': peer.get('health_detail') or {},
        'collect_status': 'success' if has_peer_state else 'unknown',
        'collect_method': 'ssh_peer' if has_peer_state else '',
        'report_host_id': cfg.get('host_id') if has_peer_state else '',
        'site_scope': _peer_site_scope(cfg, peer) if has_peer_state else '',
        'switch_run_id': _active_switch_run_id(peer),
        'switch_status': peer.get('switch_status') if _active_switch_run_id(peer) else ''
    }
    if report_time:
        host['last_report_at'] = report_time
    return host


def _active_switch_run_id(cfg):
    status = str(cfg.get('switch_status') or '').strip()
    run_id = str(cfg.get('switch_run_id') or '').strip()
    if not run_id:
        return ''
    if status in ('running', 'waiting_online') or status.endswith('_running'):
        return run_id
    return ''


def _peer_site_scope(cfg, peer):
    return 'remote'


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
        'auto_recover_as_standby': False,
        'options': {
            'local_ip': mw.getHostAddr(),
            'remote_ip': '',
            'remote_ssh_port': '22',
            'run_checksum': False,
            'sync_files': False,
            'sync_file_dirs': '/www/wwwroot,/www/wwwstorage',
            'sync_ignore_dirs': '.git,node_modules,logs,run',
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
    cfg['options'].pop('allow_checksum_diff', None)
    cfg['host_name'] = _panel_title()
    if not cfg.get('monitor_disabled') and not cfg.get('monitor_url'):
        cfg['monitor_url'] = _default_monitor_url()
    config_changed = False
    if cfg.get('peer_public_ip') and not cfg.get('peer_host_id'):
        cfg['peer_host_id'] = _peer_host_id(cfg.get('peer_public_ip'))
        config_changed = True
    cfg, identity_changed = _sync_host_id_file(cfg)
    if not cfg.get('pair_id'):
        source = cfg.get('host_id', '') + '_' + cfg.get('peer_public_ip', '')
        cfg['pair_id'] = 'HA_' + hashlib.sha1(source.encode('utf-8')).hexdigest()[:12].upper()
        config_changed = True
    if _sync_binding_options(cfg) or config_changed or identity_changed:
        _save_config(cfg)
    return cfg


def _save_config(cfg):
    _write_json(CONFIG_PATH, cfg)
    _write_panel_title_state(cfg)
    return cfg


HA_CHECK_DEFS = [
    {'group': '计划任务', 'name': '备份数据库', 'type': 'crontab', 'target': '备份数据库[backupAll]', 'master': 'disabled', 'standby': 'enabled'},
    {'group': '计划任务', 'name': 'xtrabackup', 'type': 'crontab', 'target': '[勿删]xtrabackup-cron', 'master': 'disabled', 'standby': 'enabled'},
    {'group': '计划任务', 'name': 'xtrabackup-inc 全量备份', 'type': 'crontab', 'target': '[勿删]xtrabackup-inc全量备份', 'master': 'disabled', 'standby': 'enabled'},
    {'group': '计划任务', 'name': 'xtrabackup-inc 增量备份', 'type': 'crontab', 'target': '[勿删]xtrabackup-inc增量备份', 'master': 'disabled', 'standby': 'enabled'},
    {'group': '计划任务', 'name': '备份网站配置', 'type': 'crontab', 'target': ['备份网站配置[所有]', '备份网站配置[backupAll]'], 'master': 'enabled', 'standby': 'disabled'},
    {'group': '计划任务', 'name': '备份插件配置', 'type': 'crontab', 'target': ['备份插件配置[所有]', '备份插件配置[backupAll]'], 'master': 'enabled', 'standby': 'disabled'},
    {'group': '计划任务', 'name': '证书续签任务', 'type': 'crontab', 'target': "[勿删]续签Let's Encrypt证书", 'master': 'enabled', 'standby': 'disabled'},
    {'group': '计划任务', 'name': '恢复网站配置', 'type': 'crontab', 'target': '恢复网站配置[所有]', 'master': 'disabled', 'standby': 'enabled'},
    {'group': '计划任务', 'name': '恢复插件配置', 'type': 'crontab', 'target': '恢复插件配置[所有]', 'master': 'disabled', 'standby': 'enabled'},
    {'group': 'SSH 同步', 'name': 'authorized_keys 同步公钥', 'type': 'authorized_key', 'master': 'disabled', 'standby': 'enabled'},
    {'group': 'rsync', 'name': 'rsyncd 任务', 'type': 'rsyncd_tasks', 'master': 'enabled', 'standby': 'disabled'},
    {'group': 'rsync', 'name': 'lsyncd 服务', 'type': 'lsyncd_service', 'master': 'running', 'standby': 'stopped'},
    {'group': 'Web 服务', 'name': 'OpenResty', 'type': 'openresty_service', 'master': 'running', 'standby': 'stopped'},
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


def _systemctl_is_active(name):
    out, err, code = mw.execShell('systemctl is-active {0}'.format(shlex.quote(name)))
    return code == 0 and out.strip() == 'active'


def _check_openresty_service(expected):
    openresty_active = _systemctl_is_active('openresty')
    nginx_active = _systemctl_is_active('nginx')
    if expected == 'running':
        if openresty_active and not nginx_active:
            return 'running', 'OpenResty 运行中'
        if openresty_active and nginx_active:
            return 'running_with_nginx', 'OpenResty 和系统 nginx 同时运行'
        if nginx_active:
            return 'nginx_running', '系统 nginx 运行中，OpenResty 未运行'
        return 'stopped', 'OpenResty 未运行'
    if openresty_active or nginx_active:
        active = []
        if openresty_active:
            active.append('OpenResty')
        if nginx_active:
            active.append('系统 nginx')
        return 'running', 'Web 服务运行中: ' + '、'.join(active)
    return 'stopped', 'Web 服务已停止'


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


def _run_health_check_item(item, role):
    expected = item.get(role)
    actual_text = ''
    if item.get('type') == 'crontab':
        actual = _check_crontab(item.get('target'))
        ok = actual == expected or (expected == 'disabled' and actual == 'missing')
    elif item.get('type') == 'process':
        actual = _check_process(item.get('target'))
        ok = actual == expected
    elif item.get('type') == 'openresty_service':
        actual, actual_text = _check_openresty_service(expected)
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
    return {
        'group': item.get('group'),
        'name': item.get('name'),
        'expected': _expected_text(expected),
        'actual': actual_text or _actual_text(actual),
        'status': 'pass' if ok else 'fail'
    }


def _script_health_checks_for_role(role):
    checks = []
    for item in HA_CHECK_DEFS:
        checks.append(_run_health_check_item(item, role))
    return checks


def _script_health_checks(cfg):
    role = cfg.get('role') if cfg.get('role') in ('master', 'standby') else 'standby'
    return _script_health_checks_for_role(role)


def _infer_role_from_script_state():
    scores = {}
    for role in ('master', 'standby'):
        checks = _script_health_checks_for_role(role)
        scores[role] = len([item for item in checks if item.get('status') == 'pass'])
    if scores.get('master', 0) >= scores.get('standby', 0) + 4:
        return 'master'
    if scores.get('standby', 0) >= scores.get('master', 0) + 4:
        return 'standby'
    return ''


def _switch_status_is_running(status):
    status = str(status or '')
    return status in ('running', 'waiting_online') or status.endswith('_running')


def _repair_role_from_script_state(cfg):
    if _switch_status_is_running(cfg.get('switch_status')):
        return cfg
    inferred_role = _infer_role_from_script_state()
    if inferred_role and inferred_role != cfg.get('role'):
        cfg['role'] = inferred_role
        cfg['desired_role'] = inferred_role
        _save_config(cfg)
    return cfg


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
    checks = []
    if isinstance(health_detail, dict) and isinstance(health_detail.get('script_checks'), list):
        checks = health_detail.get('script_checks')
    failed = [item for item in checks if isinstance(item, dict) and item.get('status') == 'fail']
    if failed:
        names = [str(item.get('name') or '').strip() for item in failed if str(item.get('name') or '').strip()]
        summary = '自检异常 {0} 项'.format(len(failed))
        if names:
            summary += '：' + '、'.join(names[:3])
            if len(names) > 3:
                summary += '等'
        if isinstance(health_detail, dict):
            health_detail['summary'] = summary
        return 'warning', summary
    if isinstance(health_detail, dict):
        health_detail['summary'] = '正常'
    return 'normal', '正常'


def _repair_role_from_switch_status(cfg):
    status = str(cfg.get('switch_status') or '')
    expected_role = ''
    if status == 'online_done':
        expected_role = 'master'
    elif status == 'offline_done':
        expected_role = 'standby'
    if expected_role and cfg.get('role') != expected_role:
        cfg['role'] = expected_role
        cfg['desired_role'] = expected_role
        _save_config(cfg)
    return cfg


def _state(cfg=None):
    cfg = cfg or _config()
    cfg = _repair_role_from_switch_status(cfg)
    cfg = _repair_role_from_script_state(cfg)
    state = _read_json(STATE_PATH, {})
    health_detail = _health_snapshot(cfg)
    switch_state = _switch_state_fields()
    if switch_state:
        health_detail['ha_failover'] = switch_state
        if switch_state.get('recovery_status') == 'recovery_guard':
            health_detail['summary'] = '待恢复为备机'
    health_status, health_text = _plugin_health_status(cfg, health_detail)
    if switch_state.get('mode') == 'degraded_master' or switch_state.get('pending_switch_required'):
        health_status = 'warning'
        health_text = '降级运行，等待对端恢复补全'
    if switch_state.get('recovery_status') == 'recovery_guard':
        health_status = 'warning'
        health_text = '恢复保护：待切换为备机'
    elif switch_state.get('recovery_status') == 'recovering_standby':
        health_status = 'warning'
        health_text = '正在恢复为备机'
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
        'failover': switch_state,
        'updated_at': _now()
    })
    _write_json(STATE_PATH, state)
    _write_panel_title_state(cfg)
    return state


def _seq():
    data = _read_json(SEQ_PATH, {'seq': 0})
    data['seq'] = int(data.get('seq') or 0) + 1
    _write_json(SEQ_PATH, data)
    return data['seq']


def _safe_int(value, default=0):
    try:
        return int(str(value).strip())
    except Exception:
        return default


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


def get_local_state():
    cfg = _config()
    return _return(True, 'ok', _state(cfg))


def regenerate_host_id():
    cfg = _config()
    old_host_id = cfg.get('host_id') or ''
    host_ip = mw.getHostAddr() or cfg.get('host_ip')
    new_host_id = _new_host_id()
    cfg = _set_host_id(cfg, new_host_id)
    cfg['host_ip'] = host_ip
    cfg.setdefault('options', {})['local_ip'] = host_ip
    _save_config(cfg)
    state = _state(cfg)
    report_result = _return_data(report_state()) if cfg.get('monitor_url') and not cfg.get('monitor_disabled') else {'status': True, 'msg': '未配置云监控，跳过上报'}
    return _return(True, 'host_id 已重新生成', {'old_host_id': old_host_id, 'host_id': new_host_id, 'host_ip': host_ip, 'state': state, 'report': report_result})


def title_state():
    cfg = _config()
    return _return(True, 'ok', _write_panel_title_state(cfg))


def save_binding():
    data = _args()
    cfg = _config()
    for key in ('peer_public_ip', 'peer_ssh_port', 'peer_ssh_user', 'peer_public_key', 'peer_host_id'):
        if key in data:
            cfg[key] = str(data.get(key) or '').strip()
    if not cfg.get('peer_public_ip') or not cfg.get('peer_public_key'):
        return _return(False, '请填写对方IP和对方公钥')
    if not cfg.get('peer_host_id'):
        cfg['peer_host_id'] = _peer_host_id(cfg.get('peer_public_ip'))
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


def _json_payload_text(payload, sort_keys=True):
    return json.dumps(payload, sort_keys=sort_keys, ensure_ascii=False, separators=(',', ':'))


def _sign(cfg, payload):
    timestamp = str(int(time.time()))
    nonce = hashlib.sha1((timestamp + mw.getRandomString(8)).encode('utf-8')).hexdigest()
    body = _json_payload_text(payload, True)
    body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    sign_text = '\n'.join([timestamp, nonce, body_hash])
    signature = hmac.new(str(cfg.get('api_secret')).encode('utf-8'), sign_text.encode('utf-8'), hashlib.sha256).hexdigest()
    return {'X-JH-Timestamp': timestamp, 'X-JH-Nonce': nonce, 'X-JH-Body-Hash': body_hash, 'X-JH-Signature': signature, 'Content-Type': 'application/json'}, body


def _post_monitor(cfg, action, payload, signed=True):
    url = cfg.get('monitor_url', '').rstrip('/') + '/pub/' + action
    if not cfg.get('monitor_url'):
        _append_cloud_interaction_log(action, 'skip', msg='云监控地址为空', pair_id=payload.get('pair_id') if isinstance(payload, dict) else '', host_id=cfg.get('host_id'))
        return {'status': False, 'msg': '云监控地址为空'}
    _append_cloud_interaction_log(action, 'request', url=url, signed=signed, pair_id=payload.get('pair_id') if isinstance(payload, dict) else '', host_id=cfg.get('host_id'), switch_run_id=payload.get('switch_run_id') if isinstance(payload, dict) else '', phase=payload.get('phase') if isinstance(payload, dict) else '', payload=payload)
    if signed:
        headers, body = _sign(cfg, payload)
    else:
        headers = {'Content-Type': 'application/json'}
        body = _json_payload_text(payload, False)
    req = urllib.request.Request(url, data=body.encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='replace')
            result = json.loads(text)
            _append_cloud_interaction_log(action, 'response', http_status=getattr(resp, 'status', ''), ok=result.get('status'), msg=result.get('msg'), pair_id=payload.get('pair_id') if isinstance(payload, dict) else '', host_id=cfg.get('host_id'), switch_run_id=payload.get('switch_run_id') if isinstance(payload, dict) else '', phase=payload.get('phase') if isinstance(payload, dict) else '', data=result.get('data'))
            return result
    except Exception as e:
        queue = _read_json(QUEUE_PATH, [])
        queue.append({'action': action, 'payload': payload, 'error': str(e), 'addtime': _now()})
        _write_json(QUEUE_PATH, queue[-200:])
        _append_cloud_interaction_log(action, 'error', error=str(e), pair_id=payload.get('pair_id') if isinstance(payload, dict) else '', host_id=cfg.get('host_id'), switch_run_id=payload.get('switch_run_id') if isinstance(payload, dict) else '', phase=payload.get('phase') if isinstance(payload, dict) else '')
        return {'status': False, 'msg': str(e)}


def _post_monitor_with_auth_retry(cfg, action, payload):
    res = _post_monitor(cfg, action, payload, signed=True)
    if res.get('status') or res.get('msg') != '签名错误':
        return res
    _append_cloud_interaction_log(action, 'auth_retry', msg='签名错误，尝试重新注册', pair_id=payload.get('pair_id') if isinstance(payload, dict) else '', host_id=cfg.get('host_id'), switch_run_id=payload.get('switch_run_id') if isinstance(payload, dict) else '')
    register = _return_data(_register_monitor(cfg))
    if not register.get('status'):
        return res
    cfg = _config()
    return _post_monitor(cfg, action, payload, signed=True)


def _register_monitor(cfg):
    peer_state = collect_peer_state_raw(cfg)
    peer = peer_state.get('data') if peer_state.get('status') else None
    desired_master_host_id = cfg.get('host_id') if cfg.get('role') == 'master' else _report_peer_host_id(cfg, peer or {})
    payload = {
        'pair_id': cfg.get('pair_id'),
        'pair_name': cfg.get('pair_name'),
        'api_secret': cfg.get('api_secret'),
        'desired_master_host_id': desired_master_host_id,
        'local_host': {'host_id': cfg.get('host_id'), 'host_name': cfg.get('host_name'), 'host_ip': cfg.get('host_ip'), 'role': cfg.get('role'), 'online_status': 'online'},
        'peer_host': _peer_report_host(cfg, peer)
    }
    res = _post_monitor(cfg, 'ha_register_pair', payload, signed=False)
    if res.get('status') and isinstance(res.get('data'), dict):
        cfg['pair_id'] = res['data'].get('pair_id') or cfg.get('pair_id')
        cfg['api_secret'] = res['data'].get('api_secret') or cfg.get('api_secret')
        cfg['last_report_at'] = _now()
        _save_config(cfg)
    return _return(bool(res.get('status')), res.get('msg') or '注册完成', cfg)


def save_auto_recover():
    data = _args()
    cfg = _config()
    cfg['auto_recover_as_standby'] = str(data.get('auto_recover_as_standby')).lower() in ('1', 'true', 'yes', 'on')
    _save_config(cfg)
    _append_cloud_interaction_log('save_auto_recover', 'done', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), auto_recover_as_standby=cfg.get('auto_recover_as_standby'))
    return _return(True, '自动故障恢复配置已保存', cfg)


def report_state():
    cfg = _config()
    if cfg.get('monitor_disabled') or not cfg.get('monitor_url'):
        return _return(True, '云监控地址为空，不上传状态', {'hosts': []})
    report_time = _now()
    report_batch_id = 'HRB_' + str(int(time.time())) + '_' + mw.getRandomString(6)
    local_state = _state(cfg)
    peer_state = collect_peer_state_raw(cfg)
    if peer_state.get('status'):
        repaired_cfg = _repair_duplicate_host_id(cfg, peer_state.get('data') or {})
        if repaired_cfg.get('host_id') != cfg.get('host_id'):
            cfg = repaired_cfg
            local_state = _state(cfg)
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
        'site_scope': 'local',
        'switch_run_id': _active_switch_run_id(cfg),
        'switch_status': cfg.get('switch_status') if _active_switch_run_id(cfg) else '',
        'last_report_at': report_time,
        'report_batch_id': report_batch_id
    }]
    if peer_state.get('status'):
        peer = peer_state.get('data') or {}
        collect_peer_logs(cfg, peer)
        peer_host = _peer_report_host(cfg, peer, report_time)
        peer_host['report_batch_id'] = report_batch_id
        hosts.append(peer_host)
    elif cfg.get('peer_host_id'):
        hosts.append({'host_id': cfg.get('peer_host_id'), 'host_name': '对端 ' + cfg.get('peer_public_ip', ''), 'host_ip': cfg.get('peer_public_ip'), 'role': 'unknown', 'online_status': 'unknown', 'health_status': 'unknown', 'collect_status': 'failed', 'collect_method': 'ssh_peer', 'report_host_id': cfg.get('host_id'), 'site_scope': 'remote', 'health_detail': {'summary': peer_state.get('msg')}, 'last_report_at': report_time, 'report_batch_id': report_batch_id})
    payload = {'pair_id': cfg.get('pair_id'), 'hosts': hosts, 'report_batch_id': report_batch_id}
    actual_master_id = ''
    for host in hosts:
        if host.get('role') == 'master':
            actual_master_id = host.get('host_id') or ''
            break
    if cfg.get('switch_status') == 'switch_done' and actual_master_id:
        payload['desired_master_host_id'] = actual_master_id
    res = _post_monitor_with_auth_retry(cfg, 'ha_report_state', payload)
    _append_cloud_interaction_log('report_state', 'done' if res.get('status') else 'failed', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), host_count=len(hosts), report_batch_id=report_batch_id, msg=res.get('msg'))
    if res.get('status'):
        cfg['last_report_at'] = _now()
        _save_config(cfg)
    return _return(bool(res.get('status')), res.get('msg') or '上报完成', {'hosts': hosts})


def _report_state_after_switch_delay(seconds=3):
    try:
        time.sleep(seconds)
        return _return_data(report_state())
    except Exception as e:
        return {'status': False, 'msg': str(e)}


def _report_peer_state_after_switch(switch_run_id):
    cfg = _config()
    if not cfg.get('peer_public_ip') or cfg.get('bind_test_status') != 'success':
        return {'status': False, 'msg': 'SSH未绑定或未验证'}
    remote_cmd = "cd /www/server/jh-panel && python3 /www/server/jh-panel/plugins/ha_manager/index.py report_state '{}'"
    _append_switch_log(switch_run_id, 'switch', 'running', '切换完成后触发对端状态上报，执行方式：SSH 远程触发')
    out, err, code = _ssh_peer_exec(cfg, remote_cmd, timeout=30)
    if code != 0:
        msg = err or out or '对端状态上报失败'
        _append_switch_log(switch_run_id, 'switch', 'running', '对端状态上报失败: ' + msg[-500:])
        return {'status': False, 'msg': msg}
    _append_switch_log(switch_run_id, 'switch', 'running', '对端状态上报完成')
    return {'status': True, 'msg': '对端状态上报完成'}


def _clear_peer_failover_state(cfg, switch_run_id):
    if not cfg.get('peer_public_ip') or cfg.get('bind_test_status') != 'success':
        return {'status': False, 'msg': 'SSH未绑定或未验证'}
    remote_cmd = "cd /www/server/jh-panel && python3 /www/server/jh-panel/plugins/ha_manager/index.py clear_failover_state '{}'"
    _append_switch_log(switch_run_id, 'switch', 'running', '恢复完成后清除对端待切换状态，执行方式：SSH 远程触发')
    out, err, code = _ssh_peer_exec(cfg, remote_cmd, timeout=20)
    if code != 0:
        msg = err or out or '清除对端待切换状态失败'
        _append_switch_log(switch_run_id, 'switch', 'running', '清除对端待切换状态失败: ' + msg[-500:])
        return {'status': False, 'msg': msg}
    result = _parse_plugin_json_output(out)
    if not result.get('status'):
        msg = result.get('msg') or '清除对端待切换状态失败'
        _append_switch_log(switch_run_id, 'switch', 'running', msg)
        return {'status': False, 'msg': msg}
    _append_switch_log(switch_run_id, 'switch', 'running', '对端待切换状态已清除')
    return {'status': True, 'msg': '对端待切换状态已清除'}


def _clear_failover_after_full_switch(cfg, switch_run_id):
    had_local_state = bool(_read_failover_state())
    if had_local_state:
        _clear_failover_state()
        _append_switch_log(switch_run_id, 'switch', 'running', '完整双边切换完成，已清理本机故障恢复状态')
    peer_result = _clear_peer_failover_state(cfg, switch_run_id)
    if peer_result.get('status'):
        _append_cloud_interaction_log('clear_failover_after_full_switch', 'done', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=switch_run_id, local_cleared=had_local_state, peer_cleared=True)
    else:
        _append_cloud_interaction_log('clear_failover_after_full_switch', 'partial', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=switch_run_id, local_cleared=had_local_state, peer_cleared=False, msg=peer_result.get('msg'))
    return peer_result


def _report_both_state_after_switch_delay(switch_run_id, seconds=3):
    _append_switch_log(switch_run_id, 'switch', 'running', '切换完成后等待 {0}s 执行双端状态上报'.format(seconds))
    local_result = _report_state_after_switch_delay(seconds)
    _append_switch_log(switch_run_id, 'switch', 'running', '本机状态上报' + ('完成' if local_result.get('status') else '失败: ' + str(local_result.get('msg') or '未知错误')[:500]))
    return _report_peer_state_after_switch(switch_run_id)


def _ssh_peer_exec(cfg, remote_cmd, timeout=15):
    cmd = "ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p {0} {1}@{2} {3}".format(cfg.get('peer_ssh_port'), cfg.get('peer_ssh_user'), cfg.get('peer_public_ip'), shlex.quote(remote_cmd))
    return mw.execShell(cmd, timeout=timeout)


def _parse_peer_state_output(out):
    result = json.loads(out.strip().split('\n')[-1])
    if isinstance(result, dict) and result.get('status') is True:
        state = result.get('data') or {}
    else:
        state = result
    if not isinstance(state, dict) or not state.get('host_id'):
        return None
    if state.get('switch_status') == 'online_done' and state.get('role') != 'master':
        state['role'] = 'master'
        state['desired_role'] = 'master'
    elif state.get('switch_status') == 'offline_done' and state.get('role') != 'standby':
        state['role'] = 'standby'
        state['desired_role'] = 'standby'
    state['collect_method'] = 'ssh_plugin'
    return state


def collect_peer_state_raw(cfg):
    if not cfg.get('peer_public_ip') or cfg.get('bind_test_status') != 'success':
        return {'status': False, 'msg': 'SSH未绑定或未验证'}
    remote_cmd = "cd /www/server/jh-panel && python3 /www/server/jh-panel/plugins/ha_manager/index.py get_local_state '{}'"
    out, err, code = _ssh_peer_exec(cfg, remote_cmd, timeout=15)
    if code == 0:
        try:
            state = _parse_peer_state_output(out)
            if state:
                return {'status': True, 'data': state}
        except Exception:
            pass

    py_code = 'import sys,json; sys.path.insert(0,"/www/server/jh-panel/plugins/ha_manager"); import index; index._ensure_dirs(); print(json.dumps({"status":True,"msg":"ok","data":index._state(index._config())}, ensure_ascii=False))'
    fallback_cmd = 'cd /www/server/jh-panel && python3 -c {0}'.format(shlex.quote(py_code))
    out2, err2, code2 = _ssh_peer_exec(cfg, fallback_cmd, timeout=15)
    if code2 != 0:
        return {'status': False, 'msg': err2 or out2 or err or out or 'SSH采集失败'}
    try:
        state = _parse_peer_state_output(out2)
        if not state:
            return {'status': False, 'msg': '对端状态格式错误'}
        state['collect_method'] = 'ssh_plugin_compat'
        return {'status': True, 'data': state}
    except Exception as e:
        return {'status': False, 'msg': '对端状态格式错误: ' + str(e)}


def _parse_plugin_json_output(out):
    try:
        return json.loads((out or '').strip().split('\n')[-1])
    except Exception as e:
        return {'status': False, 'msg': '插件返回格式错误: ' + str(e), 'raw': (out or '')[-1000:]}


def _peer_execution_ability(cfg):
    result = {
        'reachable': False,
        'ssh_ok': False,
        'plugin_ok': False,
        'config_ok': False,
        'lock_ok': False,
        'locked': False,
        'mode_reason': '',
        'peer': {},
        'checks': []
    }
    if not cfg.get('peer_public_ip'):
        result['mode_reason'] = '未绑定对端 IP'
        result['checks'].append({'name': 'ssh', 'status': 'failed', 'msg': result['mode_reason']})
        return result
    if cfg.get('bind_test_status') != 'success':
        result['mode_reason'] = 'SSH 未验证'
        result['checks'].append({'name': 'ssh', 'status': 'failed', 'msg': result['mode_reason']})
        return result
    out, err, code = _ssh_peer_exec(cfg, 'test -f /www/server/jh-panel/plugins/ha_manager/index.py && echo ok', timeout=8)
    result['ssh_ok'] = code == 0 and out.strip().endswith('ok')
    result['checks'].append({'name': 'ssh', 'status': 'success' if result['ssh_ok'] else 'failed', 'msg': 'SSH 可达' if result['ssh_ok'] else (err or out or 'SSH 不可达')})
    if not result['ssh_ok']:
        result['mode_reason'] = result['checks'][-1]['msg']
        return result
    remote_cmd = "cd /www/server/jh-panel && python3 /www/server/jh-panel/plugins/ha_manager/index.py get_coordination_state '{}'"
    out, err, code = _ssh_peer_exec(cfg, remote_cmd, timeout=12)
    if code != 0:
        result['mode_reason'] = err or out or '对端插件不可执行'
        result['checks'].append({'name': 'plugin', 'status': 'failed', 'msg': result['mode_reason']})
        return result
    parsed = _parse_plugin_json_output(out)
    if not parsed.get('status'):
        result['mode_reason'] = parsed.get('msg') or '对端插件返回失败'
        result['checks'].append({'name': 'plugin', 'status': 'failed', 'msg': result['mode_reason']})
        return result
    peer = parsed.get('data') or {}
    result['plugin_ok'] = True
    result['peer'] = peer
    result['checks'].append({'name': 'plugin', 'status': 'success', 'msg': '对端插件可执行'})
    result['config_ok'] = bool(peer.get('host_id'))
    result['checks'].append({'name': 'config', 'status': 'success' if result['config_ok'] else 'failed', 'msg': '对端配置完整' if result['config_ok'] else '对端 host_id 为空'})
    lock = peer.get('switch_lock') or {}
    result['locked'] = bool(lock.get('locked') and lock.get('alive'))
    result['lock_ok'] = not result['locked']
    result['checks'].append({'name': 'lock', 'status': 'success' if result['lock_ok'] else 'failed', 'msg': '对端切换锁空闲' if result['lock_ok'] else '对端已有切换任务 PID={0}'.format(lock.get('pid') or '')})
    result['reachable'] = result['ssh_ok'] and result['plugin_ok'] and result['config_ok'] and result['lock_ok']
    result['mode_reason'] = '对端可执行' if result['reachable'] else '；'.join([x.get('msg') for x in result['checks'] if x.get('status') == 'failed'])
    return result


def _switch_execution_mode(cfg, target_role=None):
    target_role = target_role or ('standby' if cfg.get('role') == 'master' else 'master')
    target_is_local = target_role == 'master'
    ability = _peer_execution_ability(cfg)
    if ability.get('reachable'):
        mode = 'full_switch'
        allowed = True
        msg = '本机与对端均可执行，允许完整双边切换'
    elif target_is_local:
        mode = 'local_failover'
        allowed = True
        msg = '对端不可达，本次将跳过对端下线并进入降级运行；请确认对端已停机、隔离或不会继续写入'
    else:
        mode = 'blocked_remote_unreachable'
        allowed = False
        msg = '目标主机为对端，但对端不可达，请到目标机房处理或等待目标恢复后再切换'
    data = {
        'mode': mode,
        'allowed': allowed,
        'message': msg,
        'reason': ability.get('mode_reason') or '',
        'target_role': target_role,
        'target_host_id': cfg.get('host_id') if target_is_local else (ability.get('peer') or {}).get('host_id') or cfg.get('peer_host_id') or '',
        'coordinator_host_id': cfg.get('host_id'),
        'peer_ability': ability
    }
    _append_cloud_interaction_log('check_switch_execution_mode', 'allowed' if allowed else 'blocked', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), mode=mode, target_role=target_role, reason=data.get('reason'), target_host_id=data.get('target_host_id'))
    return data


def check_switch_execution_mode():
    data = _args()
    cfg = _config()
    mode = _switch_execution_mode(cfg, data.get('target_role'))
    return _return(bool(mode.get('allowed')), mode.get('message'), mode)


def _require_failover_confirm(data, mode):
    if mode.get('mode') != 'local_failover':
        return True, ''
    confirmed = str(data.get('confirm_failover') or data.get('failover_confirmed') or '').lower() in ('1', 'true', 'yes', 'on')
    if confirmed:
        return True, ''
    return False, '对端不可达时执行本机故障升主需要确认：请确认对端已停机、隔离或不会继续写入'


def _record_local_failover_state(cfg, switch_run_id, reason='peer_unreachable'):
    peer_id = cfg.get('peer_host_id') or ''
    state = {
        'mode': 'degraded_master',
        'current_master_host_id': cfg.get('host_id'),
        'pending_switch_required': True,
        'pending_switch_host_id': peer_id,
        'pending_switch_host_ip': cfg.get('peer_public_ip') or '',
        'pending_switch_host_name': cfg.get('peer_host_name') or ('对端 ' + str(cfg.get('peer_public_ip') or '')),
        'pending_switch_role': 'standby',
        'unreachable_host_id': peer_id,
        'unreachable_host_ip': cfg.get('peer_public_ip') or '',
        'coordinator_host_id': cfg.get('host_id'),
        'failover_run_id': switch_run_id,
        'failover_time': _now(),
        'reason': reason,
        'recovery_mode': 'auto' if cfg.get('auto_recover_as_standby') else 'manual',
        'recovery_status': 'pending_peer_recovery',
        'recovery_required': True
    }
    _write_failover_state(state)
    _append_cloud_interaction_log('local_failover', 'recorded', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=switch_run_id, pending_switch_host_id=peer_id, reason=reason)
    return state


def _repair_failover_peer_identity(cfg, peer_coord=None):
    state = _read_failover_state()
    if not state:
        return state
    peer_coord = peer_coord or {}
    changed = False
    peer_host_id = str(peer_coord.get('host_id') or '').strip()
    peer_host_ip = str(peer_coord.get('host_ip') or cfg.get('peer_public_ip') or '').strip()
    if peer_host_id and state.get('pending_switch_host_id') != peer_host_id and (str(state.get('pending_switch_host_id') or '').startswith('H_PEER_') or state.get('pending_switch_host_ip') == peer_host_ip):
        state['pending_switch_host_id'] = peer_host_id
        state['unreachable_host_id'] = peer_host_id
        changed = True
    if peer_host_ip and state.get('pending_switch_host_ip') != peer_host_ip:
        state['pending_switch_host_ip'] = peer_host_ip
        state['unreachable_host_ip'] = peer_host_ip
        changed = True
    if peer_coord.get('host_name') and state.get('pending_switch_host_name') != peer_coord.get('host_name'):
        state['pending_switch_host_name'] = peer_coord.get('host_name')
        changed = True
    if changed:
        _write_failover_state(state)
        _append_cloud_interaction_log('repair_failover_peer_identity', 'done', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), pending_switch_host_id=state.get('pending_switch_host_id'), pending_switch_host_ip=state.get('pending_switch_host_ip'))
    return state


def _parse_time_ts(text):
    try:
        return int(time.mktime(time.strptime(str(text or ''), '%Y-%m-%d %H:%M:%S')))
    except Exception:
        return 0


def _pending_matches_local(cfg, pending_host_id, pending_host_ip):
    local_id = str(cfg.get('host_id') or '').strip()
    local_ip = str(cfg.get('host_ip') or mw.getHostAddr() or '').strip()
    pending_host_id = str(pending_host_id or '').strip()
    pending_host_ip = str(pending_host_ip or '').strip()
    if pending_host_id and pending_host_id == local_id:
        return True
    if pending_host_ip and pending_host_ip == local_ip:
        return True
    if pending_host_id.startswith('H_PEER_') and cfg.get('peer_host_id') == pending_host_id:
        return True
    return False


def _maybe_clear_normal_failover_state(cfg, switch_run_id=''):
    state = _read_failover_state()
    if not state:
        return
    if cfg.get('role') == 'master' and not state.get('pending_switch_required'):
        _clear_failover_state()
        return
    if cfg.get('role') == 'standby' and state.get('recovery_status') == 'recovered':
        _clear_failover_state()


def clear_failover_state():
    _clear_failover_state()
    cfg = _config()
    _state(cfg)
    _append_cloud_interaction_log('clear_failover_state', 'done', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'))
    return _return(True, '已清除故障恢复状态', _coordination_state_data(cfg))


def _notify_recovery_required(cfg, peer_coord, state):
    now = int(time.time())
    last_ts = _safe_int(state.get('last_notify_ts'), 0)
    if last_ts and now - last_ts < 1800:
        return {'status': True, 'msg': '通知已发送过，跳过重复通知'}
    title = '主备管理：{0} 待恢复为备机'.format(cfg.get('host_name') or cfg.get('host_id'))
    msg = '检测到当前主机需要补全为备用机。<br>当前主机：{0} ({1})<br>当前主机ID：{2}<br>对端当前主机：{3}<br>目标角色：备机<br>恢复方式：{4}<br>请进入江湖面板主备管理插件确认处理。'.format(
        cfg.get('host_name') or '', cfg.get('host_ip') or '', cfg.get('host_id') or '',
        peer_coord.get('current_master_host_id') or peer_coord.get('host_id') or '',
        '自动恢复' if cfg.get('auto_recover_as_standby') else '人工确认'
    )
    try:
        ok = mw.notifyMessage(msg=msg, msgtype='html', title=title, stype='主备故障恢复', trigger_time=0)
        state['last_notify_ts'] = now
        state['recovery_notified_at'] = _now()
        _write_failover_state(state)
        return {'status': bool(ok), 'msg': '通知已发送' if ok else '通知未发送或未配置'}
    except Exception as e:
        return {'status': False, 'msg': str(e)}


def _read_peer_coordination_state(cfg):
    ability = _peer_execution_ability(cfg)
    if ability.get('plugin_ok'):
        return {'status': True, 'data': ability.get('peer') or {}, 'ability': ability}
    return {'status': False, 'msg': ability.get('mode_reason') or '无法读取对端协调状态', 'ability': ability}


def _is_master_like(cfg):
    if cfg.get('role') == 'master' or cfg.get('desired_role') == 'master':
        return True
    inferred = _infer_role_from_script_state()
    return inferred == 'master'


def _mark_recovery_guard(cfg, peer_coord, reason):
    state = _read_failover_state()
    state.update({
        'mode': 'recovery_guard',
        'recovery_status': 'recovery_guard',
        'recovery_required': True,
        'pending_switch_required': True,
        'pending_switch_host_id': cfg.get('host_id'),
        'pending_switch_host_ip': cfg.get('host_ip') or mw.getHostAddr() or '',
        'pending_switch_host_name': cfg.get('host_name') or '',
        'pending_switch_role': 'standby',
        'current_master_host_id': peer_coord.get('current_master_host_id') or peer_coord.get('host_id') or '',
        'coordinator_host_id': peer_coord.get('coordinator_host_id') or peer_coord.get('host_id') or '',
        'reason': reason,
        'detected_at': state.get('detected_at') or _now()
    })
    _write_failover_state(state)
    _append_cloud_interaction_log('recovery_guard', 'entered', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), reason=reason, peer_current_master_host_id=state.get('current_master_host_id'))
    _notify_recovery_required(cfg, peer_coord, state)
    _state(cfg)
    report_state()
    return state


def recover_check():
    cfg = _config()
    if not cfg.get('peer_public_ip') or cfg.get('bind_test_status') != 'success':
        _append_cloud_interaction_log('recover_check', 'skip', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), msg='SSH未绑定或未验证')
        return _return(True, 'SSH未绑定或未验证，跳过恢复检查', _coordination_state_data(cfg))
    peer_res = _read_peer_coordination_state(cfg)
    if not peer_res.get('status'):
        _append_cloud_interaction_log('recover_check', 'skip', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), msg=peer_res.get('msg'))
        return _return(True, '无法确认对端协调状态，保持当前状态: ' + (peer_res.get('msg') or ''), {'peer': peer_res})
    peer_coord = peer_res.get('data') or {}
    peer_failover = peer_coord.get('failover') or {}
    local_failover = _repair_failover_peer_identity(cfg, peer_coord)
    pending_host = peer_failover.get('pending_switch_host_id') or peer_coord.get('pending_switch_host_id') or ''
    pending_ip = peer_failover.get('pending_switch_host_ip') or peer_coord.get('pending_switch_host_ip') or ''
    pending_role = peer_failover.get('pending_switch_role') or peer_coord.get('pending_switch_role') or ''
    peer_mode = peer_failover.get('mode') or peer_coord.get('mode') or ''
    matched = peer_mode == 'degraded_master' and pending_role == 'standby' and _pending_matches_local(cfg, pending_host, pending_ip)
    local_mode = local_failover.get('mode') or ''
    if not matched and peer_mode == 'degraded_master' and local_mode == 'degraded_master' and pending_role == 'standby':
        peer_ts = _parse_time_ts(peer_failover.get('failover_time') or peer_failover.get('update_time'))
        local_ts = _parse_time_ts(local_failover.get('failover_time') or local_failover.get('update_time'))
        matched = bool(peer_ts and local_ts and peer_ts > local_ts)
    _append_cloud_interaction_log('recover_check', 'checked', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), peer_mode=peer_mode, local_mode=local_mode, pending_switch_host_id=pending_host, pending_switch_host_ip=pending_ip, pending_switch_role=pending_role, local_role=cfg.get('role'), matched=matched)
    if not matched:
        return _return(True, '未发现本机待恢复为备机标识', {'peer': peer_coord, 'local': _coordination_state_data(cfg)})
    if not _is_master_like(cfg):
        if local_failover:
            _clear_failover_state()
            _append_cloud_interaction_log('recover_check', 'cleared', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), msg='本机已不是主角色，清理本机故障恢复状态')
            report_state()
        return _return(True, '本机已不是主角色，无需执行恢复保护', {'peer': peer_coord, 'local': _coordination_state_data(cfg)})
    state = _mark_recovery_guard(cfg, peer_failover, '本机匹配对端待切换为备机标识或双降级状态下对端故障升主时间更新')
    guard_run_id = state.get('recovery_run_id') or state.get('failover_run_id') or cfg.get('switch_run_id') or 'RECOVERY_GUARD'
    _append_switch_log(guard_run_id, 'recovery_guard', 'running', '检测到旧主恢复后需要补全为备机，当前进入恢复保护')
    if cfg.get('auto_recover_as_standby'):
        _append_switch_log(guard_run_id, 'recovery_guard', 'running', '自动恢复为备机已开启，准备执行 recover_as_standby')
        result = _return_data(recover_as_standby())
        return _return(bool(result.get('status')), result.get('msg') or '自动恢复处理完成', {'guard': state, 'recover': result})
    _append_switch_log(guard_run_id, 'recovery_guard', 'running', '自动恢复为备机未开启，不自动执行备机化脚本；请在插件总览页点击“恢复为备机”人工确认执行')
    return _return(True, '已进入恢复保护，等待人工确认恢复为备机', {'guard': state})


def _recovery_lock():
    if os.path.exists(RECOVERY_LOCK_PATH):
        pid = _safe_int(mw.readFile(RECOVERY_LOCK_PATH), 0)
        if pid and _pid_alive(pid):
            return False
        os.remove(RECOVERY_LOCK_PATH)
    mw.writeFile(RECOVERY_LOCK_PATH, str(os.getpid()))
    return True


def _recovery_unlock():
    if os.path.exists(RECOVERY_LOCK_PATH):
        os.remove(RECOVERY_LOCK_PATH)


def recover_as_standby():
    data = _args()
    cfg = _config()
    state = _read_failover_state()
    if not state.get('recovery_required') and not data.get('force'):
        return _return(False, '当前没有待恢复为备机状态')
    if not _recovery_lock():
        return _return(False, '已有恢复为备机任务正在执行')
    switch_run_id = data.get('switch_run_id') or state.get('recovery_run_id') or 'RECOVER_' + time.strftime('%Y%m%d%H%M%S')
    try:
        state['recovery_status'] = 'recovering_standby'
        state['recovery_run_id'] = switch_run_id
        _write_failover_state(state)
        cfg['switch_run_id'] = switch_run_id
        cfg['switch_status'] = 'offline_running'
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'offline', 'start', '开始恢复为备机，执行方式：本机直接执行，来源：主备管理插件恢复检查')
        _append_cloud_interaction_log('recover_as_standby', 'start', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=switch_run_id)
        options = _switch_options_from_request(cfg, _dict_value(data.get('options')))
        cfg = _run_local_switch_phase(cfg, 'offline', 'standby', switch_run_id, options, '本机恢复为备机', True, True)
        state['mode'] = 'recovered'
        state['recovery_status'] = 'recovered'
        state['pending_switch_required'] = False
        state['recovery_required'] = False
        state['recovered_at'] = _now()
        _write_failover_state(state)
        cfg['switch_status'] = 'recovered_standby_done'
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'offline', 'success', '恢复为备机完成')
        _clear_peer_failover_state(cfg, switch_run_id)
        _append_cloud_interaction_log('recover_as_standby', 'success', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=switch_run_id)
        report_state()
        return _return(True, '恢复为备机完成', cfg)
    except Exception as e:
        state['recovery_status'] = 'failed'
        state['recovery_error'] = str(e)
        _write_failover_state(state)
        cfg['switch_status'] = 'failed'
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'offline', 'failed', '恢复为备机失败: ' + str(e))
        _append_cloud_interaction_log('recover_as_standby', 'failed', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=switch_run_id, error=str(e))
        report_state()
        return _return(False, '恢复为备机失败: ' + str(e))
    finally:
        _recovery_unlock()


def collect_peer_logs(cfg, peer_state):
    switch_run_id = peer_state.get('switch_run_id') or cfg.get('switch_run_id')
    peer_host_id = _report_peer_host_id(cfg, peer_state)
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
            if '[switch]' in line and ('切换完成后触发对端状态上报' in line or '对端状态上报完成' in line or '对端状态上报失败' in line):
                continue
            report_switch_event(cfg, 'peer_log', 'running', line, origin_host_id=peer_host_id, seq=index, collect_method='ssh_peer', switch_run_id=switch_run_id)
    return {'status': True, 'data': {'path': local_path, 'new_count': len(new_lines)}}


def poll_monitor():
    cfg = _config()
    if cfg.get('monitor_disabled') or not cfg.get('monitor_url'):
        _append_cloud_interaction_log('poll_monitor', 'skip', msg='云监控地址为空或已禁用', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'))
        return _return(True, '云监控地址为空，不轮询期望状态', cfg)
    payload = {'pair_id': cfg.get('pair_id'), 'host_id': cfg.get('host_id')}
    res = _post_monitor_with_auth_retry(cfg, 'ha_pull_desired_state', payload)
    if res.get('status') and isinstance(res.get('data'), dict):
        run = res['data'].get('switch_run') or {}
        desired = res['data'].get('desired_master_host_id')
        _append_cloud_interaction_log('poll_monitor', 'pulled', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), desired_master_host_id=desired, switch_run_id=run.get('switch_run_id') or '', phase=run.get('execute_phase') or run.get('current_phase') or '', execute_method=run.get('execute_method') or '', execute_target_host_id=run.get('execute_target_host_id') or '', run_status=run.get('status') or '')
        desired_role = 'master' if desired == cfg.get('host_id') else 'standby'
        cfg['desired_role'] = desired_role
        if run.get('switch_run_id'):
            cfg['switch_run_id'] = run.get('switch_run_id')
            cfg['switch_status'] = run.get('status') or cfg.get('switch_status')
            cfg['log_path'] = run.get('log_path') or cfg.get('log_path')
        elif desired:
            cfg['role'] = desired_role
            if str(cfg.get('switch_status') or '').endswith('_running') or cfg.get('switch_status') == 'running':
                cfg['switch_status'] = 'idle'
        _save_config(cfg)
        _start_cloud_switch_phase(cfg, run)
    return _return(bool(res.get('status')), res.get('msg') or '轮询完成', cfg)


def _start_cloud_switch_phase(cfg, run):
    if not isinstance(run, dict) or not run.get('switch_run_id') or not run.get('execute_phase'):
        switch_run_id = run.get('switch_run_id') if isinstance(run, dict) else ''
        phase = run.get('current_phase') if isinstance(run, dict) else ''
        reason = run.get('dispatch_reason') if isinstance(run, dict) else ''
        msg = '无可执行切换阶段' + (': ' + reason if reason else '')
        _append_cloud_interaction_log('start_switch_task', 'skip', msg=msg, pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=switch_run_id, phase=run.get('execute_phase') if isinstance(run, dict) else '', current_phase=phase, execute_method=run.get('execute_method') if isinstance(run, dict) else '', execute_target_host_id=run.get('execute_target_host_id') if isinstance(run, dict) else '', run_status=run.get('status') if isinstance(run, dict) else '')
        if switch_run_id and reason:
            text = '云监控任务暂未下发给当前插件：任务ID={0}，当前阶段={1}，原因：{2}'.format(switch_run_id, _phase_text(phase), reason)
            _append_switch_log(switch_run_id, phase or 'switch', 'running', text)
            report_switch_event(cfg, phase or 'switch', 'running', text, switch_run_id=switch_run_id)
        return
    phase = run.get('execute_phase')
    run_status = str(run.get('status') or '').strip()
    if run_status not in ('pending_prepare', 'pending_finalize', 'pending_online', 'running'):
        _append_cloud_interaction_log('start_switch_task', 'skip', msg='任务状态不可领取', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=run.get('switch_run_id'), phase=phase, run_status=run_status)
        return
    claim_key = _cloud_task_claim_key(run.get('switch_run_id'), phase)
    claims = _read_cloud_task_claims()
    claim = claims.get(claim_key) if isinstance(claims.get(claim_key), dict) else {}
    lock_pid = _read_lock_pid()
    running_status = phase + '_running'
    claim_running_pid = _safe_int(claim.get('pid'), 0)
    if claim.get('status') == 'running' and claim_running_pid and _pid_alive(claim_running_pid):
        text = '云监控任务已领取，当前阶段正在执行中：任务ID={0}，阶段={1}，PID={2}，等待脚本输出或完成确认'.format(run.get('switch_run_id'), _phase_text(phase), claim_running_pid)
        _append_cloud_interaction_log('start_switch_task', 'skip', msg='本阶段已有执行进程', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=run.get('switch_run_id'), phase=phase, pid=claim_running_pid, run_status=run_status)
        _append_cloud_task_launcher_log('skip cloud task switch_run_id={0} phase={1} pid={2} reason=same_phase_already_running'.format(run.get('switch_run_id'), phase, claim_running_pid))
        _emit_cloud_claim_notice(cfg, run, phase, text, claim_key, claim)
        return
    if lock_pid and _pid_alive(lock_pid) and cfg.get('switch_run_id') == run.get('switch_run_id') and cfg.get('switch_status') in (running_status, 'running'):
        text = '云监控任务已领取，当前阶段正在执行中：任务ID={0}，阶段={1}，本地锁PID={2}，等待脚本输出或完成确认'.format(run.get('switch_run_id'), _phase_text(phase), lock_pid)
        _append_cloud_interaction_log('start_switch_task', 'skip', msg='当前阶段正在执行', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=run.get('switch_run_id'), phase=phase, lock_pid=lock_pid, current_switch_status=cfg.get('switch_status'), run_status=run_status)
        _append_cloud_task_launcher_log('skip cloud task switch_run_id={0} phase={1} lock_pid={2} current_switch_status={3} reason=same_phase_lock_running'.format(run.get('switch_run_id'), phase, lock_pid, cfg.get('switch_status')))
        _emit_cloud_claim_notice(cfg, run, phase, text, claim_key, claim)
        return
    if lock_pid and _pid_alive(lock_pid) and cfg.get('switch_run_id') == run.get('switch_run_id'):
        text = '云监控任务暂未领取下一阶段：同一切换任务上一阶段仍在收尾，本地锁PID={0}，当前本机状态={1}，等待下一轮轮询'.format(lock_pid, cfg.get('switch_status') or '--')
        _append_cloud_interaction_log('start_switch_task', 'defer', msg='同一切换任务上一阶段仍在收尾，等待本地锁释放后再领取下一阶段', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=run.get('switch_run_id'), phase=phase, lock_pid=lock_pid, current_switch_status=cfg.get('switch_status'), run_status=run_status)
        _append_cloud_task_launcher_log('defer cloud task switch_run_id={0} phase={1} lock_pid={2} current_switch_status={3} reason=same_run_previous_phase_finishing'.format(run.get('switch_run_id'), phase, lock_pid, cfg.get('switch_status')))
        _emit_cloud_claim_notice(cfg, run, phase, text, claim_key, claim)
        return
    for key, old_claim in list(claims.items()):
        if key == claim_key or not isinstance(old_claim, dict):
            continue
        if old_claim.get('switch_run_id') != run.get('switch_run_id') or old_claim.get('status') != 'running':
            continue
        old_pid = _safe_int(old_claim.get('pid'), 0)
        if old_pid and _pid_alive(old_pid):
            text = '云监控任务暂未领取下一阶段：同一切换任务的 {0} 阶段仍在执行，PID={1}，等待下一轮轮询'.format(_phase_text(old_claim.get('phase')), old_pid)
            _append_cloud_interaction_log('start_switch_task', 'defer', msg='同一切换任务已有其他阶段执行进程，等待结束后再领取下一阶段', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=run.get('switch_run_id'), phase=phase, old_phase=old_claim.get('phase'), old_pid=old_pid, run_status=run_status)
            _append_cloud_task_launcher_log('defer cloud task switch_run_id={0} phase={1} old_phase={2} old_pid={3} reason=other_phase_running'.format(run.get('switch_run_id'), phase, old_claim.get('phase'), old_pid))
            _emit_cloud_claim_notice(cfg, run, phase, text, claim_key, claim)
            return
    _preempt_old_cloud_switch_tasks(cfg, run.get('switch_run_id'), phase)
    claim = _get_cloud_task_claim(claim_key)
    if claim.get('status') == 'done':
        cfg['switch_run_id'] = run.get('switch_run_id')
        cfg['log_path'] = run.get('log_path') or cfg.get('log_path')
        _save_config(cfg)
        _append_cloud_interaction_log('start_switch_task', 'skip', msg='本阶段本机已完成，补发确认', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=run.get('switch_run_id'), phase=phase, run_status=run_status)
        ack_switch_phase(cfg, phase, 'success', _phase_text(phase) + '完成')
        return
    if cfg.get('switch_run_id') == run.get('switch_run_id') and cfg.get('switch_status') == running_status and (_pid_alive(lock_pid) or _pid_alive(claim_running_pid)):
        _append_cloud_interaction_log('start_switch_task', 'skip', msg='当前阶段正在执行', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=run.get('switch_run_id'), phase=phase, lock_pid=lock_pid, claim_pid=claim_running_pid, run_status=run_status)
        return
    options = _dict_value(run.get('options_json') or run.get('options'))
    for key in ('local_ip', 'remote_ip', 'remote_ssh_port'):
        if key in options and not str(options.get(key) or '').strip():
            options.pop(key, None)
    payload = {
        'phase': phase,
        'role': run.get('execute_role') or ('master' if phase in ('prepare_online', 'online') else 'standby'),
        'switch_run_id': run.get('switch_run_id'),
        'options': options,
        'orchestrated': True,
        'execute_method': run.get('execute_method') or 'local',
        'execute_target_host_id': run.get('execute_target_host_id') or ''
    }
    cfg['switch_run_id'] = run.get('switch_run_id')
    cfg['switch_status'] = running_status
    cfg['log_path'] = run.get('log_path') or cfg.get('log_path')
    _save_config(cfg)
    claim_text = '已领取云监控任务：任务ID={0}，阶段={1}，执行方式={2}，目标主机={3}'.format(run.get('switch_run_id'), _phase_text(phase), payload.get('execute_method'), payload.get('execute_target_host_id') or '--')
    _append_switch_log(run.get('switch_run_id'), phase, 'start', claim_text)
    _append_cloud_interaction_log('claim_switch_task', 'claimed', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=run.get('switch_run_id'), phase=phase, execute_method=payload.get('execute_method'), execute_target_host_id=payload.get('execute_target_host_id') or '', role=payload.get('role'), run_status=run_status)
    cmd = ['python3', os.path.join(PLUGIN_DIR, 'index.py'), 'switch_phase', json.dumps(payload, ensure_ascii=False)]
    stdout_fp = open(CLOUD_TASK_LAUNCHER_LOG_PATH, 'a', encoding='utf-8')
    try:
        stdout_fp.write('[{0}] start {1} pid_launch switch_run_id={2} phase={3} execute_method={4} execute_target_host_id={5}\n'.format(_now(), cfg.get('host_id') or 'unknown', run.get('switch_run_id'), phase, payload.get('execute_method'), payload.get('execute_target_host_id')))
        stdout_fp.flush()
    except Exception:
        pass
    proc = subprocess.Popen(cmd, cwd=PANEL_DIR, stdout=stdout_fp, stderr=subprocess.STDOUT, start_new_session=True)
    _append_cloud_interaction_log('start_switch_task', 'started', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=run.get('switch_run_id'), phase=phase, pid=proc.pid, execute_method=payload.get('execute_method'), execute_target_host_id=payload.get('execute_target_host_id') or '')
    try:
        stdout_fp.close()
    except Exception:
        pass
    _set_cloud_task_claim(claim_key, {'status': 'running', 'pid': proc.pid, 'switch_run_id': run.get('switch_run_id'), 'phase': phase, 'update_time': _now()})


def _cloud_task_claim_key(switch_run_id, phase):
    return str(switch_run_id or '') + ':' + str(phase or '')


def _read_cloud_task_claims():
    try:
        data = json.loads(mw.readFile(CLOUD_TASK_CLAIMS_PATH) or '{}')
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_cloud_task_claims(data):
    if not isinstance(data, dict):
        data = {}
    mw.writeFile(CLOUD_TASK_CLAIMS_PATH, json.dumps(data, ensure_ascii=False, indent=2))


def _get_cloud_task_claim(key):
    data = _read_cloud_task_claims()
    item = data.get(key) or {}
    return item if isinstance(item, dict) else {}


def _set_cloud_task_claim(key, item):
    data = _read_cloud_task_claims()
    data[key] = item if isinstance(item, dict) else {}
    if len(data) > 100:
        for old_key in sorted(data.keys())[:-100]:
            data.pop(old_key, None)
    _write_cloud_task_claims(data)


def _emit_cloud_claim_notice(cfg, run, phase, text, claim_key, claim=None, interval=30):
    try:
        now_ts = int(time.time())
        claim = dict(claim or {})
        last_ts = _safe_int(claim.get('last_notice_ts'), 0)
        if last_ts and now_ts - last_ts < interval:
            return
        switch_run_id = run.get('switch_run_id') if isinstance(run, dict) else cfg.get('switch_run_id')
        _append_switch_log(switch_run_id, phase or 'switch', 'running', text)
        report_switch_event(cfg, phase or 'switch', 'running', text, switch_run_id=switch_run_id)
        if claim_key:
            claim['last_notice_ts'] = now_ts
            claim['last_notice_text'] = text[:500]
            claim['update_time'] = _now()
            _set_cloud_task_claim(claim_key, claim)
    except Exception:
        pass


def _append_cloud_task_launcher_log(text):
    try:
        _ensure_dirs()
        with open(CLOUD_TASK_LAUNCHER_LOG_PATH, 'a', encoding='utf-8') as fp:
            fp.write('[{0}] {1}\n'.format(_now(), text))
    except Exception:
        pass


def _short_json(data, max_len=1200):
    try:
        text = json.dumps(data, ensure_ascii=False, sort_keys=True)
    except Exception:
        text = str(data)
    text = text.replace('\n', ' ')
    if len(text) > max_len:
        text = text[:max_len] + '...'
    return text


def _append_cloud_interaction_log(action, status='info', **kwargs):
    try:
        _ensure_dirs()
        if os.path.exists(CLOUD_INTERACTION_LOG_PATH) and os.path.getsize(CLOUD_INTERACTION_LOG_PATH) > 5 * 1024 * 1024:
            backup_path = CLOUD_INTERACTION_LOG_PATH + '.1'
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(CLOUD_INTERACTION_LOG_PATH, backup_path)
        parts = ['[{0}]'.format(_now()), 'action={0}'.format(action), 'status={0}'.format(status)]
        for key in sorted(kwargs.keys()):
            if key in ('api_secret', 'signature', 'peer_public_key'):
                continue
            value = kwargs.get(key)
            if isinstance(value, (dict, list)):
                value = _short_json(value)
            value = str(value if value is not None else '').replace('\n', ' ')
            if len(value) > 1200:
                value = value[:1200] + '...'
            parts.append('{0}={1}'.format(key, value))
        with open(CLOUD_INTERACTION_LOG_PATH, 'a', encoding='utf-8') as fp:
            fp.write(' '.join(parts) + '\n')
    except Exception:
        pass


def _preempt_old_cloud_switch_tasks(cfg, switch_run_id, phase):
    switch_run_id = str(switch_run_id or '').strip()
    phase = str(phase or '').strip()
    if not switch_run_id:
        return False
    current_key = _cloud_task_claim_key(switch_run_id, phase)
    stopped = False
    claims = _read_cloud_task_claims()
    for key, claim in list(claims.items()):
        if key == current_key or not isinstance(claim, dict):
            continue
        if claim.get('status') != 'running':
            continue
        pid = _safe_int(claim.get('pid'), 0)
        if not pid or not _pid_alive(pid):
            claim['status'] = 'stale'
            claim['update_time'] = _now()
            claims[key] = claim
            continue
        if not _is_ha_switch_process(pid):
            continue
        old_run_id = claim.get('switch_run_id') or cfg.get('switch_run_id') or 'latest'
        old_phase = claim.get('phase') or 'switch'
        _append_switch_log(old_run_id, old_phase, 'failed', '收到新云监控切换任务 {0}，停止旧任务并切换到新任务'.format(switch_run_id))
        _append_cloud_task_launcher_log('preempt old cloud task key={0} pid={1} new_switch_run_id={2} new_phase={3}'.format(key, pid, switch_run_id, phase))
        _terminate_pid_tree(pid)
        claim['status'] = 'preempted'
        claim['preempted_by'] = switch_run_id
        claim['update_time'] = _now()
        claims[key] = claim
        stopped = True
    _write_cloud_task_claims(claims)
    return _preempt_switch_lock_for_new_task(cfg, switch_run_id, phase) or stopped


def _preempt_switch_lock_for_new_task(cfg, switch_run_id, phase):
    switch_run_id = str(switch_run_id or '').strip()
    if not switch_run_id:
        return False
    lock_pid = _read_lock_pid()
    if not lock_pid:
        return False
    if not _pid_alive(lock_pid):
        _unlock()
        return True
    if cfg.get('switch_run_id') == switch_run_id:
        return False
    if not _is_ha_switch_process(lock_pid):
        return False
    old_run_id = cfg.get('switch_run_id') or 'latest'
    old_status = str(cfg.get('switch_status') or '').strip()
    old_phase = old_status[:-8] if old_status.endswith('_running') else 'switch'
    _append_switch_log(old_run_id, old_phase, 'failed', '收到新云监控切换任务 {0}，停止旧任务并清理本地切换锁'.format(switch_run_id))
    _append_cloud_task_launcher_log('preempt locked switch pid={0} old_switch_run_id={1} new_switch_run_id={2} new_phase={3}'.format(lock_pid, old_run_id, switch_run_id, phase))
    _terminate_pid_tree(lock_pid)
    _unlock()
    cfg['switch_status'] = 'failed'
    _save_config(cfg)
    return True


def ack_switch_phase(cfg, phase, phase_status, step='', last_error=''):
    if not cfg.get('monitor_url') or not cfg.get('switch_run_id'):
        _append_cloud_interaction_log('ack_switch_phase', 'skip', msg='无需确认', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=cfg.get('switch_run_id'), phase=phase, phase_status=phase_status)
        return {'status': False, 'msg': '无需确认'}
    payload = {
        'pair_id': cfg.get('pair_id'),
        'switch_run_id': cfg.get('switch_run_id'),
        'phase': phase,
        'phase_status': phase_status,
        'current_step': step,
        'last_error': last_error
    }
    res = _post_monitor_with_auth_retry(cfg, 'ha_ack_switch_phase', payload)
    _append_cloud_interaction_log('ack_switch_phase', 'done' if res.get('status') else 'failed', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=cfg.get('switch_run_id'), phase=phase, phase_status=phase_status, msg=res.get('msg'))
    return res


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
    return 'plugins/ha_manager/index.py' in cmdline and (' local_switch' in cmdline or ' switch_phase' in cmdline or ' prepare_switch' in cmdline or ' finalize_switch' in cmdline)


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


def _remote_phase_options(cfg, phase, run_options=None):
    options = dict(cfg.get('options') or {})
    options.update(_dict_value(run_options))
    for key in ('local_ip', 'remote_ip', 'remote_ssh_port'):
        options.pop(key, None)
    return options


def _phase_text(phase):
    if phase == 'prepare_online':
        return '预上线'
    if phase == 'online':
        return '正式上线'
    if phase == 'offline':
        return '下线'
    return phase


def _is_checksum_confirm_error(error):
    return 'CHECKSUM_DIFF_CONFIRM_REQUIRED' in str(error)


def _repair_switch_ips(cfg, options):
    options = _dict_value(options)
    if not str(options.get('local_ip') or '').strip():
        options['local_ip'] = cfg.get('host_ip') or mw.getHostAddr()
    if not str(options.get('remote_ip') or '').strip():
        options['remote_ip'] = cfg.get('peer_public_ip') or ''
    options['remote_ssh_port'] = cfg.get('peer_ssh_port') or '22'
    return options


def _switch_options_from_request(cfg, request_options):
    request_options = _dict_value(request_options)
    switch_options = dict(_default_config().get('options') or {})
    saved_options = _dict_value(cfg.get('options'))
    for key in ('local_ip', 'remote_ip', 'remote_ssh_port', 'sync_file_dirs', 'sync_ignore_dirs'):
        if key in saved_options:
            switch_options[key] = saved_options.get(key)
    switch_options.update(request_options)
    for key in ('run_checksum', 'sync_files', 'restore_site_setting', 'restore_plugin_setting', 'run_xtrabackup_inc_restore', 'checksum_confirmed', 'promote_mysql'):
        if key not in request_options:
            switch_options[key] = False
    if 'promote_mysql' not in request_options:
        switch_options['promote_mysql'] = True
    return _repair_switch_ips(cfg, switch_options)


def _run_local_switch_phase(cfg, phase, role, switch_run_id, options=None, label='本机', echo_output=False, persist_options=True):
    original_options = dict(_dict_value(cfg.get('options')))
    run_options = _dict_value(options)
    cfg['switch_run_id'] = switch_run_id
    cfg['switch_status'] = phase + '_running'
    if not isinstance(cfg.get('options'), dict):
        cfg['options'] = {}
    cfg['options'].update(run_options)
    _save_config(cfg)
    _append_switch_log(switch_run_id, phase, 'start', label + '开始执行' + _phase_text(phase) + '脚本，目标角色：' + ('主' if role == 'master' else '备') + '，执行方式：本机直接执行')
    try:
        _run_executor(phase, cfg, echo_output)
    except Exception:
        if not persist_options:
            cfg['options'] = original_options
            _save_config(cfg)
        raise
    if phase != 'prepare_online':
        cfg['role'] = role
        cfg['desired_role'] = role
    cfg['switch_status'] = phase + '_done'
    if not persist_options:
        cfg['options'] = original_options
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
    env_prefix = 'HA_MANAGER_SWITCH_DRY_RUN=1 ' if DRY_RUN else ''
    remote_cmd = 'cd /www/server/jh-panel && {0}PYTHONUNBUFFERED=1 python3 /www/server/jh-panel/plugins/ha_manager/index.py switch_phase {1}'.format(env_prefix, args)
    cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=no', '-p', str(cfg.get('peer_ssh_port')), cfg.get('peer_ssh_user') + '@' + cfg.get('peer_public_ip'), remote_cmd]
    peer_origin_host_id = cfg.get('peer_host_id') or cfg.get('peer_public_ip') or 'peer'
    try:
        peer_state = collect_peer_state_raw(cfg)
        if peer_state.get('status') and isinstance(peer_state.get('data'), dict):
            peer_origin_host_id = _report_peer_host_id(cfg, peer_state.get('data') or {})
    except Exception:
        pass
    start_text = '开始通过 SSH 在对端执行' + _phase_text(phase) + '脚本，执行方式：SSH 远程触发'
    _append_switch_log(switch_run_id, phase, 'start', start_text)
    report_switch_event(cfg, phase, 'start', start_text, origin_host_id=peer_origin_host_id, collect_method='ssh_peer', switch_run_id=switch_run_id)
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
            log_line = '对端: ' + line
            _append_switch_log(switch_run_id, phase, 'running', log_line)
            report_switch_event(cfg, phase, 'running', log_line, origin_host_id=peer_origin_host_id, collect_method='ssh_peer', switch_run_id=switch_run_id)
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
    success_text = '对端' + _phase_text(phase) + '脚本执行完成'
    _append_switch_log(switch_run_id, phase, 'success', success_text)
    report_switch_event(cfg, phase, 'success', success_text, origin_host_id=peer_origin_host_id, collect_method='ssh_peer', switch_run_id=switch_run_id)
    return result.get('data') or {}


def _run_switch_phase_with_method(cfg, phase, role, switch_run_id, switch_options=None, execute_method='local', source_label='', echo_output=False, persist_options=True):
    switch_options = _dict_value(switch_options)
    if execute_method == 'ssh_peer':
        if source_label:
            _append_switch_log(switch_run_id, phase, 'start', source_label + '，执行方式：SSH 远程触发对端执行' + ('，目标角色：主' if role == 'master' else '，目标角色：备'))
        return _run_remote_switch_phase(cfg, phase, role, switch_run_id, _remote_phase_options(cfg, phase, switch_options))
    if source_label:
        _append_switch_log(switch_run_id, phase, 'start', source_label + '，执行方式：本机直接执行' + ('，目标角色：主' if role == 'master' else '，目标角色：备'))
    return _run_local_switch_phase(cfg, phase, role, switch_run_id, switch_options, '本机', echo_output, persist_options)


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
        if data.get('orchestrated') and _preempt_switch_lock_for_new_task(cfg, data.get('switch_run_id') or '', phase):
            if not _lock():
                return _return(False, '已有切换任务正在执行')
        else:
            return _return(False, '已有切换任务正在执行')
    claim_key = _cloud_task_claim_key(data.get('switch_run_id') or '', phase)
    try:
        switch_run_id = data.get('switch_run_id') or 'LOCAL_' + time.strftime('%Y%m%d%H%M%S')
        request_options = _dict_value(data.get('options'))
        if data.get('orchestrated'):
            claim_text = '开始处理已领取的云监控任务：任务ID={0}，阶段={1}，执行方式={2}，目标主机={3}'.format(switch_run_id, _phase_text(phase), data.get('execute_method') or 'local', data.get('execute_target_host_id') or '--')
            _append_switch_log(switch_run_id, phase, 'start', claim_text)
            report_switch_event(cfg, phase, 'start', claim_text, switch_run_id=switch_run_id)
        _append_switch_log(switch_run_id, phase, 'running', '收到云监控切换选项：' + json.dumps(request_options, ensure_ascii=False, sort_keys=True))
        switch_options = _switch_options_from_request(cfg, request_options)
        if request_options.get('confirm_failover'):
            data['confirm_failover'] = True
        _append_switch_log(switch_run_id, phase, 'running', '本次执行选项：sync_files={0}, run_checksum={1}, run_xtrabackup_inc_restore={2}, promote_mysql={3}'.format(str(switch_options.get('sync_files')).lower(), str(switch_options.get('run_checksum')).lower(), str(switch_options.get('run_xtrabackup_inc_restore')).lower(), str(switch_options.get('promote_mysql')).lower()))
        source_label = '云监控轮询领取' if data.get('orchestrated') else '手工触发'
        execute_method = data.get('execute_method') or 'local'
        if data.get('orchestrated'):
            target_role_for_mode = 'master' if (data.get('execute_target_host_id') == cfg.get('host_id') or execute_method == 'local') else 'standby'
            mode = _switch_execution_mode(cfg, target_role_for_mode)
            _append_switch_log(switch_run_id, phase, 'running', '云监控任务执行能力检查：mode={0}, allowed={1}, reason={2}'.format(mode.get('mode'), mode.get('allowed'), mode.get('reason') or '--'))
            if execute_method == 'ssh_peer' and phase == 'offline' and not mode.get('peer_ability', {}).get('reachable') and data.get('confirm_failover'):
                text = '对端不可达，操作员已确认故障升主，跳过对端下线阶段并继续目标主机正式上线'
                _append_switch_log(switch_run_id, phase, 'success', text)
                report_switch_event(cfg, phase, 'success', text, switch_run_id=switch_run_id)
                ack_switch_phase(cfg, phase, 'success', text)
                _set_cloud_task_claim(claim_key, {'status': 'done', 'switch_run_id': switch_run_id, 'phase': phase, 'update_time': _now(), 'skipped': True, 'reason': mode.get('reason') or ''})
                return _return(True, '对端下线阶段已按故障升主确认跳过', cfg)
            if execute_method == 'ssh_peer' and not mode.get('peer_ability', {}).get('reachable'):
                raise RuntimeError('对端不可达，无法执行远程阶段: ' + (mode.get('reason') or '未知原因'))
        result_cfg = _run_switch_phase_with_method(cfg, phase, role, switch_run_id, switch_options, execute_method, source_label, True, False)
        if execute_method != 'ssh_peer':
            cfg = result_cfg
        if phase == 'online':
            if data.get('orchestrated') and data.get('confirm_failover') and execute_method != 'ssh_peer' and mode.get('mode') == 'local_failover':
                mode = _switch_execution_mode(cfg, 'master')
                if mode.get('mode') == 'local_failover':
                    _record_local_failover_state(cfg, switch_run_id, mode.get('reason') or 'peer_unreachable')
            elif not data.get('confirm_failover') or mode.get('mode') == 'full_switch':
                _clear_failover_after_full_switch(cfg, switch_run_id)
            _report_both_state_after_switch_delay(switch_run_id, 3)
        else:
            _report_state_after_switch_delay(3)
        ack_switch_phase(cfg, phase, 'success', _phase_text(phase) + '完成')
        _set_cloud_task_claim(claim_key, {'status': 'done', 'switch_run_id': switch_run_id, 'phase': phase, 'update_time': _now()})
        return _return(True, '阶段执行完成', cfg)
    except Exception as e:
        _append_switch_log(cfg.get('switch_run_id') or data.get('switch_run_id') or 'failed', phase or 'switch', 'failed', str(e))
        cfg['switch_status'] = 'failed'
        _save_config(cfg)
        ack_switch_phase(cfg, phase, 'failed', str(e), str(e))
        _set_cloud_task_claim(claim_key, {'status': 'failed', 'switch_run_id': data.get('switch_run_id') or '', 'phase': phase, 'error': str(e), 'update_time': _now()})
        if _is_checksum_confirm_error(e):
            return _return(False, 'CHECKSUM_DIFF_CONFIRM_REQUIRED: checksum 检查发现差异，需要确认后继续')
        return _return(False, '阶段执行失败: ' + str(e))
    finally:
        _unlock()


def local_switch():
    data = _args()
    cfg = _config()
    target_role = data.get('target_role') or ('standby' if cfg.get('role') == 'master' else 'master')
    mode = _switch_execution_mode(cfg, target_role)
    if not mode.get('allowed'):
        return _return(False, mode.get('message') or '当前执行模式不允许切换', mode)
    ok, msg = _require_failover_confirm(data, mode)
    if not ok:
        return _return(False, msg, mode)
    if not _lock():
        return _return(False, '已有切换任务正在执行')
    try:
        switch_run_id = data.get('switch_run_id') or 'LOCAL_' + time.strftime('%Y%m%d%H%M%S')
        cfg['switch_run_id'] = switch_run_id
        cfg['switch_status'] = 'running'
        request_options = _dict_value(data.get('options'))
        _append_switch_log(switch_run_id, 'switch', 'running', '收到切换选项：' + json.dumps(request_options, ensure_ascii=False, sort_keys=True))
        switch_options = _switch_options_from_request(cfg, request_options)
        cfg['options'].update(switch_options)
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'switch', 'running', '本次预上线选项：sync_files={0}, run_checksum={1}, promote_mysql={2}'.format(str(switch_options.get('sync_files')).lower(), str(switch_options.get('run_checksum')).lower(), str(switch_options.get('promote_mysql')).lower()))
        _append_switch_log(switch_run_id, 'switch', 'running', '切换执行模式：{0}，协调主机：{1}，原因：{2}'.format(mode.get('mode'), mode.get('coordinator_host_id') or '--', mode.get('reason') or '--'))
        if mode.get('mode') == 'local_failover':
            _append_switch_log(switch_run_id, 'switch', 'start', '对端不可达，执行本机故障升主；已跳过对端下线阶段')
            cfg = _run_switch_phase_with_method(cfg, 'prepare_online', 'master', switch_run_id, switch_options, 'local')
            cfg = _run_switch_phase_with_method(cfg, 'online', 'master', switch_run_id, switch_options, 'local')
            _record_local_failover_state(cfg, switch_run_id, mode.get('reason') or 'peer_unreachable')
        elif target_role == 'master':
            _append_switch_log(switch_run_id, 'switch', 'start', '切换主备开始：先在目标主机（本机）执行预上线，再在目标备用机（对端）执行下线，最后在目标主机（本机）执行正式上线')
            cfg = _run_switch_phase_with_method(cfg, 'prepare_online', 'master', switch_run_id, switch_options, 'local')
            _run_switch_phase_with_method(cfg, 'offline', 'standby', switch_run_id, switch_options, 'ssh_peer')
            cfg = _run_switch_phase_with_method(cfg, 'online', 'master', switch_run_id, switch_options, 'local')
        else:
            _append_switch_log(switch_run_id, 'switch', 'start', '切换主备开始：先在目标主机（对端）执行预上线，再在目标备用机（本机）执行下线，最后在目标主机（对端）执行正式上线')
            _run_switch_phase_with_method(cfg, 'prepare_online', 'master', switch_run_id, switch_options, 'ssh_peer')
            cfg = _run_switch_phase_with_method(cfg, 'offline', 'standby', switch_run_id, switch_options, 'local')
            _run_switch_phase_with_method(cfg, 'online', 'master', switch_run_id, switch_options, 'ssh_peer')
        cfg['desired_role'] = target_role
        cfg['switch_status'] = 'switch_done'
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'switch', 'success', '切换主备完成')
        if mode.get('mode') == 'full_switch':
            _clear_failover_after_full_switch(cfg, switch_run_id)
        _state(cfg)
        _report_both_state_after_switch_delay(switch_run_id, 3) if mode.get('mode') == 'full_switch' else _report_state_after_switch_delay(3)
        report_switch_event(cfg, 'switch', 'success', '切换主备完成')
        return _return(True, '切换执行完成', cfg)
    except Exception as e:
        _append_switch_log(cfg.get('switch_run_id') or 'failed', 'switch', 'failed', str(e))
        cfg['switch_status'] = 'failed'
        _save_config(cfg)
        report_switch_event(cfg, 'switch', 'failed', str(e))
        if _is_checksum_confirm_error(e):
            return _return(False, 'CHECKSUM_DIFF_CONFIRM_REQUIRED: checksum 检查发现差异，需要确认后继续')
        return _return(False, '切换失败: ' + str(e))
    finally:
        _unlock()


def prepare_switch():
    data = _args()
    cfg = _config()
    target_role = data.get('target_role') or ('standby' if cfg.get('role') == 'master' else 'master')
    mode = _switch_execution_mode(cfg, target_role)
    if not mode.get('allowed'):
        return _return(False, mode.get('message') or '当前执行模式不允许切换', mode)
    if not _lock():
        return _return(False, '已有切换任务正在执行')
    try:
        switch_run_id = data.get('switch_run_id') or 'PREPARE_' + time.strftime('%Y%m%d%H%M%S')
        cfg['switch_run_id'] = switch_run_id
        cfg['switch_status'] = 'running'
        request_options = _dict_value(data.get('options'))
        _append_switch_log(switch_run_id, 'switch', 'start', '预上线任务已创建，执行方式：' + ('本机直接执行' if target_role == 'master' else 'SSH 远程触发'))
        _append_switch_log(switch_run_id, 'switch', 'running', '收到预上线选项：' + json.dumps(request_options, ensure_ascii=False, sort_keys=True))
        switch_options = _switch_options_from_request(cfg, request_options)
        cfg['options'].update(switch_options)
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'switch', 'running', '预上线执行模式：{0}，协调主机：{1}，原因：{2}'.format(mode.get('mode'), mode.get('coordinator_host_id') or '--', mode.get('reason') or '--'))
        _append_switch_log(switch_run_id, 'switch', 'start', '预备上线开始：在切换后的目标主机执行预上线')
        _append_switch_log(switch_run_id, 'switch', 'running', '本次预上线选项：sync_files={0}, run_checksum={1}'.format(str(switch_options.get('sync_files')).lower(), str(switch_options.get('run_checksum')).lower()))
        if target_role == 'master':
            cfg = _run_switch_phase_with_method(cfg, 'prepare_online', 'master', switch_run_id, switch_options, 'local')
        else:
            _run_switch_phase_with_method(cfg, 'prepare_online', 'master', switch_run_id, switch_options, 'ssh_peer')
        cfg['switch_status'] = 'prepare_switch_done'
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'switch', 'success', '预备上线完成')
        return _return(True, '预备上线完成', cfg)
    except Exception as e:
        _append_switch_log(cfg.get('switch_run_id') or 'failed', 'switch', 'failed', str(e))
        cfg['switch_status'] = 'failed'
        _save_config(cfg)
        report_switch_event(cfg, 'switch', 'failed', str(e))
        if _is_checksum_confirm_error(e):
            return _return(False, 'CHECKSUM_DIFF_CONFIRM_REQUIRED: checksum 检查发现差异，需要确认后继续')
        return _return(False, '预备上线失败: ' + str(e))
    finally:
        _unlock()


def finalize_switch():
    data = _args()
    cfg = _config()
    target_role = data.get('target_role') or ('standby' if cfg.get('role') == 'master' else 'master')
    mode = _switch_execution_mode(cfg, target_role)
    if not mode.get('allowed'):
        return _return(False, mode.get('message') or '当前执行模式不允许切换', mode)
    ok, msg = _require_failover_confirm(data, mode)
    if not ok:
        return _return(False, msg, mode)
    if not _lock():
        return _return(False, '已有切换任务正在执行')
    try:
        switch_run_id = data.get('switch_run_id') or 'FINAL_' + time.strftime('%Y%m%d%H%M%S')
        cfg['switch_run_id'] = switch_run_id
        cfg['switch_status'] = 'running'
        request_options = _dict_value(data.get('options'))
        _append_switch_log(switch_run_id, 'switch', 'start', '正式上线任务已创建，执行方式：' + ('本机直接执行' if target_role == 'master' else 'SSH 远程触发'))
        switch_options = _switch_options_from_request(cfg, request_options)
        cfg['options'].update(switch_options)
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'switch', 'running', '收到正式上线选项：' + json.dumps(request_options, ensure_ascii=False, sort_keys=True))
        _append_switch_log(switch_run_id, 'switch', 'running', '正式上线执行模式：{0}，协调主机：{1}，原因：{2}'.format(mode.get('mode'), mode.get('coordinator_host_id') or '--', mode.get('reason') or '--'))
        _append_switch_log(switch_run_id, 'switch', 'start', '正式上线开始：不执行预上线，只执行目标备用机下线和目标主机正式上线')
        if mode.get('mode') == 'local_failover':
            _append_switch_log(switch_run_id, 'switch', 'start', '对端不可达，跳过对端下线阶段，仅执行本机正式上线并进入降级运行')
            cfg = _run_switch_phase_with_method(cfg, 'online', 'master', switch_run_id, switch_options, 'local')
            _record_local_failover_state(cfg, switch_run_id, mode.get('reason') or 'peer_unreachable')
        elif target_role == 'master':
            _run_switch_phase_with_method(cfg, 'offline', 'standby', switch_run_id, switch_options, 'ssh_peer')
            cfg = _run_switch_phase_with_method(cfg, 'online', 'master', switch_run_id, switch_options, 'local')
        else:
            cfg = _run_switch_phase_with_method(cfg, 'offline', 'standby', switch_run_id, switch_options, 'local')
            _run_switch_phase_with_method(cfg, 'online', 'master', switch_run_id, switch_options, 'ssh_peer')
        cfg['desired_role'] = target_role
        cfg['switch_status'] = 'switch_done'
        _save_config(cfg)
        _append_switch_log(switch_run_id, 'switch', 'success', '正式上线完成，切换主备完成')
        if mode.get('mode') == 'full_switch':
            _clear_failover_after_full_switch(cfg, switch_run_id)
        _state(cfg)
        _report_both_state_after_switch_delay(switch_run_id, 3) if mode.get('mode') == 'full_switch' else _report_state_after_switch_delay(3)
        report_switch_event(cfg, 'switch', 'success', '正式上线完成，切换主备完成')
        return _return(True, '正式上线完成', cfg)
    except Exception as e:
        _append_switch_log(cfg.get('switch_run_id') or 'failed', 'switch', 'failed', str(e))
        cfg['switch_status'] = 'failed'
        _save_config(cfg)
        report_switch_event(cfg, 'switch', 'failed', str(e))
        return _return(False, '正式上线失败: ' + str(e))
    finally:
        _unlock()


def _run_executor(phase, cfg, echo_output=False):
    script_phase = 'online' if phase == 'prepare_online' else phase
    script = '/www/server/jh-panel/scripts/os_tool/vm/default/switch__generate_' + script_phase + '.sh'
    if not os.path.exists(script):
        raise RuntimeError('切换脚本不存在: ' + script)
    args = json.dumps(cfg.get('options') or {}, ensure_ascii=False)
    cmd = ['bash', script, '--plugin-run', '--args', args]
    if shutil.which('stdbuf'):
        cmd = ['stdbuf', '-oL', '-eL'] + cmd
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['NODE_DISABLE_COLORS'] = '1'
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
            if echo_output:
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
        _append_cloud_interaction_log('report_switch_event', 'skip', msg='无需上报', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=switch_run_id, phase=phase, event_status=status)
        return {'status': False, 'msg': '无需上报'}
    seq = seq or _seq()
    origin_host_id = origin_host_id or cfg.get('host_id')
    payload = {'pair_id': cfg.get('pair_id'), 'switch_run_id': switch_run_id, 'event_id': origin_host_id + '-' + str(seq), 'origin_host_id': origin_host_id, 'report_host_id': cfg.get('host_id'), 'collect_method': collect_method, 'seq': seq, 'phase': phase, 'step': text, 'status': status, 'log_text': text}
    res = _post_monitor_with_auth_retry(cfg, 'ha_report_switch_event', payload)
    _append_cloud_interaction_log('report_switch_event', 'done' if res.get('status') else 'failed', pair_id=cfg.get('pair_id'), host_id=cfg.get('host_id'), switch_run_id=switch_run_id, phase=phase, event_status=status, origin_host_id=origin_host_id, collect_method=collect_method, seq=seq, msg=res.get('msg'), text=text)
    return res


if __name__ == '__main__':
    _ensure_dirs()
    func = sys.argv[1] if len(sys.argv) > 1 else ''
    if func == 'status':
        print(status())
    elif func == 'get_state':
        print(get_state())
    elif func == 'get_local_state':
        print(get_local_state())
    elif func == 'get_coordination_state':
        print(get_coordination_state())
    elif func == 'check_switch_execution_mode':
        print(check_switch_execution_mode())
    elif func == 'recover_check':
        print(recover_check())
    elif func == 'recover_as_standby':
        print(recover_as_standby())
    elif func == 'clear_failover_state':
        print(clear_failover_state())
    elif func == 'regenerate_host_id':
        print(regenerate_host_id())
    elif func == 'title_state':
        print(title_state())
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
    elif func == 'save_auto_recover':
        print(save_auto_recover())
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
    elif func == 'prepare_switch':
        print(prepare_switch())
    elif func == 'finalize_switch':
        print(finalize_switch())
    elif func == 'local_switch':
        print(local_switch())
    else:
        print('error')
