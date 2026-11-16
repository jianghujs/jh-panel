# 实施与验证记录

本记录用于确认实时数据库名单与失败反馈已经实现，并说明未执行的生产操作。

## 实现结果

数据库专属逻辑按用户补充要求留在插件：MySQL、PostgreSQL 的 `getServerDatabases`、`prepareDatabaseBackup`、`ensureBackupDatabase`、`exportDatabaseBackup` 由通用备份脚本直接调用。页面“从服务器获取”复用同一名单查询，通用脚本不再解析连接配置或构建导出命令。

共用的 `class/plugin/database_backup.py` 仅负责命令退出状态/超时回收、SQLite 事务补登记和错误脱敏。MySQL ORM 新增可选读写超时，未设置时保持原有默认行为。

## 验证结果

| 检查 | 结果 |
| --- | --- |
| `python3 -m unittest discover -s test -p test_backup_live_inventory.py` | 31 个测试通过 |
| `python3 -m unittest discover -s test -p test_mysql_apt_init_slave.py` | 11 个现有回归测试通过 |
| 6 个新增/变更 Python 文件的 `py_compile` | 通过 |
| `git diff --check` | 通过 |
| `openspec validate refresh-database-list-before-backup --strict` | 通过 |
| 已有本地数据库任务检查 | 发现 1 个仍调用通用脚本的旧 `database backupAll` 任务，无需重建，未改写任务文件 |
| 本机 `mydumper --help` | 只读核对 defaults-file、socket、port、trx-consistency-only 参数支持 |

## 规格覆盖

| 规格场景 | 验证依据 |
| --- | --- |
| 新库纳入、旧库排除、一次名单快照、单库限定目标 | live snapshot、single target、individual failure 测试 |
| 系统库过滤、异常对象/畸形结果、合法空名单 | 两插件 inventory 与 missing target 测试 |
| 非默认连接参数、特殊库名、双层 shell 引号 | MySQL export connection、PostgreSQL export quoting 测试 |
| 补登记、原字段保留、并发复用、重复记录与写入失败 | registration、transactional、concurrent 测试，使用临时 SQLite 实际事务 |
| 未安装、配置缺失、查询错误与空名单区分 | configuration、missing target 测试 |
| 超时回收、管道失败状态 | command runner 测试；实际运行无数据库的 `exit 7` 与 gzip 管道，验证非零压缩头文件不被误判成功 |
| mydumper 导出/打包失败、pg_dump 与压缩失败 | 两插件 export 错误模拟及 pipeline 测试 |
| 合法空库、不完整产物清理、登记失败保留完整文件、无覆盖发布 | orchestration、missing/zero size、publication、history insert failed 测试；合法空库使用模拟导出结果 |
| 跨引擎 ID、完整库名、模式字符、旧前缀、目录边界 | history cleanup exact identity 测试，在临时目录实际验证其他库与目录外文件保留 |
| 失败汇总、非零退出、旧双引擎失败即停止 | individual failure、actual CLI exit status、CLI scopes、task compatibility 测试 |
| UI 同步复用、加载插件无运行期写操作 | UI sync、plugin load 测试 |
| 非数据库备份不变 | non-database cleanup 测试及差异复核：网站/目录/插件配置分支不变 |

## 生效与限制

- 已有本地数据库任务通过通用脚本自动生效，不要求重建任务或重启面板。
- 名单是每个引擎查询时的快照；后建库下次纳入，后删库按导出失败反馈。
- 页面选库清单仍读本地列表，FTP 等第三方备份目标链路未改。
- 同引擎逐库尽力处理并汇总；MySQL 失败后双引擎任务停止，不继续 PostgreSQL，与既有新任务的 `set -e` 策略一致。
- 不自动删除插件旧记录；陈旧库或孤立备份文件保守保留。
- 所有文件生成/删除验证仅在临时目录进行；未连接业务数据库、未安装依赖、未执行生产备份或清理、未重启服务。
- 尚未在真实测试数据库完成导出和恢复演练，隔离测试不等价于备份可恢复性证明。
