## ADDED Requirements

### Requirement: 主从页面显示半同步开关
`masterOrSlaveConf` 页必须（SHALL）展示 MySQL 半同步复制是否启用，并提供可直接切换状态的控件。

#### Scenario: 渲染开关状态
- **WHEN** 用户打开主从配置页
- **THEN** 前端必须向后端请求半同步状态，并渲染带标签的开关及状态文字。

#### Scenario: 切换前确认
- **WHEN** 用户在 MySQL 运行中点击开关
- **THEN** UI 必须弹出确认提示，阻止重复点击，在操作执行后或出错时刷新主从配置状态。

### Requirement: 半同步配置管理
后端必须（MUST）确保 `my.cnf` 中包含（或移除）约定的指令，并在半同步状态变化时重启 MySQL。

#### Scenario: 启用时写入配置
- **WHEN** 用户启用半同步
- **THEN** 后端必须在 `[mysqld]` 段新增缺失的 `plugin-load-add = semisync_master.so`、`plugin-load-add = semisync_slave.so`、`rpl-semi-sync-master-timeout = 5000`、`rpl-semi-sync-master-wait-no-slave = ON`、`rpl-semi-sync-master-wait-point = AFTER_SYNC`，并在重启成功后才返回成功。

#### Scenario: 禁用时移除配置
- **WHEN** 用户禁用半同步
- **THEN** 后端必须从 `my.cnf` 移除上述指令，重启 MySQL，并在出现文件或重启失败时向 UI 返回错误。

### Requirement: 半同步角色绑定
半同步能力必须（MUST）在启用后自动保持主/从运行时变量与角色一致，避免额外的手动步骤。

#### Scenario: 启用后自动应用主角色
- **WHEN** 用户开启半同步开关
- **THEN** 后端必须在配置写入并重启成功后自动执行 `SET GLOBAL rpl_semi_sync_master_enabled = 1;` 与 `SET GLOBAL rpl_semi_sync_slave_enabled = 0;`。

#### Scenario: 从节点初始化 SQL
- **WHEN** 操作员在启用半同步后执行从节点初始化
- **THEN** 后端必须依次执行 `SET GLOBAL rpl_semi_sync_master_enabled = 0;` 和 `SET GLOBAL rpl_semi_sync_slave_enabled = 1;` 再返回成功。
