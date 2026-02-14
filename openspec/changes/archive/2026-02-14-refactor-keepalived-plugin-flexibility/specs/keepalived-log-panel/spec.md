## ADDED Requirements
### Requirement: Keepalived 日志面板
Keepalived 插件 SHALL 提供“日志”标签页，列出 `/www/server/keepalived/logs` 目录下全部日志文件，并支持切换查看文件内容。

#### Scenario: 日志列表展示
- **当** 用户进入“日志”标签页或点击刷新
- **则** 后端返回 `/www/server/keepalived/logs` 下的日志文件列表，前端显示可切换的文件选择项。

#### Scenario: 日志内容切换
- **当** 用户选择不同日志文件
- **则** 前端读取该日志的最近内容并展示，读取失败时提示错误。
