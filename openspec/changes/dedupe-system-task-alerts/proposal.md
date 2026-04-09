## Why

`task.py` 里的 `systemTask()` 当前依赖 `mw.notifyMessage(..., trigger_time=600)` 做时间窗口限流，同一类异常在问题持续期间仍会按周期重复发送。对于 CPU/内存/磁盘、MySQL 从库、Rsync、Keepalived 等持续性故障，这会造成重复报警噪音，影响真正的新故障识别。

这次变更要把告警语义从“按时间间隔重复发送”调整为“同一问题生命周期内只发送一次，只有问题恢复后再次出现才重新发送”，让异常通知更符合运维排障预期。

## What Changes

- 为 `systemTask()` 监控告警增加“故障状态记忆”能力，识别同一异常是否仍处于未恢复状态。
- 将监控项通知逻辑从单纯依赖 `trigger_time` 限流，调整为基于“首次出现 -> 恢复 -> 再次出现”的状态变化发送。
- 为多类监控异常定义稳定的问题标识，确保 CPU/内存/磁盘、SSL 证书、MySQL 从库、Rsync、Keepalived 等项目可以分别去重。
- 在问题恢复时清理对应状态，使后续再次异常时能够重新发送通知。
- 保持现有通知渠道和消息内容兼容，不改变 Telegram / 邮件通知配置入口。

## Capabilities

### New Capabilities
- `system-task-alert-deduplication`: Ensure system monitor alerts are sent once per active problem and are only re-sent after the problem clears and reoccurs.

### Modified Capabilities
- None.

## Impact

- Affected code: `task.py`, `class/core/mw.py`
- Runtime state: likely a new or extended local state file under `data/` or `tmp/` for persisted alert-active flags
- Notifications: `面板监控` alarm sending path and related monitor error classification
- Operations impact: reduces repeated alert noise without changing existing notification channel settings
