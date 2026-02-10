# coding: utf-8

import os
import re
import sys

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')

sys.path.append(os.getcwd() + '/class/core')
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


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python3 tool.py update_priority <instance> <priority> [conf]')
        sys.exit(1)

    action = sys.argv[1]
    if action == 'update_priority':
        inst = sys.argv[2]
        prio = sys.argv[3] if len(sys.argv) > 3 else ''
        conf_path = sys.argv[4] if len(sys.argv) > 4 else None
        result = update_priority(inst, prio, conf_path)
        print(mw.returnJson(result, 'ok' if result else 'fail'))
    else:
        print('error')
