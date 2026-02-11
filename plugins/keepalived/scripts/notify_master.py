#!/usr/bin/env python3
# coding: utf-8
"""keepalived notify_master：提升本节点为主库并上报状态。"""

from __future__ import annotations

import json
import os
import shlex
import sys
import time

server_path = "{$SERVER_PATH}"
panel_dir = f"{server_path}/jh-panel"
log_file = f"{server_path}/keepalived/logs/notify_master.log"
keepalived_instance = "VI_1"
desired_priority = "100"
alert_config = f"{server_path}/keepalived/config/alert_settings.json"
panel_config = f"{panel_dir}/data/json/config.json"
retry_times = 3
retry_interval = 1

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
    ok, output = run_with_retry(
        f"priority 设置为 {target}",
        cmd,
        lambda rc, out: (rc == 0, f"命令执行失败: {out}".strip()),
    )
    if ok:
        log(f"priority 已设置为 {target}: {output}")
    return ok


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

    should_notify = bool(config.get("notify_enabled", False))
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


def send_error_notify(action: str, detail: str) -> None:
    content_raw = mw.readFile(alert_config)
    should_notify = True
    if content_raw:
        try:
            config = json.loads(content_raw)
            should_notify = bool(config.get("notify_enabled", True))
        except Exception:
            log("通知配置解析失败，仍尝试发送异常通知")
    else:
        log("通知配置不存在，仍尝试发送异常通知")

    if not should_notify:
        log("异常通知未开启，跳过")
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
    safe_detail = detail or "无输出"
    content = (
        "Keepalived 动作执行异常。\n"
        f"动作: {action}\n"
        f"最后一次输出: {safe_detail}\n"
        f"已重试 {retry_times} 次仍失败。"
    )
    notify_title = f"节点执行异常通知：{title} {current_time} "
    notify_msg = "{}|节点[{}:{}]\n{}".format(current_time, title, local_ip, content)
    cmd = (
        f"python3 {panel_dir}/tools.py notify_msg "
        f"{shlex.quote(notify_title)} {shlex.quote(notify_msg)} keepalived"
    )
    mw.execShell(cmd)


def run_with_retry(action: str, cmd: str, checker) -> tuple[bool, str]:
    last_output = ""
    last_reason = ""
    for attempt in range(1, retry_times + 1):
        try:
            out, err, rc = mw.execShell(cmd)
        except Exception as exc:
            last_reason = f"执行异常: {exc}"
            log(f"{action} 失败({attempt}/{retry_times}): {last_reason}")
            if attempt < retry_times:
                time.sleep(retry_interval)
            continue

        output = (out or err or "").strip()
        last_output = output
        ok, reason = checker(rc, output)
        if ok:
            return True, output
        last_reason = reason or output or "无输出"
        log(f"{action} 失败({attempt}/{retry_times}): {last_reason}")
        if attempt < retry_times:
            time.sleep(retry_interval)

    send_error_notify(action, last_reason)
    return False, last_output


def main() -> int:
    log("notify_master 触发")

    try:
        # 1) 清理从库配置，准备升主
        log("执行 delete_slave 清理从库配置")
        ok, output = run_with_retry(
            "delete_slave 清理从库配置",
            "python3 plugins/mysql-apt/index.py delete_slave",
            lambda rc, out: (
                rc == 0 and parse_status(out),
                f"返回失败状态或响应无法解析: {out}" if rc == 0 else f"命令执行失败: {out}",
            ),
        )
        if not ok:
            return 1
        log(f"delete_slave 输出: {output}")

        # 2) 启动 OpenResty，对外接管
        log("启动 OpenResty")
        ok, output = run_with_retry(
            "OpenResty 启动",
            "python3 plugins/openresty/index.py start",
            lambda rc, out: (
                rc == 0 and out.strip() == "ok",
                f"返回值异常: {out}" if rc == 0 else f"命令执行失败: {out}",
            ),
        )
        if not ok:
            return 1
        log("OpenResty 启动完成")

        # 3) 提升 keepalived priority
        if not update_priority(desired_priority):
            return 1

        # 4) 发送提升为主通知
        log("发送提升为主通知")
        send_notify()
        log("通知发送完毕")

        log("notify_master 执行完毕")
        return 0
    except Exception as exc:
        log(f"执行异常: {exc}")
        send_error_notify("notify_master 运行异常", str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
