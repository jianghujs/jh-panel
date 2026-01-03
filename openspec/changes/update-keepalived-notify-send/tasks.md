## 1. 实现
- [ ] 1.1 为 `alert_settings.json` 增加 `notify_promote`/`notify_demote` 的后端读取与兜底逻辑，保证文件缺失或字段为空时可返回默认值。
- [ ] 1.2 在 `tools.py` 或独立模块封装调用 `mw.sendMessage` 的 CLI 方法，支持 shell 传入主题、正文与附加上下文。
- [ ] 1.3 修改 `notify_master.sh`、`notify_backup.sh`，读取 `alert_settings.json` 并在开关开启时调用上一步封装，组装角色/VIP/MySQL 信息。
- [ ] 1.4 更新 keepalived 插件（如 `index.py`、前端 JS）确保新增字段存取一致，同时在保存配置时写入上述布尔值。
- [ ] 1.5 通过手动或脚本方式模拟漂移，验证在开关开启/关闭情况下的邮件行为，并记录日志路径。
