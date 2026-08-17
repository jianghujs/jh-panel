## ADDED Requirements

### Requirement: 主备关联插件入口
江湖面板 SHALL 提供 `ha_manager` 插件，用于管理两台服务器之间的主备关系、SSH 互信和状态检查。

#### Scenario: 插件安装信息
- **WHEN** 系统加载插件列表
- **THEN** `ha_manager` SHALL 以“主备管理”插件展示，并使用 `/www/server/ha_manager/` 作为运行数据目录。

#### Scenario: 插件页面入口
- **WHEN** 用户打开 `ha_manager` 插件窗口
- **THEN** 页面 SHALL 提供关系配置、连接状态、自检结果和状态输出相关操作入口。

### Requirement: 主备关系配置
`ha_manager` SHALL 保存单组两机主备关系配置，并把配置写入 `/www/server/ha_manager/config.json`。

#### Scenario: 保存主备关系
- **WHEN** 用户提交 `relation_id`、`peer_ip`、`ssh_user`、`ssh_port`、`peer_ssh_public_key` 和 `configured_role`
- **THEN** 插件 SHALL 校验必填字段和角色值，并把配置保存到 `/www/server/ha_manager/config.json`。

#### Scenario: 读取主备关系
- **WHEN** 用户进入插件页面或点击刷新
- **THEN** 插件 SHALL 返回当前保存的主备关系配置；未配置时 SHALL 返回空配置和 `pending` 连接状态。

#### Scenario: 配置角色限制
- **WHEN** 用户保存 `configured_role`
- **THEN** 插件 MUST 只接受 `primary` 或 `standby`，其它值 SHALL 返回明确错误且不写入配置文件。

### Requirement: SSH 密钥与授权
`ha_manager` SHALL 自主管理主备探测使用的 SSH 密钥，并支持把对端公钥写入本机授权文件。

#### Scenario: 生成本机密钥
- **WHEN** 插件需要展示本机 SSH 公钥且 `/root/.ssh/ha_manager.pub` 不存在
- **THEN** 插件 SHALL 生成 `/root/.ssh/ha_manager` 和 `/root/.ssh/ha_manager.pub`，私钥权限 MUST 为 `0600`。

#### Scenario: 展示本机公钥
- **WHEN** 用户打开关系配置页面
- **THEN** 插件 SHALL 展示 `/root/.ssh/ha_manager.pub` 的内容，供用户复制到对端插件。

#### Scenario: 授权对端公钥
- **WHEN** 用户保存包含 `peer_ssh_public_key` 的配置
- **THEN** 插件 SHALL 将该公钥追加到 `/root/.ssh/authorized_keys`，且 MUST 避免重复写入同一公钥。

### Requirement: 对端连接测试
`ha_manager` SHALL 通过 SSH 测试对端插件是否可访问，并记录连接状态。

#### Scenario: 对端连接成功
- **WHEN** 用户点击测试连接且 SSH 到 `peer_ip` 成功执行 `python3 /www/server/jh-panel/plugins/ha_manager/index.py get_status --local-only`
- **THEN** 插件 SHALL 将连接状态更新为 `connected`，并保存最近一次对端状态摘要。

#### Scenario: 对端 SSH 失败
- **WHEN** SSH 连接超时或认证失败
- **THEN** 插件 SHALL 将连接状态分别记录为 `ssh_timeout` 或 `ssh_auth_failed`，并保存失败原因和检查时间。

#### Scenario: 对端插件缺失
- **WHEN** SSH 成功但对端命令不存在或返回无法解析的插件缺失错误
- **THEN** 插件 SHALL 将连接状态记录为 `peer_plugin_missing`。

#### Scenario: 关系 ID 不一致
- **WHEN** 对端返回的 `relation_id` 与本机配置不一致
- **THEN** 插件 SHALL 将连接状态记录为 `relation_id_mismatch`。

### Requirement: 主备状态输出
`ha_manager` SHALL 提供结构化状态输出，供页面、自检和后续云监控采集复用。

#### Scenario: 输出完整状态
- **WHEN** 执行 `python3 /www/server/jh-panel/plugins/ha_manager/index.py get_status`
- **THEN** 插件 SHALL 输出包含 `relation_id`、`local_ip`、`configured_role`、`actual_role`、`switch_state`、`peer`、`checks`、`summary_status` 和 `summary_msg` 的 JSON。

#### Scenario: 输出本机状态
- **WHEN** 执行 `get_status --local-only`
- **THEN** 插件 SHALL 只执行本机检查，不再 SSH 到对端，避免两端互相递归调用。

#### Scenario: 未配置状态
- **WHEN** 尚未保存主备关系配置
- **THEN** 插件 SHALL 返回 `summary_status=warning`，并在检查项中说明 `ha_config_missing`。

### Requirement: mysql-apt 状态检查
首版 `ha_manager` SHALL 只支持 `mysql-apt` 插件的 MySQL 状态读取和主备角色判断。

#### Scenario: mysql-apt 存在时检查
- **WHEN** `/www/server/jh-panel/plugins/mysql-apt/index.py` 存在
- **THEN** 插件 SHALL 调用 `python3 plugins/mysql-apt/index.py get_master_status` 读取复制状态，并把结果纳入检查项。

#### Scenario: mysql-apt 不存在
- **WHEN** `mysql-apt` 插件不存在
- **THEN** 插件 SHALL 将 MySQL 检查项标记为 `warning`，原因 SHALL 为 `mysql_apt_missing`。

#### Scenario: 角色与 MySQL 状态不一致
- **WHEN** `configured_role=primary` 但 MySQL 处于只读或从库状态，或 `configured_role=standby` 但 MySQL 被判断为可写主库
- **THEN** 插件 SHALL 输出 `role_mismatch` 或对应 MySQL 异常原因，并将 `summary_status` 至少标记为 `warning`。

### Requirement: 一主一备检查
`ha_manager` SHALL 综合本机和对端状态判断两台服务器是否满足一主一备关系。

#### Scenario: 一主一备正常
- **WHEN** 本机和对端 `relation_id` 相同，且两端角色分别为一个 `primary` 和一个 `standby`
- **THEN** 插件 SHALL 将一主一备检查项标记为 `normal`。

#### Scenario: 角色冲突
- **WHEN** 本机和对端同时为 `primary` 或同时为 `standby`
- **THEN** 插件 SHALL 输出 `ha_role_conflict`，并将 `summary_status` 标记为 `error`。

#### Scenario: 对端切换中
- **WHEN** 对端返回 `switch_state=switching`
- **THEN** 插件 SHALL 展示切换中状态；若切换持续超过 1 小时，检查项 SHALL 输出 `switching_timeout`。

### Requirement: 切换状态写入
`ha_manager` SHALL 提供 `switch_role` 命令，供切换脚本统一写入角色和切换状态。

#### Scenario: 开始切换
- **WHEN** 执行 `python3 /www/server/jh-panel/plugins/ha_manager/index.py switch_role switching`
- **THEN** 插件 SHALL 写入 `switch_state=switching` 和 `switch_started_at`。

#### Scenario: 切换成功
- **WHEN** 执行 `switch_role primary` 或 `switch_role standby`
- **THEN** 插件 SHALL 更新 `configured_role` 为目标角色，并写入 `switch_state=normal`。

#### Scenario: 切换失败
- **WHEN** 执行 `switch_role failed`
- **THEN** 插件 SHALL 写入 `switch_state=failed`、失败时间和最近一次失败摘要。

#### Scenario: 非法切换参数
- **WHEN** `switch_role` 收到非 `switching/primary/standby/failed` 的参数
- **THEN** 插件 MUST 返回错误且不修改配置文件。
