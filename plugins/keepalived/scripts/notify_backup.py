#!/usr/bin/env python3
# coding: utf-8
"""keepalived notify_backup：降级本节点，释放 VIP 并降低优先级。"""

from __future__ import annotations

import json
import os
import sys
import time

server_path = "{$SERVER_PATH}"
panel_dir = f"{server_path}/jh-panel"
log_file = f"{server_path}/keepalived/logs/notify_backup.log"
keepalived_instance = "VI_1"
desired_priority = "90"
alert_config = f"{server_path}/keepalived/config/alert_settings.json"
panel_config = f"{panel_dir}/data/json/config.json"

if sys.platform != "darwin":
    os.chdir(panel_dir)

sys.path.append("/www/server/jh-panel/class/core")
import mw

def log(message: str) -> None:
    mw.writeFileLog(f"{mw.getDate()} [notify_backup] {message}", log_file)


def update_priority(target: str) -> bool:
    cmd = (
        f"python3 {panel_dir}/plugins/keepalived/tool.py update_priority "
        f"{keepalived_instance} {target}"
    )
    # print(cmd)
    out, err, rc = mw.execShell(cmd)
    output = (out or err or "").strip()
    if rc == 0:
        log(f"priority 已设置为 {target}: {output}")
        return True
    else:
        log(f"WARN: priority 设置失败: {output}")
    return False


def parse_status(output: str) -> bool:
    try:
        data = json.loads(output)
    except Exception:
        return False
    status = data.get("status")
    if isinstance(status, bool):
        return status
    if isinstance(status, str):
        return status.lower() == "true"
    return False


def send_notify() -> None:
    content_raw = mw.readFile(alert_config)
    if not content_raw:
        log("通知配置不存在，跳过")
        return

    try:
        config = json.loads(content_raw)
    except Exception:
        log("通知配置解析失败，跳过")
        return

    should_notify = bool(config.get("notify_demote", False))
    content = "Keepalived 状态变更为 BACKUP (备节点)。\nVIP 已释放。"

    if not should_notify:
        log("通知未开启，跳过")
        return

    title = "江湖面板"
    panel_raw = mw.readFile(panel_config)
    if panel_raw:
        try:
            title = json.loads(panel_raw).get("title", title)
        except Exception:
            pass

    local_ip = mw.getLocalIp()
    current_time = mw.getDate()
    notify_title = f"节点状态变更通知：{title} {current_time} "
    notify_msg = "{}|节点[{}:{}]\n{}".format(current_time, title, local_ip, content)
    mw.execShell(f"python3 {panel_dir}/tools.py notify_msg '{notify_title}' '{notify_msg}' keepalived")


def main() -> int:
    log("notify_backup 触发")

    # 1) 停止 OpenResty，先下掉业务入口
    log("停止 OpenResty")
    out, err, rc = mw.execShell("python3 plugins/openresty/index.py stop")
    output = (out or err or "").strip()
    if rc != 0:
        log(f"OpenResty 停止命令执行失败: {output}")
        return 1
    if output.strip() != "ok":
        log(f"OpenResty 停止失败: {output}")
        return 1
    log("OpenResty 停止完成")

    # 2) 降低 keepalived priority
    if not update_priority(desired_priority):
        log("priority_update 更新失败")
        return 1
    log("priority_update 更新成功")

    # 3) 数据库切只读并重启，保证从库一致
    log("执行 set_db_read_only 设置数据库只读")
    out, err, rc = mw.execShell("python3 plugins/mysql-apt/index.py set_db_read_only")
    output = (out or err or "").strip()
    if rc != 0:
        log(f"set_db_read_only 命令执行失败: {output}")
        return 1
    log(f"set_db_read_only 输出: {output}")
    if not parse_status(output):
        log("set_db_read_only 返回失败状态或响应无法解析，退出")
        return 1

    log("重启 MySQL，确保状态正常")
    out, err, rc = mw.execShell("python3 plugins/mysql-apt/index.py restart")
    output = (out or err or "").strip()
    if rc != 0:
        log(f"mysql restart 命令执行失败: {output}")
        return 1
    if output.strip() != "ok":
        log(f"mysql restart 失败: {output}")
        return 1
    log("MySQL 重启完成")

    time.sleep(1)

    # 4) 初始化从库状态
    log("执行 init_slave_status 初始化从库状态")
    out, err, rc = mw.execShell("python3 plugins/mysql-apt/index.py init_slave_status")
    output = (out or err or "").strip()
    if rc != 0:
        log(f"init_slave_status 命令执行失败: {output}")
        return 1
    log(f"init_slave_status 输出: {output}")
    if not parse_status(output):
        log("init_slave_status 返回失败状态或响应无法解析，退出")
        return 1

    # 5) 发送降级通知
    log("发送降级通知")
    send_notify()
    log("通知发送完毕")

    log("notify_backup 执行完毕")
    return 0


if __name__ == "__main__":
    sys.exit(main())
