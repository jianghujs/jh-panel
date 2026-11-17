#!/usr/bin/env bash
# 独立诊断脚本：不依赖面板，不安装软件，不修改配置或重启服务。
set +x
set +v
umask 077
export LC_ALL=C

WG_DIAG_IFACE=${1:-wg0}
WG_DIAG_TARGET=${2:-}
if [[ $# -gt 2 || ! $WG_DIAG_IFACE =~ ^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,14}$ ||
      -z $WG_DIAG_TARGET || ! $WG_DIAG_TARGET =~ ^[0-9a-fA-F:.]+$ ]]; then
    printf '用法：bash %s <接口名> <对方隧道IP>\n示例：bash %s wg0 10.0.0.1\n' "$0" "$0"
    exit 2
fi
for WG_DIAG_CMD in awk sed tee mktemp timeout; do
    if ! command -v "$WG_DIAG_CMD" >/dev/null 2>&1; then
        printf '缺少命令 %s，未执行诊断；请勿为此重启网络。\n' "$WG_DIAG_CMD" >&2
        exit 1
    fi
done
WG_DIAG_LOG=$(mktemp /tmp/wireguard-diag.XXXXXX.log) || exit 1

section() {
    printf '\n-----------------------\n%s\n-----------------------\n' "$1"
}

run() {
    printf '\n$'
    printf ' %q' "$@"
    printf '\n'
    if ! command -v "$1" >/dev/null 2>&1; then
        printf '[跳过] 未安装 %s\n' "$1"
        return 0
    fi
    local result=0
    timeout 8s "$@" 2>&1 || result=$?
    if [[ $result -ne 0 ]]; then
        printf '[提示] 退出码 %s（124 表示超时；命令失败不代表已确定故障原因）\n' "$result"
    fi
}

snapshot() {
    # 明确列出安全字段，禁止使用 dump/showconf，避免泄露私钥与预共享密钥。
    local field
    for field in public-key listen-port peers allowed-ips endpoints latest-handshakes transfer persistent-keepalive; do
        run wg show "$WG_DIAG_IFACE" "$field"
    done
}

main() {
    printf 'WireGuard 点对点诊断 v1\n'
    printf '时间：%s\n接口：%s\n目标隧道 IP：%s\n' "$(date -Is)" "$WG_DIAG_IFACE" "$WG_DIAG_TARGET"
    printf '1. 检查系统、接口与路由\n2. 对照磁盘配置与运行中的 Peer\n'
    printf '3. 查看监听端口、防火墙和服务状态\n4. 两轮各发送 3 次 ping，再次查看握手与流量\n'
    printf '不会改配置、生成密钥或重启服务；只生成本地日志并发送诊断流量。\n'
    printf '私钥/预共享密钥不输出；日志包含公钥、主机名、IP、端口和路由，请仅发给可信人员。\n'
    if [[ $EUID -ne 0 ]]; then
        printf '[警告] 当前不是 root，部分信息可能因权限不足而缺失。建议用 sudo bash 运行。\n'
    fi

    section '1/5 系统、接口与路由'
    run hostname
    run uname -sr
    run wg --version
    run ip -brief address
    run ip -details link show dev "$WG_DIAG_IFACE"
    run ip route get "$WG_DIAG_TARGET"
    run ip -4 rule show
    run ip -4 route show table all
    if [[ $WG_DIAG_TARGET == *:* ]]; then
        run ip -6 rule show
        run ip -6 route show table all
    fi

    section '2/5 磁盘配置摘要与运行配置（ping 前）'
    local config="/etc/wireguard/$WG_DIAG_IFACE.conf"
    if [[ -r $config ]]; then
        printf '配置文件：%s\n' "$config"
        # 白名单输出；PostUp/PostDown 等命令及其他未知内容不输出。
        awk '
            /^[[:space:]]*\[/ { print; next }
            /^[[:space:]]*[#;]/ { next }
            {
                pos = index($0, "="); if (!pos) next;
                key = tolower(substr($0, 1, pos - 1)); gsub(/[[:space:]]/, "", key);
                if (key == "privatekey" || key == "presharedkey") { print key " = [REDACTED]"; next }
                if (key ~ /^(address|listenport|publickey|allowedips|endpoint|persistentkeepalive|mtu|table|saveconfig)$/) print;
            }
        ' "$config"
        if command -v wg >/dev/null 2>&1; then
            printf '\n磁盘配置私钥推导的公钥（用于与运行中公钥交叉核对）：\n'
            # 私钥仅经管道交给 wg pubkey，不进入输出或命令行参数。
            awk '
                {
                    pos = index($0, "="); if (!pos) next;
                    key = tolower(substr($0, 1, pos - 1)); gsub(/[[:space:]]/, "", key);
                    if (key == "privatekey") {
                        value = substr($0, pos + 1); sub(/#.*/, "", value);
                        gsub(/[[:space:]]/, "", value); print value; exit;
                    }
                }
            ' "$config" | timeout 8s wg pubkey 2>/dev/null || printf '[提示] 无法从配置推导公钥\n'
        fi
    else
        printf '[提示] 配置文件不存在或不可读：%s\n' "$config"
    fi
    snapshot

    section '3/5 Peer 的外层网络路由'
    if command -v wg >/dev/null 2>&1; then
        local public_key endpoint endpoint_ip
        while read -r public_key endpoint; do
            [[ -z $endpoint || $endpoint == '(none)' ]] && continue
            endpoint_ip=${endpoint%:*}
            endpoint_ip=${endpoint_ip#[}
            endpoint_ip=${endpoint_ip%]}
            printf '\nPeer：%s；Endpoint：%s\n' "$public_key" "$endpoint"
            run ip route get "$endpoint_ip"
        done < <(timeout 8s wg show "$WG_DIAG_IFACE" endpoints 2>/dev/null)
    fi

    section '4/5 监听端口、防火墙与服务状态'
    run ss -lun
    run systemctl show "wg-quick@$WG_DIAG_IFACE.service" --no-pager \
        -p ActiveState -p SubState -p Result -p ExecMainStatus
    run iptables -w 2 -nvL INPUT --line-numbers
    run iptables -w 2 -nvL OUTPUT --line-numbers
    run iptables -w 2 -nvL FORWARD --line-numbers
    if [[ $WG_DIAG_TARGET == *:* ]]; then
        run ip6tables -w 2 -nvL INPUT --line-numbers
        run ip6tables -w 2 -nvL OUTPUT --line-numbers
    fi
    printf '\n注意：这里不完整导出 nftables、云安全组或路由器规则，不能据此断言防火墙已放行。\n'

    section '5/5 发送 3 次 ping，并复查握手与流量'
    printf '普通 ping 按系统路由选接口；绑定接口 ping 用于对比。未握手时可能触发少量握手流量。\n'
    run ping -n -c 3 -W 1 -w 5 "$WG_DIAG_TARGET"
    run ping -n -c 3 -W 1 -w 5 -I "$WG_DIAG_IFACE" "$WG_DIAG_TARGET"
    snapshot
    printf '\n======================= 采集完成 =======================\n'
    printf '日志文件：%s\n请在另一台机器也运行，将两份日志一起发回。\n' "$WG_DIAG_LOG"
    printf '这是诊断采集完成，不表示连接已恢复；请不要为此重新生成密钥。\n'
}

# 最后一层防护：对命令错误信息中的常见敏感字段再次脱敏。
main 2>&1 | sed -u -E \
    -e 's/((PrivateKey|PresharedKey|private key|preshared key)[[:space:]]*[:=])[[:space:]]*[^[:space:]#;]+/\1 [REDACTED]/Ig' \
    | tee "$WG_DIAG_LOG"
WG_DIAG_RESULTS=("${PIPESTATUS[@]}")
if [[ ${WG_DIAG_RESULTS[0]} -ne 0 || ${WG_DIAG_RESULTS[1]} -ne 0 || ${WG_DIAG_RESULTS[2]} -ne 0 ]]; then
    printf '日志采集未完整完成，请检查屏幕报错。\n' >&2
    exit 1
fi
