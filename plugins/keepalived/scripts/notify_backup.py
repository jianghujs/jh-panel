#!/usr/bin/env python3
# coding: utf-8
"""keepalived notify_backup：降级本节点，释放 VIP 并降低优先级。"""

from __future__ import annotations

import json
import os
import shlex
import sys
import time
import fcntl

server_path = "{$SERVER_PATH}"
panel_dir = f"{server_path}/jh-panel"
log_file = f"{server_path}/keepalived/logs/notify_backup.log"
lock_file = f"{server_path}/keepalived/notify.lock"
keepalived_instance = "VI_1"
desired_priority = "90"
alert_config = f"{server_path}/keepalived/config/alert_settings.json"
panel_config = f"{panel_dir}/data/json/config.json"
retry_times = 3
retry_interval = 1

if sys.platform != "darwin":
    os.chdir(panel_dir)

sys.path.append("/www/server/jh-panel/class/core")
sys.path.append("/www/server/jh-panel/class/plugin")
import mw
from retry_tool import retry

lock_fd = None

def log(message: str) -> None:
    mw.writeFileLog(f"{mw.getDate()} [notify_backup] {message}", log_file)


def log_run_start() -> None:
    log("--------------------------------------------------")
    log("notify_backup 开始执行")
    log("--------------------------------------------------")


def log_run_end() -> None:
    log("--------------------------------------------------")
    log("notify_backup 执行结束")
    log("--------------------------------------------------")


def acquire_lock() -> bool:
    global lock_fd
    try:
        os.makedirs(os.path.dirname(lock_file), exist_ok=True)
        lock_fd = open(lock_file, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        log("检测到另一个 notify 正在执行，跳过本次运行")
        return False
    except Exception as exc:
        log(f"获取执行锁失败: {exc}，为避免并发，本次退出")
        return False


def release_lock() -> None:
    global lock_fd
    if lock_fd is None:
        return
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        lock_fd.close()
    except Exception:
        pass
    lock_fd = None


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


def is_slave_running() -> bool | None:
    cmd = "python3 plugins/mysql-apt/index.py get_master_status"
    try:
        out, err, rc = mw.execShell(cmd)
    except Exception as exc:
        log(f"获取主从状态异常: {exc}")
        return None

    if rc != 0:
        detail = (err or out or "").strip()
        log(f"获取主从状态失败: {detail or '无输出'}")
        return None

    try:
        data = json.loads((out or "").strip())
    except Exception:
        log("获取主从状态解析失败")
        return None

    slave_status = data.get("data", {}).get("slave_status")
    return bool(slave_status)


def run_switch_cmd(action: str, subcommand: str, arg: str | None = None) -> bool:
    cmd = f"python3 {panel_dir}/scripts/switch.py {subcommand}"
    if arg is not None:
        cmd = f"{cmd} {shlex.quote(arg)}"
    ok, output = run_with_retry(
        action,
        cmd,
        lambda rc, out: (rc == 0, f"命令执行失败: {out}".strip()),
    )
    if ok and output:
        log(f"{action} 输出: {output}")
    return ok


def send_notify() -> None:
    content_raw = mw.readFile(alert_config)
    if not content_raw:
        log("通知配置不存在，跳过")
        return

    try:
        config = json.loads(content_raw)
    except Exception:
        log("通知配置解析失败，跳过 ❌")
        return

    if not bool(config.get("notify_enabled", False)):
        log("通知总开关未开启，跳过")
        return

    should_notify = bool(config.get("notify_demote", True))
    content = "节点已降为从节点"

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
    notify_title = f"✅ 节点降级为从成功：{title} {current_time} "
    notify_msg = "{}|节点[{}:{}]\n{}".format(current_time, title, local_ip, content)
    mw.execShell(f"python3 {panel_dir}/tools.py notify_msg '{notify_title}' '{notify_msg}' keepalived")


def send_error_notify(action: str, detail: str) -> None:
    content_raw = mw.readFile(alert_config)
    if not content_raw:
        log("通知配置不存在，跳过异常通知")
        return

    try:
        config = json.loads(content_raw)
    except Exception:
        log("通知配置解析失败，跳过异常通知 ❌")
        return

    if not bool(config.get("notify_enabled", False)):
        log("通知总开关未开启，跳过异常通知")
        return

    should_notify = bool(config.get("notify_exception", True))

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
        "降级执行失败。\n"
        f"动作: {action}\n"
        f"最后输出: {safe_detail}\n"
        f"重试 {retry_times} 次仍失败。"
    )
    notify_title = f"❌ 节点降级为从失败：{title} {current_time} "
    notify_msg = "{}|节点[{}:{}]\n{}".format(current_time, title, local_ip, content)
    cmd = (
        f"python3 {panel_dir}/tools.py notify_msg "
        f"{shlex.quote(notify_title)} {shlex.quote(notify_msg)} keepalived"
    )
    mw.execShell(cmd)


class RetryableError(RuntimeError):
    pass


def run_with_retry(action: str, cmd: str, checker) -> tuple[bool, str]:
    last_output = ""
    last_reason = ""
    attempt = 0

    @retry(max_retry=retry_times, delay=retry_interval)
    def _run():
        nonlocal attempt, last_output, last_reason
        attempt += 1
        try:
            out, err, rc = mw.execShell(cmd)
        except Exception as exc:
            last_reason = f"执行异常: {exc}"
            log(f"{action} 失败({attempt}/{retry_times}): {last_reason} ❌")
            raise RetryableError(last_reason)

        output = (out or err or "").strip()
        last_output = output
        ok, reason = checker(rc, output)
        if ok:
            return output
        last_reason = reason or output or "无输出"
        log(f"{action} 失败({attempt}/{retry_times}): {last_reason} ❌")
        raise RetryableError(last_reason)

    try:
        output = _run()
        return True, output
    except Exception as exc:
        if not last_reason:
            last_reason = str(exc) or "执行异常"
        send_error_notify(action, last_reason)
        return False, last_output


def main() -> int:
    log_run_start()
    if not acquire_lock():
        log_run_end()
        return 0
    try:
        # 1) 停止 OpenResty，先下掉业务入口
        log("|- 停止 OpenResty")
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
        log("OpenResty 停止完成 ✅")

        # 2) 降低 keepalived priority
        if not update_priority(desired_priority):
            log("priority_update 更新失败 ❌")
            return 1
        log("priority_update 更新成功 ✅")

        # 3) 数据库切只读并重启，保证从库一致
        log("|- 执行 set_db_read_only 设置数据库只读")
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

        log("|- 重启 MySQL，确保状态正常")
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
        log("MySQL 重启完成 ✅")

        time.sleep(1)

        # 4) 初始化从库状态
        log("|- 检查从库状态")
        slave_running = is_slave_running()
        if slave_running:
            log("从库已启动，跳过初始化")
        else:
            if slave_running is None:
                log("从库状态未知，继续初始化")
            log("|- 执行 init_slave_status 初始化从库状态")
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

        # 5) 调整计划任务
        cron_actions = [
            ("开启 备份数据库 定时任务", "openCrontab", "备份数据库[backupAll]"),
            ("开启 xtrabackup 定时任务", "openCrontab", "[勿删]xtrabackup-cron"),
            ("开启 xtrabackup-inc全量备份 定时任务", "openCrontab", "[勿删]xtrabackup-inc全量备份"),
            ("开启 xtrabackup-inc增量备份 定时任务", "openCrontab", "[勿删]xtrabackup-inc增量备份"),
            ("关闭 备份网站配置 定时任务", "closeCrontab", "备份网站配置[backupAll]"),
            ("关闭 备份插件配置 定时任务", "closeCrontab", "备份插件配置[backupAll]"),
            ("关闭 lsyncd实时任务定时同步 定时任务", "closeCrontab", "[勿删]lsyncd实时任务定时同步"),
            ("关闭 续签Let's Encrypt证书 定时任务", "closeCrontab", "[勿删]续签Let's Encrypt证书"),
        ]
        for action, cmd, arg in cron_actions:
            log(f"|- {action}")
            if not run_switch_cmd(action, cmd, arg):
                return 1

        # 6) 关闭 SSL 证书到期预提醒
        log("|- 关闭 SSL证书到期预提醒")
        if not run_switch_cmd("关闭 SSL证书到期预提醒", "setNotifyValue", '{"ssl_cert":-1}'):
            return 1

        # 7) 同步 standby 公钥到 authorized_keys
        log("|- 启用 standby 同步")
        if not run_switch_cmd("启用 standby 同步", "enableStandbySync"):
            return 1

        # 8) 关闭 rsyncd 任务并清理进程
        log("|- 关闭 rsyncd 任务")
        if not run_switch_cmd("关闭 lsyncd 任务", "disableAllLsyncdTask"):
            return 1
        log("|- 清理 rsync 进程")
        ok, output = run_with_retry(
            "清理 rsync 进程",
            "ps aux | grep '/bin/[r]sync' | awk '{print $2}' | xargs -r kill -9",
            lambda rc, out: (rc == 0, f"命令执行失败: {out}".strip()),
        )
        if ok and output:
            log(f"清理 rsync 进程 输出: {output}")
        if not ok:
            return 1

        # 9) 关闭主从同步异常提醒
        log("|- 关闭 主从同步异常提醒")
        if not run_switch_cmd("关闭 主从同步异常提醒", "closeMysqlSlaveNotify"):
            return 1

        # 10) 关闭 Rsync 状态异常提醒
        log("|- 关闭 Rsync 状态异常提醒")
        if not run_switch_cmd("关闭 Rsync状态异常提醒", "closeRsyncStatusNotify"):
            return 1

        # 11) 发送降级通知
        log("|- 发送降级通知")
        send_notify()
        log("通知发送完毕 ✅")

        return 0
    except Exception as exc:
        log(f"执行异常: {exc} ❌")
        send_error_notify("notify_backup 运行异常", str(exc))
        return 1
    finally:
        release_lock()
        log_run_end()


if __name__ == "__main__":
    sys.exit(main())
