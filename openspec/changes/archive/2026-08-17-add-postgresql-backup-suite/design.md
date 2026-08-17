## Context

江湖面板的数据库备份目前以 MySQL 为核心。MySQL 插件通过 `scripts/backup.py database <name>` 执行单库逻辑备份，输出到 `/www/backup/database`，文件名前缀 `db_`。计划任务页面通过 `crontab_api.getDataListApi()` 获取数据库列表，通过 `getShell()` 生成备份脚本。

PostgreSQL 插件虽有 `pgBack()` / `pgBackList()` / `importDbBackup()` 入口，但存在多个缺陷：
- 备份输出到 `/www/backup/pg/upload`，与 MySQL 备份目录不统一
- `importDbBackup()` 恢复命令残留 `mysql` 而非 `psql`
- `setDbBackup()` 引用的 `scripts/backup.py` 不存在
- 计划任务数据库列表只读 MySQL，无法选择 PostgreSQL 数据库

此外，MySQL 和 PostgreSQL 备份文件共用 `db_` 前缀会导致列表混淆。

## Goals / Non-Goals

**Goals:**
- PostgreSQL 单库备份输出到统一目录 `/www/backup/database`，文件名前缀 `postgres_`
- MySQL 新备份文件名前缀改为 `mysql_`，列表兼容旧 `db_` 前缀
- PostgreSQL 备份可通过面板 UI 和计划任务执行、查看、恢复、删除
- 计划任务数据库下拉同时展示 MySQL 和 PostgreSQL 数据库
- 备份失败时不留损坏文件

**Non-Goals:**
- 单表备份（`pg_dump -t`）— 留待后续阶段
- 整实例物理备份（`pg_basebackup`）— 留待后续阶段
- PITR / WAL 归档 — 留待后续阶段
- `pg_dump -Fc` custom format — 当前用 plain SQL + gzip，保持和 MySQL 备份体验一致

## Decisions

**D1: 文件名前缀按数据库类型区分**

MySQL 新备份用 `mysql_<db>_<timestamp>`，PostgreSQL 用 `postgres_<db>_<timestamp>`。旧 MySQL 备份 `db_` 前缀在列表匹配时兼容。

理由：共用前缀会导致 PostgreSQL 列表误匹配 MySQL 备份文件。前缀带尾随下划线 `mysql_<db>_` 避免同名前缀数据库（如 `app` 匹配 `app2`）误判。

**D2: 计划任务 sname 带来源前缀**

任务保存时 `sname` 字段值为 `mysql:<db>` 或 `postgresql:<db>`。后端 `getShell()` 解析前缀分流。旧任务 `sname=<db>` 默认按 MySQL 处理，无需迁移。

理由：不改 `crontab` 表结构，不改 `sname` 语义，只在值里编码来源。向后兼容。

**D3: PostgreSQL 备份命令用 `bash -lc` + `pipefail`**

`pg_dump | gzip` 管道在默认 `/bin/sh` 下不支持 `pipefail`。用 `bash -lc` 包裹整条命令，确保 `pg_dump` 失败时能检测到。

理由：`mw.execShell` 用 Python `subprocess.Popen(shell=True)`，默认 shell 是 `/bin/sh`（dash），不支持 `pipefail`。

**D4: PostgreSQL 备份统一走 `scripts/backup.py pg_database`**

PostgreSQL 手动备份和计划任务都调用 `scripts/backup.py pg_database <db> <save>`。插件 `pgBack()` 只作为 UI 入口转调通用脚本；计划任务 `getDatabaseBackupShell()` 对 `postgresql:` 前缀生成同样的通用脚本命令。

理由：这样 MySQL 和 PostgreSQL 的备份入口形态一致，均由通用脚本负责备份、写入 `backup` 表、按 `cleanBackupByHistory()` 清理历史记录。插件层只负责 UI/API 转调，避免计划任务和手动备份逻辑分叉。

**D5: 前端备份方式下拉按数据库类型控制**

MySQL 显示 `mysqldump/mydumper`，PostgreSQL 隐藏。

理由：PostgreSQL 当前只走 `pg_dump`，没有多备份方式选择。隐藏而非禁用，减少界面噪音。

## Risks / Trade-offs

- [旧 MySQL 计划任务的 `sname` 不带前缀] → 后端 `parseDatabaseSname()` 默认按 MySQL 处理，向前兼容
- [PostgreSQL 备份和 MySQL 备份在同一目录] → 文件名前缀隔离，列表匹配按前缀过滤
- [`bash -lc` 在某些精简系统可能不可用] → 面板本身依赖 bash，风险低
- [PostgreSQL 计划任务没有完整跨类型 `backupAll` 支持] → 当前旧 `ALL` 仍默认按 MySQL 处理，后续需在 UI 屏蔽或引入明确的 `postgresql:ALL`
