# coding: utf-8

import os
import re
import sys
import signal

PANEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT_NOTIFY_KEYWORDS = ("notify_backup.py", "notify_master.py")
if sys.platform != 'darwin':
    os.chdir(PANEL_DIR)

sys.path.append(PANEL_DIR + '/class/core')
import mw


def _get_conf_path(conf=None):
    if conf:
        return conf
    return mw.getServerDir() + '/keepalived/etc/keepalived/keepalived.conf'


def update_priority(instance, priority, conf=None):
    if not priority:
        return False

    if not str(priority).isdigit():
        return False

    conf_path = _get_conf_path(conf)
    if not os.path.exists(conf_path):
        return False

    content = mw.readFile(conf_path)
    if not content:
        return False

    pattern = re.compile(
        r'(vrrp_instance\s+' + re.escape(instance) + r'\s*\{.*?\bpriority\s+)(\d+)',
        re.S
    )
    match = pattern.search(content)
    if not match:
        return False

    current = match.group(2)
    desired = str(priority)
    if current == desired:
        return True

    updated = pattern.sub(lambda m: m.group(1) + desired, content, count=1)
    return bool(mw.writeFile(conf_path, updated))


def cleanup_notify_processes(keywords=None, exclude_pid=None):
    if keywords is None:
        keywords = DEFAULT_NOTIFY_KEYWORDS
    if not keywords:
        return 0
    if exclude_pid is None:
        exclude_pid = os.getpid()

    try:
        out, _, _ = mw.execShell("ps -eo pid=,args=")
    except Exception:
        return 0

    cleaned = 0
    for line in (out or "").splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) < 2:
            continue
        pid_str, cmdline = parts
        if not any(keyword in cmdline for keyword in keywords):
            continue
        try:
            pid = int(pid_str)
        except Exception:
            continue
        if pid == exclude_pid:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
            cleaned += 1
        except Exception:
            pass
    return cleaned


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 tool.py update_priority <instance> <priority> [conf]')
        print('       python3 tool.py cleanup_notify_processes [exclude_pid]')
        sys.exit(1)

    action = sys.argv[1]
    if action == 'update_priority':
        if len(sys.argv) < 4:
            print('Usage: python3 tool.py update_priority <instance> <priority> [conf]')
            sys.exit(1)
        inst = sys.argv[2]
        prio = sys.argv[3]
        conf_path = sys.argv[4] if len(sys.argv) > 4 else None
        result = update_priority(inst, prio, conf_path)
        print(mw.returnJson(result, 'ok' if result else 'fail'))
    elif action == 'cleanup_notify_processes':
        try:
            exclude_pid = None
            if len(sys.argv) > 2 and sys.argv[2].isdigit():
                exclude_pid = int(sys.argv[2])
            cleaned = cleanup_notify_processes(exclude_pid=exclude_pid)
            print(mw.returnJson(True, 'ok', cleaned))
        except Exception as exc:
            print(mw.returnJson(False, str(exc) or 'fail'))
    else:
        print('error')
