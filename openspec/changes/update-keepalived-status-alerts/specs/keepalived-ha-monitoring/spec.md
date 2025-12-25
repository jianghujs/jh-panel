## ADDED Requirements
### Requirement: Keepalived 状态告警开关
Keepalived 插件 SHALL 在“状态”标签页提供三个与漂移/监测相关的布尔开关，并把选择结果写入 `/www/server/keepalived/config/alert_settings.json` 供脚本与后台任务共享。

#### Scenario: 展示与刷新
- **WHEN** 用户进入 Keepalived 状态页或点击刷新
- **THEN** 页面展示“提升为主邮件通知”“降级为备邮件通知”“Keepalived 实时监测报告”三个开关，默认值均为关闭，并从 `alert_settings.json` 读取当前状态（文件不存在时由后端创建并返回默认值）。

#### Scenario: 保存配置
- **WHEN** 用户切换任一开关并点击保存
- **THEN** `index.py` 通过新的 `save_alert_settings` 接口校验布尔值、落盘到 `alert_settings.json`，立即回传最新配置；该文件的所有权与 keepalived 目录一致，供 shell、Python 脚本只读使用。

### Requirement: Keepalived 漂移邮件通知
keepalived 的 `notify_master.sh` 与 `notify_backup.sh` SHALL 根据 `alert_settings.json` 决定是否在角色变更时推送邮件，邮件通过面板现有通知通道发出并包含关键上下文。

#### Scenario: 提升为主时触发邮件
- **WHEN** keepalived 调用 `notify_master.sh` 且“提升为主邮件通知”开关为开启
- **THEN** 脚本调用面板通知 helper 发送一封 HTML 邮件，至少包含事件时间、本机 IP/主机名、VIP、检测到的 MySQL 读写状态，并在脚本日志中记录邮件发送结果；若通知关闭或面板未配置邮件/TG，则不发送。

#### Scenario: 降级为备时触发邮件
- **WHEN** keepalived 调用 `notify_backup.sh` 且“降级为备邮件通知”开关为开启
- **THEN** 脚本发送“降级”主题的邮件，描述本机优先级、是否仍持有 VIP、MySQL 读写状态，失败时写入 `notify_backup.log` 并返回非零退出码以提示管理员检查。

### Requirement: Keepalived 实时监测告警
`plugins/keepalived/notify_util.py` SHALL 提供 Keepalived 状态巡检与报告格式化能力，`mw.generateMonitorReportAndNotify` SHALL 在“Keepalived 实时监测报告”开关开启时每 10 分钟调用该 helper 并在异常时推送告警。

#### Scenario: 巡检与调度
- **WHEN** 巡检开关开启
- **THEN** helper 读取 `alert_settings.json` 与 keepalived 配置，执行以下检测：
  1. `systemctl is-active keepalived` 或 `pidof keepalived`，判定服务是否运行；
  2. 解析配置的 VIP/interface，并检查本机 `ip addr` 是否持有 VIP 来确定 VRRP 角色；
  3. 对 VIP 执行 `ping`（3 次、1 秒超时）与 `nc`/`telnet` 到 MySQL 端口，若全部失败则判定“无节点持有 VIP”；若 `arping`/`ip neigh` 返回多个 MAC，则判定“多节点持有 VIP”；
  4. 通过 TCP 探测与 `SELECT @@global.read_only` 判断本地 MySQL 端口可达且角色=MASTER 时可写、角色=BACKUP 时只读，防止双主；
  5. 任一检测不可执行（如缺少命令或凭据）时，结果标记为“未知”但不会误报。
- **AND** `mw.generateMonitorReportAndNotify` 每 10 分钟调用 helper，写入 `/www/server/keepalived/logs/keepalived_monitor.log`，若存在异常则通过 `mw.notifyMessage(..., stype='keepalived-monitor', trigger_time=600)` 发送 HTML 告警，每 10 分钟最多一条。
