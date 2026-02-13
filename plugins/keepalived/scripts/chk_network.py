#!/usr/bin/env python3
# coding: utf-8
"""网络健康检查脚本。"""

from __future__ import annotations

import os
import re
import shlex
import sys

server_path = "/www/server"
panel_dir = f"{server_path}/jh-panel"
log_file = f"{server_path}/keepalived/logs/keepalived_network_check.log"
keepalived_conf = f"{server_path}/keepalived/etc/keepalived/keepalived.conf"

ping_count = 1
ping_timeout = 1
min_success = 1

if sys.platform != "darwin":
    os.chdir(panel_dir)

sys.path.append("/www/server/jh-panel/class/core")
import mw


def log(message: str) -> None:
    mw.writeFileLog(f"{mw.getDate()} [chk_network] {message}", log_file)


def parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
    env_targets = os.environ.get("NETWORK_TARGETS", "").strip()
    targets: list[str] = []

    if env_targets:
        for item in re.split(r"[\s,]+", env_targets):
            if item:
                targets.append(item)
    else:
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

    count = parse_int(os.environ.get("NETWORK_PING_COUNT", ""), ping_count)
    timeout = parse_int(os.environ.get("NETWORK_PING_TIMEOUT", ""), ping_timeout)
    required = parse_int(os.environ.get("NETWORK_MIN_SUCCESS", ""), min_success)

    targets = build_targets()
    if not targets:
        log("WARN: 未找到检测目标，跳过网络检查")
        return 0

    success = 0
    for target in targets:
        if ping_target(target, count, timeout):
            log(f"ping {target} 成功 ✅")
            success += 1
        else:
            log(f"ping {target} 失败 ❌")

    if success >= required:
        log(f"网络检查通过 ✅ (成功 {success}/{len(targets)})")
        return 0

    log(f"网络检查失败 ❌ (成功 {success}/{len(targets)})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
