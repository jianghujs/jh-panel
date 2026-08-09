# coding: utf-8

import argparse
import json
import os
import subprocess
import sys

PANEL_DIR = '/www/server/jh-panel'
SWITCH_PY = os.path.join(PANEL_DIR, 'scripts/switch.py')
RSYNCD_INDEX = os.path.join(PANEL_DIR, 'plugins/rsyncd/index.py')
OPENRESTY_INDEX = os.path.join(PANEL_DIR, 'plugins/openresty/index.py')
DRY_RUN = os.environ.get('HA_MANAGER_SWITCH_DRY_RUN') == '1'
OS_TOOL_DIR = '/www/server/jh-panel/scripts/os_tool/vm/default'
STANDBY_SYNC_PUBLIC_KEY = '/root/.ssh/standby_sync.pub'
AUTHORIZED_KEYS = '/root/.ssh/authorized_keys'


def _run(cmd, step):
    print('|- ' + step)
    if DRY_RUN:
        print('|- dry-run: ' + cmd)
        return
    proc = subprocess.run(cmd, cwd=PANEL_DIR, shell=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError('{0} 失败 exit_code={1}'.format(step, proc.returncode))


def _run_bash(cmd, step):
    _run('bash -lc ' + _quote(cmd), step)


def _run_node_script(script_name, step):
    script_path = os.path.join(OS_TOOL_DIR, script_name)
    if not os.path.exists(script_path):
        raise RuntimeError('Node脚本不存在: ' + script_path)
    _run('HA_MANAGER_AUTO_CONFIRM=1 node {0}'.format(_quote(script_path)), step)


def _json_arg(raw):
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _rsyncd_names():
    config_path = '/www/server/rsyncd/config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
    except Exception:
        return ''
    tasks = ((data.get('send') or {}).get('list') or [])
    return '|'.join([item.get('name', '') for item in tasks if item.get('name')])


def _set_rsyncd_tasks(status):
    names = _rsyncd_names()
    if not names:
        print('|- rsyncd 同步任务为空，跳过任务状态调整')
        return
    _run('python3 {0} lsyncd_status_batch {{names:"{1}",status:{2}}}'.format(RSYNCD_INDEX, names, status), '调整 rsyncd 同步任务为 ' + status)


def _open_cron(name):
    _run('python3 {0} openCrontab {1}'.format(SWITCH_PY, _quote(name)), '开启定时任务 ' + name)


def _close_cron(name):
    _run('python3 {0} closeCrontab {1}'.format(SWITCH_PY, _quote(name)), '关闭定时任务 ' + name)


def _quote(value):
    return "'" + str(value).replace("'", "'\\''") + "'"


def _bool_opt(opts, key, default=False):
    value = opts.get(key, default)
    if isinstance(value, str):
        return value.lower() in ('1', 'true', 'yes', 'y', 'on')
    return bool(value)


def _standby_sync_public_key():
    if not os.path.exists(STANDBY_SYNC_PUBLIC_KEY):
        return ''
    with open(STANDBY_SYNC_PUBLIC_KEY, 'r', encoding='utf-8') as fp:
        return fp.read().strip()


def _set_authorized_key(enabled):
    pub_key = _standby_sync_public_key()
    if not pub_key:
        print('|- standby_sync 同步公钥不存在，跳过 authorized_keys 切换')
        return
    action = '加入' if enabled else '移除'
    print('|- {0} standby_sync 同步公钥到 authorized_keys'.format(action))
    if DRY_RUN:
        print('|- dry-run: {0} {1}'.format(action, AUTHORIZED_KEYS))
        return
    ssh_dir = os.path.dirname(AUTHORIZED_KEYS)
    os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
    try:
        os.chmod(ssh_dir, 0o700)
    except Exception:
        pass
    if os.path.exists(AUTHORIZED_KEYS):
        with open(AUTHORIZED_KEYS, 'r', encoding='utf-8') as fp:
            lines = fp.read().splitlines()
    else:
        lines = []
    if enabled:
        if pub_key not in lines:
            lines.append(pub_key)
    else:
        lines = [line for line in lines if line.strip() != pub_key]
    with open(AUTHORIZED_KEYS, 'w', encoding='utf-8') as fp:
        fp.write('\n'.join(lines).strip() + ('\n' if lines else ''))
    os.chmod(AUTHORIZED_KEYS, 0o600)


def run_offline(args):
    _set_authorized_key(True)
    _open_cron('备份数据库[backupAll]')
    _open_cron('[勿删]xtrabackup-cron')
    _open_cron('[勿删]xtrabackup-inc全量备份')
    _open_cron('[勿删]xtrabackup-inc增量备份')
    _close_cron('备份网站配置[backupAll]')
    _close_cron('备份插件配置[所有]')
    _close_cron('备份插件配置[backupAll]')
    _close_cron('[勿删]lsyncd实时任务定时同步')
    _close_cron("[勿删]续签Let's Encrypt证书")
    _open_cron('恢复网站配置[所有]')
    _open_cron('恢复插件配置[所有]')
    _run('python3 {0} setNotifyValue \'{{"ssl_cert":-1}}\''.format(SWITCH_PY), '关闭 SSL证书到期预提醒')
    _run('python3 {0} closeMysqlSlaveNotify'.format(SWITCH_PY), '关闭主从同步异常提醒')
    _run('python3 {0} closeRsyncStatusNotify'.format(SWITCH_PY), '关闭Rsync状态异常提醒')
    _set_rsyncd_tasks('disabled')
    _run('systemctl stop lsyncd', '停止 lsyncd 服务')
    _run("ps aux | grep '/bin/[r]sync' | awk '{print $2}' | xargs -r kill -9", '清理 rsync 进程')
    _run('python3 {0} stop'.format(OPENRESTY_INDEX), '关闭 OpenResty')


def run_prepare_online(args):
    opts = _json_arg(args.args)
    print('|- 预上线选项 sync_files={0}, run_checksum={1}'.format(str(_bool_opt(opts, 'sync_files')).lower(), str(_bool_opt(opts, 'run_checksum')).lower()))
    if _bool_opt(opts, 'run_xtrabackup_inc_restore'):
        _run('python3 /www/server/jh-panel/plugins/xtrabackup-inc/index.py get_inc_recovery_cron_script | python3 -c "import sys,json,subprocess; d=json.load(sys.stdin); script=d.get(\'data\') or \"\"; subprocess.check_call(script, shell=True) if script else None"', '执行 xtrabackup 增量恢复')
    if _bool_opt(opts, 'run_checksum'):
        if DRY_RUN:
            _run_node_script('monitor__export_mysql_checksum_compare.js', '检查主备服务器 checksum')
        else:
            proc = subprocess.run(['node', os.path.join(OS_TOOL_DIR, 'monitor__export_mysql_checksum_compare.js')], cwd=OS_TOOL_DIR, text=True)
            if proc.returncode != 0 and not _bool_opt(opts, 'allow_checksum_diff'):
                raise RuntimeError('checksum 检查失败，未允许忽略差异')
            if proc.returncode != 0:
                print('|- checksum 存在差异，已按参数允许忽略')
    if _bool_opt(opts, 'sync_files'):
        remote_ip = opts.get('remote_ip') or ''
        remote_port = opts.get('remote_ssh_port') or '22'
        dirs = [item.strip() for item in str(opts.get('sync_file_dirs') or '/www/wwwroot,/www/wwwstorage').split(',') if item.strip()]
        ignores = [item.strip() for item in str(opts.get('sync_ignore_dirs') or 'node_modules,logs,run').split(',') if item.strip()]
        for sync_dir in dirs:
            cmd = ['rsync', '-avzP', '--delete', '-e', 'ssh -p ' + str(remote_port)]
            for ignore in ignores:
                cmd.append('--exclude=' + ignore)
            cmd.append('root@{0}:{1}/'.format(remote_ip, sync_dir.rstrip('/')))
            cmd.append(sync_dir.rstrip('/') + '/')
            _run(' '.join([_quote(x) for x in cmd]), '同步文件 ' + sync_dir)
    else:
        print('|- 跳过同步文件')
    if _bool_opt(opts, 'restore_site_setting'):
        restore_site_setting(opts)
    if _bool_opt(opts, 'restore_plugin_setting'):
        restore_plugin_setting(opts)


def run_online(args):
    opts = _json_arg(args.args)
    if _bool_opt(opts, 'promote_mysql', True):
        _run_node_script('switch__mysql_master.js', '将当前数据库提升为主')
    _set_authorized_key(False)
    _close_cron('备份数据库[backupAll]')
    _close_cron('[勿删]xtrabackup-cron')
    _close_cron('[勿删]xtrabackup-inc全量备份')
    _close_cron('[勿删]xtrabackup-inc增量备份')
    _open_cron('备份网站配置[backupAll]')
    _open_cron('备份插件配置[所有]')
    _open_cron('备份插件配置[backupAll]')
    _open_cron('[勿删]lsyncd实时任务定时同步')
    _open_cron("[勿删]续签Let's Encrypt证书")
    _close_cron('恢复网站配置[所有]')
    _close_cron('恢复插件配置[所有]')
    _run('python3 {0} setNotifyValue \'{{"ssl_cert":14}}\''.format(SWITCH_PY), '开启 SSL证书到期预提醒')
    _set_rsyncd_tasks('enabled')
    _run('systemctl restart lsyncd', '启动 lsyncd 服务')
    _run('python3 {0} start'.format(OPENRESTY_INDEX), '启动 OpenResty')
    _run('python3 {0} openEmailNotify'.format(SWITCH_PY), '开启邮件通知')
    _run('python3 {0} openMysqlSlaveNotify'.format(SWITCH_PY), '开启主从同步异常提醒')
    _run('python3 {0} openRsyncStatusNotify'.format(SWITCH_PY), '开启Rsync状态异常提醒')


def _latest_file(directory, prefix):
    files = []
    if os.path.isdir(directory):
        for name in os.listdir(directory):
            if name.startswith(prefix) and name.endswith('.zip'):
                files.append(os.path.join(directory, name))
    if not files:
        return ''
    files.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    return files[0]


def restore_site_setting(opts):
    backup_dir = opts.get('site_setting_backup_dir') or '/www/backup/site_setting'
    backup_file = opts.get('site_setting_file') or _latest_file(backup_dir, 'all_')
    if not backup_file:
        raise RuntimeError('未找到网站配置备份文件')
    tmp_dir = '/tmp/site_setting-restore'
    _run('rm -rf {0} && mkdir -p {0} && unzip -o {1} -d {0}'.format(_quote(tmp_dir), _quote(backup_file)), '解压网站配置备份')
    _run('python3 /www/server/jh-panel/scripts/migrate.py importSiteInfo {0}'.format(_quote(os.path.join(tmp_dir, 'site_info.json'))), '导入站点数据')
    _run('python3 /www/server/jh-panel/scripts/migrate.py importLetsencryptOrder {0}'.format(_quote(os.path.join(tmp_dir, 'letsencrypt.json'))), '合并 letsencrypt.json')
    _run('unzip -o {0} -d /www/server/web_conf/'.format(_quote(os.path.join(tmp_dir, 'web_conf.zip'))), '恢复 Web 配置')
    _run('python3 {0} restart'.format(OPENRESTY_INDEX), '重启 OpenResty')


def restore_plugin_setting(opts):
    backup_dir = opts.get('plugin_setting_backup_dir') or '/www/backup/plugin_setting'
    backup_file = opts.get('plugin_setting_file') or _latest_file(backup_dir, 'all_')
    if not backup_file:
        raise RuntimeError('未找到插件配置备份文件')
    tmp_dir = '/tmp/plugin_setting-restore'
    _run('rm -rf {0} && mkdir -p {0} && unzip -o {1} -d {0}'.format(_quote(tmp_dir), _quote(backup_file)), '解压插件配置备份')
    if DRY_RUN:
        print('|- dry-run: 跳过遍历插件配置解压目录')
        return
    selected = opts.get('restore_plugins') or 'all'
    selected_set = set([item.strip() for item in str(selected).split(',') if item.strip()]) if selected != 'all' else None
    for name in os.listdir(tmp_dir):
        if not name.endswith('.zip'):
            continue
        plugin_name = name[:-4]
        if selected_set is not None and plugin_name not in selected_set:
            continue
        _run('mkdir -p {0} && unzip -o {1} -d {0}'.format(_quote('/www/server/' + plugin_name), _quote(os.path.join(tmp_dir, name))), '恢复插件配置 ' + plugin_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['offline', 'prepare_online', 'online'], required=True)
    parser.add_argument('--args', default='{}')
    args = parser.parse_args()
    if args.phase == 'offline':
        run_offline(args)
    elif args.phase == 'prepare_online':
        run_prepare_online(args)
    else:
        run_online(args)
    print('|- 插件切换阶段执行完成')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('|- 插件切换阶段执行失败: ' + str(e), file=sys.stderr)
        sys.exit(1)
