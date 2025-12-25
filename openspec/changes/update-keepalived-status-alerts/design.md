## Context
- Keepalived 插件的“状态”页目前只展示服务/VIP/优先级，缺少任何告警相关配置，更谈不上开关化控制。
- 场景需要在 keepalived 漂移时（notify_master/notify_backup）立刻发邮件，以及周期性地检查 VIP、VRRP、MySQL 状态并推报警文；这些能力涉及前端、插件后端、shell 脚本与全局 `task.py`。

## Goals / Non-Goals
- **Goals**: 暴露三个可持久化的布尔开关；为 `notify_master.sh`/`notify_backup.sh` 添加邮件发送能力；在 `task.py` 内实现 10 分钟一次的 keepalived 健康巡检并通过面板统一通知系统发告警。
- **Non-Goals**: 不改动 keepalived 的核心配置解析/保存逻辑；不实现面板侧新的通知渠道（沿用已有邮件/TG 机制）。

## Decisions
1. **配置持久化位置**：新增 `/www/server/keepalived/config/alert_settings.json`（由插件负责初始化/读写）。该文件放在 keepalived server 目录，shell 脚本与 Python 均可直接读取，数据结构包含三个 bool 值及最近一次检测时间戳。
2. **前后端交互**：`index.py` 暴露 `get_alert_settings`/`save_alert_settings`，返回/接收 JSON；状态页新增一个卡片（沿用 rsyncd 实时服务风格）展示三个开关并调用上述接口。
3. **脚本邮件发送**：在 `scripts/util` 新增轻量 Python/ shell helper，shell 读取 `alert_settings.json` 判断是否需要发送，再通过 `python3 /www/server/jh-panel/scripts/notify_helper.py ...`（新建）调用 `mw.notifyMessage` 发送 HTML 邮件，避免直接在 shell 里实现 SMTP。
4. **监测任务**：`task.py` 引入 `collect_keepalived_health()` helper，读取 keepalived 配置解析 VIP/interface/mysql 端口；执行以下检查：
   - keepalived 服务状态（`systemctl is-active`）。
   - VRRP 角色（本机是否持有 VIP）。
   - VIP reachability：`ping -c3 VIP`，并用 `arping`/`ip neigh` 分析是否出现多个 MAC；再执行 `nc -z VIP MYSQL_PORT` 验证端口。
   - 本地 MySQL 端口可达（TCP）及 `@@global.read_only`；若角色=MASTER 却仍为只读，或角色=BACKUP 但已可写，则认定双主风险。
   检查失败时拼装异常列表，通过 `mw.notifyMessage(..., stype='keepalived-monitor', trigger_time=600)` 推送。
5. **节流与日志**：`alert_settings.json` 记录 `last_monitor_ts`，配合 `mw.notifyMessage` 的 `trigger_time` 双重限制，确保 10 分钟内只发一次；脚本发信和巡检失败都写入 keepalived 的 `logs/` 下专用文件，便于排查。

## Risks / Trade-offs
- **依赖 mysql 凭据**：需要读取面板记录的 root 密码才能判断 read_only，若用户自定义密码或插件无法检测，将导致监测项降级为“未知”。准备在告警中说明“无法连接 MySQL”。
- **网络工具可用性**：`arping` 并非所有系统预装，如缺失则只能监测 ping/nc 结果；告警中需注明“未能检测多持有”而不是误报。
- **脚本触发频率**：notify_master/notify_backup 可能在几秒内被 keepalived 多次调用，需要在 helper 里基于上次事件时间去重，避免邮件轰炸。

## Open Questions
- 是否需要在面板 UI 中展示最近一次 Keepalived 监测结果？本次仅实现告警与日志，不额外扩展 UI。
