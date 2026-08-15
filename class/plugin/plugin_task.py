# coding: utf-8

import json
import os
import re
import subprocess
import time

import mw
from value_tool import boundedInt, safeBool, safeJsonText, shortText


PLUGIN_TASK_MIN_INTERVAL = 5
PLUGIN_TASK_DEFAULT_INTERVAL = 60
PLUGIN_TASK_DEFAULT_TIMEOUT = 30
PLUGIN_TASK_MAX_TIMEOUT = 300
PLUGIN_TASK_OUTPUT_LIMIT = 2000
PLUGIN_TASK_FUNC_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,63}$')


def pluginTaskStatePath():
    return os.path.join(mw.getRunDir(), 'data/plugin_scheduled_tasks_state.json')


def pluginTaskLogPath():
    return os.path.join(mw.getRunDir(), 'logs/plugin_scheduled_tasks.log')


def pluginTaskLog(message):
    try:
        line = '[{0}] {1}'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), message)
        mw.writeFileLog(line, pluginTaskLogPath(), limit_size=1 * 1024 * 1024, save_limit=5)
    except Exception:
        print(message)


def pluginTaskLabel(task):
    return 'plugin={0} func={1} title={2}'.format(task.get('plugin'), task.get('func'), task.get('title') or task.get('func'))


def pluginInstallCheckPath(info):
    checks = str(info.get('checks') or '').strip()
    if not checks:
        return ''
    if checks.startswith('/'):
        return checks
    return os.path.join(mw.getRootDir(), checks)


def isPluginInstalled(info):
    check_path = pluginInstallCheckPath(info)
    if not check_path:
        return False
    if 'VERSION' in check_path:
        versions = info.get('versions') or []
        if not isinstance(versions, list):
            versions = [versions]
        for version in versions:
            if os.path.exists(check_path.replace('VERSION', str(version))):
                return True
        return False
    return os.path.exists(check_path)


def validatePluginTask(plugin_name, task_info):
    if not isinstance(task_info, dict):
        return None, '任务配置不是对象'
    if safeBool(task_info.get('enabled'), True) is False:
        return None, ''
    func = str(task_info.get('func') or '').strip()
    if not func or not PLUGIN_TASK_FUNC_RE.match(func) or func.startswith('_'):
        return None, 'func格式非法: ' + func
    args = task_info.get('args')
    if args is None:
        args = {}
    interval = boundedInt(task_info.get('interval'), PLUGIN_TASK_DEFAULT_INTERVAL, PLUGIN_TASK_MIN_INTERVAL, 86400)
    timeout = boundedInt(task_info.get('timeout'), PLUGIN_TASK_DEFAULT_TIMEOUT, 1, PLUGIN_TASK_MAX_TIMEOUT)
    title = str(task_info.get('title') or func).strip()
    return {
        'plugin': plugin_name,
        'func': func,
        'args_json': safeJsonText(args, {}),
        'interval': interval,
        'timeout': timeout,
        'title': title,
        'task_key': plugin_name + ':' + func
    }, ''


def scanPluginScheduledTasks():
    result = []
    plugin_dir = mw.getPluginDir()
    if not os.path.exists(plugin_dir):
        return result
    for plugin_name in sorted(os.listdir(plugin_dir)):
        if plugin_name.startswith('.'):
            continue
        plugin_path = os.path.join(plugin_dir, plugin_name)
        info_path = os.path.join(plugin_path, 'info.json')
        if not os.path.isdir(plugin_path) or not os.path.exists(info_path):
            continue
        try:
            with open(info_path, 'r', encoding='utf-8') as fp:
                info = json.load(fp)
        except Exception as e:
            pluginTaskLog('插件定时任务元数据读取失败 plugin={0} error={1}'.format(plugin_name, str(e)))
            continue
        if not isinstance(info, dict) or not isPluginInstalled(info):
            continue
        tasks = info.get('tasks') or []
        if not isinstance(tasks, list):
            pluginTaskLog('插件定时任务配置忽略 plugin={0} reason=tasks不是数组'.format(plugin_name))
            continue
        for task_info in tasks:
            task, error = validatePluginTask(plugin_name, task_info)
            if error:
                pluginTaskLog('插件定时任务配置忽略 plugin={0} reason={1}'.format(plugin_name, error))
            if task:
                result.append(task)
    return result


def readPluginTaskState():
    state_path = pluginTaskStatePath()
    if not os.path.exists(state_path):
        return {}
    try:
        state = json.loads(mw.readFile(state_path) or '{}')
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def savePluginTaskState(state):
    mw.writeFile(pluginTaskStatePath(), json.dumps(state, ensure_ascii=False, indent=2))


def updatePluginTaskState(state, task, status, message='', output='', duration=0):
    now = int(time.time())
    state[task['task_key']] = {
        'plugin': task['plugin'],
        'func': task['func'],
        'title': task.get('title') or task['func'],
        'interval': task['interval'],
        'timeout': task['timeout'],
        'last_run_at': now,
        'next_run_at': now + task['interval'],
        'last_status': status,
        'last_message': shortText(message, 500),
        'last_output': shortText(output, PLUGIN_TASK_OUTPUT_LIMIT),
        'duration': duration
    }
    savePluginTaskState(state)


def executePluginScheduledTask(task, state):
    start = time.time()
    index_py = os.path.join(mw.getPluginDir(), task['plugin'], 'index.py')
    if not os.path.exists(index_py):
        updatePluginTaskState(state, task, 'failed', '插件入口不存在: ' + index_py)
        pluginTaskLog('插件定时任务失败 {0} status=failed reason=插件入口不存在 path={1}'.format(pluginTaskLabel(task), index_py))
        return
    cmd = ['python3', index_py, task['func'], task['args_json']]
    pluginTaskLog('插件定时任务开始 {0} interval={1}s timeout={2}s'.format(pluginTaskLabel(task), task['interval'], task['timeout']))
    try:
        proc = subprocess.run(cmd, cwd=mw.getRunDir(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=task['timeout'])
        output = shortText((proc.stdout or '') + (('\n' + proc.stderr) if proc.stderr else ''), PLUGIN_TASK_OUTPUT_LIMIT)
        duration = round(time.time() - start, 3)
        if proc.returncode == 0:
            updatePluginTaskState(state, task, 'success', '执行成功', output, duration)
            pluginTaskLog('插件定时任务完成 {0} status=success duration={1}s next_run_at={2}'.format(
                pluginTaskLabel(task), duration, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(time.time()) + task['interval']))
            ))
            return
        updatePluginTaskState(state, task, 'failed', 'exit_code={0}'.format(proc.returncode), output, duration)
        pluginTaskLog('插件定时任务失败 {0} status=failed exit_code={1} duration={2}s output={3}'.format(pluginTaskLabel(task), proc.returncode, duration, output[-500:]))
    except subprocess.TimeoutExpired as e:
        output = shortText((e.stdout or '') + (('\n' + e.stderr) if e.stderr else ''), PLUGIN_TASK_OUTPUT_LIMIT)
        duration = round(time.time() - start, 3)
        updatePluginTaskState(state, task, 'timeout', 'timeout={0}'.format(task['timeout']), output, duration)
        pluginTaskLog('插件定时任务超时 {0} status=timeout timeout={1}s duration={2}s output={3}'.format(pluginTaskLabel(task), task['timeout'], duration, output[-500:]))
    except Exception as e:
        duration = round(time.time() - start, 3)
        updatePluginTaskState(state, task, 'failed', str(e), '', duration)
        pluginTaskLog('插件定时任务异常 {0} status=failed duration={1}s error={2}'.format(pluginTaskLabel(task), duration, str(e)))


def runPluginScheduledTasksOnce():
    state = readPluginTaskState()
    now = int(time.time())
    for task in scanPluginScheduledTasks():
        task_state = state.get(task['task_key']) or {}
        next_run_at = boundedInt(task_state.get('next_run_at'), 0, 0, None)
        if next_run_at > now:
            continue
        executePluginScheduledTask(task, state)


def pluginScheduledTaskService():
    while True:
        try:
            runPluginScheduledTasksOnce()
            time.sleep(5)
        except Exception as e:
            pluginTaskLog('插件定时任务调度循环异常: ' + str(e))
            time.sleep(30)
