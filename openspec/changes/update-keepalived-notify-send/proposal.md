# Change: Keepalived 漂移通知脚本接入面板消息

## Why
- Keepalived 插件虽然已经在前端提供“提升为主/降级为备”告警开关，但脚本端仍然直接输出日志，未调用面板统一的通知通道。
- 需要让 `notify_master.sh` 与 `notify_backup.sh` 在对应开关开启时读取 `alert_settings.json`，并通过 `mw.sendMessage` 发送邮件，使通知链路与面板一致。

## What Changes
- 补充脚本到面板通知系统的调用流程，必要时在 `tools.py` 中提供封装以便 shell 脚本复用。
- 规范 `alert_settings.json` 中 `notify_promote`、`notify_demote` 的语义，并确保脚本读取失败时具备默认策略与错误日志。
- 记录邮件内容字段（角色、VIP、MySQL 状态等）与回退行为，保证运维可观测性。

## Impact
- Affected specs: keepalived-ha-monitoring
- Affected code: plugins/keepalived/index.py, plugins/keepalived/js/keepalived.js, /www/server/keepalived/scripts/notify_master.sh, /www/server/keepalived/scripts/notify_backup.sh, class/core/mw.py, tools.py
