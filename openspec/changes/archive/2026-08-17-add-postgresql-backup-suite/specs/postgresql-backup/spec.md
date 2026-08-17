## ADDED Requirements

### Requirement: PostgreSQL 单库备份

系统 SHALL 允许用户通过面板 UI 对 PostgreSQL 单个数据库执行逻辑备份，使用 `pg_dump` 导出为 gzip 压缩的 SQL 文件。

#### Scenario: 手动备份单个 PostgreSQL 数据库
- **WHEN** 用户在 PostgreSQL 数据库列表中点击"备份"
- **THEN** 系统执行 `pg_dump -c <db> -p <port>` 并 gzip 压缩，输出文件为 `/www/backup/database/postgres_<db>_<timestamp>.sql.gz`
- **AND** 备份成功后在面板 `backup` 表中记录文件名、路径、大小、时间
- **AND** 返回成功提示

#### Scenario: 备份失败时不留损坏文件
- **WHEN** `pg_dump` 执行失败（如数据库不存在、连接失败）
- **THEN** 系统不创建空 gzip 文件，返回失败提示

### Requirement: PostgreSQL 备份文件名前缀

系统 SHALL 将 PostgreSQL 备份文件名前缀设为 `postgres_<dbname>_`，与 MySQL 的 `mysql_` / 旧 `db_` 前缀隔离。

#### Scenario: 文件名格式
- **WHEN** 备份数据库 `mydb`
- **THEN** 文件名匹配 `postgres_mydb_YYYYmmdd_HHMMSS.sql.gz`

### Requirement: PostgreSQL 备份列表

系统 SHALL 允许用户查看指定 PostgreSQL 数据库的备份历史列表。

#### Scenario: 查看备份列表
- **WHEN** 用户查看数据库 `mydb` 的备份详情
- **THEN** 系统从 `/www/backup/database` 目录列出所有以 `postgres_mydb_` 开头的文件
- **AND** 列表按修改时间倒序排列
- **AND** 每条记录包含文件名、大小、备份时间、文件路径

### Requirement: PostgreSQL 备份恢复

系统 SHALL 允许用户从备份文件恢复 PostgreSQL 数据库，使用 `psql` 而非 `mysql`。

#### Scenario: 从备份恢复
- **WHEN** 用户点击某备份文件的"导入"
- **THEN** 系统从 `/www/backup/database/<file>` 读取文件，gunzip 解压后通过 `psql -d <db> -p <port>` 恢复
- **AND** 使用 `su - postgres -c` 切换用户执行

### Requirement: PostgreSQL 备份删除

系统 SHALL 允许用户删除 PostgreSQL 备份文件。

#### Scenario: 删除备份
- **WHEN** 用户点击某备份文件的"删除"
- **THEN** 系统从 `/www/backup/database/` 删除该文件

### Requirement: 计划任务数据库列表包含 PostgreSQL

系统 SHALL 在计划任务"备份数据库"的数据库下拉中同时展示 MySQL 和 PostgreSQL 数据库。

#### Scenario: 获取数据库列表
- **WHEN** 用户在计划任务页面选择"备份数据库"
- **THEN** 下拉列表展示所有 MySQL 数据库（前缀 `mysql:`）和 PostgreSQL 数据库（前缀 `postgresql:`）
- **AND** 每项显示类型标签，如 `[MySQL] dbname[备注]` 或 `[PostgreSQL] dbname[备注]`

### Requirement: 计划任务按数据库类型分流备份脚本

系统 SHALL 根据计划任务 `sname` 的来源前缀生成不同的备份脚本。

#### Scenario: MySQL 计划任务
- **WHEN** 任务 `sname` 为 `mysql:<db>` 或不带前缀（旧任务兼容）
- **THEN** 生成的脚本调用 `scripts/backup.py database <db>` 执行 MySQL 备份

#### Scenario: PostgreSQL 计划任务
- **WHEN** 任务 `sname` 为 `postgresql:<db>`
- **THEN** 生成的脚本调用 `scripts/backup.py pg_database <db> <save>` 执行 PostgreSQL 备份
- **AND** 通用脚本写入 `backup` 表并按保留规则清理该数据库历史备份

### Requirement: 计划任务前端按数据库类型控制备份方式

系统 SHALL 在计划任务页面根据所选数据库类型控制备份方式下拉的显示。

#### Scenario: 选择 MySQL 数据库
- **WHEN** 用户选择一个 MySQL 数据库
- **THEN** 显示备份方式下拉（mysqldump / mydumper）

#### Scenario: 选择 PostgreSQL 数据库
- **WHEN** 用户选择一个 PostgreSQL 数据库
- **THEN** 隐藏备份方式下拉

### Requirement: MySQL 备份文件名前缀迁移

系统 SHALL 将 MySQL 新备份文件名前缀从 `db_` 改为 `mysql_`，同时兼容旧 `db_` 前缀的备份文件恢复。

#### Scenario: 新备份文件名
- **WHEN** 执行 MySQL 单库备份
- **THEN** 文件名前缀为 `mysql_<db>_<timestamp>`

#### Scenario: 旧备份文件兼容
- **WHEN** 备份列表中存在旧 `db_<db>_<timestamp>` 文件
- **THEN** 列表和恢复功能仍能识别并处理这些文件
- **AND** 新备份不再使用 `db_` 前缀
