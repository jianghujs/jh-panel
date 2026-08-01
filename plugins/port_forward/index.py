# coding:utf-8

import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
from urllib.parse import unquote
import ipaddress

sys.path.append(os.getcwd() + "/class/core")
import mw

PLUGIN_NAME = 'port_forward'
SERVER_DIR_NAME = 'port_forward'
RULE_PREFIX = 'jh-panel-port-forward'
CONFIG_PATH = mw.getServerDir() + '/' + SERVER_DIR_NAME + '/config.json'
LOG_PATH = mw.getServerDir() + '/' + SERVER_DIR_NAME + '/port_forward.log'
SERVICE_NAME = 'jh-panel-port-forward-restore.service'


def getPluginName():
    return PLUGIN_NAME


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + SERVER_DIR_NAME


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
        tmp[key] = unquote(value, 'utf-8').replace('+', ' ')
    return tmp


def checkArgs(data, ck=[]):
    for item in ck:
        if item not in data:
            return (False, mw.returnJson(False, '参数:(' + item + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def _ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _now():
    return int(time.time())


def _log(message):
    _ensure_dir(getServerDir())
    line = time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(message).strip() + '\n'
    try:
        with open(LOG_PATH, 'a') as fp:
            fp.write(line)
    except Exception:
        pass


def _run(command, timeout=20):
    try:
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or '').strip(), (proc.stderr or '').strip()
    except subprocess.TimeoutExpired:
        return 124, '', 'timeout'
    except Exception as exc:
        return 1, '', str(exc)


def _default_rules():
    return []


def _default_config():
    now = _now()
    return {
        'version': 1,
        'rule_prefix': RULE_PREFIX,
        'rules': _default_rules(),
        'created_at': now,
        'updated_at': now,
    }


def _safe_int(value, default=0):
    try:
        if value is None or value == '':
            return default
        return int(value)
    except Exception:
        return default


def _safe_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['1', 'true', 'yes', 'on', 'enabled']
    return bool(value)


def _normalize_id(value, fallback):
    value = str(value or '').strip()
    value = re.sub(r'[^A-Za-z0-9_.-]+', '-', value).strip('-')
    return value or fallback


def _normalize_rule(raw, index=0):
    raw = raw if isinstance(raw, dict) else {}
    fallback = 'rule-%s' % (index + 1)
    rule = {
        'id': _normalize_id(raw.get('id'), fallback),
        'enabled': _safe_bool(raw.get('enabled', True)),
        'listen_ip': str(raw.get('listen_ip', '') or '').strip(),
        'listen_iface': str(raw.get('listen_iface', '') or '').strip(),
        'listen_port': _safe_int(raw.get('listen_port'), 0),
        'target_ip': str(raw.get('target_ip', '') or '').strip(),
        'target_iface': str(raw.get('target_iface', '') or '').strip(),
        'target_port': _safe_int(raw.get('target_port'), 0),
        'remark': str(raw.get('remark', '') or '').strip(),
    }
    return rule


def _normalize_config(data):
    base = _default_config()
    if not isinstance(data, dict):
        return base
    raw_rules = data.get('rules')
    rules = []
    if isinstance(raw_rules, list):
        for idx, raw_rule in enumerate(raw_rules):
            rules.append(_normalize_rule(raw_rule, idx))
    base.update({
        'version': _safe_int(data.get('version', 1), 1),
        'rule_prefix': RULE_PREFIX,
        'rules': rules,
    })
    if 'created_at' in data:
        base['created_at'] = _safe_int(data.get('created_at'), base['created_at'])
    if 'updated_at' in data:
        base['updated_at'] = _safe_int(data.get('updated_at'), base['updated_at'])
    return base


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
    config['updated_at'] = _now()
    mw.writeFile(CONFIG_PATH, json.dumps(config, ensure_ascii=False, indent=2))
    return config


def _validate_iface(name, label):
    if not name:
        return False, label + '不能为空'
    if not re.match(r'^[A-Za-z0-9_.:-]+$', name):
        return False, label + '格式错误'
    return True, ''


def _validate_port(port, label):
    if port < 1 or port > 65535:
        return False, label + '必须在1-65535之间'
    return True, ''


def _validate_ip(value, label):
    if not value:
        return False, label + '不能为空'
    try:
        ipaddress.ip_address(value)
    except Exception:
        return False, label + '格式错误'
    return True, ''


def _validate_rule(rule):
    checks = [
        _validate_ip(rule.get('listen_ip'), '监听IP'),
        _validate_iface(rule.get('listen_iface'), '入口网卡'),
        _validate_port(rule.get('listen_port'), '监听端口'),
        _validate_ip(rule.get('target_ip'), '目标IP'),
        _validate_iface(rule.get('target_iface'), '出口网卡'),
        _validate_port(rule.get('target_port'), '目标端口'),
    ]
    for ok, msg in checks:
        if not ok:
            return False, msg
    return True, 'ok'


def _validate_config(config):
    ids = set()
    pairs = set()
    for idx, rule in enumerate(config.get('rules', [])):
        ok, msg = _validate_rule(rule)
        if not ok:
            return False, '规则%s: %s' % (idx + 1, msg)
        if rule['id'] in ids:
            return False, '规则ID重复: ' + rule['id']
        ids.add(rule['id'])
        pair = (rule['listen_ip'], rule['listen_port'])
        if pair in pairs:
            return False, '监听地址端口重复: %s:%s' % pair
        pairs.add(pair)
    return True, 'ok'


def _comment(rule):
    return '%s-%s-to-%s-%s' % (
        RULE_PREFIX,
        rule['listen_port'],
        rule['target_ip'].replace(':', '-').replace('.', '-'),
        rule['target_port'],
    )


def _is_loopback_ip(value):
    try:
        return ipaddress.ip_address(value).is_loopback
    except Exception:
        return False


def _q(value):
    return shlex.quote(str(value))


def _rule_commands(rule):
    comment = _comment(rule)
    listen_iface = _q(rule['listen_iface'])
    listen_port = _q(rule['listen_port'])
    target_ip = _q(rule['target_ip'])
    target_port = _q(rule['target_port'])
    target_iface = _q(rule['target_iface'])
    comment_q = _q(comment)
    dnat_to = _q('%s:%s' % (rule['target_ip'], rule['target_port']))
    listen_dest_match = '' if rule['listen_ip'] == '0.0.0.0' else ' -d ' + _q(rule['listen_ip'])
    if _is_loopback_ip(rule['target_ip']):
        commands = [
            {
                'table': 'sysctl',
                'chain': 'route_localnet',
                'check': '',
                'add': 'sysctl -w net.ipv4.conf.all.route_localnet=1',
                'delete': '',
            },
            {
                'table': 'nat',
                'chain': 'PREROUTING',
                'check': 'iptables -t nat -C PREROUTING -i %s%s -p tcp --dport %s -m comment --comment %s -j DNAT --to-destination %s' % (listen_iface, listen_dest_match, listen_port, comment_q, dnat_to),
                'add': 'iptables -t nat -A PREROUTING -i %s%s -p tcp --dport %s -m comment --comment %s -j DNAT --to-destination %s' % (listen_iface, listen_dest_match, listen_port, comment_q, dnat_to),
                'delete': 'iptables -t nat -D PREROUTING -i %s%s -p tcp --dport %s -m comment --comment %s -j DNAT --to-destination %s' % (listen_iface, listen_dest_match, listen_port, comment_q, dnat_to),
            }
        ]
        if rule['listen_ip'] != '0.0.0.0':
            listen_ip = _q(rule['listen_ip'])
            commands.append({
                'table': 'nat',
                'chain': 'OUTPUT',
                'check': 'iptables -t nat -C OUTPUT -d %s -p tcp --dport %s -m comment --comment %s -j DNAT --to-destination %s' % (listen_ip, listen_port, comment_q, dnat_to),
                'add': 'iptables -t nat -A OUTPUT -d %s -p tcp --dport %s -m comment --comment %s -j DNAT --to-destination %s' % (listen_ip, listen_port, comment_q, dnat_to),
                'delete': 'iptables -t nat -D OUTPUT -d %s -p tcp --dport %s -m comment --comment %s -j DNAT --to-destination %s' % (listen_ip, listen_port, comment_q, dnat_to),
            })
        return commands
    return [
        {
            'table': 'nat',
            'chain': 'PREROUTING',
            'check': 'iptables -t nat -C PREROUTING -i %s%s -p tcp --dport %s -m comment --comment %s -j DNAT --to-destination %s' % (listen_iface, listen_dest_match, listen_port, comment_q, dnat_to),
            'add': 'iptables -t nat -A PREROUTING -i %s%s -p tcp --dport %s -m comment --comment %s -j DNAT --to-destination %s' % (listen_iface, listen_dest_match, listen_port, comment_q, dnat_to),
            'delete': 'iptables -t nat -D PREROUTING -i %s%s -p tcp --dport %s -m comment --comment %s -j DNAT --to-destination %s' % (listen_iface, listen_dest_match, listen_port, comment_q, dnat_to),
        },
        {
            'table': 'filter',
            'chain': 'FORWARD',
            'check': 'iptables -C FORWARD -i %s -o %s -p tcp -d %s --dport %s -m comment --comment %s -j ACCEPT' % (listen_iface, target_iface, target_ip, target_port, comment_q),
            'add': 'iptables -A FORWARD -i %s -o %s -p tcp -d %s --dport %s -m comment --comment %s -j ACCEPT' % (listen_iface, target_iface, target_ip, target_port, comment_q),
            'delete': 'iptables -D FORWARD -i %s -o %s -p tcp -d %s --dport %s -m comment --comment %s -j ACCEPT' % (listen_iface, target_iface, target_ip, target_port, comment_q),
        },
        {
            'table': 'filter',
            'chain': 'FORWARD',
            'check': 'iptables -C FORWARD -i %s -o %s -p tcp -s %s --sport %s -m conntrack --ctstate ESTABLISHED,RELATED -m comment --comment %s -j ACCEPT' % (target_iface, listen_iface, target_ip, target_port, comment_q),
            'add': 'iptables -A FORWARD -i %s -o %s -p tcp -s %s --sport %s -m conntrack --ctstate ESTABLISHED,RELATED -m comment --comment %s -j ACCEPT' % (target_iface, listen_iface, target_ip, target_port, comment_q),
            'delete': 'iptables -D FORWARD -i %s -o %s -p tcp -s %s --sport %s -m conntrack --ctstate ESTABLISHED,RELATED -m comment --comment %s -j ACCEPT' % (target_iface, listen_iface, target_ip, target_port, comment_q),
        },
        {
            'table': 'nat',
            'chain': 'POSTROUTING',
            'check': 'iptables -t nat -C POSTROUTING -p tcp -d %s --dport %s -o %s -m comment --comment %s -j MASQUERADE' % (target_ip, target_port, target_iface, comment_q),
            'add': 'iptables -t nat -A POSTROUTING -p tcp -d %s --dport %s -o %s -m comment --comment %s -j MASQUERADE' % (target_ip, target_port, target_iface, comment_q),
            'delete': 'iptables -t nat -D POSTROUTING -p tcp -d %s --dport %s -o %s -m comment --comment %s -j MASQUERADE' % (target_ip, target_port, target_iface, comment_q),
        },
    ]


def _ensure_ipv4_forwarding():
    code, out, err = _run('sysctl -w net.ipv4.ip_forward=1')
    if code != 0:
        return False, err or out or '开启IPv4转发失败'
    return True, 'ok'


def _apply_rule(rule):
    _delete_rule(rule)
    actions = []
    for command in _rule_commands(rule):
        if command.get('table') == 'sysctl':
            code, out, err = _run(command['add'])
            if code != 0:
                return False, err or out or '开启route_localnet失败', actions
            actions.append({'chain': command['chain'], 'action': 'sysctl'})
            continue
        code, _, _ = _run(command['check'])
        if code == 0:
            actions.append({'chain': command['chain'], 'action': 'exists'})
            continue
        code, out, err = _run(command['add'])
        if code != 0:
            return False, err or out or '添加iptables规则失败', actions
        actions.append({'chain': command['chain'], 'action': 'added'})
    return True, 'ok', actions


def _delete_rule(rule):
    comment = _comment(rule)
    comment_actions = _delete_rules_by_comment(comment)
    actions = []
    for command in _rule_commands(rule):
        if command.get('table') == 'sysctl':
            continue
        deleted = 0
        while True:
            code, out, err = _run(command['delete'])
            if code != 0:
                break
            deleted += 1
        actions.append({'chain': command['chain'], 'deleted': deleted})
    if comment_actions:
        actions = comment_actions + actions
    return True, 'ok', actions


def _delete_rules_by_comment(comment):
    actions = []
    chain_specs = [
        ('nat', 'PREROUTING'),
        ('nat', 'OUTPUT'),
        ('nat', 'POSTROUTING'),
        ('filter', 'FORWARD'),
    ]
    for table, chain in chain_specs:
        list_cmd = 'iptables -t %s -S %s' % (_q(table), _q(chain)) if table != 'filter' else 'iptables -S %s' % _q(chain)
        code, out, err = _run(list_cmd, timeout=10)
        if code != 0 or not out:
            continue
        for line in out.split('\n'):
            if ('--comment ' + comment) not in line and ('--comment "' + comment + '"') not in line and ("--comment '" + comment + "'") not in line:
                continue
            if not line.startswith('-A ' + chain + ' '):
                continue
            delete_args = line.replace('-A ' + chain, '-D ' + chain, 1)
            delete_cmd = 'iptables -t %s %s' % (_q(table), delete_args) if table != 'filter' else 'iptables %s' % delete_args
            deleted = 0
            while True:
                d_code, d_out, d_err = _run(delete_cmd, timeout=10)
                if d_code != 0:
                    break
                deleted += 1
            if deleted:
                actions.append({'chain': chain, 'table': table, 'deleted_by_comment': deleted})
    return actions


def _install_restore_service(enable=True):
    system_dir = mw.systemdCfgDir()
    if not os.path.exists(system_dir):
        return False, 'systemd目录不存在: ' + system_dir
    tpl_path = getPluginDir() + '/init.d/port-forward-restore.service.tpl'
    content = mw.readFile(tpl_path)
    if not content:
        return False, '服务模板不存在'
    content = content.replace('{$ROOT_PATH}', mw.getRootDir())
    service_path = system_dir + '/' + SERVICE_NAME
    mw.writeFile(service_path, content)
    _run('systemctl daemon-reload')
    if enable:
        _run('systemctl enable ' + shlex.quote(SERVICE_NAME))
    return True, service_path


def _persist_runtime_rules():
    checks = [
        ('netfilter-persistent', 'command -v netfilter-persistent >/dev/null 2>&1 && netfilter-persistent save'),
        ('iptables-service', 'test -x /usr/libexec/iptables/iptables.init && /usr/libexec/iptables/iptables.init save'),
        ('service-iptables', 'service iptables save'),
    ]
    for name, command in checks:
        code, out, err = _run(command, timeout=30)
        if code == 0:
            return {'status': True, 'method': name, 'msg': out or 'saved'}
    if os.path.isdir('/etc/iptables'):
        code, out, err = _run('iptables-save > /etc/iptables/rules.v4', timeout=30)
        if code == 0:
            return {'status': True, 'method': 'iptables-save-rules.v4', 'msg': 'saved'}
        return {'status': False, 'method': 'iptables-save-rules.v4', 'msg': err or out}
    return {'status': False, 'method': 'none', 'msg': '未检测到iptables持久化组件，使用systemd恢复兜底'}


def _disable_restore_service():
    system_dir = mw.systemdCfgDir()
    service_path = system_dir + '/' + SERVICE_NAME
    _run('systemctl disable ' + shlex.quote(SERVICE_NAME))
    if os.path.exists(service_path):
        try:
            os.remove(service_path)
        except Exception:
            pass
    _run('systemctl daemon-reload')


def getConfig():
    config = _load_config()
    return mw.returnJson(True, 'ok', config)


def saveConfig():
    args = getArgs()
    data = {}
    old_config = _load_config()
    if 'config' in args:
        try:
            data = json.loads(args['config'])
        except Exception as exc:
            return mw.returnJson(False, '配置JSON格式错误: ' + str(exc))
    elif 'rules' in args:
        try:
            data = {'rules': json.loads(args['rules'])}
        except Exception as exc:
            return mw.returnJson(False, '规则JSON格式错误: ' + str(exc))
    else:
        return mw.returnJson(False, '缺少配置参数')
    current = old_config
    current.update(data)
    config = _normalize_config(current)
    ok, msg = _validate_config(config)
    if not ok:
        return mw.returnJson(False, msg)
    _cleanup_changed_rules(old_config, config)
    _write_config(config)
    _log('save config rules=%s' % len(config.get('rules', [])))
    return mw.returnJson(True, '保存成功', config)


def _cleanup_changed_rules(old_config, new_config):
    old_rules = {rule.get('id'): rule for rule in old_config.get('rules', [])}
    for rule in new_config.get('rules', []):
        old_rule = old_rules.get(rule.get('id'))
        if not old_rule:
            continue
        if old_rule != rule:
            _delete_rule(old_rule)


def getInterfaces():
    code, out, err = _run("ip -o -4 addr show | awk '{print $2, $4}'", timeout=10)
    items = []
    if code == 0 and out:
        for line in out.split('\n'):
            parts = line.split()
            if len(parts) >= 2:
                items.append({'iface': parts[0], 'cidr': parts[1], 'ip': parts[1].split('/')[0]})
    panel_ip = mw.getHostAddr()
    if not panel_ip or panel_ip == '127.0.0.1':
        panel_ip = mw.getLocalIp()
    return mw.returnJson(True, 'ok', {'items': items, 'panel_ip': panel_ip, 'error': err if code != 0 else ''})


def applyRules(restore=False):
    config = _load_config()
    ok, msg = _validate_config(config)
    if not ok:
        return mw.returnJson(False, msg)
    ok, msg = _ensure_ipv4_forwarding()
    if not ok:
        return mw.returnJson(False, msg)
    results = []
    for rule in config.get('rules', []):
        if not rule.get('enabled'):
            ok, msg, actions = _delete_rule(rule)
            results.append({'id': rule['id'], 'comment': _comment(rule), 'status': ok, 'msg': 'disabled-cleanup', 'actions': actions})
            continue
        ok, msg, actions = _apply_rule(rule)
        results.append({'id': rule['id'], 'comment': _comment(rule), 'status': ok, 'msg': msg, 'actions': actions})
        if not ok:
            _log('apply failed id=%s msg=%s' % (rule['id'], msg))
            return mw.returnJson(False, msg, {'results': results})
    persistence = {'status': False, 'method': 'skipped', 'msg': 'restore mode'} if restore else _persist_runtime_rules()
    if not restore:
        if persistence.get('status'):
            _disable_restore_service()
        else:
            _install_restore_service(True)
    _log('apply rules count=%s restore=%s persist=%s:%s' % (len(results), restore, persistence.get('method'), persistence.get('msg')))
    return mw.returnJson(True, '应用成功', {'results': results, 'persistence': persistence})


def restoreRules():
    return applyRules(True)


def deleteRules():
    config = _load_config()
    results = []
    for rule in config.get('rules', []):
        ok, msg, actions = _delete_rule(rule)
        results.append({'id': rule['id'], 'comment': _comment(rule), 'status': ok, 'msg': msg, 'actions': actions})
    persistence = _persist_runtime_rules()
    _log('delete rules count=%s persist=%s:%s' % (len(results), persistence.get('method'), persistence.get('msg')))
    return mw.returnJson(True, '删除成功', {'results': results, 'persistence': persistence})


def deleteRule():
    args = getArgs()
    if 'rule' not in args:
        return mw.returnJson(False, '缺少规则参数')
    try:
        rule = _normalize_rule(json.loads(args['rule']), 0)
    except Exception as exc:
        return mw.returnJson(False, '规则JSON格式错误: ' + str(exc))
    ok, msg = _validate_rule(rule)
    if not ok:
        return mw.returnJson(False, msg)
    ok, msg, actions = _delete_rule(rule)
    persistence = _persist_runtime_rules()
    _log('delete rule id=%s persist=%s:%s' % (rule.get('id'), persistence.get('method'), persistence.get('msg')))
    return mw.returnJson(True, '删除运行规则成功', {'id': rule.get('id'), 'actions': actions, 'persistence': persistence})


def _get_matching_rules():
    commands = [
        ('nat', 'iptables -t nat -S'),
        ('filter', 'iptables -S FORWARD'),
    ]
    rules = []
    for table, command in commands:
        code, out, err = _run(command, timeout=10)
        if code != 0:
            rules.append({'table': table, 'error': err or out})
            continue
        for line in out.split('\n'):
            if RULE_PREFIX in line:
                rules.append({'table': table, 'rule': line})
    return rules


def _get_counters():
    commands = [
        ('nat_prerouting', 'iptables -t nat -L PREROUTING -n -v --line-numbers'),
        ('nat_postrouting', 'iptables -t nat -L POSTROUTING -n -v --line-numbers'),
        ('forward', 'iptables -L FORWARD -n -v --line-numbers'),
    ]
    counters = []
    for name, command in commands:
        code, out, err = _run(command, timeout=10)
        if code != 0:
            counters.append({'chain': name, 'error': err or out})
            continue
        for line in out.split('\n'):
            if RULE_PREFIX in line or line.lower().startswith('num'):
                counters.append({'chain': name, 'line': line})
    return counters


def _read_ipv4_forwarding():
    code, out, err = _run('sysctl -n net.ipv4.ip_forward', timeout=5)
    if code == 0:
        return out
    return 'unknown: ' + (err or out)


def statusRules():
    config = _load_config()
    data = {
        'config': config,
        'ipv4_forwarding': _read_ipv4_forwarding(),
        'iptables_version': _run('iptables --version', timeout=5)[1],
        'rules': _get_matching_rules(),
        'counters': _get_counters(),
    }
    return mw.returnJson(True, 'ok', data)


def _route_to(ip):
    code, out, err = _run('ip route get ' + shlex.quote(ip), timeout=10)
    return {'status': code == 0, 'output': out, 'error': err}


def _tcp_check(ip, port):
    try:
        sock = socket.create_connection((ip, int(port)), timeout=5)
        sock.close()
        return {'status': True, 'msg': 'reachable'}
    except Exception as exc:
        return {'status': False, 'msg': str(exc)}


def checkRules():
    config = _load_config()
    code, addr_out, addr_err = _run('ip -o -4 addr show', timeout=10)
    local_ips = []
    if code == 0:
        for line in addr_out.split('\n'):
            parts = line.split()
            if len(parts) >= 4:
                local_ips.append({'iface': parts[1], 'cidr': parts[3], 'ip': parts[3].split('/')[0]})
    results = []
    for rule in config.get('rules', []):
        local_match = [item for item in local_ips if item['ip'] == rule['listen_ip'] and item['iface'] == rule['listen_iface']]
        listen_ip_exists = True if rule['listen_ip'] == '0.0.0.0' else len(local_match) > 0
        results.append({
            'id': rule['id'],
            'enabled': rule.get('enabled'),
            'comment': _comment(rule),
            'valid': _validate_rule(rule)[0],
            'listen_ip_exists': listen_ip_exists,
            'route': _route_to(rule['target_ip']),
            'target_port': _tcp_check(rule['target_ip'], rule['target_port']),
        })
    data = {
        'ipv4_forwarding': _read_ipv4_forwarding(),
        'local_addresses': local_ips,
        'local_addresses_error': addr_err if code != 0 else '',
        'results': results,
        'counters': _get_counters(),
    }
    return mw.returnJson(True, '检查完成', data)


def runLog():
    return LOG_PATH


def getLogs():
    if not os.path.exists(LOG_PATH):
        return mw.returnJson(True, 'ok', '')
    return mw.returnJson(True, 'ok', mw.getLastLine(LOG_PATH, 300))


def installPlugin():
    _ensure_dir(getServerDir())
    config = _load_config()
    _write_config(config)
    return mw.returnJson(True, 'ok', config)


def uninstallPlugin():
    deleteRules()
    _disable_restore_service()
    return mw.returnJson(True, '卸载完成')


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
    ok, msg = _install_restore_service(True)
    return 'ok' if ok else msg


def initdUinstall():
    _disable_restore_service()
    return 'ok'


if __name__ == "__main__":
    func = sys.argv[1] if len(sys.argv) > 1 else 'status'
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
    elif func == 'install_plugin':
        print(installPlugin())
    elif func == 'uninstall_plugin':
        print(uninstallPlugin())
    elif func == 'get_config':
        print(getConfig())
    elif func == 'save_config':
        print(saveConfig())
    elif func == 'get_interfaces':
        print(getInterfaces())
    elif func == 'apply_rules':
        print(applyRules(False))
    elif func == 'restore_rules':
        print(restoreRules())
    elif func == 'delete_rules':
        print(deleteRules())
    elif func == 'delete_rule':
        print(deleteRule())
    elif func == 'status_rules':
        print(statusRules())
    elif func == 'check_rules':
        print(checkRules())
    elif func == 'run_log':
        print(runLog())
    elif func == 'get_logs':
        print(getLogs())
    else:
        print('error')
