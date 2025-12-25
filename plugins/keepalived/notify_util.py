#!/usr/bin/env python3
# Keepalived notification + monitoring helper

import os
import sys
import json
import time
import socket
import shutil
import argparse
import subprocess
import importlib.util
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_DIR = os.path.join(ROOT_DIR, 'server')
KEEPALIVED_SERVER_DIR = os.path.join(SERVER_DIR, 'keepalived')
KEEPALIVED_ALERT_FILE = os.path.join(KEEPALIVED_SERVER_DIR, 'config', 'alert_settings.json')
KEEPALIVED_MONITOR_LOG = os.path.join(KEEPALIVED_SERVER_DIR, 'logs', 'keepalived_monitor.log')
KEEPALIVED_PLUGIN_DIR = os.path.join(ROOT_DIR, 'plugins', 'keepalived')

_CONFIG_UTIL = None
_INDEX_MODULE = None


def _load_config_util():
    global _CONFIG_UTIL
    if _CONFIG_UTIL is not None:
        return _CONFIG_UTIL
    path = os.path.join(KEEPALIVED_PLUGIN_DIR, 'config_util.py')
    if not os.path.exists(path):
        _CONFIG_UTIL = False
        return None
    spec = importlib.util.spec_from_file_location('keepalived_config_util_cli', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _CONFIG_UTIL = module
    return module


def _load_index_module():
    global _INDEX_MODULE
    if _INDEX_MODULE is not None:
        return _INDEX_MODULE
    path = os.path.join(KEEPALIVED_PLUGIN_DIR, 'index.py')
    if not os.path.exists(path):
        _INDEX_MODULE = False
        return None
    spec = importlib.util.spec_from_file_location('keepalived_index_cli', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _INDEX_MODULE = module
    return module


def _ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, 0o755)


def read_alert_settings():
    defaults = {
        'notify_promote': False,
        'notify_demote': False,
        'monitor_enabled': False,
        'updated_at': int(time.time()),
        'monitor_last_run': 0
    }
    if not os.path.exists(KEEPALIVED_ALERT_FILE):
        return defaults
    try:
        with open(KEEPALIVED_ALERT_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        return defaults
    defaults.update({
        'notify_promote': bool(data.get('notify_promote', False)),
        'notify_demote': bool(data.get('notify_demote', False)),
        'monitor_enabled': bool(data.get('monitor_enabled', False)),
        'monitor_last_run': int(data.get('monitor_last_run', 0) or 0),
        'updated_at': int(data.get('updated_at', int(time.time())))
    })
    return defaults


def write_alert_settings(data):
    _ensure_dir(os.path.dirname(KEEPALIVED_ALERT_FILE))
    with open(KEEPALIVED_ALERT_FILE, 'w', encoding='utf-8') as fh:
        json.dump(data, fh)


def append_monitor_log(payload):
    _ensure_dir(os.path.dirname(KEEPALIVED_MONITOR_LOG))
    with open(KEEPALIVED_MONITOR_LOG, 'a+', encoding='utf-8') as fh:
        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False)
        fh.write('[{0}] {1}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), payload))


def _read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return fh.read()
    except Exception:
        return ''


def collect_keepalived_form_data():
    conf_path = os.path.join(KEEPALIVED_SERVER_DIR, 'etc/keepalived/keepalived.conf')
    tpl_path = os.path.join(KEEPALIVED_PLUGIN_DIR, 'config/keepalived.conf')
    if not os.path.exists(conf_path):
        return {}
    content = _read_file(conf_path)
    tpl_content = _read_file(tpl_path)
    config_util = _load_config_util()
    if config_util:
        try:
            return config_util.get_vrrp_form_data(content, tpl_content)
        except Exception:
            pass
    # Fallback parsing
    result = {
        'interface': '',
        'virtual_ipaddress': '',
        'priority': ''
    }
    vip_block = False
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('!'):
            continue
        if stripped.startswith('interface'):
            parts = stripped.split()
            if len(parts) > 1:
                result['interface'] = parts[1]
        elif stripped.startswith('priority'):
            parts = stripped.split()
            if len(parts) > 1:
                result['priority'] = parts[1]
        elif stripped.startswith('virtual_ipaddress'):
            vip_block = True
            continue
        elif vip_block:
            if stripped.startswith('}'):
                vip_block = False
                continue
            if stripped and not stripped.startswith('#'):
                result['virtual_ipaddress'] = stripped.split()[0]
                vip_block = False
    return result


def is_keepalived_service_running():
    try:
        res = subprocess.run(['systemctl', 'is-active', 'keepalived'], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip() == 'active':
            return True
    except Exception:
        pass
    res = subprocess.run(['pidof', 'keepalived'], capture_output=True, text=True)
    return bool(res.stdout.strip())


def check_vip_ping(pure_vip):
    if not pure_vip:
        return {'status': 'unknown', 'message': '未配置VIP'}
    res = subprocess.run(['ping', '-c', '3', '-W', '1', pure_vip], capture_output=True, text=True)
    if res.returncode == 0:
        return {'status': 'ok', 'message': '成功'}
    return {'status': 'fail', 'message': res.stdout.strip() or res.stderr.strip()}


def check_tcp_port(host, port, timeout=3):
    if not host or not port:
        return False
    try:
        sock = socket.create_connection((host, int(port)), timeout=timeout)
        sock.close()
        return True
    except Exception:
        return False


def detect_vip_conflict(pure_vip, interface):
    if not pure_vip or not interface:
        return {'status': 'unknown', 'message': '缺少VIP或接口'}
    arping_bin = shutil.which('arping')
    if not arping_bin:
        return {'status': 'unknown', 'message': '系统缺少 arping'}
    cmd = [arping_bin, '-c', '2', '-I', interface, pure_vip]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return {'status': 'unknown', 'message': res.stdout.strip() or res.stderr.strip()}
    macs = set()
    for line in res.stdout.splitlines():
        line = line.strip().lower()
        if line.startswith('unicast reply from'):
            parts = line.split()
            for part in parts:
                if part.startswith('[') and part.endswith(']'):
                    macs.add(part.strip('[]'))
    if len(macs) > 1:
        return {'status': 'fail', 'message': '检测到多个MAC响应'}
    return {'status': 'ok', 'message': '单节点持有'}


def detect_mysql_instance():
    server_path = SERVER_DIR
    mysql_plugins = [
        {'path': os.path.join(server_path, 'mysql-apt'), 'client_bin': '/bin/usr/bin/mysql'},
        {'path': os.path.join(server_path, 'mysql-yum'), 'client_bin': '/bin/usr/bin/mysql'},
        {'path': os.path.join(server_path, 'mysql'), 'client_bin': '/bin/mysql'},
        {'path': os.path.join(server_path, 'mariadb'), 'client_bin': '/bin/mysql'}
    ]
    for plugin in mysql_plugins:
        base_path = plugin['path']
        conf = os.path.join(base_path, 'etc/my.cnf')
        if not os.path.exists(conf):
            continue
        content = _read_file(conf)
        port = _parse_mysql_conf_value(content, 'port') or '3306'
        socket_file = _parse_mysql_conf_value(content, 'socket')
        password = ''
        try:
            config_db = os.path.join(base_path, 'mysql.db')
            if os.path.exists(config_db):
                import sqlite3
                conn = sqlite3.connect(config_db)
                cursor = conn.cursor()
                cursor.execute("SELECT mysql_root FROM config WHERE id=1")
                row = cursor.fetchone()
                if row and row[0]:
                    password = row[0]
                conn.close()
        except Exception:
            password = ''
        client_bin = os.path.join(base_path, plugin['client_bin'].lstrip('/'))
        if not os.path.exists(client_bin):
            client_bin = 'mysql'
        return {
            'user': 'root',
            'password': password,
            'port': port,
            'socket': socket_file,
            'client_bin': client_bin
        }
    return None


def _parse_mysql_conf_value(content, key):
    pattern = r'^\s*' + re.escape(key) + r'\s*=\s*(.+)$'
    matches = re.findall(pattern, content, re.MULTILINE)
    if not matches:
        return ''
    return matches[-1].strip()


def query_mysql_read_only(mysql_info):
    if not mysql_info:
        return {'status': 'unknown', 'message': '无法检测MySQL实例'}
    client_bin = mysql_info.get('client_bin') or 'mysql'
    cmd = [client_bin, '--connect-timeout=3', '--batch', '-N', '-B']
    socket_file = mysql_info.get('socket')
    if socket_file:
        cmd.extend(['-S', socket_file])
    else:
        cmd.extend(['-h', mysql_info.get('host', '127.0.0.1'), '-P', str(mysql_info.get('port', '3306'))])
    cmd.extend(['-u', mysql_info.get('user', 'root'), '-e', 'SELECT @@GLOBAL.read_only, @@GLOBAL.super_read_only'])
    env = os.environ.copy()
    password = mysql_info.get('password')
    if password:
        env['MYSQL_PWD'] = str(password)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=5)
    except Exception as exc:
        return {'status': 'unknown', 'message': 'MySQL命令失败: {0}'.format(exc)}
    if res.returncode != 0:
        return {'status': 'unknown', 'message': res.stderr.strip() or 'MySQL命令失败'}
    lines = res.stdout.strip().splitlines()
    if not lines:
        return {'status': 'unknown', 'message': 'MySQL无输出'}
    parts = lines[-1].split()
    if len(parts) < 2:
        return {'status': 'unknown', 'message': '输出无法解析: {0}'.format(lines[-1])}
    ro, sro = parts[0], parts[1]
    if ro == '0' and sro == '0':
        return {'status': 'rw', 'message': 'MySQL可写'}
    return {'status': 'ro', 'message': 'MySQL只读(read_only={0}, super_read_only={1})'.format(ro, sro)}


def collect_keepalived_health():
    data = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'service_running': False,
        'vip': '',
        'interface': '',
        'priority': '',
        'vip_owned': False,
        'vip_ping': {'status': 'unknown', 'message': ''},
        'vip_conflict': {'status': 'unknown', 'message': ''},
        'vip_mysql_port_ok': False,
        'local_mysql_port_ok': False,
        'mysql_state': {'status': 'unknown', 'message': ''},
        'issues': []
    }
    if not os.path.exists(KEEPALIVED_SERVER_DIR):
        data['issues'].append('未检测到 keepalived 安装目录')
        return data

    form_data = collect_keepalived_form_data()
    if form_data.get('error'):
        data['issues'].append('解析 keepalived 配置失败: {0}'.format(form_data['error']))
    vip_raw = form_data.get('virtual_ipaddress', '')
    pure_vip = vip_raw.split('/')[0] if vip_raw else ''
    interface = form_data.get('interface', '')
    data['vip'] = vip_raw
    data['interface'] = interface
    data['priority'] = str(form_data.get('priority', ''))

    data['service_running'] = is_keepalived_service_running()
    if not data['service_running']:
        data['issues'].append('Keepalived 服务未运行')

    if pure_vip:
        vip_output = subprocess.run(['sh', '-c', "ip addr | grep -w {0}".format(pure_vip)], capture_output=True, text=True)
        data['vip_owned'] = bool(vip_output.stdout.strip())
        data['vip_ping'] = check_vip_ping(pure_vip)
        data['vip_conflict'] = detect_vip_conflict(pure_vip, interface)
    else:
        data['vip_ping'] = {'status': 'unknown', 'message': '未配置VIP'}
        data['vip_conflict'] = {'status': 'unknown', 'message': '未配置VIP'}

    mysql_info = detect_mysql_instance()
    mysql_port = mysql_info.get('port') if mysql_info else '3306'
    data['vip_mysql_port_ok'] = check_tcp_port(pure_vip, mysql_port) if pure_vip else False
    data['local_mysql_port_ok'] = check_tcp_port('127.0.0.1', mysql_port)
    data['mysql_state'] = query_mysql_read_only(mysql_info)

    role = 'MASTER' if data['vip_owned'] else 'BACKUP'

    if pure_vip and data['vip_ping']['status'] == 'fail':
        data['issues'].append('VIP {0} 无法Ping通'.format(pure_vip))

    if data['vip_conflict']['status'] == 'fail':
        data['issues'].append('检测到 VIP {0} 可能被多个节点持有'.format(pure_vip))

    if not data['local_mysql_port_ok']:
        data['issues'].append('本地 MySQL 端口 {0} 不可用'.format(mysql_port))

    if pure_vip and data['vip_owned'] and not data['vip_mysql_port_ok']:
        data['issues'].append('持有 VIP 但无法通过 VIP:{0} 访问 MySQL'.format(mysql_port))

    if data['mysql_state']['status'] == 'ro' and role == 'MASTER':
        data['issues'].append('MASTER 节点 MySQL 仍为只读状态')
    if data['mysql_state']['status'] == 'rw' and role == 'BACKUP':
        data['issues'].append('BACKUP 节点 MySQL 处于可写状态，存在双主风险')

    return data


def format_keepalived_monitor_message(data):
    issues = data.get('issues', [])
    detail_items = [
        'Keepalived 服务状态：{0}'.format('运行中' if data.get('service_running') else '未运行'),
        'VIP：{0}'.format(data.get('vip') or '未配置'),
        '网络接口：{0}'.format(data.get('interface') or '-'),
        '本机是否持有VIP：{0}'.format('是' if data.get('vip_owned') else '否'),
        'VIP Ping：{0}'.format(data.get('vip_ping', {}).get('status')),
        'VIP 冲突检测：{0}'.format(data.get('vip_conflict', {}).get('status')),
        '通过VIP访问MySQL：{0}'.format('正常' if data.get('vip_mysql_port_ok') else '失败'),
        '本地MySQL端口：{0}'.format('正常' if data.get('local_mysql_port_ok') else '失败'),
        'MySQL 读写状态：{0}'.format(data.get('mysql_state', {}).get('status'))
    ]
    issue_html = ''.join('<li>{0}</li>'.format(item) for item in issues) or '<li>无</li>'
    detail_html = ''.join('<li>{0}</li>'.format(item) for item in detail_items)
    return (
        '<p>Keepalived 实时监测报告（{0}）</p>'.format(data.get('timestamp')) +
        '<p>异常项：</p><ul>{0}</ul>'.format(issue_html) +
        '<p>检测详情：</p><ul>{0}</ul>'.format(detail_html)
    )


def _send_notification(title, content, stype, trigger_time):
    sys.path.append(os.path.join(ROOT_DIR, 'class', 'core'))
    import mw  # type: ignore
    return mw.notifyMessage(msg=content, msgtype='html', title=title, stype=stype, trigger_time=trigger_time, is_write_log=True)


def parse_args():
    parser = argparse.ArgumentParser(description='Send keepalived notifications via mw.notifyMessage')
    parser.add_argument('--title', required=True, help='Notification title')
    parser.add_argument('--content', help='Notification content string')
    parser.add_argument('--content-file', help='Path to file for notification content')
    parser.add_argument('--msgtype', default='html', help='Message type (text/html)')
    parser.add_argument('--stype', default='keepalived-alert', help='Notification channel key')
    parser.add_argument('--trigger-time', type=int, default=300, help='Throttle window in seconds')
    return parser.parse_args()


def main_cli():
    args = parse_args()
    content = args.content
    if args.content_file:
        try:
            with open(args.content_file, 'r', encoding='utf-8') as fh:
                content = fh.read()
        except Exception as exc:
            print(json.dumps({'status': False, 'msg': f'Failed to read content file: {exc}'}))
            return 1
    if not content:
        print(json.dumps({'status': False, 'msg': 'Content is empty'}))
        return 1
    try:
        ok = _send_notification(args.title, content, args.stype, args.trigger_time)
    except Exception as exc:
        print(json.dumps({'status': False, 'msg': f'notifyMessage failed: {exc}'}))
        return 1
    print(json.dumps({'status': ok}))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main_cli())
