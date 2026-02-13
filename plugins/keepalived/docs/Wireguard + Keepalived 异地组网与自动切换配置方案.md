# Wireguard + Keepalived 异地组网与自动切换配置方案

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      互联网公网                              │
│                        (UDP 51820)                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
    ┌───────▼───────┐               ┌───────▼───────┐
    │   机房 A       │               │   机房 B       │
    │  主服务器     │←─────────────→│  备服务器     │
    │  (Master)    │   Wireguard   │  (Backup)    │
    │  公网IP: A   │   隧道连接    │  公网IP: B   │
    └───────┬───────┘               └───────┬───────┘
            │                               │
            │         Keepalived VIP        │
            │      虚拟IP: 10.0.0.100       │
            │                               │
            ▼                               ▼
    ┌───────────────────────────────────────────────┐
    │              内部业务网络 (可选)                  │
    └───────────────────────────────────────────────┘
```

## 二、核心组件职责

### 2.1 Wireguard

- **职责**：建立机房之间的加密隧道
- **特点**：轻量、快速、内置加密
- **端口**：UDP 51820

### 2.2 Keepalived

- **职责**：实现 VIP 自动漂移和健康检查
- **核心功能**：
  - VRRP 协议实现 VIP 自动切换
  - 健康检查（脚本/端口/进程）
  - 脑裂防护机制

### 2.3 辅助脚本

- **健康检查脚本**：`chk_wireguard.py` + `chk_network.py`
- **切换通知脚本**：`notify_master.py` + `notify_backup.py`
- **状态记录脚本**：`notify.sh` 写入切换日志

## 三、详细配置

### 3.1 Wireguard 配置

#### 机房 A（主服务器）

```ini
# 1) 配置防火墙（放行 UDP 51820）
iptables -I INPUT -p udp --dport 51820 -j ACCEPT

# 2) 安装 Wireguard
apt install wireguard -y  # Ubuntu/Debian
yum install wireguard-tools -y  # CentOS

# 3) 生成密钥对
wg genkey | tee privatekey | wg pubkey > publickey

# 4) /etc/wireguard/wg0.conf
[Interface]
Address = 10.0.0.1/24
PrivateKey = <机房A私钥>
ListenPort = 51820

PostUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostUp = iptables -A FORWARD -o wg0 -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT
PostDown = iptables -D FORWARD -o wg0 -j ACCEPT

[Peer]
# 机房 B
PublicKey = <机房B公钥>
AllowedIPs = 10.0.0.2/32,10.0.0.100/32
Endpoint = <机房B公网IP>:51820
PersistentKeepalive = 25
```

#### 机房 B（备服务器）

```ini
# 1) 配置防火墙（放行 UDP 51820）
iptables -I INPUT -p udp --dport 51820 -j ACCEPT

# 2) /etc/wireguard/wg0.conf
[Interface]
Address = 10.0.0.2/24
PrivateKey = <机房B私钥>
ListenPort = 51820

PostUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostUp = iptables -A FORWARD -o wg0 -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT
PostDown = iptables -D FORWARD -o wg0 -j ACCEPT

[Peer]
# 机房 A
PublicKey = <机房A公钥>
AllowedIPs = 10.0.0.1/32,10.0.0.100/32
Endpoint = <机房A公网IP>:51820
PersistentKeepalive = 25
```

**要点说明**：

- VIP `10.0.0.100/32` 被放入 `AllowedIPs`，便于对端学习 VIP 路由。
- 通过 `PostUp` 开启转发并放行 wg0 转发流量，配合 Keepalived 漂移 VIP。
- 端口统一为 `51820`。

#### 启动与开机自启

```bash
# 启动 Wireguard（推荐）
wg-quick up wg0

# 停止 Wireguard
wg-quick down wg0

# 设置开机自启
systemctl enable wg-quick@wg0

# 查看状态
systemctl status wg-quick@wg0

# 查看隧道信息
wg show wg0
```

### 3.2 Keepalived 配置

#### 防火墙放行 VRRP（两端都需要）

```bash
iptables -I INPUT -p vrrp -j ACCEPT
```

#### 机房 A（MASTER）

```conf
global_defs {
    script_user root
    enable_script_security
}

vrrp_script chk_wg {
    script "/www/server/keepalived/scripts/chk_wireguard.py"
    interval 2
    weight -200
    fall 2
    rise 1
}

vrrp_script chk_network {
    script "/www/server/keepalived/scripts/chk_network.py"
    interval 2
    weight -200
    fall 2
    rise 1
}

vrrp_instance VI_1 {
  state MASTER
  interface wg0
  virtual_router_id 52
  priority 100
  nopreempt
  advert_int 2

  unicast_src_ip 10.0.0.1
  unicast_peer {
      10.0.0.2
  }

  virtual_ipaddress {
      10.0.0.100/32 dev wg0
  }

  track_script {
    chk_wg
    chk_network
  }

  notify_backup "/www/server/keepalived/scripts/notify_backup.py"
  notify_master "/www/server/keepalived/scripts/notify_master.py"
  notify "/www/server/keepalived/scripts/notify.sh"
}
```

#### 机房 B（BACKUP）

```conf
global_defs {
    script_user root
    enable_script_security
}

vrrp_script chk_wg {
    script "/www/server/keepalived/scripts/chk_wireguard.py"
    interval 2
    weight -200
    fall 2
    rise 1
}

vrrp_script chk_network {
    script "/www/server/keepalived/scripts/chk_network.py"
    interval 2
    weight -200
    fall 2
    rise 1
}

vrrp_instance VI_1 {
  state BACKUP
  interface wg0
  virtual_router_id 52
  priority 90
  nopreempt
  advert_int 2

  unicast_src_ip 10.0.0.2
  unicast_peer {
      10.0.0.1
  }

  virtual_ipaddress {
      10.0.0.100/32 dev wg0
  }

  track_script {
    chk_wg
    chk_network
  }

  notify_backup "/www/server/keepalived/scripts/notify_backup.py"
  notify_master "/www/server/keepalived/scripts/notify_master.py"
  notify "/www/server/keepalived/scripts/notify.sh"
}
```

**要点说明**：

- VRRP 走 `wg0` 接口，VIP 为 `10.0.0.100/32`（挂在 Wireguard 隧道内）。
- 单播模式：`unicast_src_ip 10.0.0.1` → `unicast_peer 10.0.0.2`。
- `chk_wg` + `chk_network` 双重健康检查，失败将大幅降权（`weight -200`）。
- `notify_master/notify_backup/notify` 已指向插件内脚本（Python + Shell）。

### 3.3 辅助脚本

> 以下脚本来自 `/www/server/keepalived/scripts/`，为当前插件实际使用脚本的关键逻辑摘录。

#### 3.3.1 Wireguard 健康检查（chk_wireguard.py）

```python
log_file = "/www/server/keepalived/logs/keepalived_wg_check.log"
wg_interface = "wg0"
wg_peer_key = ""
max_handshake_age = ""

out, err, rc = mw.execShell(f"ip link show {wg_interface}")
out, err, rc = mw.execShell("wg show")
out, err, rc = mw.execShell(f"wg show {wg_interface} peers")
out, err, rc = mw.execShell(f"wg show {wg_interface} dump")
# 读取指定 peer 的 handshake 时间戳，失败或过期则返回 1
```

**行为摘要**：

- 检查 `wg0` 接口存在、`wg` 命令可用；
- 自动选择唯一 peer，或要求指定 `WG_PEER_KEY`；
- 读取握手时间戳，若为 `0` 或超龄则视为异常；
- 日志写入 `logs/keepalived_wg_check.log`。

#### 3.3.2 网络连通性检查（chk_network.py）

```python
keepalived_conf = "/www/server/keepalived/etc/keepalived/keepalived.conf"

targets = build_targets()  # 默认：网关 + keepalived.conf 中 unicast_peer
ping_count = 1
ping_timeout = 1
min_success = 1
```

**行为摘要**：

- 默认 ping 网关 + `unicast_peer`；
- 可用环境变量覆盖：`NETWORK_TARGETS`/`NETWORK_PING_COUNT`/`NETWORK_PING_TIMEOUT`/`NETWORK_MIN_SUCCESS`；
- 日志写入 `logs/keepalived_network_check.log`。

#### 3.3.3 切换为 MASTER（notify_master.py）

```python
keepalived_instance = "VI_1"
desired_priority = "100"
retry_times = 3

# 关键动作（顺序简化）
# 1) delete_slave 清理从库配置
# 2) 启动 OpenResty
# 3) 提升 keepalived priority
# 4) 调整定时任务（备份/lsyncd/续签证书）
# 5) 开启告警与通知
# 6) 禁用 standby 同步，开启 rsyncd 任务
```

**行为摘要**：

- 使用 `plugins/mysql-apt/index.py delete_slave` 清理从库配置；
- 启动 OpenResty 接管入口；
- 调整多个定时任务与告警开关；
- 发送“提升为主”通知，日志写入 `logs/notify_master.log`。

#### 3.3.4 切换为 BACKUP（notify_backup.py）

```python
keepalived_instance = "VI_1"
desired_priority = "90"
retry_times = 3

# 关键动作（顺序简化）
# 1) 停止 OpenResty
# 2) 降低 keepalived priority
# 3) 关闭主从/Rsync 异常提醒
# 4) set_db_read_only + 重启 MySQL
# 5) 初始化从库状态（必要时）
# 6) 调整定时任务（备份/lsyncd/续签证书）
# 7) 启用 standby 同步，关闭 rsyncd 任务并清理进程
```

**行为摘要**：

- 将数据库切只读并重启 MySQL；
- 维护从库同步状态；
- 停止 OpenResty，关闭 rsyncd 任务；
- 发送“降级为从”通知，日志写入 `logs/notify_backup.log`。

#### 3.3.5 状态变更记录（notify.sh）

```sh
STATE="$1"
PREV_STATE="$2"
TYPE="$3"
LOG_FILE="/www/server/keepalived/logs/events.log"
MSG="$(date +'%Y-%m-%d %H:%M:%S') [keepalived] VRRP ${TYPE}: ${PREV_STATE} -> ${STATE}"
```

**行为摘要**：

- 将 VRRP 角色变更写入 `logs/events.log`，便于追踪切换历史。

### 3.4 域名切换方案（Zenlayer 主备 IP）

使用 Zenlayer 的主备解析能力配置两个公网 IP：

- 主记录：绑定当前主节点公网 IP
- 备记录：绑定当前备节点公网 IP
- 健康检查：建议以 OpenResty 对外端口为探测目标

切换逻辑说明：

- Keepalived 提升为主时会启动 OpenResty；
- Keepalived 降级为备时会停止 OpenResty；
- Zenlayer 健康检查会自动把解析流量切向 OpenResty 正常的节点。

## 四、自动切换流程说明

### 4.1 断电流程（主节点掉电）

**触发**：主节点物理断电或强制关机。

**过程**：
- 主节点无法发送 VRRP 通告；
- 备节点在超时后提升为 MASTER，并接管 VIP；
- `notify_master.py` 启动 OpenResty，对外服务恢复；
- Zenlayer 健康检查切换到新的主节点。

**恢复**：
- 原主节点上电后因 `nopreempt` 不会抢占；
- 原主节点保持 BACKUP；
- 若需强制让本机成为主节点，可执行 `jh 22` 的“修复Keepalived双节点”。

### 4.2 断网流程（主节点网络中断）

**触发**：主节点公网或隧道网络中断（如 `wg0` 异常、对端不可达）。

**过程**：
- `chk_network.py`/`chk_wireguard.py` 检测失败后降低优先级；
- 备节点成为 MASTER 并接管 VIP；
- OpenResty 在新主节点启动，Zenlayer 解析随健康检查切换。

**恢复**：
- 主节点网络恢复后保持 BACKUP（`nopreempt` 不抢占）；
- 如出现双主或 VIP 异常，可使用 `jh 22` 修复。

## 五、常见问题处理

### 5.1 Keepalived 状态修复

当双节点 keepalived 状态异常或 VIP 未在本机时，可使用面板工具强制修复并确保本机成为主节点：

```bash
jh 22
# 选择：服务器修复 -> 修复Keepalived双节点
# 说明：确保双节点 keepalived 状态，本机成为主节点
```

**脚本摘要**：

- 确保本地与对端 keepalived 都已启动（使用 `/www/server/keepalived/init.d/keepalived`）
- 设置本地 priority=100，对端 priority=90（`plugins/keepalived/tool.py update_priority`）
- 读取 `keepalived.conf` 中的 VIP 列表并检测 VIP 位置
- 如果 VIP 在对端：停止对端 keepalived，等待 VIP 漂移到本地，再重启对端 keepalived
- 可选执行修复上下线脚本：本地 `notify_master.py`、对端 `notify_backup.py`

**交互输入**：

- 对端 IP
- 对端 SSH 端口（默认 `10022`）
- VRRP 实例名（默认 `VI_1`）

### 5.2 VIP 无法漂移

**症状**：主服务器故障，VIP 不在备服务器上

**排查步骤**：

```bash
# 1. 检查 VRRP 通信（当前配置走 wg0 单播）
tcpdump -i wg0 vrrp -n

# 2. 检查防火墙
iptables -L INPUT -n | grep vrrp

# 3. 检查 Keepalived 日志
tail -f /var/log/syslog | grep Keepalived

# 4. 验证优先级设置
grep priority /www/server/keepalived/etc/keepalived/keepalived.conf
```

**解决方案**：

```bash
# 确保防火墙放行 VRRP
iptables -I INPUT -p vrrp -j ACCEPT

# 确保网卡名称正确
ip addr  # 查看实际网卡名称

# 确保 virtual_router_id 两端一致
grep virtual_router_id /www/server/keepalived/etc/keepalived/keepalived.conf
```

### 5.3 脑裂问题（双主）

**症状**：两台服务器都持有 VIP

**原因**：

- 网络分区导致两台服务器无法通信
- VRRP 认证失败
- 配置错误

**解决方案**：

```bash
# 1. 启用脑裂检测脚本
# 在 /etc/keepalived/keepalived.conf 中添加（当前插件路径为 /www/server/keepalived/etc/keepalived/keepalived.conf）

vrrp_script chk_split_brain {
    script "/usr/local/bin/check_split_brain.sh"
    interval 5
    weight -100  # 权重降为负数，直接切换
}

track_script {
    chk_split_brain
}

# 2. 脑裂检测脚本
cat > /usr/local/bin/check_split_brain.sh << 'EOF'
#!/bin/bash
# 检测脑裂：如果检测到本机不应该持有 VIP，则自杀

VIP="10.0.0.100"
LOG_FILE="/var/log/split_brain.log"

# 检查对端是否可达
if ! ping -c 2 <对端公网IP> -W 2 > /dev/null 2>&1; then
    # 对端不可达，可能已经发生脑裂
    echo "$(date) - Split brain detected, releasing VIP" >> $LOG_FILE
    ip addr del $VIP/24 dev wg0 2>/dev/null || true
    exit 1
fi

exit 0
EOF

# 3. 增加 VRRP 认证
authentication {
    auth_type PASS
    auth_pass "strong_password_here"
}
```

**文档版本**：v1.5
**更新日期**：2026-02-13
**作者**：Fortuna
