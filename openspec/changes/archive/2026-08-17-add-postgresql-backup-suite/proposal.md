## Why

PostgreSQL 插件此前只有半成品的单库备份入口：`pgBack()` 用 `pg_dump` 导出但存到独立目录、`importDbBackup()` 恢复命令残留 MySQL 命令、`scripts/backup.py` 缺失导致计划任务 `setDbBackup()` 空转。MySQL 插件新备份用 `db_` 前缀和 PostgreSQL 冲突。用户需要一个和 MySQL 插件体验对等的 PostgreSQL 备份方案：单库逻辑备份、可恢复、可在计划任务中选择。

## What Changes

- 统一 PostgreSQL 单库备份输出到 `/www/backup/database`，文件名前缀 `postgres_<db>_<timestamp>.sql.gz`，与 MySQL 的 `mysql_` / 旧 `db_` 前缀隔离
- 修复 PostgreSQL `importDbBackup()` 恢复命令：用 `psql` 而非 `mysql`，从正确的文件路径恢复
- PostgreSQL 备份列表、删除、恢复统一从 `/www/backup/database` 读取，废弃旧的 `/www/backup/pg/upload` 路径
- 备份命令加 `pipefail` 和空文件清理，避免 `pg_dump` 失败时留下损坏的 gzip 文件
- MySQL 备份文件名前缀改为 `mysql_<db>_<timestamp>`，列表匹配同时兼容旧 `db_` 前缀
- 计划任务"备份数据库"下拉同时展示 MySQL 和 PostgreSQL 数据库，任务保存为 `mysql:<db>` / `postgresql:<db>` 前缀分流
- 计划任务后端 `getShell()` 按 `postgresql:` 前缀分流到 `scripts/backup.py pg_database`，统一由通用脚本备份、记录和清理
- 前端按数据库类型控制备份方式下拉：MySQL 显示 `mysqldump/mydumper`，PostgreSQL 隐藏

## Capabilities

### New Capabilities
- `postgresql-backup`: PostgreSQL 单库逻辑备份的备份、列表、恢复、删除，以及计划任务集成

### Modified Capabilities

## Impact

- `plugins/postgresql/index.py` — `pgBack()`, `pgBackList()`, `importDbBackup()`, `deleteDbBackup()`, `getDbBackupListFunc()`
- `plugins/mysql-apt/index.py` — `getDbBackupListFunc()`, `getDbListPage()` 前缀匹配
- `plugins/mysql-apt/scripts/backup.py` — 文件名前缀
- `scripts/backup.py` — MySQL 备份文件名前缀、PostgreSQL `pg_database` 入口
- `class/core/crontab_api.py` — `getDataListApi()`, `getShell()` 数据库分流
- `route/static/app/crontab.js` — 数据库下拉渲染、备份方式切换、编辑回显
