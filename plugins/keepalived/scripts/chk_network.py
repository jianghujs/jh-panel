#!/usr/bin/env python3
# coding: utf-8
"""网络健康检查脚本。"""

from __future__ import annotations

import os
import shlex
import sys
import time

server_path = "/www/server"
panel_dir = f"{server_path}/jh-panel"
log_file = f"{server_path}/keepalived/logs/keepalived_network_check.log"
keepalived_conf = f"{server_path}/keepalived/etc/keepalived/keepalived.conf"

network_targets: list[str] = []
ping_count = 1
ping_timeout = 1
min_success = 1
retry_times = 3
retry_interval = 1
quiet_enabled = False
quiet_start_hour = 1
quiet_end_hour = 3

if sys.platform != "darwin":
    os.chdir(panel_dir)

sys.path.append("/www/server/jh-panel/class/core")
import mw


def log(message: str) -> None:
    mw.writeFileLog(f"{mw.getDate()} [chk_network] {message}", log_file, 2 * 1024 * 1024, 3)


def in_quiet_hours(start_hour: int, end_hour: int, now: time.struct_time | None = None) -> bool:
    if start_hour == end_hour:
        return False
    if now is None:
        now = time.localtime()
    hour = now.tm_hour
    if start_hour < end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour


def read_unicast_peers(path: str) -> list[str]:
    peers: list[str] = []
    try:
        content = mw.readFile(path)
    except Exception:
        content = ""
    if not content:
        return peers

    in_block = False
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("unicast_peer"):
            in_block = "{" in line
            continue
        if in_block:
            if "}" in line:
                break
            value = line.split("#", 1)[0].strip()
            if value:
                peers.append(value)
    return peers


def get_default_gateway() -> str:
    out, err, rc = mw.execShell("ip route show default")
    if rc != 0:
        return ""
    data = (out or err or "").strip()
    for line in data.splitlines():
        parts = line.split()
        if "via" in parts:
            idx = parts.index("via")
            if idx + 1 < len(parts):
                return parts[idx + 1]
    return ""


def build_targets() -> list[str]:
    targets = [target.strip() for target in network_targets if target and target.strip()]

    if not targets:
        gateway = get_default_gateway()
        if gateway:
            targets.append(gateway)
        targets.extend(read_unicast_peers(keepalived_conf))

    deduped: list[str] = []
    seen: set[str] = set()
    for target in targets:
        if target in seen:
            continue
        seen.add(target)
        deduped.append(target)
    return deduped


def ping_target(target: str, count: int, timeout: int) -> bool:
    cmd = f"ping -c {count} -W {timeout} {shlex.quote(target)}"
    out, err, rc = mw.execShell(cmd)
    if rc == 0:
        return True
    output = (out or err or "").strip()
    if output:
        log(f"ping {target} 失败: {output}")
    return False


def main() -> int:
    log("开始网络健康检查")

    if quiet_enabled and in_quiet_hours(quiet_start_hour, quiet_end_hour):
        log(f"处于免切换时间段({quiet_start_hour:02d}:00-{quiet_end_hour:02d}:00)，跳过网络检查")
        return 0

    targets = build_targets()
    if not targets:
        log("WARN: 未找到检测目标，跳过网络检查")
        return 0

    retries = max(1, retry_times)
    interval = max(0, retry_interval)

    for attempt in range(1, retries + 1):
        success = 0
        for target in targets:
            if ping_target(target, ping_count, ping_timeout):
                log(f"ping {target} 成功 ✅")
                success += 1
            else:
                log(f"ping {target} 失败 ❌")

        if success >= min_success:
            log(f"网络检查通过 ✅ (成功 {success}/{len(targets)})")
            return 0

        log(f"网络检查失败 ❌ (成功 {success}/{len(targets)})")
        if attempt < retries and interval > 0:
            log(f"等待 {interval}s 后重试({attempt}/{retries})...")
            time.sleep(interval)

    log(f"网络检查失败(重试 {retries} 次仍未通过) ❌")
    return 1


if __name__ == "__main__":
    sys.exit(main())
