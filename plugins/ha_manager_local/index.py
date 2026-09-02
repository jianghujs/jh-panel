# coding:utf-8

import json
import os
import signal
import shlex
import subprocess
import sys
import time
import urllib.parse
import tempfile

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'status':
    print('start')
    sys.exit(0)

PANEL_DIR = '/www/server/jh-panel'
sys.path.append(os.path.join(PANEL_DIR, 'class/core'))
import mw


PLUGIN_NAME = 'ha_manager_local'
PLUGIN_DIR = os.path.join(PANEL_DIR, 'plugins', PLUGIN_NAME)
RUNTIME_DIR = '/www/server/ha_manager_local'
DATA_DIR = os.path.join(RUNTIME_DIR, 'data')
LOG_DIR = os.path.join(RUNTIME_DIR, 'logs')
STEP_LOG_DIR = os.path.join(LOG_DIR, 'steps')
VERSION_PATH = os.path.join(RUNTIME_DIR, 'version.pl')
CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')
STATE_PATH = os.path.join(DATA_DIR, 'state.json')
STEP_STATE_PATH = os.path.join(DATA_DIR, 'step_state.json')
ROLE_PATH = os.path.join(RUNTIME_DIR, 'role')
LOCK_PATH = os.path.join(DATA_DIR, 'switch.lock')
ACTION_LOG_PATH = os.path.join(LOG_DIR, 'actions.log')
PANEL_TITLE_STATE_PATH = '/www/server/jh-panel/data/ha_manager_title_state.json'
SWITCH_PY = os.path.join(PANEL_DIR, 'scripts/switch.py')
MYSQL_PY = os.path.join(PANEL_DIR, 'scripts/mysql.py')
MYSQL_APT_INDEX = os.path.join(PANEL_DIR, 'plugins/mysql-apt/index.py')
RSYNCD_INDEX = os.path.join(PANEL_DIR, 'plugins/rsyncd/index.py')
OPENRESTY_INDEX = os.path.join(PANEL_DIR, 'plugins/openresty/index.py')
OS_TOOL_DIR = os.path.join(PANEL_DIR, 'scripts/os_tool/vm/default')
STANDBY_SYNC_PUBLIC_KEY = '/root/.ssh/standby_sync.pub'
AUTHORIZED_KEYS = '/root/.ssh/authorized_keys'
DRY_RUN = os.environ.get('HA_MANAGER_LOCAL_DRY_RUN') == '1'
CURRENT_STEP_RUN_ID = ''


class StepCommandError(RuntimeError):
    def __init__(self, message, logs):
        super(StepCommandError, self).__init__(message)
        self.logs = logs


def _now():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


def _ensure_dirs():
    for path in (RUNTIME_DIR, DATA_DIR, LOG_DIR, STEP_LOG_DIR):
        if not os.path.exists(path):
            os.makedirs(path, mode=0o700, exist_ok=True)
    if not os.path.exists(VERSION_PATH) or not mw.readFile(VERSION_PATH).strip():
        mw.writeFile(VERSION_PATH, '1.0')
    if not os.path.exists(ROLE_PATH):
        mw.writeFile(ROLE_PATH, 'standby')


def _read_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        return data if isinstance(data, type(default)) else default
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
    if '%' in raw:
        raw = urllib.parse.unquote(raw)
    try:
        data = json.loads(raw)
        if isinstance(data, str):
            data = json.loads(data)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _return(status, msg, data=None):
    return mw.returnJson(bool(status), msg, data if data is not None else {})


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


def _host_id():
    _ensure_dirs()
    host_file = os.path.join(RUNTIME_DIR, 'host_id.pl')
    current = mw.readFile(host_file).strip() if os.path.exists(host_file) else ''
    if current:
        return current
    current = 'H_LOCAL_' + time.strftime('%Y%m%d%H%M%S', time.localtime()) + '_' + mw.getRandomString(8).upper()
    mw.writeFile(host_file, current)
    return current


def _read_role(default='standby'):
    _ensure_dirs()
    role = mw.readFile(ROLE_PATH).strip() if os.path.exists(ROLE_PATH) else ''
    return role if role in ('master', 'standby') else default


def _write_role(role):
    if role not in ('master', 'standby'):
        raise RuntimeError('未知主备状态: ' + str(role))
    _ensure_dirs()
    mw.writeFile(ROLE_PATH, role)
    cfg = _config(False)
    cfg['role'] = role
    cfg['desired_role'] = role
    cfg['switch_status'] = 'idle'
    _save_config(cfg)
    return cfg


def _default_config():
    role = _read_role()
    return {
        'host_id': _host_id(),
        'host_name': _panel_title(),
        'host_ip': mw.getHostAddr(),
        'pair_id': '',
        'pair_name': '',
        'monitor_url': '',
        'report_interval': 30,
        'last_report_at': '',
        'role': role,
        'desired_role': role,
        'switch_status': 'idle',
        'last_action': '等待操作',
        'options': {}
    }


def _config(save_missing=True):
    _ensure_dirs()
    cfg = _default_config()
    saved = _read_json(CONFIG_PATH, {})
    cfg.update(saved)
    cfg['host_name'] = _panel_title()
    cfg['host_ip'] = mw.getHostAddr() or cfg.get('host_ip')
    file_role = _read_role(cfg.get('role') or 'standby')
    if file_role in ('master', 'standby'):
        cfg['role'] = file_role
    if cfg.get('desired_role') not in ('master', 'standby'):
        cfg['desired_role'] = cfg.get('role') or 'standby'
    if save_missing:
        _save_config(cfg)
    return cfg


def _write_panel_title_state(cfg):
    data = {
        'installed': True,
        'role': cfg.get('role') or 'standby',
        'desired_role': cfg.get('desired_role') or cfg.get('role') or 'standby',
        'switch_status': cfg.get('switch_status') or 'idle',
        'host_name': cfg.get('host_name') or _panel_title(),
        'updated_at': _now()
    }
    parent = os.path.dirname(PANEL_TITLE_STATE_PATH)
    if not os.path.exists(parent):
        os.makedirs(parent, mode=0o700, exist_ok=True)
    _write_json(PANEL_TITLE_STATE_PATH, data)
    return data


def _save_config(cfg):
    _write_json(CONFIG_PATH, cfg)
    _write_panel_title_state(cfg)
    return cfg


def _append_log(text):
    _ensure_dirs()
    line = '[{0}] {1}'.format(_now(), text)
    with open(ACTION_LOG_PATH, 'a', encoding='utf-8') as fp:
        fp.write(line + '\n')
    return line


def _step_log_path(run_id):
    run_id = ''.join([ch for ch in str(run_id or 'latest') if ch.isalnum() or ch in ('_', '-')]) or 'latest'
    return os.path.join(STEP_LOG_DIR, run_id + '.log')


def _append_step_log(run_id, text):
    _ensure_dirs()
    path = _step_log_path(run_id)
    with open(path, 'a', encoding='utf-8') as fp:
        fp.write(str(text).rstrip('\n') + '\n')
    return path


def _read_step_log(run_id):
    path = _step_log_path(run_id)
    if not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8', errors='replace') as fp:
        return fp.read()[-200000:]


def _step_log_lines(run_id):
    return _split_lines(_read_step_log(run_id))


def _split_lines(text):
    if not text:
        return []
    if isinstance(text, list):
        return [str(item) for item in text if str(item).strip()]
    return [line.rstrip('\n') for line in str(text).splitlines() if str(line).strip()]


def _read_logs(limit=200):
    if not os.path.exists(ACTION_LOG_PATH):
        return []
    try:
        with open(ACTION_LOG_PATH, 'r', encoding='utf-8') as fp:
            return [line.rstrip('\n') for line in fp.readlines()[-limit:]]
    except Exception:
        return []


def _quote(value):
    return shlex.quote(str(value))


def _node_script_cmd(script_name):
    script_path = os.path.join(OS_TOOL_DIR, script_name)
    env = 'HA_MANAGER_AUTO_CONFIRM=1 HA_MANAGER_SSH_AUTO_CONFIRM=1 NODE_DISABLE_COLORS=1 '
    if os.path.exists('/www/server/nodejs/fnm'):
        return 'export PATH="/www/server/nodejs/fnm:$PATH" && eval "$(fnm env --use-on-cd --shell bash)" && {0} node {1}'.format(env, _quote(script_path))
    return env + 'node ' + _quote(script_path)


def _script_header(title):
    return 'cd {0}\necho "执行目录: $(pwd)"\necho {1}\nset -e\nset -x'.format(_quote(PANEL_DIR), _quote('开始执行: ' + str(title or '当前步骤')))


def _script_runtime_wrapper(script_content, title):
    return _script_header(title) + '\n' + str(script_content or '').rstrip() + '\n'


def _rsyncd_task_script(status):
    return """names=$(python3 - <<'PY'
import json
path = '/www/server/rsyncd/config.json'
try:
    data = json.load(open(path, encoding='utf-8'))
except Exception:
    data = {{}}
items = ((data.get('send') or {{}}).get('list') or [])
print('|'.join([item.get('name', '') for item in items if item.get('name')]))
PY
)
if [ -n "$names" ]; then
  python3 {rsyncd_index} lsyncd_status_batch {{names:"$names",status:{status}}}
else
  echo "|- rsyncd 同步任务为空，跳过任务状态调整"
fi""".format(rsyncd_index=_quote(RSYNCD_INDEX), status=status)


def _authorized_key_script(enabled):
    if enabled:
        return """pub_file={pub_file}
auth_file={auth_file}
if [ -s "$pub_file" ]; then
  mkdir -p "$(dirname "$auth_file")"
  touch "$auth_file"
  pub=$(cat "$pub_file")
  grep -qxF "$pub" "$auth_file" || echo "$pub" >> "$auth_file"
  chmod 600 "$auth_file"
  echo "|- 已授权 standby_sync 同步公钥"
else
  echo "|- standby_sync.pub 不存在，跳过同步公钥授权"
fi""".format(pub_file=_quote(STANDBY_SYNC_PUBLIC_KEY), auth_file=_quote(AUTHORIZED_KEYS))
    return """pub_file={pub_file}
auth_file={auth_file}
if [ -s "$pub_file" ] && [ -f "$auth_file" ]; then
  pub=$(cat "$pub_file")
  grep -vxF "$pub" "$auth_file" > "$auth_file.tmp" || true
  mv "$auth_file.tmp" "$auth_file"
  chmod 600 "$auth_file"
  echo "|- 已移除 standby_sync 同步公钥"
else
  echo "|- standby_sync.pub 或 authorized_keys 不存在，跳过同步公钥移除"
fi""".format(pub_file=_quote(STANDBY_SYNC_PUBLIC_KEY), auth_file=_quote(AUTHORIZED_KEYS))


def _health_check_script(role):
    return """result=$(python3 {index_py} health_check '{{}}')
echo "$result"
echo "$result" | grep -q '"health_status": "normal"'""".format(index_py=_quote(os.path.join(PLUGIN_DIR, 'index.py')))


def _mysql_apt_init_slave_script():
    return """result_file=$(mktemp /tmp/hml_mysql_apt_init_slave.XXXXXX)
trap 'rm -f "$result_file"' EXIT
python3 {mysql_apt_index} init_slave_status 2>&1 | tee "$result_file"
python3 - "$result_file" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, 'r', encoding='utf-8', errors='replace') as fp:
    text = fp.read().strip()
lines = [line.strip() for line in text.splitlines() if line.strip()]
for line in reversed(lines):
    if line.startswith('{{') or line.startswith('['):
        data = json.loads(line)
        if not data.get('status'):
            sys.stderr.write('|- mysql-apt 初始化从库失败: ' + str(data.get('msg') or data) + '\\n')
            sys.exit(1)
        print('|- mysql-apt 初始化从库返回成功: ' + str(data.get('msg') or 'ok'))
        sys.exit(0)
sys.stderr.write('|- mysql-apt init_slave_status 未返回 JSON，无法确认执行结果\\n')
sys.exit(1)
PY""".format(mysql_apt_index=_quote(MYSQL_APT_INDEX))


def _step_script_body(step_key, target_role=''):
    step_meta = _step_meta(target_role if target_role in ('master', 'standby') else 'master', step_key)
    scripts = {
        'mysql_online': 'python3 {0} ensureRunning --reason {1}'.format(_quote(MYSQL_PY), _quote('HA 本地切换')) if os.path.exists(MYSQL_PY) else 'systemctl start mysqld',
        'promote_mysql': _node_script_cmd('switch__mysql_master.js'),
        'open_lsyncd_cron': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote('[勿删]lsyncd实时任务定时同步')),
        'enable_rsyncd_tasks': _rsyncd_task_script('enabled'),
        'restart_lsyncd': 'systemctl restart lsyncd',
        'authorized_key_off': _authorized_key_script(False),
        'close_backup_db': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote('备份数据库[backupAll]')),
        'close_xtrabackup': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote('[勿删]xtrabackup-cron')),
        'close_xtrabackup_full': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote('[勿删]xtrabackup-inc全量备份')),
        'close_xtrabackup_inc': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote('[勿删]xtrabackup-inc增量备份')),
        'open_site_backup': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote('备份网站配置[backupAll]')),
        'open_plugin_backup_all': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote('备份插件配置[所有]')),
        'open_plugin_backup_batch': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote('备份插件配置[backupAll]')),
        'close_site_restore': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote('恢复网站配置[所有]')),
        'close_plugin_restore': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote('恢复插件配置[所有]')),
        'open_cert_cron': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote("[勿删]续签Let's Encrypt证书")),
        'open_email_notify': 'python3 {0} openEmailNotify'.format(_quote(SWITCH_PY)),
        'open_mysql_notify': 'python3 {0} openMysqlSlaveNotify'.format(_quote(SWITCH_PY)),
        'open_rsync_notify': 'python3 {0} openRsyncStatusNotify'.format(_quote(SWITCH_PY)),
        'open_ssl_notify': 'python3 {0} setNotifyValue {1}'.format(_quote(SWITCH_PY), _quote(json.dumps({'ssl_cert': 14}, ensure_ascii=False))),
        'master_openresty': '\n'.join(['systemctl stop nginx || true', 'systemctl disable nginx || true', 'systemctl unmask openresty || true', 'systemctl enable openresty || true', 'python3 {0} start'.format(_quote(OPENRESTY_INDEX)) if os.path.exists(OPENRESTY_INDEX) else 'systemctl start openresty']),
        'role_master': 'echo master > {0}'.format(_quote(ROLE_PATH)),
        'master_check': _health_check_script('master'),
        'close_external': '\n'.join(['python3 {0} stop'.format(_quote(OPENRESTY_INDEX)) if os.path.exists(OPENRESTY_INDEX) else 'systemctl stop openresty', 'systemctl stop openresty || true', 'systemctl disable openresty || true', 'systemctl mask openresty || true', 'systemctl stop nginx || true', 'systemctl disable nginx || true']),
        'demote_mysql': _mysql_apt_init_slave_script(),
        'disable_rsyncd_tasks': _rsyncd_task_script('disabled'),
        'stop_lsyncd': 'systemctl stop lsyncd',
        'kill_rsync': "ps aux | grep '/bin/[r]sync' | awk '{print $2}' | xargs -r kill -9",
        'close_lsyncd_cron': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote('[勿删]lsyncd实时任务定时同步')),
        'close_mysql_notify': 'python3 {0} closeMysqlSlaveNotify'.format(_quote(SWITCH_PY)),
        'close_rsync_notify': 'python3 {0} closeRsyncStatusNotify'.format(_quote(SWITCH_PY)),
        'close_ssl_notify': 'python3 {0} setNotifyValue {1}'.format(_quote(SWITCH_PY), _quote(json.dumps({'ssl_cert': -1}, ensure_ascii=False))),
        'authorized_key_on': _authorized_key_script(True),
        'open_backup_db': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote('备份数据库[backupAll]')),
        'open_xtrabackup': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote('[勿删]xtrabackup-cron')),
        'open_xtrabackup_full': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote('[勿删]xtrabackup-inc全量备份')),
        'open_xtrabackup_inc': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote('[勿删]xtrabackup-inc增量备份')),
        'close_site_backup': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote('备份网站配置[backupAll]')),
        'close_plugin_backup_all': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote('备份插件配置[所有]')),
        'close_plugin_backup_batch': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote('备份插件配置[backupAll]')),
        'open_site_restore': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote('恢复网站配置[所有]')),
        'open_plugin_restore': 'python3 {0} openCrontab {1}'.format(_quote(SWITCH_PY), _quote('恢复插件配置[所有]')),
        'close_cert_cron': 'python3 {0} closeCrontab {1}'.format(_quote(SWITCH_PY), _quote("[勿删]续签Let's Encrypt证书")),
        'role_standby': 'echo standby > {0}'.format(_quote(ROLE_PATH)),
        'standby_check': _health_check_script('standby')
    }
    return scripts.get(step_key) or step_meta.get('code') or ('echo ' + _quote('未知步骤: ' + step_key))


def _step_script_content(step_key, target_role=''):
    step_meta = _step_meta(target_role if target_role in ('master', 'standby') else 'master', step_key)
    title = step_meta.get('title') or step_key
    return _script_runtime_wrapper(_step_script_body(step_key, target_role), title)


def _run(cmd, title, timeout=1800, required=True):
    log = ['|- ' + title, '|- 执行目录: ' + PANEL_DIR, '|- 执行脚本: ' + cmd]
    if CURRENT_STEP_RUN_ID:
        _write_step_log_lines(CURRENT_STEP_RUN_ID, log)
    if DRY_RUN:
        dry_run_line = '|- dry-run: ' + cmd
        log.append(dry_run_line)
        if CURRENT_STEP_RUN_ID:
            _append_step_log(CURRENT_STEP_RUN_ID, dry_run_line)
        return '\n'.join(log)
    proc = subprocess.Popen(cmd, shell=True, cwd=PANEL_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1, executable='/bin/bash', preexec_fn=os.setsid)
    started_at = time.time()
    timed_out = False
    output_lines = []
    while True:
        line = proc.stdout.readline() if proc.stdout else ''
        if line:
            text = line.rstrip('\n')
            if text.strip():
                output_lines.append(text)
                log.append(text)
                if CURRENT_STEP_RUN_ID:
                    _append_step_log(CURRENT_STEP_RUN_ID, text)
        if proc.poll() is not None:
            rest = proc.stdout.read() if proc.stdout else ''
            for text in _split_lines(rest):
                output_lines.append(text)
                log.append(text)
                if CURRENT_STEP_RUN_ID:
                    _append_step_log(CURRENT_STEP_RUN_ID, text)
            break
        if timeout and time.time() - started_at > timeout:
            timed_out = True
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                pass
            time.sleep(1)
            if proc.poll() is None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
            break
        time.sleep(0.05)
    code = proc.poll()
    if code is None:
        code = -9
    if timed_out:
        timeout_line = '|- 执行超时，已终止脚本 timeout={0}s'.format(timeout)
        log.append(timeout_line)
        if CURRENT_STEP_RUN_ID:
            _append_step_log(CURRENT_STEP_RUN_ID, timeout_line)
    if code != 0 and required:
        tail = '；'.join((output_lines or ['无输出'])[-10:])
        exit_line = '|- exit_code: {0}'.format(code)
        log.append(exit_line)
        if CURRENT_STEP_RUN_ID:
            _append_step_log(CURRENT_STEP_RUN_ID, exit_line)
        raise StepCommandError('{0} 失败 exit_code={1}: {2}'.format(title, code, tail[-1000:]), log)
    if code != 0:
        exit_line = '|- 已忽略非关键失败 exit_code={0}'.format(code)
    else:
        exit_line = '|- exit_code: 0'
    log.append(exit_line)
    if CURRENT_STEP_RUN_ID:
        _append_step_log(CURRENT_STEP_RUN_ID, exit_line)
    return '\n'.join(log)


def _write_step_log_lines(run_id, lines):
    for line in _split_lines(lines):
        _append_step_log(run_id, line)


def _overwrite_step_log_lines(run_id, lines):
    _ensure_dirs()
    path = _step_log_path(run_id)
    with open(path, 'w', encoding='utf-8') as fp:
        for line in _split_lines(lines):
            fp.write(line + '\n')
    return path


def _run_script_content(script_content, title, run_id, timeout=1800):
    _ensure_dirs()
    script_content = str(script_content or '').rstrip() + '\n'
    fd, script_path = tempfile.mkstemp(prefix='hml_step_', suffix='.sh', dir=LOG_DIR)
    os.close(fd)
    try:
        runtime_script = _script_runtime_wrapper(script_content, title)
        with open(script_path, 'w', encoding='utf-8') as fp:
            fp.write(runtime_script)
        os.chmod(script_path, 0o750)
        _append_step_log(run_id, '|- 临时脚本文件: ' + script_path)
        _append_step_log(run_id, '|- 脚本内容开始')
        _write_step_log_lines(run_id, runtime_script)
        _append_step_log(run_id, '|- 脚本内容结束')
        return _run('bash ' + _quote(script_path), title, timeout=timeout)
    finally:
        try:
            if os.path.exists(script_path):
                os.remove(script_path)
        except Exception:
            pass


def _run_optional(cmd, title):
    return _run(cmd, title, required=False)


def _run_node_script(script_name, title):
    script_path = os.path.join(OS_TOOL_DIR, script_name)
    if not os.path.exists(script_path):
        raise RuntimeError('脚本不存在: ' + script_path)
    env = 'HA_MANAGER_AUTO_CONFIRM=1 HA_MANAGER_SSH_AUTO_CONFIRM=1 NODE_DISABLE_COLORS=1 '
    if os.path.exists('/www/server/nodejs/fnm'):
        cmd = 'export PATH="/www/server/nodejs/fnm:$PATH" && eval "$(fnm env --use-on-cd --shell bash)" && {0} node {1}'.format(env, _quote(script_path))
    else:
        cmd = env + 'node ' + _quote(script_path)
    return _run(cmd, title)


def _systemctl_active(service):
    out, err, code = mw.execShell('systemctl is-active {0}'.format(_quote(service)))
    return code == 0 and out.strip() == 'active'


def _systemctl_exists(service):
    out, err, code = mw.execShell('systemctl list-unit-files {0}.service --no-legend'.format(_quote(service)))
    return code == 0 and bool(out.strip())


def _cron_status(name):
    names = name if isinstance(name, list) else [name]
    for cron_name in names:
        info = mw.M('crontab').where('name=?', (cron_name,)).field('id,name,status').find()
        if info:
            return 'enabled' if int(info.get('status') or 0) == 1 else 'disabled'
    return 'missing'


def _set_cron(name, enabled):
    func = 'openCrontab' if enabled else 'closeCrontab'
    action = '开启' if enabled else '关闭'
    return _run('python3 {0} {1} {2}'.format(_quote(SWITCH_PY), func, _quote(name)), action + '定时任务 ' + name)


def _notify_status(name):
    data = mw.getControlNotifyConfig()
    return 'enabled' if int(data.get(name) or 0) == 1 else 'disabled'


def _set_notify_func(func, title):
    return _run('python3 {0} {1}'.format(_quote(SWITCH_PY), func), title)


def _set_ssl_notify(value):
    payload = json.dumps({'ssl_cert': value}, ensure_ascii=False)
    return _run('python3 {0} setNotifyValue {1}'.format(_quote(SWITCH_PY), _quote(payload)), ('开启' if value > 0 else '关闭') + ' SSL 到期提醒')


def _standby_sync_public_key():
    if not os.path.exists(STANDBY_SYNC_PUBLIC_KEY):
        return ''
    return mw.readFile(STANDBY_SYNC_PUBLIC_KEY).strip()


def _authorized_key_status():
    pub = _standby_sync_public_key()
    auth = mw.readFile(AUTHORIZED_KEYS) if os.path.exists(AUTHORIZED_KEYS) else ''
    return 'authorized' if pub and pub in auth else 'unauthorized'


def _set_authorized_key(enabled):
    pub = _standby_sync_public_key()
    if not pub:
        return '|- standby_sync.pub 不存在，跳过同步公钥授权'
    if DRY_RUN:
        return '|- dry-run: ' + ('授权' if enabled else '移除') + ' standby_sync.pub'
    ssh_dir = os.path.dirname(AUTHORIZED_KEYS)
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
    lines = mw.readFile(AUTHORIZED_KEYS).splitlines() if os.path.exists(AUTHORIZED_KEYS) else []
    if enabled and pub not in lines:
        lines.append(pub)
    if not enabled:
        lines = [line for line in lines if line.strip() != pub]
    mw.writeFile(AUTHORIZED_KEYS, ('\n'.join(lines).strip() + '\n') if lines else '')
    try:
        os.chmod(AUTHORIZED_KEYS, 0o600)
    except Exception:
        pass
    return '|- 已' + ('授权' if enabled else '移除') + ' standby_sync 同步公钥'


def _rsyncd_tasks():
    data = _read_json('/www/server/rsyncd/config.json', {})
    return ((data.get('send') or {}).get('list') or [])


def _rsyncd_names():
    return '|'.join([item.get('name', '') for item in _rsyncd_tasks() if item.get('name')])


def _set_rsyncd_tasks(status):
    names = _rsyncd_names()
    if not names:
        return '|- rsyncd 同步任务为空，跳过任务状态调整'
    return _run('python3 {0} lsyncd_status_batch {{names:"{1}",status:{2}}}'.format(_quote(RSYNCD_INDEX), names, status), '调整 rsyncd 同步任务为 ' + status)


def _check_rsyncd_tasks(expected):
    tasks = _rsyncd_tasks()
    total = len(tasks)
    enabled_count = len([item for item in tasks if item.get('status', 'enabled') == 'enabled'])
    if total == 0:
        return 'skip', '无同步任务'
    actual = 'enabled' if enabled_count > 0 else 'disabled'
    if expected == 'disabled' and enabled_count == 0:
        actual = 'disabled'
    return actual, '同步任务 {0} 个，已启用 {1} 个'.format(total, enabled_count)


def _check_lsyncd_service(expected):
    realtime_tasks = [item for item in _rsyncd_tasks() if item.get('realtime') == 'true']
    if len(realtime_tasks) == 0:
        return 'skip', '无实时同步任务'
    active = 'running' if _systemctl_active('lsyncd') else 'stopped'
    return active, '实时任务 {0} 个，lsyncd {1}'.format(len(realtime_tasks), _actual_text(active))


def _check_openresty_service(expected):
    openresty_active = _systemctl_active('openresty')
    nginx_active = _systemctl_active('nginx')
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


def _expected_text(value):
    return {'enabled': '应启用', 'disabled': '应停用', 'running': '应运行', 'stopped': '应停止', 'authorized': '应授权', 'unauthorized': '应未授权'}.get(value, value)


def _actual_text(value):
    return {'enabled': '已启用', 'disabled': '已停用', 'missing': '不存在', 'running': '运行中', 'stopped': '已停止', 'authorized': '已授权', 'unauthorized': '未授权', 'skip': '无任务', 'unknown': '未知'}.get(value, value)


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
    {'group': 'SSH 同步', 'name': 'authorized_keys 同步公钥', 'type': 'authorized_key', 'master': 'unauthorized', 'standby': 'authorized'},
    {'group': 'rsync', 'name': 'rsyncd 任务', 'type': 'rsyncd_tasks', 'master': 'enabled', 'standby': 'disabled'},
    {'group': 'rsync', 'name': 'lsyncd 服务', 'type': 'lsyncd_service', 'master': 'running', 'standby': 'stopped'},
    {'group': 'Web 服务', 'name': 'OpenResty', 'type': 'openresty_service', 'master': 'running', 'standby': 'stopped'},
    {'group': '监控提醒', 'name': '主从同步异常提醒', 'type': 'notify', 'target': 'mysql_slave_status_notice', 'master': 'enabled', 'standby': 'disabled'},
    {'group': '监控提醒', 'name': 'Rsync 状态异常提醒', 'type': 'notify', 'target': 'rsync_status_notice', 'master': 'enabled', 'standby': 'disabled'},
    {'group': '监控提醒', 'name': 'SSL 到期提醒', 'type': 'notify_ssl', 'master': 'enabled', 'standby': 'disabled'},
    {'group': '角色状态', 'name': '本机角色标记', 'type': 'role', 'master': 'master', 'standby': 'standby'}
]


def _run_health_check_item(item, role):
    expected = item.get(role)
    actual_text = ''
    if item.get('type') == 'crontab':
        actual = _cron_status(item.get('target'))
        ok = actual == expected or (expected == 'disabled' and actual == 'missing')
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
        actual = _notify_status(item.get('target'))
        ok = actual == expected
    elif item.get('type') == 'notify_ssl':
        data = mw.getControlNotifyConfig()
        ssl_value = int(data.get('ssl_cert') or -1)
        actual = 'enabled' if ssl_value > 0 else 'disabled'
        ok = actual == expected
    elif item.get('type') == 'authorized_key':
        actual = _authorized_key_status()
        ok = actual == expected
    elif item.get('type') == 'role':
        actual = _read_role()
        ok = actual == expected
    else:
        actual = 'unknown'
        ok = False
    return {'group': item.get('group'), 'name': item.get('name'), 'expected': _expected_text(expected), 'actual': actual_text or _actual_text(actual), 'status': 'pass' if ok else 'fail'}


def _health_checks(role):
    return [_run_health_check_item(item, role) for item in HA_CHECK_DEFS]


def _health_summary(checks):
    failed = [item for item in checks if item.get('status') == 'fail']
    if failed:
        return 'warning', '自检异常 {0} 项'.format(len(failed))
    return 'normal', '正常'


def _external_closed():
    actual, text = _check_openresty_service('stopped')
    return actual == 'stopped'


def _step_state():
    data = _read_json(STEP_STATE_PATH, {})
    return data if isinstance(data, dict) else {}


def _save_step_result(target_role, step_key, status, logs='', msg=''):
    data = _step_state()
    flow = data.setdefault(target_role, {})
    flow[step_key] = {'state': status, 'logs': _split_lines(logs)[-400:], 'msg': msg, 'updated_at': _now()}
    _write_json(STEP_STATE_PATH, data)


def _step_list(target_role):
    flow_config = _read_json(os.path.join(PLUGIN_DIR, 'flow_config.json'), {})
    steps = (((flow_config.get('roles') or {}).get(target_role) or {}).get('steps') or [])
    saved = (_step_state().get(target_role) or {})
    result = []
    for step in steps:
        item = step.copy()
        state = saved.get(item.get('key')) or {}
        item['state'] = state.get('state') or 'pending'
        item['logs'] = state.get('logs') or []
        item['failure_msg'] = state.get('msg') or ''
        result.append(item)
    return result


def _step_meta(target_role, step_key):
    flow_config = _read_json(os.path.join(PLUGIN_DIR, 'flow_config.json'), {})
    steps = (((flow_config.get('roles') or {}).get(target_role) or {}).get('steps') or [])
    for step in steps:
        if step.get('key') == step_key:
            return step
    return {'key': step_key, 'title': step_key}


def _state(cfg=None):
    cfg = cfg or _config()
    role = cfg.get('role') or _read_role()
    checks = _health_checks(role)
    health_status, health_text = _health_summary(checks)
    data = cfg.copy()
    data.update({
        'role': role,
        'desired_role': cfg.get('desired_role') or role,
        'health_status': health_status,
        'health_text': health_text,
        'external_closed': _external_closed(),
        'checks': checks,
        'steps': _step_list('master' if role == 'standby' else 'standby'),
        'step_list': _step_state(),
        'log': _read_logs(),
        'last_action': cfg.get('last_action') or '等待操作'
    })
    _write_json(STATE_PATH, data)
    return data


def _ensure_mysql_running():
    if os.path.exists(MYSQL_PY):
        return _run('python3 {0} ensureRunning --reason {1}'.format(_quote(MYSQL_PY), _quote('HA 本地切换')), '确认 MySQL 服务正常')
    return _run('systemctl start mysqld', '启动 MySQL 服务')


def _openresty_master():
    logs = []
    if _systemctl_exists('nginx'):
        logs.append(_run_optional('systemctl stop nginx', '停止系统 nginx 服务'))
        logs.append(_run_optional('systemctl disable nginx', '禁用系统 nginx 自启动'))
    logs.append(_run_optional('systemctl unmask openresty', '解除 OpenResty 锁定'))
    logs.append(_run_optional('systemctl enable openresty', '启用 OpenResty 自启动'))
    if os.path.exists(OPENRESTY_INDEX):
        logs.append(_run('python3 {0} start'.format(_quote(OPENRESTY_INDEX)), '启动 OpenResty'))
    else:
        logs.append(_run('systemctl start openresty', '启动 OpenResty'))
    if not DRY_RUN and not _systemctl_active('openresty'):
        logs.append(_run('systemctl start openresty', '兜底启动 OpenResty'))
    if not DRY_RUN and not _systemctl_active('openresty'):
        raise RuntimeError('启动 OpenResty 后仍未运行')
    return '\n'.join(logs)


def _openresty_standby():
    logs = []
    if os.path.exists(OPENRESTY_INDEX):
        logs.append(_run('python3 {0} stop'.format(_quote(OPENRESTY_INDEX)), '停止 OpenResty'))
    logs.append(_run_optional('systemctl stop openresty', '兜底停止 OpenResty 服务'))
    logs.append(_run_optional('systemctl disable openresty', '禁用 OpenResty 自启动'))
    logs.append(_run_optional('systemctl mask openresty', '锁定 OpenResty，防止自动拉起'))
    if _systemctl_exists('nginx'):
        logs.append(_run_optional('systemctl stop nginx', '停止系统 nginx 服务'))
        logs.append(_run_optional('systemctl disable nginx', '禁用系统 nginx 自启动'))
    if not DRY_RUN and (_systemctl_active('openresty') or _systemctl_active('nginx')):
        raise RuntimeError('关闭对外服务后 Web 服务仍在运行')
    return '\n'.join(logs)


def _demote_mysql_to_standby():
    return _run(_mysql_apt_init_slave_script(), '调用 mysql-apt 初始化从库')


STEP_ACTIONS = {
    'mysql_online': lambda: _ensure_mysql_running(),
    'promote_mysql': lambda: _run_node_script('switch__mysql_master.js', '将数据库提升为主'),
    'open_lsyncd_cron': lambda: _set_cron('[勿删]lsyncd实时任务定时同步', True),
    'enable_rsyncd_tasks': lambda: _set_rsyncd_tasks('enabled'),
    'restart_lsyncd': lambda: _run('systemctl restart lsyncd', '启动 lsyncd 服务'),
    'authorized_key_off': lambda: _set_authorized_key(False),
    'close_backup_db': lambda: _set_cron('备份数据库[backupAll]', False),
    'close_xtrabackup': lambda: _set_cron('[勿删]xtrabackup-cron', False),
    'close_xtrabackup_full': lambda: _set_cron('[勿删]xtrabackup-inc全量备份', False),
    'close_xtrabackup_inc': lambda: _set_cron('[勿删]xtrabackup-inc增量备份', False),
    'open_site_backup': lambda: _set_cron('备份网站配置[backupAll]', True),
    'open_plugin_backup_all': lambda: _set_cron('备份插件配置[所有]', True),
    'open_plugin_backup_batch': lambda: _set_cron('备份插件配置[backupAll]', True),
    'close_site_restore': lambda: _set_cron('恢复网站配置[所有]', False),
    'close_plugin_restore': lambda: _set_cron('恢复插件配置[所有]', False),
    'open_cert_cron': lambda: _set_cron("[勿删]续签Let's Encrypt证书", True),
    'open_email_notify': lambda: _set_notify_func('openEmailNotify', '开启邮件通知'),
    'open_mysql_notify': lambda: _set_notify_func('openMysqlSlaveNotify', '开启主从同步异常提醒'),
    'open_rsync_notify': lambda: _set_notify_func('openRsyncStatusNotify', '开启 Rsync 状态异常提醒'),
    'open_ssl_notify': lambda: _set_ssl_notify(14),
    'master_openresty': lambda: _openresty_master(),
    'role_master': lambda: '|- ' + _write_role('master').get('role', 'master'),
    'master_check': lambda: _assert_health('master'),
    'close_external': lambda: _openresty_standby(),
    'demote_mysql': lambda: _demote_mysql_to_standby(),
    'disable_rsyncd_tasks': lambda: _set_rsyncd_tasks('disabled'),
    'stop_lsyncd': lambda: _run_optional('systemctl stop lsyncd', '停止 lsyncd 服务'),
    'kill_rsync': lambda: _run_optional("ps aux | grep '/bin/[r]sync' | awk '{print $2}' | xargs -r kill -9", '清理 rsync 进程'),
    'close_lsyncd_cron': lambda: _set_cron('[勿删]lsyncd实时任务定时同步', False),
    'close_mysql_notify': lambda: _set_notify_func('closeMysqlSlaveNotify', '关闭主从同步异常提醒'),
    'close_rsync_notify': lambda: _set_notify_func('closeRsyncStatusNotify', '关闭 Rsync 状态异常提醒'),
    'close_ssl_notify': lambda: _set_ssl_notify(-1),
    'authorized_key_on': lambda: _set_authorized_key(True),
    'open_backup_db': lambda: _set_cron('备份数据库[backupAll]', True),
    'open_xtrabackup': lambda: _set_cron('[勿删]xtrabackup-cron', True),
    'open_xtrabackup_full': lambda: _set_cron('[勿删]xtrabackup-inc全量备份', True),
    'open_xtrabackup_inc': lambda: _set_cron('[勿删]xtrabackup-inc增量备份', True),
    'close_site_backup': lambda: _set_cron('备份网站配置[backupAll]', False),
    'close_plugin_backup_all': lambda: _set_cron('备份插件配置[所有]', False),
    'close_plugin_backup_batch': lambda: _set_cron('备份插件配置[backupAll]', False),
    'open_site_restore': lambda: _set_cron('恢复网站配置[所有]', True),
    'open_plugin_restore': lambda: _set_cron('恢复插件配置[所有]', True),
    'close_cert_cron': lambda: _set_cron("[勿删]续签Let's Encrypt证书", False),
    'role_standby': lambda: '|- ' + _write_role('standby').get('role', 'standby'),
    'standby_check': lambda: _assert_health('standby')
}

STEP_ACTIONS_APPEND_RESULT = {'authorized_key_off', 'authorized_key_on', 'role_master', 'role_standby', 'master_check', 'standby_check'}


def _assert_health(role):
    checks = _health_checks(role)
    failed = [item for item in checks if item.get('status') == 'fail']
    if failed:
        names = '、'.join([item.get('name') or '' for item in failed[:5]])
        raise RuntimeError('自检发现 {0} 个异常项：{1}'.format(len(failed), names))
    return '|- 自检通过'


def _lock():
    _ensure_dirs()
    if os.path.exists(LOCK_PATH):
        try:
            pid = int(mw.readFile(LOCK_PATH).strip() or '0')
            if pid and os.path.exists('/proc/{0}'.format(pid)):
                return False
        except Exception:
            pass
    mw.writeFile(LOCK_PATH, str(os.getpid()))
    return True


def _unlock():
    try:
        if os.path.exists(LOCK_PATH):
            os.remove(LOCK_PATH)
    except Exception:
        pass


def get_state():
    cfg = _config()
    return _return(True, 'ok', _state(cfg))


def title_state():
    cfg = _config()
    return _return(True, 'ok', _write_panel_title_state(cfg))


def health_check():
    cfg = _config()
    checks = _health_checks(cfg.get('role') or 'standby')
    status_text, msg = _health_summary(checks)
    return _return(True, msg, {'checks': checks, 'health_status': status_text, 'health_text': msg, 'external_closed': _external_closed()})


def get_step_script():
    data = _args()
    step_key = str(data.get('step_key') or data.get('key') or '').strip()
    target_role = str(data.get('target_role') or '').strip()
    if target_role not in ('master', 'standby'):
        return _return(False, '目标状态无效')
    if step_key not in STEP_ACTIONS:
        return _return(False, '未知步骤: ' + step_key)
    step_meta = _step_meta(target_role, step_key)
    script = _step_script_body(step_key, target_role)
    return _return(True, 'ok', {'step_key': step_key, 'target_role': target_role, 'title': step_meta.get('title') or step_key, 'script': script})


def run_step():
    global CURRENT_STEP_RUN_ID
    data = _args()
    step_key = str(data.get('step_key') or data.get('key') or '').strip()
    target_role = str(data.get('target_role') or '').strip()
    run_id = str(data.get('run_id') or data.get('step_run_id') or ('STEP_' + time.strftime('%Y%m%d%H%M%S', time.localtime()))).strip()
    script_content = str(data.get('script_content') or '').strip()
    if target_role not in ('master', 'standby'):
        return _return(False, '目标状态无效')
    if step_key not in STEP_ACTIONS:
        return _return(False, '未知步骤: ' + step_key)
    if not _lock():
        return _return(False, '已有步骤正在执行，请稍后再试')
    cfg = _config()
    cfg['desired_role'] = target_role
    cfg['switch_status'] = 'running'
    cfg['last_action'] = '执行步骤: ' + step_key
    _save_config(cfg)
    try:
        CURRENT_STEP_RUN_ID = run_id
        step_meta = _step_meta(target_role, step_key)
        start_logs = ['|- 开始执行步骤: {0}'.format(step_meta.get('title') or step_key)]
        if step_meta.get('code'):
            start_logs.append('|- 预期脚本: ' + str(step_meta.get('code')))
        if script_content:
            start_logs.append('|- 执行来源: 前端代码编辑框')
            start_logs.append('|- 实际执行脚本: 前端提交脚本内容')
            start_logs.append('|- 前端提交脚本长度: {0} 字符'.format(len(script_content)))
        _overwrite_step_log_lines(run_id, start_logs)
        _save_step_result(target_role, step_key, 'running', start_logs, '')
        if script_content:
            _run_script_content(script_content, step_meta.get('title') or step_key, run_id)
        else:
            action_result = STEP_ACTIONS[step_key]()
            if step_key in STEP_ACTIONS_APPEND_RESULT and action_result:
                _write_step_log_lines(run_id, action_result)
        _append_step_log(run_id, '|- 步骤执行完成')
        done_logs = _step_log_lines(run_id)
        _save_step_result(target_role, step_key, 'done', done_logs, '')
        cfg = _config()
        cfg['desired_role'] = target_role
        cfg['switch_status'] = 'idle'
        cfg['last_action'] = '步骤完成: ' + step_key
        _save_config(cfg)
        _append_log(cfg['last_action'])
        return _return(True, '步骤执行完成', {'state': 'done', 'logs': done_logs, 'log': _read_step_log(run_id), 'run_id': run_id, 'log_path': _step_log_path(run_id), 'state_snapshot': _state(cfg)})
    except Exception as e:
        msg = str(e)
        step_meta = _step_meta(target_role, step_key)
        if not _read_step_log(run_id):
            fail_logs = ['|- 开始执行步骤: {0}'.format(step_meta.get('title') or step_key)]
            if step_meta.get('code'):
                fail_logs.append('|- 步骤配置脚本: ' + str(step_meta.get('code')))
            _overwrite_step_log_lines(run_id, fail_logs)
        if not isinstance(e, StepCommandError):
            _write_step_log_lines(run_id, _split_lines(msg))
        _append_step_log(run_id, '|- 步骤执行失败: ' + msg)
        fail_logs = _step_log_lines(run_id)
        _save_step_result(target_role, step_key, 'failed', fail_logs, msg)
        cfg = _config()
        cfg['switch_status'] = 'failed'
        cfg['last_action'] = '步骤失败: ' + step_key
        _save_config(cfg)
        _append_log(cfg['last_action'] + '，' + msg)
        return _return(False, msg, {'state': 'failed', 'logs': fail_logs, 'log': _read_step_log(run_id), 'run_id': run_id, 'log_path': _step_log_path(run_id), 'repair': _repair_guidance(step_key, msg), 'state_snapshot': _state(cfg)})
    finally:
        CURRENT_STEP_RUN_ID = ''
        _unlock()


def read_step_log():
    data = _args()
    run_id = data.get('run_id') or data.get('step_run_id') or ''
    return _return(True, 'ok', {'run_id': run_id, 'log': _read_step_log(run_id), 'log_path': _step_log_path(run_id)})


def _repair_guidance(step_key, msg):
    if step_key in ('close_external', 'master_openresty'):
        return {'title': '检查 OpenResty', 'action': '重新执行当前步骤', 'text': '请检查 OpenResty 服务状态和 80/443 端口占用后重试。'}
    if step_key in ('demote_mysql', 'promote_mysql', 'mysql_online'):
        return {'title': '检查数据库', 'action': '处理数据库后重试', 'text': '请确认 MySQL 服务正常、主从参数完整，再重新执行当前步骤。'}
    if 'cron' in step_key or 'backup' in step_key or 'restore' in step_key:
        return {'title': '检查计划任务', 'action': '重新执行当前步骤', 'text': '请确认计划任务存在，必要时先在计划任务页面恢复对应任务。'}
    return {'title': '查看日志后重试', 'action': '重新执行当前步骤', 'text': msg}


def reset_step():
    data = _args()
    step_key = str(data.get('step_key') or data.get('key') or '').strip()
    target_role = str(data.get('target_role') or '').strip()
    if target_role not in ('master', 'standby') or not step_key:
        return _return(False, '参数无效')
    state = _step_state()
    if target_role in state and step_key in state[target_role]:
        del state[target_role][step_key]
        _write_json(STEP_STATE_PATH, state)
    return _return(True, '已重置步骤', {'step_key': step_key, 'target_role': target_role})


def close_external_service():
    try:
        logs = _openresty_standby()
        _append_log('关闭对外服务完成')
        return _return(True, '关闭对外服务完成', {'external_closed': _external_closed(), 'logs': logs.splitlines(), 'state_snapshot': _state(_config())})
    except Exception as e:
        return _return(False, str(e), {'repair': _repair_guidance('close_external', str(e))})


def open_external_service():
    try:
        logs = _openresty_master()
        _append_log('打开对外服务完成')
        return _return(True, '打开对外服务完成', {'external_closed': _external_closed(), 'logs': logs.splitlines(), 'state_snapshot': _state(_config())})
    except Exception as e:
        return _return(False, str(e), {'repair': _repair_guidance('master_openresty', str(e))})


def save_monitor():
    data = _args()
    cfg = _config()
    for key in ('pair_id', 'pair_name', 'monitor_url', 'report_interval'):
        if key in data:
            cfg[key] = data.get(key) or ''
    _save_config(cfg)
    return _return(True, '已保存配置', cfg)


def clear_monitor():
    cfg = _config()
    cfg['monitor_url'] = ''
    cfg['last_report_at'] = ''
    _save_config(cfg)
    return _return(True, '已清空云监控地址', cfg)


def regenerate_host_id():
    new_host_id = 'H_LOCAL_' + time.strftime('%Y%m%d%H%M%S', time.localtime()) + '_' + mw.getRandomString(8).upper()
    mw.writeFile(os.path.join(RUNTIME_DIR, 'host_id.pl'), new_host_id)
    cfg = _config(False)
    cfg['host_id'] = new_host_id
    _save_config(cfg)
    return _return(True, '本机ID已重新生成', {'host_id': new_host_id})


def report_state():
    cfg = _config()
    cfg['last_report_at'] = _now()
    _save_config(cfg)
    return _return(True, '本机状态已刷新', cfg)


def read_log():
    return _return(True, 'ok', {'log': _read_logs()})


def status():
    return 'start'


if __name__ == '__main__':
    _ensure_dirs()
    func = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if func == 'status':
        print(status())
    elif func == 'get_state':
        print(get_state())
    elif func == 'title_state':
        print(title_state())
    elif func == 'health_check':
        print(health_check())
    elif func == 'get_step_script':
        print(get_step_script())
    elif func == 'run_step':
        print(run_step())
    elif func == 'read_step_log':
        print(read_step_log())
    elif func == 'reset_step':
        print(reset_step())
    elif func == 'close_external_service':
        print(close_external_service())
    elif func == 'open_external_service':
        print(open_external_service())
    elif func == 'save_monitor':
        print(save_monitor())
    elif func == 'clear_monitor':
        print(clear_monitor())
    elif func == 'regenerate_host_id':
        print(regenerate_host_id())
    elif func == 'report_state':
        print(report_state())
    elif func == 'read_log':
        print(read_log())
    else:
        print('error')
