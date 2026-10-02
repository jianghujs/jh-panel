# coding:utf-8

import sys
import os
import re
import json
import time
import subprocess
import traceback
import tempfile

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


def collectDeletedPaths(output):
    # --itemize-changes 的标记占 11 列，随后一个空格才是文件名。
    return [line[12:] for line in output.splitlines() if line.startswith('*deleting   ')]


def writeAbortLog(log_dir, message):
    ts = time.strftime('%Y%m%d_%H%M%S')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    fd, log_file = tempfile.mkstemp(prefix='preflight_' + ts + '_', suffix='.log', dir=log_dir)
    os.close(fd)
    mw.writeFile(log_file, message.rstrip() + '\n')
    print(message)
    print('preflight abort log: %s' % log_file)
    return log_file


def buildDryRunCmd(task, paths, rsync_bin):
    cmd = [rsync_bin, '-avzPr', '--dry-run', '--stats', '--itemize-changes', '--8-bit-output']
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




def getRsyncErrorSummary(content, max_lines=20):
    if not content:
        return ''
    keywords = [
        'rsync:',
        '@ERROR:',
        'ssh:',
        '失败',
        '超时',
        'Error:',
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


def preflightResultPath(task):
    # 旧 cmd 没有导出结果路径。两个 Python 步骤由同一个 Bash 父进程启动，
    # 用父进程身份关联结果，避免并发任务互相覆盖或读取历史阈值记录。
    result_path = os.environ.get('RSYNCD_PREFLIGHT_RESULT')
    if result_path:
        return result_path
    if task:
        parent_pid = os.getppid()
        with open('/proc/%s/stat' % parent_pid) as stream:
            start_time = stream.read().rsplit(')', 1)[1].split()[19]
        return os.path.join(taskPaths(task)['log_dir'], '.preflight_%s_%s.json' % (parent_pid, start_time))
    return None


def savePreflightResult(result, task=None):
    result_path = preflightResultPath(task)
    if result_path:
        os.makedirs(os.path.dirname(result_path), exist_ok=True)
        # 显式写文件，不能静默忽略 mw.writeFile 返回的写入失败。
        with open(result_path, 'w', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False)


def readPreflightResult(task=None, phase=None):
    result_path = preflightResultPath(task)
    if result_path and os.path.isfile(result_path):
        try:
            result = json.loads(mw.readFile(result_path))
            if isinstance(result, dict) and result.get('kind') in ('ok', 'threshold', 'error'):
                return result
        except (ValueError, TypeError, OSError):
            pass
    # 只读取本次运行日志；不能用历史阈值拦截覆盖本次连接错误。
    log_file = os.environ.get('RSYNCD_RUN_LOG', '')
    if task and phase == 'preflight' and log_file and os.path.isfile(log_file):
        content = mw.readFile(log_file) or ''
        pattern = (r'^rsync preflight task=' + re.escape(task['name']) +
                   r' deleted=(\d+) total=(\d+) ratio=([\d.]+)% threshold=(\d+)%\n'
                   r'abort: delete ratio exceeds threshold, real rsync skipped(?:\n|$)')
        matches = list(re.finditer(pattern, content, re.M))
        if matches:
            match = matches[-1]
            deleted, total, ratio, threshold = match.groups()
            if float(ratio) > int(threshold):
                return dict(kind='threshold', deleted_count=int(deleted), total=int(total),
                            ratio=float(ratio), threshold=int(threshold), deleted=None)
    return {}


def formatDeleteDetails(task, result):
    deleted = result.get('deleted')
    lines = ['待删除清单（目标端相对路径，目录以 / 结尾）：']
    if deleted is None and task.get('delete') == 'true':
        lines.append('本次删除清单未能读取，请查看预检记录。')
    elif deleted:
        lines.extend('- ' + item for item in deleted)
        if result.get('kind') == 'error':
            lines.append('预检异常，以上仅为已获取的清单，可能不完整。')
    elif task.get('delete') != 'true':
        lines.append('未启用删除。')
    elif result.get('kind') in ('ok', 'threshold'):
        lines.append('无。')
    else:
        lines.append('未能取得完整删除清单。')
    return '\n'.join(lines)


def runPreflight():
    if len(sys.argv) < 3:
        print('usage: tool_run.py preflight <task_name>')
        sys.exit(1)
    task = loadTask(sys.argv[2])
    paths = taskPaths(task)
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    cmd = buildDryRunCmd(task, paths, whichRsync())
    result = {'kind': 'error', 'deleted': []}
    output = ''
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        stdout = proc.stdout.decode('utf-8', 'replace') if proc.stdout else ''
        stderr = proc.stderr.decode('utf-8', 'replace') if proc.stderr else ''
        output = stdout + ('\n' + stderr if stderr else '')
        result['deleted'] = collectDeletedPaths(stdout)
        result['exit_code'] = proc.returncode
        if proc.returncode != 0:
            result['error'] = stderr.strip() or getRsyncErrorSummary(stdout) or stdout.strip() or 'rsync 未输出错误详情。'
        total_files = statInt(stdout, 'Number of files')
        if total_files is None:
            if proc.returncode == 0:
                result.update(exit_code=1, error='无法解析预检统计：缺少 Number of files（rsync 退出码为 0）。')
        else:
            deleted_files = statInt(stdout, 'Number of deleted files') or len(result['deleted'])
            threshold = normalizeMaxDeletePercent(task.get('max_delete_percent', 30))
            ratio = 0 if total_files == 0 else (deleted_files * 100.0 / total_files)
            if ratio > threshold or proc.returncode == 0:
                result.update(kind='threshold' if ratio > threshold else 'ok',
                              total=total_files, deleted_count=deleted_files,
                              ratio=ratio, threshold=threshold)
    except OSError as exc:
        result.update(exit_code=1, error='%s: %s' % (type(exc).__name__, exc), errno=exc.errno)

    savePreflightResult(result, task)
    if result['kind'] in ('ok', 'threshold'):
        summary = 'rsync preflight task=%s deleted=%s total=%s ratio=%.2f%% threshold=%s%%' % (
            task['name'], result['deleted_count'], result['total'], result['ratio'], result['threshold'])
        if result['kind'] == 'ok':
            print(summary)
            return
        log_message = summary + '\nabort: delete ratio exceeds threshold, real rsync skipped'
    else:
        log_message = 'rsync preflight failed for task %s, exit_code=%s\n%s' % (
            task['name'], result['exit_code'], result['error'])
    result['log_file'] = writeAbortLog(paths['log_dir'], log_message)
    savePreflightResult(result, task)
    sys.exit(result['exit_code'] or 1)


def buildReason(task, exit_code, phase, result=None):
    if result is None:
        result = readPreflightResult(task, phase)
    threshold_exceeded = phase == 'preflight' and result.get('kind') == 'threshold'
    if task.get('conn_type') == 'ssh':
        target = '%s:%s' % (task.get('ip', ''), task.get('target_path', ''))
    else:
        target = '%s::%s（rsync 模块）' % (task.get('ip', ''), task.get('name', ''))
    phase_name = {'preflight': '同步前检查', 'mount': '目录检查'}.get(phase, 'rsync同步')
    log_file = os.environ.get('RSYNCD_RUN_LOG', '')
    log_content = (mw.readFile(log_file) or '') if log_file and os.path.isfile(log_file) else ''
    error_log = os.environ.get('RSYNCD_ERROR_LOG', '')
    if phase in ('mount', 'rsync') and error_log and os.path.isfile(error_log):
        log_content = mw.readFile(error_log) or ''
    lines = ['rsync同步已中止：待删除比例超过阈值' if threshold_exceeded else 'rsync同步异常']
    if threshold_exceeded:
        lines.extend([
            '删除比例：%.2f%%，超过阈值 %s%%（待删除 %s 项 / 源端 %s 项，含目录）。' % (
                result['ratio'], result['threshold'], result['deleted_count'], result['total']),
            '执行结果：已停止同步，本次未执行文件删除。',
        ])
    else:
        actual_code = result.get('exit_code', exit_code) if phase == 'preflight' else exit_code
        error = result.get('error', '') if phase == 'preflight' else ''
        error = error or getRsyncErrorSummary(log_content) or '\n'.join(log_content.splitlines()[-30:]) or '未获取到错误输出，请查看本次运行日志。'
        lines.extend(['失败阶段：%s' % phase_name, '错误码：%s' % actual_code, '报错信息：\n%s' % error])
        if phase == 'preflight' and result.get('errno') is not None:
            lines.append('系统错误码（errno）：%s' % result['errno'])
        if phase in ('preflight', 'mount'):
            lines.append('执行结果：已停止同步，本次未执行文件删除。')
        else:
            lines.append('执行结果：同步中途失败，部分文件可能已同步或删除；以下为预检计划清单。')
    lines.extend([
        '任务名称：%s' % task.get('name', ''),
        '源目录：%s' % task.get('path', ''),
        '目标：%s' % target,
        '同步模式：%s' % ('完全同步' if task.get('delete') == 'true' else '增量同步'),
    ])
    if threshold_exceeded or phase == 'rsync':
        lines.extend(['', formatDeleteDetails(task, result)])
    if log_file:
        lines.append('本次运行日志：%s' % log_file)
    if result.get('log_file'):
        lines.append('预检日志：%s' % result['log_file'])
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
    result = readPreflightResult(task, phase)
    reason = buildReason(task, exit_code, phase, result=result)
    if not os.environ.get('RSYNCD_PREFLIGHT_RESULT'):
        result_path = preflightResultPath(task)
        if os.path.isfile(result_path):
            os.remove(result_path)

    notify_msg = mw.generateCommonNotifyMessage(reason)
    label = 'rsync同步中止：删除比例超过阈值' if phase == 'preflight' and result.get('kind') == 'threshold' else 'rsync同步异常'
    title = '{}：{} | {} | {}'.format(
        label, name, mw.getConfig('title'), time.strftime('%Y-%m-%d %H:%M:%S'))
    category = 'threshold' if phase == 'preflight' and result.get('kind') == 'threshold' else phase
    stype = 'rsyncd同步失败:%s:%s' % (name, category)
    # 发送前检查旧记录，不能把本次发送时新写入的锁误判成限频。
    lock_file = os.path.join(mw.getPanelTmp(), 'notify_lock.json')
    try:
        locks = json.loads(mw.readFile(lock_file) or '{}')
        retry_at = float(locks.get(stype, {}).get('do_time', 0)) + 3600
    except (ValueError, TypeError, AttributeError, OSError):
        retry_at = 0
    if retry_at > time.time():
        print('rsync notify: 已被一小时通知限频拦截，本次未尝试发送；可重试时间：%s；通知类型：%s。' % (
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(retry_at)), stype))
        return 0
    config = mw.getNotifyData()
    email_enabled = config.get('email', {}).get('enable', False)
    if not email_enabled:
        print('rsync notify: 面板未启用邮件通知，请在通知设置中启用邮件并配置收件人。')
    sent = mw.notifyMessage(title=title, msg=notify_msg, stype=stype, trigger_time=3600)
    if not sent:
        print('rsync notify: 通知未发送或未成功；本次调用前未被限频，请检查上方异常和面板错误日志。'
              '面板可能已记录本次尝试时间，再次尝试可能被限频。')
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
