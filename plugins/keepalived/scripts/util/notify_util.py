# coding: utf-8
import sys
import os
import json
import subprocess
import datetime

def get_local_ip():
    try:
        # Call tools.py to get IP to ensure consistency
        result = subprocess.check_output(['python3', '/www/server/jh-panel/tools.py', 'getLocalIp'])
        return result.decode('utf-8').strip()
    except:
        return "Unknown"

def get_panel_title():
    try:
        config_file = '/www/server/jh-panel/data/json/config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
                return data.get('title', '江湖面板')
    except:
        pass
    return '江湖面板'

def send_notify_via_tools(title, msg, stype):
    try:
        subprocess.run(['python3', '/www/server/jh-panel/tools.py', 'notify_msg', title, msg, stype])
    except Exception as e:
        print("Failed to send notify: " + str(e))

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 notify_util.py [master|backup]")
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
    local_ip = get_local_ip()
    panel_title = get_panel_title()
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if notify_type == 'master':
        if config.get('notify_promote', False):
            should_notify = True
            title = "节点提升为主通知：{} {}".format(panel_title, current_time)
            content = "Keepalived 状态变更为 MASTER (主节点)。\nVIP 已绑定，服务已接管。"
    elif notify_type == 'backup':
        if config.get('notify_demote', False):
            should_notify = True
            title = "节点降级为备通知：{} {}".format(panel_title, current_time)
            content = "Keepalived 状态变更为 BACKUP (备节点)。\nVIP 已释放。"

    if should_notify:
        # 格式参考 mw.generateCommonNotifyMessage
        msg = "{}|节点[{}:{}]\n{}".format(current_time, panel_title, local_ip, content)
        send_notify_via_tools(title, msg, 'keepalived')

if __name__ == "__main__":
    main()
