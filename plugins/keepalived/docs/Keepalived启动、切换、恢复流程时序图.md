这是一个非常经典的**高可用（High Availability）**架构场景。

为了让图表更具技术深度和指导意义，我建议将 `Keepalived集群` 拆分为 `KA_Master`（运行在主库机器上的 Keepalived）和 `KA_Slave`（运行在从库机器上的 Keepalived），这样能更清晰地展示 VRRP 协议的交互和 VIP 的漂移过程。

以下为您完善的三个阶段的 Mermaid 时序图：

### 1. 启动与正常运行流程 (Startup & Normal State)

在这个阶段，重点展示主从复制关系的建立、VIP 的绑定以及应用程序的正常访问。

代码段

```mermaid
sequenceDiagram
    autonumber
    participant App as 应用程序
    participant VIP as 虚拟IP (1.100)
    box "主节点 (Master Node)" #e1f5fe
        participant KA_M as Keepalived (主)
        participant DB_M as MySQL主库 (1.10)
    end
    box "从节点 (Slave Node)" #fff3e0
        participant KA_S as Keepalived (备)
        participant DB_S as MySQL从库 (1.11)
    end

    Note over DB_M, DB_S: 1. 数据库层初始化
    DB_M->>DB_M: 启动，设为 ReadWrite
    DB_S->>DB_M: 连接主库，开启 Binlog 复制
    DB_S->>DB_S: 启动，设为 ReadOnly

    Note over KA_M, KA_S: 2. Keepalived 竞选与 VIP 绑定
    KA_M->>KA_S: 发送 VRRP 广播 (Priority=100)
    KA_S->>KA_M: 发送 VRRP 广播 (Priority=90)
    Note right of KA_M: 优先级更高，当选 Master
    KA_M->>VIP: 绑定 VIP (ip addr add 1.100)
    KA_M->>App: 发送免费 ARP (GARP) 广播<br/>(通知网络设备 VIP 在此处)

    Note over App, DB_S: 3. 业务流量接入
    App->>VIP: 发起读写请求
    VIP->>DB_M: 流量路由至 1.10
    DB_M-->>App: 返回数据
    par 数据同步
        DB_M->>DB_S: 异步/半同步复制数据
    end
```

------

### 2. 故障切换流程 (Failover Flow)

这是核心流程。重点展示 Keepalived 如何检测故障、VIP 如何漂移（Drift）、以及从库如何提升为主库（Promotion）。

代码段

```mermaid
sequenceDiagram
    autonumber
    participant App as 应用程序
    participant VIP as 虚拟IP (1.100)
    box "原主节点 (1.10)" #ffebee
        participant KA_M as Keepalived (主)
        participant DB_M as MySQL主库 (1.10)
    end
    box "新主节点 (1.11)" #e8f5e9
        participant KA_S as Keepalived (备)
        participant DB_S as MySQL从库 (1.11)
    end

    Note over DB_M: ⚠️ 突发故障 (宕机/断网)
    
    rect rgb(255, 240, 240)
        Note over KA_M, KA_S: 1. 故障检测
        KA_S-xKA_M: 未收到 VRRP 心跳包
        KA_S->>KA_S: 判定原主节点失效<br/>转换为 VRRP Master 状态
    end

    rect rgb(240, 255, 240)
        Note over KA_S, DB_S: 2. 数据库提升 (Promotion)
        KA_S->>DB_S: 触发 notify_master 脚本
        DB_S->>DB_S: stop slave io_thread (停止IO接收)
        Note right of DB_S: 检查并等待 Relay Log 回放完成<br/>(确保数据一致性)
        DB_S->>DB_S: stop slave (停止SQL线程)
        DB_S->>DB_S: reset slave all (重置主从)
        DB_S->>DB_S: set global read_only=0 (开启写权限)
    end

    rect rgb(255, 255, 240)
        Note over KA_S, VIP: 3. 流量切换
        KA_S->>VIP: 绑定 VIP 到本地网卡
        KA_S->>App: 发送免费 ARP (GARP)<br/>刷新交换机/客户端 MAC 缓存
    end
    
    Note over App, DB_S: 4. 业务恢复
    App->>VIP: 重连请求 (TCP Retransmit)
    VIP->>DB_S: 流量路由至 1.11 (新主)
    DB_S-->>App: 业务恢复正常
```

------

### 3. 故障恢复与节点重加 (Recovery & Re-join)

这是很多设计容易忽略的地方。**注意**：通常我们配置 Keepalived 为 `nopreempt`（不抢占）模式。原主库恢复后，**不应立即抢回 Master 地位**，否则会导致数据不一致和二次业务抖动。它应该先作为“从库”加入集群。

代码段

```mermaid
sequenceDiagram
    autonumber
    box "原主节点 (现为从)" #e1f5fe
        participant KA_Old as Keepalived (1.10)
        participant DB_Old as MySQL (1.10)
    end
    box "现主节点 (1.11)" #e8f5e9
        participant KA_New as Keepalived (1.11)
        participant DB_New as MySQL (1.11)
    end
    participant VIP as 虚拟IP (1.100)

    Note over KA_Old, DB_Old: 1. 原故障节点重启恢复
    KA_Old->>KA_Old: 启动 Keepalived
    KA_Old->>KA_New: 接收到 Master 的 VRRP 包
    Note right of KA_Old: 发现已有 Master<br/>且配置为"非抢占模式"<br/>自动进入 Backup 状态

    Note over DB_Old, DB_New: 2. 数据追平 (重建主从)
    DB_Old->>DB_Old: 手动或脚本触发：<br/>清理旧数据/GTID对齐
    DB_Old->>DB_New: Change Master to 1.11
    DB_Old->>DB_New: Start Slave (作为从库运行)
    DB_New->>DB_Old: 发送在故障期间产生的新 Binlog

    Note over KA_Old, VIP: 3. 集群稳态
    Note right of KA_New: VIP 保持在 1.11 不动<br/>业务无感知
    
    opt 管理员手动切回 (如需)
        Note over KA_Old, KA_New: 择机进行计划性切换
        KA_New->>KA_New: 降低优先级或停止服务
        KA_Old->>VIP: 重新接管 VIP
        DB_New->>DB_New: 降级为从库
    end
```

### 给您的优化建议

1. **GARP (Gratuitous ARP) 是关键**：在图表中我特意加入了 `发送免费 ARP` 这一步。这是 VIP 漂移生效的关键，它强制更新交换机和客户端的 ARP 缓存，否则应用程序可能仍然试图向旧的 MAC 地址发送数据。
2. **明确“提升”动作**：在切换流程中，`Slave` 变为 `Master` 不是自动发生的，必须由 Keepalived 调用脚本（`notify_master`）去执行 SQL 命令（如关闭 read_only），这一点在图中已体现。
3. **防止“脑裂”**：恢复流程中，原主库回来后，如果不处理，可能会出现两个主库（双写）。因此流程图强调了**“原主库作为从库加入”**这一逻辑。

您想针对其中某个特定脚本（比如 Keepalived 的检测脚本）进行详细讨论吗？