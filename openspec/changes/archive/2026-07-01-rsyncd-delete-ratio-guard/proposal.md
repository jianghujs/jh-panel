## Why

rsync 完全同步模式（`--delete`）在源目录与目标目录发生非预期漂移，或路径配置错误时，可能会一次性删除目标端大量数据。当前 rsyncd 插件的非实时同步链路没有任何前置安全检查，一次误操作就可能造成数据丢失。需要在真正执行同步前先评估“会删除多少”，超过阈值就直接中止。

## What Changes

- 为 rsyncd 插件的非实时同步任务增加“删除比例”前置守卫。
- 每次执行真正的 rsync 命令前，先跑一次 dry-run 并解析 `--stats` 输出，计算 `删除文件数 / 源端总文件数`。
- 当删除比例大于任务配置的阈值时，硬中止本次同步，不执行真正的 rsync。
- 在“添加/编辑同步任务”弹窗中新增可编辑字段“删除比例超过百分之多少则终止同步”，默认值 30。
- 兼容旧任务：旧任务缺少该字段时，打开编辑弹窗默认显示 30，保存后字段落入 `config.json`，无需数据迁移。
- 目标目录为空时天然放行（dry-run 得到删除数为 0）。
- 本次不改动 lsyncd 实时同步（`sync {}`）的行为。

## Capabilities

### New Capabilities
- `rsyncd-delete-ratio-guard`：覆盖非实时 rsyncd 同步任务的“dry-run 删除比例评估 + 超阈值硬中止”能力。

### Modified Capabilities
- 无。

## Impact

- 后端受影响：`/www/server/jh-panel/plugins/rsyncd/index.py` 中的命令生成、任务添加/编辑/读取逻辑，以及 `/www/server/rsyncd/send/<task>/` 下生成的文件。
- 前端受影响：`/www/server/jh-panel/plugins/rsyncd/js/rsyncd.js` 的添加/编辑任务弹窗与请求体。
- 执行路径受影响：手动执行、定时任务执行、全量执行——这三条路径都会跑生成的 `send/<name>/cmd` 脚本。
- 不受影响：lsyncd 实时 `sync {}` 执行链路。
- 无新增外部依赖。
