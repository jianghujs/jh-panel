# keepalived-script-editor Specification

## Purpose
TBD - created by archiving change refactor-keepalived-plugin-flexibility. Update Purpose after archive.
## Requirements
### Requirement: Keepalived 脚本编辑面板
Keepalived 插件 SHALL 提供“脚本编辑”标签页，列出 `/www/server/keepalived/scripts` 下全部脚本文件，允许选择并编辑保存。

#### Scenario: 脚本列表展示
- **当** 用户进入“脚本编辑”标签页或点击刷新
- **则** 后端扫描 `/www/server/keepalived/scripts` 下的脚本文件列表并返回，前端按文件名展示选项，同时显示当前脚本路径。

#### Scenario: 脚本内容读取
- **当** 用户选择某个脚本
- **则** 前端读取脚本内容并展示在编辑器中，脚本不存在时提示错误并清空编辑器。

#### Scenario: 脚本保存
- **当** 用户保存脚本内容
- **则** 后端将内容写回所选脚本路径并返回保存结果。

