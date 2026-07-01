## Context

rsyncd 插件（`plugins/rsyncd`）在 `index.py::makeLsyncdConf` 中为每个任务生成 `/www/server/rsyncd/send/<taskName>/cmd`。这个脚本是非实时同步的统一执行入口，覆盖手动执行（`lsyncdRun`）、定时任务执行（`tool_task.py::createBgTaskByName` 生成的 crontab）和全量执行（`lsyncdRealtimeAllRun`）。lsyncd 实时同步走 `lsyncd.conf` 里的 `sync {}` 块，不经过 `cmd`，本次不纳入范围。

任务配置位于 `/www/server/rsyncd/config.json` 的 `send.list[*]`。每个任务已有 `delete`、`realtime`、`exclude`、`conn_type` 和 rsync 参数等字段。任务添加/编辑入口是 `index.py::lsyncdAdd`，编辑弹窗回填入口是 `index.py::lsyncdGet`，前端弹窗由 `js/rsyncd.js` 渲染。

现有 `checkLsyncdTaskDryRun` 不适合作为本次基础：它把 `--dry-run` 拼到局部变量 `cmd` 后，最终却执行原始 `send/<name>/cmd` 文件，拼出来的 dry-run 命令没有真正运行。因此本次设计独立的 preflight 逻辑。

## Goals / Non-Goals

**Goals：**

- 保护非实时 rsyncd 任务执行路径，避免删除比例过高的同步真正执行。
- 使用 rsync `--dry-run --stats` 输出计算 `删除文件数 / 源端总文件数`，超过阈值时硬中止。
- 阈值按任务配置，默认 30；旧任务无需迁移，打开编辑弹窗时默认显示 30。
- 守卫主逻辑与失败邮件通知统一放在插件目录的 `tool_run.py` 中，通过 `preflight`/`notify_fail` 子命令分派；`cmd` 只通过任务名调用它，其他字段由 `tool_run.py` 自己回读 `/www/server/rsyncd/config.json`。

**Non-Goals：**

- 不保护 lsyncd 实时 `sync {}` 执行链路。
- 不修改接收端 rsyncd 模块配置。
- 不引入带宽比例、变更文件比例等其他度量，本次只按删除比例判断。
- 不接入面板级通知或外部告警，v1 只落任务日志。

## Decisions

### D1：`cmd` 内联 preflight 调用

`makeLsyncdConf` 每次保存任务都会重写 `cmd`，所以守卫入口必须由同一个生成流程管理。方案是在插件目录维护共享核心脚本 `plugins/rsyncd/tool_run.py`（参考 `tool_task.py` 的子命令分派风格），`cmd` 只写两行调用：`python3 tool_run.py preflight <task_name>`（挂载检查后、真实 rsync 前，`-f` 时跳过）和 `python3 tool_run.py notify_fail <task_name> <exit_code> <phase>`（在 `notify_rsync_failure` shell 函数里）。`tool_run.py` 会根据任务名回读 `/www/server/rsyncd/config.json`，重构 dry-run 命令、拼接失败通知原因，并调用 `mw.notifyMessage`。不再生成 `send/<name>/preflight`、`preflight.json`，也不再往 `cmd` 里嵌入 JSON 或字段列表。

`cmd` 的真实 rsync 命令前只写一行调用：

```bash
python3 /path/to/plugins/rsyncd/tool_run.py preflight <task_name>
```

`tool_run.py` 打开 `/www/server/rsyncd/config.json`，按 `name` 定位当前任务，重新构造 dry-run 命令。手动执行、定时任务、全量执行都会自动被守卫覆盖，因为它们都执行同一个 `cmd`。

备选方案一：把完整 dry-run 逻辑直接写进每个任务目录的独立脚本。否决原因是重复代码过多，后续修复解析逻辑需要重新生成所有任务。

备选方案二：额外生成 `preflight.json` 配置文件、独立 `preflight` 脚本，或把任务字段以 CLI/JSON 形式嵌入 `cmd`。按用户决策否决，任务字段以任务名为主键，全部由 `tool_run.py` 自行回读，`cmd` 保持最短。

### D2：preflight 从任务配置重新构造 dry-run 命令

`tool_run.py preflight` 不对已有 `cmd` 做字符串替换，而是根据任务名从 `/www/server/rsyncd/config.json` 加载配置，重新构造与真实同步等价的 dry-run 命令。它保留 source、target、exclude-from、password-file、SSH 端口、SSH key、bwlimit 等参数，并额外加上 `--dry-run --stats`，同时确保递归扫描开启。

这样可以避免“在 rsync 命令末尾追加参数但顺序无效”“替换路径误伤 SSH target”“最终执行的不是修改后的命令”等问题。

### D3：删除比例算法固定为 D / X

preflight 从 `--stats` 中解析：

- X：`Number of files`
- D：`Number of deleted files`

比例计算为 `D / X * 100`。当 `X == 0` 时比例按 0 处理。若 rsync 没有输出 deleted-files 行，则按 D=0 处理；若连 total-files 行都解析不到，则 preflight 非零退出并写明解析失败。

当任务 `delete=false` 时，D 会是 0，守卫自然放行。这符合本次目标，因为风险来自完全同步删除目标端文件。

### D4：每任务字段为 `max_delete_percent`，默认 30

任务配置新增可选字段 `max_delete_percent`。`lsyncdAdd` 接收并持久化该字段；`lsyncdGet` 对旧任务使用 `info.get('max_delete_percent', 30)` 回填编辑弹窗。旧任务无需批量迁移，只要重新打开编辑并保存，就会写入新字段。

字段范围建议限制为 0 到 100。值为 100 时等价于基本关闭守卫，因为删除比例不会超过 100。

### D5：目标为空不做额外探测

目标为空时 dry-run 的删除数 D=0，比例自然为 0%，因此放行。不额外执行远端 `--list-only` 或目录探测，避免增加复杂度和连接差异处理。

### D6：违反阈值时硬中止并落日志

当 `ratio > max_delete_percent` 时，preflight 写入 `send/<name>/logs/preflight_<timestamp>.log`，内容包含任务名、删除文件数、总文件数、计算比例、阈值和中止原因，然后非零退出。`cmd` 因 `|| exit $?` 直接中止，真实 rsync 不会执行。

手动执行和定时任务原本就会记录 `cmd` 输出，preflight 的失败信息也会进入既有运行日志；独立 `preflight_*.log` 用于快速定位本次中止原因。

### D7：实时同步本次不处理

lsyncd 实时同步不经过 `cmd`，如果要覆盖实时链路，需要把 lsyncd 的 rsync binary 替换为 wrapper 或改动 lsyncd 配置生成方式，复杂度明显更高。本次按用户决策只覆盖非实时路径。

## Risks / Trade-offs

- [dry-run 开销] 每次非实时同步前会多一次源端扫描。缓解：dry-run 不传输文件，只读元数据；相比误删数据，该成本可接受。
- [rsync stats 文案差异] 不同 rsync 版本的 stats 行可能略有差异。缓解：强制 `LC_ALL=C`，并对 deleted-files 缺失按 0 处理，对 total-files 缺失按解析失败中止。
- [旧任务缺字段] 旧任务不会立即写入 `max_delete_percent`。缓解：读取和生成脚本时都用默认 30 兜底；用户编辑保存后自然落盘。
- [实时同步仍无守卫] 实时任务大规模删除仍不被本次保护。缓解：这是明确的非目标；后续如需覆盖，可单独设计 lsyncd wrapper 方案。

## Migration Plan

不做数据迁移。旧任务缺少 `max_delete_percent` 时，后端读取、脚本生成和前端回填均使用默认值 30。用户重新编辑并保存旧任务后，该字段写入 `/www/server/rsyncd/config.json`。

回滚时还原插件代码即可。下一次任务保存会重新生成不含 preflight 调用与失败通知的 `cmd`。遗留的任务目录 `preflight` 文件即便存在，只要 `cmd` 不再调用它就不会生效；共享的 `plugins/rsyncd/tool_run.py` 也可一并删除。

## Open Questions

无。已确认的决策如下：

- 口径：删除比例。
- 默认阈值：30，可在添加/编辑任务时设置。
- 目标为空：放行。
- 超阈值：硬中止。
- 实时同步：本次不处理。
