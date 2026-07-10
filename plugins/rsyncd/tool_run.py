# coding:utf-8

import sys
import os
import re
import json
import time
import subprocess
import traceback

_PANEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
os.chdir(_PANEL_DIR)
sys.path.append(os.path.join(_PANEL_DIR, 'class/core'))
import mw


def getPluginName():
    return 'rsyncd'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def loadTask(name):
    cfg_path = getServerDir() + '/config.json'
    cfg = json.loads(mw.readFile(cfg_path))
    for item in cfg.get('send', {}).get('list', []):
        if item.get('name') == name:
            return item
    raise RuntimeError('task not found in config.json: %s' % name)


def normalizeMaxDeletePercent(value):
    try:
        value = int(float(value))
    except Exception:
        value = 30
    if value < 0:
        return 0
    if value > 100:
        return 100
    return value


def whichRsync():
    out = mw.execShell('which rsync')[0]
    return out.strip() or 'rsync'


def taskPaths(task):
    name_dir = getServerDir() + '/send/' + task['name']
    return {
        'name_dir': name_dir,
        'log_dir': name_dir + '/logs',
        'exclude': name_dir + '/exclude',
        'pass_file': name_dir + '/pass',
    }


def statInt(output, label):
    pattern = r'^' + re.escape(label) + r':\s*([0-9][0-9,]*)'
    for line in output.splitlines():
        m = re.search(pattern, line.strip())
        if m:
            return int(m.group(1).replace(',', ''))
    return None


def collectPreflightChanges(output, limit=300):
    deleted = []
    changed = []
    skipped_prefixes = (
        'sending incremental file list',
        'Number of files:',
        'Number of created files:',
        'Number of deleted files:',
        'Number of regular files transferred:',
        'Total file size:',
        'Total transferred file size:',
        'Literal data:',
        'Matched data:',
        'File list size:',
        'File list generation time:',
        'File list transfer time:',
        'Total bytes sent:',
        'Total bytes received:',
        'sent ',
        'total size is ',
    )

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('*deleting '):
            deleted.append(line[len('*deleting '):])
            continue
        if line.startswith(skipped_prefixes):
            continue
        if re.match(r'^[<>ch\.\*][fdLDS][A-Za-z0-9\.\+\?]{8}\s+.+', line):
            changed.append(line)
            continue
        if line.startswith(('cd', 'created directory ')):
            changed.append(line)

    return {
        'deleted': deleted,
        'changed': changed,
        'deleted_more': max(0, len(deleted) - limit),
        'changed_more': max(0, len(changed) - limit),
        'deleted_items': deleted[:limit],
        'changed_items': changed[:limit],
    }


def formatPreflightChanges(changes):
    lines = []
    deleted_items = changes.get('deleted_items', [])
    changed_items = changes.get('changed_items', [])
    if deleted_items:
        lines.append('删除明细（dry-run，最多显示 %s 条）：' % len(deleted_items))
        lines.extend(['- ' + item for item in deleted_items])
        if changes.get('deleted_more', 0) > 0:
            lines.append('- ... 还有 %s 条删除未显示' % changes['deleted_more'])
    else:
        lines.append('删除明细：无')

    if changed_items:
        lines.append('')
        lines.append('变更明细（dry-run，最多显示 %s 条）：' % len(changed_items))
        lines.extend(['- ' + item for item in changed_items])
        if changes.get('changed_more', 0) > 0:
            lines.append('- ... 还有 %s 条变更未显示' % changes['changed_more'])
    return '\n'.join(lines)


def writeAbortLog(log_dir, message):
    ts = time.strftime('%Y%m%d_%H%M%S')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = log_dir + '/preflight_' + ts + '.log'
    mw.writeFile(log_file, message.rstrip() + '\n')
    print(message)
    print('preflight abort log: %s' % log_file)


def buildDryRunCmd(task, paths, rsync_bin):
    cmd = [rsync_bin, '-avzPr', '--dry-run', '--stats', '--itemize-changes']
    if task.get('delete') == 'true':
        cmd.append('--delete')

    bwlimit = str(task.get('rsync', {}).get('bwlimit', '0'))
    if task.get('conn_type') == 'ssh':
        ssh_cmd = 'ssh -p %s -i %s -o UserKnownHostsFile=/root/.ssh/known_hosts -o StrictHostKeyChecking=no' % (
            task.get('ssh_port', '22'), task.get('key_path', ''))
        cmd.extend([
            '-e', ssh_cmd,
            '--bwlimit=%s' % bwlimit,
            '--exclude-from=%s' % paths['exclude'],
            task.get('path', ''),
            'root@%s:%s' % (task.get('ip', ''), task.get('target_path', '')),
        ])
        return cmd

    remote_addr = task['name'] + '@' + task.get('ip', '') + '::' + task['name']
    cmd.extend([
        '--fake-super',
        '--port=%s' % task.get('rsync', {}).get('port', ''),
        '--bwlimit=%s' % bwlimit,
        '--exclude-from=%s' % paths['exclude'],
        '--password-file=%s' % paths['pass_file'],
        task.get('path', ''),
        remote_addr,
    ])
    return cmd




def getLatestRunLog(task):
    paths = taskPaths(task)
    log_dir = paths['log_dir']
    if not os.path.isdir(log_dir):
        return '', ''
    files = []
    for filename in os.listdir(log_dir):
        full_path = os.path.join(log_dir, filename)
        if filename.startswith('run_') and filename.endswith('.log') and os.path.isfile(full_path):
            files.append((full_path, os.path.getmtime(full_path)))
    if not files:
        return '', ''
    files.sort(key=lambda x: x[1], reverse=True)
    latest_log = files[0][0]
    return latest_log, mw.readFile(latest_log) or ''




def getRsyncErrorSummary(content, max_lines=20):
    if not content:
        return ''
    keywords = [
        'rsync:',
        'rsync error',
        'failed:',
        'Permission denied',
        'Operation not permitted',
        'No such file or directory',
        'Input/output error',
        'Connection refused',
        'Connection timed out',
        'connection unexpectedly closed',
        'No route to host',
        'some files/attrs were not transferred',
    ]
    lines = content.splitlines()
    selected = []
    for idx, line in enumerate(lines):
        if any(keyword in line for keyword in keywords):
            start = max(0, idx - 2)
            end = min(len(lines), idx + 3)
            selected.extend(lines[start:end])
    if not selected:
        return ''

    result = []
    seen = set()
    for line in selected:
        clean = line.rstrip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
    return '\n'.join(result[-max_lines:])


def runPreflight():
    if len(sys.argv) < 3:
        print('usage: tool_run.py preflight <task_name>')
        sys.exit(1)
    name = sys.argv[2]
    task = loadTask(name)
    paths = taskPaths(task)
    rsync_bin = whichRsync()

    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    cmd = buildDryRunCmd(task, paths, rsync_bin)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    stdout = proc.stdout.decode('utf-8', 'replace') if proc.stdout else ''
    stderr = proc.stderr.decode('utf-8', 'replace') if proc.stderr else ''
    output = stdout + ('\n' + stderr if stderr else '')

    if proc.returncode != 0:
        writeAbortLog(paths['log_dir'], 'rsync preflight failed for task %s, exit_code=%s\ncmd=%s\n%s' % (
            name, proc.returncode, ' '.join(cmd), output.strip()))
        sys.exit(1)

    total_files = statInt(output, 'Number of files')
    if total_files is None:
        writeAbortLog(paths['log_dir'], 'rsync preflight parse failed for task %s: missing Number of files.\ncmd=%s\n%s' % (
            name, ' '.join(cmd), output.strip()))
        sys.exit(1)

    deleted_files = statInt(output, 'Number of deleted files') or 0
    threshold = normalizeMaxDeletePercent(task.get('max_delete_percent', 30))
    ratio = 0 if total_files == 0 else (deleted_files * 100.0 / total_files)
    summary = 'rsync preflight task=%s deleted=%s total=%s ratio=%.2f%% threshold=%s%%' % (
        name, deleted_files, total_files, ratio, threshold)
    changes = collectPreflightChanges(output)
    detail = formatPreflightChanges(changes)
    print(summary)
    if changes.get('deleted_items'):
        print('rsync preflight deleting preview:')
        for item in changes['deleted_items'][:30]:
            print('- ' + item)
        if changes.get('deleted_more', 0) > 0:
            print('- ... 还有 %s 条删除未显示' % changes['deleted_more'])

    if ratio > threshold:
        writeAbortLog(paths['log_dir'], summary + '\nabort: delete ratio exceeds threshold, real rsync skipped\n\n' + detail)
        sys.exit(1)


def buildReason(task, exit_code, phase):
    if task.get('conn_type') == 'ssh':
        target = '%s:%s' % (task.get('ip', ''), task.get('target_path', ''))
    else:
        target = '%s:%s' % (task.get('ip', ''), task.get('name', ''))
    phase_name = '同步前检查' if phase == 'preflight' else 'rsync同步'
    mode = '完全同步' if task.get('delete') == 'true' else '增量同步'
    threshold = normalizeMaxDeletePercent(task.get('max_delete_percent', 30))
    paths = taskPaths(task)
    lines = [
        'rsync同步失败',
        '任务名称：%s' % task.get('name', ''),
        '失败阶段：%s' % phase_name,
        '退出码：%s' % exit_code,
        '源目录：%s' % task.get('path', ''),
        '目标：%s' % target,
        '同步模式：%s' % mode,
        '连接方式：%s' % task.get('conn_type', ''),
        '删除保护阈值：%s%%' % threshold,
        '日志目录：%s' % paths['log_dir'],
    ]
    latest_log, latest_log_content = getLatestRunLog(task)
    error_summary = getRsyncErrorSummary(latest_log_content)
    if latest_log:
        lines.append('最近日志：%s' % latest_log)
    if error_summary:
        lines.append('错误摘要：\n%s' % error_summary)
    lines.append('提示：如确认需要跳过删除比例检查，可手动执行 bash cmd -f；rsync阶段失败仍需检查日志和连接状态。')
    return '\n'.join(lines)


def runNotifyFail():
    # 用法: tool_run.py notify_fail <task_name> <exit_code> <phase>
    if len(sys.argv) < 5:
        print('usage: tool_run.py notify_fail <task_name> <exit_code> <phase>')
        return 1

    name = sys.argv[2]
    exit_code = sys.argv[3]
    phase = sys.argv[4]

    task = loadTask(name)
    reason = buildReason(task, exit_code, phase)

    notify_msg = mw.generateCommonNotifyMessage(reason)
    title = '🔴rsync同步失败：{} | {}'.format(name, mw.getConfig('title'))
    stype = 'rsyncd同步失败:' + name
    mw.notifyMessage(title=title, msg=notify_msg, stype=stype, trigger_time=3600)
    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1:
        action = sys.argv[1]
        try:
            if action == 'preflight':
                runPreflight()
            elif action == 'notify_fail':
                sys.exit(runNotifyFail())
            else:
                print('unknown action: %s' % action)
                sys.exit(2)
        except SystemExit:
            raise
        except Exception:
            print(traceback.format_exc())
            sys.exit(1)
    else:
        print('usage: tool_run.py <preflight|notify_fail> <task_name> [args]')
        sys.exit(2)
