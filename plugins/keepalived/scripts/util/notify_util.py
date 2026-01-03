# coding: utf-8
import sys
import os
import json
import subprocess

def get_local_ip():
    try:
        # Call tools.py to get IP to ensure consistency
        result = subprocess.check_output(['python3', '/www/server/jh-panel/tools.py', 'getLocalIp'])
        return result.decode('utf-8').strip()
    except:
        return "Unknown"

def send_notify_via_tools(title, msg, stype):
    try:
        subprocess.run(['python3', '/www/server/jh-panel/tools.py', 'notify_msg', title, msg, stype])
    except Exception as e:
        print("Failed to send notify: " + str(e))

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 keepalived_notify.py [master|backup]")
        return

    notify_type = sys.argv[1]
    config_file = '/www/server/keepalived/config/alert_settings.json'
    
    if not os.path.exists(config_file):
        print("Config file not found")
        return

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except:
        print("Config file read error")
        return

    should_notify = False
    title = "Keepalived 通知"
    msg = ""
    local_ip = get_local_ip()

    if notify_type == 'master':
        if config.get('notify_promote', False):
            should_notify = True
            title = "Keepalived 状态变更：升级为 MASTER"
            msg = "服务器 [{}] Keepalived 状态已变更为 MASTER (主节点)。\nVIP 已绑定，服务已接管。".format(local_ip)
    elif notify_type == 'backup':
        if config.get('notify_demote', False):
            should_notify = True
            title = "Keepalived 状态变更：降级为 BACKUP"
            msg = "服务器 [{}] Keepalived 状态已变更为 BACKUP (备节点)。\nVIP 已释放。".format(local_ip)

    if should_notify:
        send_notify_via_tools(title, msg, 'keepalived')

if __name__ == "__main__":
    main()

