## 1. PostgreSQL 单库备份核心

- [x] 1.1 新增 `getDatabaseBackupDir()` helper，返回 `/www/backup/database` 并确保目录存在
- [x] 1.2 修改 `pgBack()`：备份输出到 `/www/backup/database`，文件名前缀 `postgres_<db>_<timestamp>.sql.gz`
- [x] 1.3 修改 `pgBack()`：用 `bash -lc` + `set -o pipefail` 包裹 `pg_dump | gzip` 命令
- [x] 1.4 修改 `pgBack()`：备份失败时清理空文件并返回失败，成功时写入 `backup` 表

## 2. PostgreSQL 备份列表与恢复

- [x] 2.1 修改 `getDbBackupListFunc()`：从 `/www/backup/database` 读取，匹配 `postgres_<db>_` 前缀，按修改时间倒序
- [x] 2.2 修改 `pgBackList()`：从 `/www/backup/database` 读取列表
- [x] 2.3 修改 `importDbBackup()`：用 `psql` 而非 `mysql` 恢复，从正确文件路径读取
- [x] 2.4 修改 `deleteDbBackup()`：从 `/www/backup/database` 删除文件

## 3. MySQL 备份文件名前缀迁移

- [x] 3.1 修改 `scripts/backup.py`：MySQL 备份文件名前缀 `db_` 改为 `mysql_`
- [x] 3.2 修改 `plugins/mysql-apt/scripts/backup.py`：文件名前缀同步改为 `mysql_`
- [x] 3.3 修改 `plugins/mysql-apt/index.py` `getDbBackupListFunc()`：同时匹配 `mysql_<db>_` 和 `db_<db>_`
- [x] 3.4 修改 `plugins/mysql-apt/index.py` `getDbListPage()`：`is_backup` 判断兼容新旧前缀

## 4. 计划任务后端分流

- [x] 4.1 新增 `getDatabaseDataList()`：读取 MySQL 和 PostgreSQL 数据库列表，返回带 `db_type` 的项
- [x] 4.2 修改 `getDataListApi()`：`stype=databases` 时调用 `getDatabaseDataList()`
- [x] 4.3 新增 `parseDatabaseSname()`：解析 `mysql:` / `postgresql:` 前缀，旧值默认 MySQL
- [x] 4.4 新增 `getDatabaseBackupShell()`：按类型分流，PostgreSQL 调用 `scripts/backup.py pg_database`
- [x] 4.5 修改 `getShell()`：`stype=database` 时调用 `getDatabaseBackupShell()`

## 5. 计划任务前端适配

- [x] 5.1 新增前端 helper：`getBackupItemLabel` / `getBackupItemDisplayName` / `toggleDumpTypeByDatabaseValue` / `escapeHtml`
- [x] 5.2 修改新增任务弹窗：数据库下拉项展示类型标签和 `raw_name`，任务名用 `raw_name`
- [x] 5.3 修改新增任务弹窗：备份方式下拉用 `.dump-type` 包裹，按数据库类型显隐
- [x] 5.4 修改新增任务弹窗：选择数据库项时按类型切换备份方式，任务名同步 `raw_name`
- [x] 5.5 修改保存逻辑：PostgreSQL 任务 `dumpType` 为空
- [x] 5.6 修改编辑弹窗：兼容旧 `sname=<db>` 选中 MySQL 项，PostgreSQL 隐藏备份方式

## 6. 验证

- [x] 6.1 `python3 -m py_compile` 检查所有改动文件
- [x] 6.2 `node --check` 检查 `crontab.js` 语法
- [x] 6.3 验证 `getDatabaseDataList()` 同时返回 MySQL 和 PostgreSQL 数据库
- [x] 6.4 验证 `getDatabaseBackupShell()` 对 MySQL / PostgreSQL / 旧任务分别生成正确脚本
- [x] 6.5 验证前缀匹配：`mysql_<db>_` 和 `db_<db>_` 不误匹配同名前缀数据库
- [x] 6.6 面板重启后功能正常
