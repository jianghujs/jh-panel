#!/usr/bin/env python3
# coding: utf-8
"""keepalived notify_backup：降级本节点，释放 VIP 并降低优先级。"""

from __future__ import annotations

import json
import os
import shlex
import sys
import time

server_path = "{$SERVER_PATH}"
panel_dir = f"{server_path}/jh-panel"
log_file = f"{server_path}/keepalived/logs/notify_backup.log"
keepalived_instance = "VI_1"
desired_priority = "90"
alert_config = f"{server_path}/keepalived/config/alert_settings.json"
panel_config = f"{panel_dir}/data/json/config.json"
retry_times = 3
retry_interval = 1

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
    log("notify_backup 触发")
    try:
        # 1) 停止 OpenResty，先下掉业务入口
        log("停止 OpenResty")
        ok, _ = run_with_retry(
            "OpenResty 停止",
            "python3 plugins/openresty/index.py stop",
            lambda rc, out: (
                rc == 0 and out.strip() == "ok",
                f"返回值异常: {out}" if rc == 0 else f"命令执行失败: {out}",
            ),
        )
        if not ok:
            return 1
        log("OpenResty 停止完成")

        # 2) 降低 keepalived priority
        if not update_priority(desired_priority):
            log("priority_update 更新失败")
            return 1
        log("priority_update 更新成功")

        # 3) 数据库切只读并重启，保证从库一致
        log("执行 set_db_read_only 设置数据库只读")
        ok, output = run_with_retry(
            "set_db_read_only 设置数据库只读",
            "python3 plugins/mysql-apt/index.py set_db_read_only",
            lambda rc, out: (
                rc == 0 and parse_status(out),
                f"返回失败状态或响应无法解析: {out}" if rc == 0 else f"命令执行失败: {out}",
            ),
        )
        if not ok:
            return 1
        log(f"set_db_read_only 输出: {output}")

        log("重启 MySQL，确保状态正常")
        ok, _ = run_with_retry(
            "MySQL 重启",
            "python3 plugins/mysql-apt/index.py restart",
            lambda rc, out: (
                rc == 0 and out.strip() == "ok",
                f"返回值异常: {out}" if rc == 0 else f"命令执行失败: {out}",
            ),
        )
        if not ok:
            return 1
        log("MySQL 重启完成")

        time.sleep(1)

        # 4) 初始化从库状态
        log("执行 init_slave_status 初始化从库状态")
        ok, output = run_with_retry(
            "init_slave_status 初始化从库状态",
            "python3 plugins/mysql-apt/index.py init_slave_status",
            lambda rc, out: (
                rc == 0 and parse_status(out),
                f"返回失败状态或响应无法解析: {out}" if rc == 0 else f"命令执行失败: {out}",
            ),
        )
        if not ok:
            return 1
        log(f"init_slave_status 输出: {output}")

        # 5) 发送降级通知
        log("发送降级通知")
        send_notify()
        log("通知发送完毕")

        log("notify_backup 执行完毕")
        return 0
    except Exception as exc:
        log(f"执行异常: {exc}")
        send_error_notify("notify_backup 运行异常", str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
