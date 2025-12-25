# Change: Keepalived 状态面板增加漂移告警

## Why
- Keepalived 插件当前只有简单的状态卡片，缺少“提升为主/降级为备”的邮件通知配置，切换事件只能靠人工查日志，无法在漂移时第一时间得到提醒。
- 也没有类似 rsyncd 实时服务的健康监控面板/任务，不能监测 VIP 是否失联、MySQL 读写状态是否和 VRRP 角色一致，难以及时发现双主等高危异常。

## What Changes
- 在 Keepalived 状态页新增三个可持久化的开关：提升为主邮件通知、降级为备邮件通知、Keepalived 实时监测报告，交互对齐 rsyncd 实时服务卡片。
- 扩展 `notify_master.sh`、`notify_backup.sh`：根据开关决定是否调用面板通知系统发送结构化邮件，附带 VIP、节点、MySQL 状态等上下文。
- 在 `task.py` 中补充 Keepalived 监测逻辑：当监测开关打开时，每 10 分钟检测 keepalived/vip/mysql 各项状态，发现异常后推送一条“Keepalived 实时监测报告”告警。

## Impact
- Specs: keepalived-ha-monitoring（新增能力，涵盖状态开关、漂移通知、监测任务）
- Code: `plugins/keepalived/index.py`、`plugins/keepalived/js/keepalived.js`、`plugins/keepalived/scripts/notify_master.sh`、`plugins/keepalived/scripts/notify_backup.sh`、`task.py`，以及可能新增的配置/工具文件。
