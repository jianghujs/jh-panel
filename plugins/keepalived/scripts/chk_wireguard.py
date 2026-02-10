#!/usr/bin/env python3
# coding: utf-8
"""检查 WireGuard 隧道状态。"""

from __future__ import annotations

import os
import sys
import time


server_path = "{$SERVER_PATH}"
panel_dir = f"{server_path}/jh-panel"
log_file = f"{server_path}/keepalived/logs/keepalived_wg_check.log"
wg_interface = "wg0"
wg_peer_key = ""
max_handshake_age = ""

if sys.platform != "darwin":
    os.chdir(panel_dir)


sys.path.append("/www/server/jh-panel/class/core")
import mw

def log(message: str) -> None:
    mw.writeFileLog(f"{mw.getDate()} - {message}", log_file)


def main() -> int:
    # 1) 基础检查：网卡与 wg 命令
    out, err, rc = mw.execShell(f"ip link show {wg_interface}")
    if rc != 0:
        log(f"ERROR: Wireguard interface {wg_interface} not found")
        return 1

    out, err, rc = mw.execShell("wg show")
    if rc != 0:
        log("ERROR: wg command not found")
        return 1

    # 2) 选择需要检查的对端
    out, err, rc = mw.execShell(f"wg show {wg_interface} peers")
    peers_out = (out or err or "").strip()
    peers = [line.strip() for line in peers_out.splitlines() if line.strip()]
    if not peers:
        log("ERROR: No peers configured")
        return 1

    target_peer = wg_peer_key
    if not target_peer:
        if len(peers) == 1:
            target_peer = peers[0]
        else:
            log("ERROR: Multiple peers configured, set WG_PEER_KEY to target peer public key")
            return 1

    # 3) 读取 handshake 时间戳
    out, err, rc = mw.execShell(f"wg show {wg_interface} dump")
    dump_out = (out or err or "").strip()
    handshake = ""
    if rc == 0:
        for line in dump_out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0] == target_peer:
                handshake = parts[4]
                break

    if not handshake:
        log(f"ERROR: Peer {target_peer} not found")
        return 1

    if handshake == "0":
        log(f"ERROR: Handshake failed with peer {target_peer}")
        return 1

    # 4) 可选：检查 handshake 是否过期
    if max_handshake_age:
        try:
            max_age = int(max_handshake_age)
            now_ts = int(time.time())
            if now_ts - int(handshake) > max_age:
                log(f"ERROR: Handshake too old with peer {target_peer}")
                return 1
        except ValueError:
            log("ERROR: MAX_HANDSHAKE_AGE must be an integer")
            return 1

    log("OK: Wireguard tunnel is healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
