#!/usr/bin/env python3
# coding: utf-8
"""keepalived notify_master：提升本节点为主库并上报状态。"""

from __future__ import annotations

import json
import os
import sys

server_path = "/www/server"
panel_dir = f"{server_path}/jh-panel"
log_file = f"{server_path}/keepalived/notify_master.log"
keepalived_instance = "VI_1"
desired_priority = "100"
alert_config = f"{server_path}/keepalived/config/alert_settings.json"
panel_config = f"{panel_dir}/data/json/config.json"

if sys.platform != "darwin":
    os.chdir(panel_dir)

sys.path.append("/www/server/jh-panel/class/core")
import mw

def log(message: str) -> None:
    mw.writeFileLog(f"{mw.getDate()} [notify_master] {message}", log_file)


def update_priority(target: str) -> bool:
    cmd = (
        f"python3 {panel_dir}/plugins/keepalived/tool.py update_priority "
        f"{keepalived_instance} {target}"
    )
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

    should_notify = bool(config.get("notify_promote", False))
    content = "Keepalived 状态变更为 MASTER (主节点)。\nVIP 已绑定，服务已接管。"

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
    log("notify_master 触发")

    # 1) 清理从库配置，准备升主
    log("执行 delete_slave 清理从库配置")
    out, err, rc = mw.execShell("python3 plugins/mysql-apt/index.py delete_slave")
    output = (out or err or "").strip()
    if rc != 0:
        log(f"delete_slave 命令执行失败: {output}")
        return 1
    log(f"delete_slave 输出: {output}")
    if not parse_status(output):
        log("delete_slave 返回失败状态或响应无法解析，退出")
        return 1

    # 2) 启动 OpenResty，对外接管
    log("启动 OpenResty")
    out, err, rc = mw.execShell("python3 plugins/openresty/index.py start")
    output = (out or err or "").strip()
    if rc != 0:
        log(f"OpenResty 启动命令执行失败: {output}")
        return 1
    if output.strip() != "ok":
        log(f"OpenResty 启动失败: {output}")
        return 1
    log("OpenResty 启动完成")

    # 3) 提升 keepalived priority
    update_priority(desired_priority)

    # 4) 发送提升为主通知
    log("发送提升为主通知")
    send_notify()
    log("通知发送完毕")

    log("notify_master 执行完毕")
    return 0


if __name__ == "__main__":
    sys.exit(main())
