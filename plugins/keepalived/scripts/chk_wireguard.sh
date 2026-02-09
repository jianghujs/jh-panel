#!/bin/bash
# 检查 Wireguard 隧道状态

LOG_FILE="/www/server/keepalived/logs/keepalived_wg_check.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# WireGuard 接口与对端配置
WG_INTERFACE="${WG_INTERFACE:-wg0}"
WG_PEER_KEY="${WG_PEER_KEY:-}"
MAX_HANDSHAKE_AGE="${MAX_HANDSHAKE_AGE:-}"

# 检查 Wireguard 接口是否存在
if ! ip link show "$WG_INTERFACE" > /dev/null 2>&1; then
    log "ERROR: Wireguard interface ${WG_INTERFACE} not found"
    exit 1
fi

# 检查 Wireguard 隧道是否正常（检查对端是否在线）
if ! command -v wg >/dev/null 2>&1; then
    log "ERROR: wg command not found"
    exit 1
fi

WG_STATUS=$(wg show "$WG_INTERFACE" peers)
if [ -z "$WG_STATUS" ]; then
    log "ERROR: No peers configured"
    exit 1
fi

# 选择要检查的对端
TARGET_PEER="$WG_PEER_KEY"
if [ -z "$TARGET_PEER" ]; then
    PEER_COUNT=$(echo "$WG_STATUS" | wc -l | tr -d ' ')
    if [ "$PEER_COUNT" -eq 1 ]; then
        TARGET_PEER="$WG_STATUS"
    else
        log "ERROR: Multiple peers configured, set WG_PEER_KEY to target peer public key"
        exit 1
    fi
fi

# 检查特定对端是否 handshake 成功
DUMP_OUTPUT=$(wg show "$WG_INTERFACE" dump 2>/dev/null)
HANDSHAKE=$(echo "$DUMP_OUTPUT" | awk -v peer="$TARGET_PEER" '$1==peer {print $5; exit}')
if [ -z "$HANDSHAKE" ]; then
    log "ERROR: Peer ${TARGET_PEER} not found"
    exit 1
fi
if [ "$HANDSHAKE" -eq 0 ]; then
    log "ERROR: Handshake failed with peer ${TARGET_PEER}"
    exit 1
fi

# 可选：检查 handshake 是否过旧
if [ -n "$MAX_HANDSHAKE_AGE" ]; then
    NOW_TS=$(date +%s)
    if [ $((NOW_TS - HANDSHAKE)) -gt "$MAX_HANDSHAKE_AGE" ]; then
        log "ERROR: Handshake too old with peer ${TARGET_PEER}"
        exit 1
    fi
fi

# 可选：检查业务服务是否正常运行
# 比如检查 Nginx、MySQL 等
# if ! systemctl is-active --quiet nginx; then
#     log "ERROR: Nginx not running"
#     exit 1
# fi

log "OK: Wireguard tunnel is healthy"
exit 0
