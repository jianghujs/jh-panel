## ADDED Requirements

### Requirement: 非实时同步必须在真实 rsync 前执行删除比例 preflight
系统 SHALL 在任何非实时任务执行真实 rsync 前，先运行带有 `--dry-run --stats` 的 rsync dry-run，并计算删除比例 `删除文件数 / 总文件数 * 100`。当计算出的删除比例大于任务配置的 `max_delete_percent` 时，系统 SHALL NOT 执行真实 rsync。

#### Scenario: 删除比例低于阈值时允许同步
- **WHEN** 一个非实时任务的 `max_delete_percent` 为 30，且 dry-run 报告总文件数 100、删除文件数 10（比例 10%）
- **THEN** 系统 SHALL 执行真实 rsync 命令

#### Scenario: 删除比例高于阈值时中止同步
- **WHEN** 一个非实时任务的 `max_delete_percent` 为 30，且 dry-run 报告总文件数 100、删除文件数 50（比例 50%）
- **THEN** 系统 SHALL NOT 执行真实 rsync 命令，并 SHALL 以非零状态退出

#### Scenario: 非删除同步自然放行
- **WHEN** 任务的 `delete` 配置为 `false`
- **THEN** dry-run 的删除文件数 SHALL 为 0，删除比例 SHALL 为 0%，系统 SHALL 执行真实 rsync 命令

#### Scenario: 目标为空时放行
- **WHEN** 目标目录为空，且 dry-run 报告删除文件数为 0
- **THEN** 删除比例 SHALL 为 0%，系统 SHALL 执行真实 rsync 命令

### Requirement: 每个任务必须有可编辑的最大删除比例配置
系统 SHALL 为每个同步任务存储 `max_delete_percent` 字段。添加和编辑任务弹窗 SHALL 展示该字段的可编辑输入框，默认值为 30。缺少该字段的旧任务 SHALL 在打开编辑弹窗时显示 30，并在下一次保存后持久化该字段。

#### Scenario: 新建任务默认阈值为 30
- **WHEN** 用户打开添加任务弹窗
- **THEN** 最大删除比例输入框 SHALL 显示 30

#### Scenario: 旧任务编辑时默认显示 30
- **WHEN** 用户打开一个不包含 `max_delete_percent` 字段的旧任务进行编辑
- **THEN** 编辑弹窗中的最大删除比例输入框 SHALL 显示 30

#### Scenario: 保存任务时持久化阈值
- **WHEN** 用户将最大删除比例设置为 20 并保存任务
- **THEN** 该任务在 `config.json` 中 SHALL 包含值为 20 的 `max_delete_percent` 字段

#### Scenario: 阈值为 100 时等价于关闭守卫
- **WHEN** 任务的 `max_delete_percent` 设置为 100，且 dry-run 报告的删除比例不超过 100%
- **THEN** 系统 SHALL 执行真实 rsync 命令

### Requirement: preflight 中止必须写入任务日志目录
当 preflight 因删除比例超阈值而中止同步时，系统 SHALL 在 `send/<name>/logs/preflight_<timestamp>.log` 写入带时间戳的日志，记录计算比例、阈值和中止原因。由于 `cmd` 会非零退出，该中止也 SHALL 能在既有运行日志中看到。

#### Scenario: 中止同步时写入 preflight 日志
- **WHEN** preflight 因删除比例超过阈值而中止同步
- **THEN** `send/<name>/logs/` 下 SHALL 存在名为 `preflight_<timestamp>.log` 的文件，且内容 SHALL 包含比例、阈值和中止原因

#### Scenario: 允许同步时不写中止日志
- **WHEN** preflight 因删除比例低于或等于阈值而放行
- **THEN** 本次运行 SHALL NOT 写入表示中止的 `preflight_<timestamp>.log`

### Requirement: 实时 lsyncd 同步不得被本次守卫影响
删除比例 preflight SHALL 只应用于执行生成脚本 `send/<name>/cmd` 的路径。lsyncd 实时 `sync {}` 执行 SHALL 继续保持原行为，不运行 preflight。

#### Scenario: 实时同步不受影响
- **WHEN** 一个 `realtime` 为 `true` 的任务触发 lsyncd 实时 rsync 事件
- **THEN** 系统 SHALL NOT 运行 preflight dry-run，rsync SHALL 继续由 lsyncd 直接执行
