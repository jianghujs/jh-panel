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
- **THEN** 后端必须在 `[mysqld]` 段新增缺失的 `plugin-load-add = semisync_master.so`、`plugin-load-add = semisync_slave.so`、`rpl-semi-sync-master-timeout = 5000`、`rpl-semi-sync-master-wait-no-slave = ON`、`rpl-semi-sync-master-wait-point = AFTER_SYNC`、`rpl_semi_sync_master_enabled = 1`、`rpl_semi_sync_slave_enabled = 1`，并在重启成功后才返回成功。

#### Scenario: 禁用时移除配置
- **WHEN** 用户禁用半同步
- **THEN** 后端必须从 `my.cnf` 移除上述指令，重启 MySQL，并在出现文件或重启失败时向 UI 返回错误。

### Requirement: 半同步运行变量
半同步能力必须（MUST）通过配置项确保 `rpl_semi_sync_master_enabled` 与 `rpl_semi_sync_slave_enabled` 始终与开关状态一致。

#### Scenario: 启用后运行变量可用
- **WHEN** 用户开启半同步开关
- **THEN** 配置文件中必须包含 `rpl_semi_sync_master_enabled = 1` 与 `rpl_semi_sync_slave_enabled = 1`，使 MySQL 在启动/重启后主、从运行变量均为开启状态，无需额外 SQL。

#### Scenario: 禁用后运行变量关闭
- **WHEN** 用户关闭半同步开关
- **THEN** 配置文件必须移除 `rpl_semi_sync_master_enabled` 与 `rpl_semi_sync_slave_enabled`，确保服务重启后两个变量恢复为关闭状态。
