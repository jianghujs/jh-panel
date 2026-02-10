#!/usr/bin/env python3
# coding: utf-8
"""MySQL 健康检查脚本。"""

from __future__ import annotations

import os
import socket
import stat
import sys

server_path = "{$SERVER_PATH}"
panel_dir = f"{server_path}/jh-panel"
log_file = f"{server_path}/keepalived/chk_mysql.log"

mysql_host = "localhost"
mysql_port = 33067
mysql_user = "root"
mysql_password = "2MwZrMbzYKHEBWRL"
mysql_bin = f"{server_path}/mysql-apt/bin/usr/bin/mysql"
mysql_socket = f"{server_path}/mysql-apt/mysql.sock"
mysql_timeout = 3

keepalived_service = "keepalived"
keepalived_instance = "VI_1"
fail_priority = "90"

# 非 macOS 环境切到面板目录，保证依赖可用
if sys.platform != "darwin":
    os.chdir(panel_dir)

sys.path.append("/www/server/jh-panel/class/core")
import mw


def log(message: str) -> None:
    mw.writeFileLog(f"{mw.getDate()} [chk_mysql] {message}", log_file)


def quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def mysql_cmd(sql: str, extra: str = "") -> tuple[int, str]:
    sql_q = quote(sql)
    base = f"{mysql_bin} --connect-timeout={mysql_timeout} -u{mysql_user} -p{mysql_password}"
    if os.path.exists(mysql_socket) and stat.S_ISSOCK(os.stat(mysql_socket).st_mode):
        base += f" --socket={mysql_socket}"
    else:
        base += f" -h{mysql_host} -P{mysql_port}"
    if extra:
        base += f" {extra}"
    cmd = f"{base} -e {sql_q}"
    out, err, rc = mw.execShell(cmd)
    output = (out or err or "").strip()
    return rc, output


def update_priority(target: str) -> None:
    cmd = (
        f"python3 {panel_dir}/plugins/keepalived/tool.py update_priority "
        f"{keepalived_instance} {target}"
    )
    out, err, rc = mw.execShell(cmd)
    output = (out or err or "").strip()
    if rc == 0:
        log(f"priority 已设置为 {target}: {output}")
    else:
        log(f"WARN: priority 设置失败: {output}")


def stop_keepalived() -> None:
    out, err, rc = mw.execShell("command -v systemctl")
    if rc == 0:
        mw.execShell(f"systemctl stop {keepalived_service}")
        return

    out, err, rc = mw.execShell("command -v service")
    if rc == 0:
        mw.execShell(f"service {keepalived_service} stop")
        return

    mw.execShell("pkill keepalived")


def handle_fatal_failure(reason: str) -> int:
    log(reason)
    update_priority(fail_priority)
    stop_keepalived()
    log("MySQL健康检查失败，已降级并停止 keepalived")
    return 1


def check_socket() -> bool:
    return os.path.exists(mysql_socket) and stat.S_ISSOCK(os.stat(mysql_socket).st_mode)


def check_port() -> bool:
    try:
        with socket.create_connection((mysql_host, mysql_port), timeout=mysql_timeout):
            return True
    except OSError:
        return False


def parse_slave_status(raw: str) -> dict:
    info = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        info[key.strip()] = value.strip()
    return info


def main() -> int:
    log("开始MySQL健康检查")

    if not os.path.isfile(mysql_bin) or not os.access(mysql_bin, os.X_OK):
        return handle_fatal_failure(f"MySQL客户端{mysql_bin}不可用")

    if not check_socket():
        return handle_fatal_failure(f"MySQL socket {mysql_socket} 不存在，数据库未启动")

    if not check_port():
        return handle_fatal_failure(f"MySQL端口{mysql_port}不可达")

    rc, output = mysql_cmd("SELECT 1")
    if rc != 0:
        return handle_fatal_failure(f"MySQL连接失败: {output}")

    rc, slave_output = mysql_cmd("SHOW SLAVE STATUS\\G")
    if rc != 0:
        log(f"读取复制状态失败: {slave_output}")
        return 1

    slave_status = slave_output if "Slave_IO_State" in slave_output else ""

    rc, writable_output = mysql_cmd("SELECT @@GLOBAL.read_only, @@GLOBAL.super_read_only", "-N -B")
    if rc != 0:
        log(f"读取read_only状态失败: {writable_output}")
        return 1

    parts = writable_output.split()
    read_only = parts[0] if len(parts) > 0 else ""
    super_read_only = parts[1] if len(parts) > 1 else ""

    if read_only != "0" or super_read_only != "0":
        if slave_status:
            log(f"检测到复制从库，只读模式(read_only={read_only}, super_read_only={super_read_only})允许存在")
        else:
            log(f"MySQL处于只读模式(read_only={read_only}, super_read_only={super_read_only})")
            return 1

    if slave_status:
        info = parse_slave_status(slave_status)
        io_running = info.get("Slave_IO_Running", "")
        sql_running = info.get("Slave_SQL_Running", "")
        last_error = info.get("Last_Error", "")

        if io_running == "Yes" and sql_running == "Yes":
            log("从库复制正常，可以作为备选主库")
        else:
            log(f"从库复制异常：IO={io_running}, SQL={sql_running}, Error: {last_error}")
            return 1
    else:
        log("当前为主库或无复制状态，可以作为主库")

    log("MySQL健康检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
