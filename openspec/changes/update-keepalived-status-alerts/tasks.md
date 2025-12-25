# 任务清单

## 1. 配置与 API
- [x] 1.1 在 `/www/server/keepalived/config/alert_settings.json` 初始化/读取/写入邮件&监测开关，暴露 `get_alert_settings`、`save_alert_settings` 接口（含输入校验）。
- [x] 1.2 为前端提供统一的数据结构（包含默认值/最后更新时间），并补充单元/人工测试：调用接口前后读文件结果一致。

## 2. 前端交互
- [x] 2.1 在 Keepalived 状态面板中新增与 rsyncd 实时服务一致的设置区，渲染三个开关 + 保存按钮。
- [x] 2.2 对接新接口，实现刷新/保存提示，确保版本切换或 reload 后状态正确回显。

## 3. 漂移脚本告警
- [x] 3.1 扩展 `notify_master.sh`、`notify_backup.sh`：读取 `alert_settings.json` 判定是否发信，并通过 Python helper 调用 `mw.notifyMessage` 发送邮件，所有分支写入日志。
- [x] 3.2 为脚本增加幂等与失败回退（例如 helper 异常时不中断原逻辑但记录失败原因）。

## 4. 实时监测任务
- [x] 4.1 在 `plugins/keepalived/notify_util.py` 中实现 keepalived 健康巡检方法（解析 VIP/interface、执行 ping/arping/nc/mysql 读写状态检测），并对外暴露格式化结果/日志写入能力。
- [x] 4.2 在 `mw.generateMonitorReportAndNotify` 中调用 helper：基于 10 分钟周期运行巡检、写入 keepalived 监测日志、并在有异常时通过 `mw.notifyMessage(..., stype='keepalived-monitor', trigger_time=600)` 推送通知。

- [x] 5.1 手动验证：
  - 开关默认关闭→启用→刷新→状态持久。
  - 模拟 `notify_master`/`notify_backup` 调用（可手动执行脚本）观察邮件/日志。
  - 暂停 keepalived 或禁用 MySQL 读写，确认 10 分钟巡检产生一条告警，重复异常不会 10 分钟内重复推送。
- [x] 5.2 若存在自测脚本/日志，附在 MR 描述中，确保 reviewer 可复现。
