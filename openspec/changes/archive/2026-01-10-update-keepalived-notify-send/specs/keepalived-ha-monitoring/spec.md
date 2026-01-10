## MODIFIED Requirements
### Requirement: Keepalived 漂移邮件通知
keepalived 的 `notify_master.sh` 与 `notify_backup.sh` SHALL 在执行前读取 `/www/server/keepalived/config/alert_settings.json`，识别 `notify_promote`、`notify_demote` 布尔值并决定是否推送漂移邮件；脚本调用 `/www/server/jh-panel/class/core/mw.py` 的 `sendMessage`（允许经 `tools.py` 封装）将 HTML 通知发送到面板配置好的渠道，并在日志中输出调用结果。

#### Scenario: 提升为主时触发邮件
- **WHEN** keepalived 调用 `notify_master.sh` 且 `alert_settings.json` 中的 `notify_promote=true`
- **THEN** 脚本补全事件时间、本机主机名、管理 IP、VRRP VIP、MySQL 读写角色后，通过 `mw.sendMessage(..., stype='keepalived-promote')` 或等效封装发出“提升为主”主题邮件；调用失败或 `sendMessage` 抛错时写入 `notify_master.log` 并返回非零码，若开关关闭或未配置通知通道则直接退出且记录原因。

#### Scenario: 降级为备时触发邮件
- **WHEN** keepalived 调用 `notify_backup.sh` 且 `alert_settings.json` 中的 `notify_demote=true`
- **THEN** 脚本读取当前优先级、是否持有 VIP、MySQL 读写状态，按照 promote 同样的封装调用 `mw.sendMessage`，使用 `stype='keepalived-backup'` 并在 `notify_backup.log` 中记录成功/失败；当读取配置失败时应采用默认关闭策略并提醒管理员检查配置文件。
