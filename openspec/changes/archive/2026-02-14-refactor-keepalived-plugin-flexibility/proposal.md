# Change: Refactor keepalived plugin panels for flexible status, scripts, and logs

## Why
现有 keepalived 插件在多实例、脚本编辑和日志查看上不够灵活，需要覆盖多 vrrp_instance、全量脚本与日志文件的选择与查看。

## What Changes
- 状态页支持读取多个 vrrp_instance 列表并展示每个实例的 VIP 与优先级状态
- 脚本编辑页支持列出 `/www/server/keepalived/scripts` 下全部脚本并可切换编辑
- 日志页支持列出 `/www/server/keepalived/logs` 下全部日志并可切换查看

## Impact
- Affected specs: keepalived-status-panel, keepalived-script-editor, keepalived-log-panel
- Affected code: plugins/keepalived/index.py, plugins/keepalived/config_util.py, plugins/keepalived/js/keepalived.js, plugins/keepalived/index.html
