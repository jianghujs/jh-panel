## 1. 后端配置与参数

- [x] 1.1 在 `plugins/rsyncd/index.py::lsyncdGet` 中为默认 `info` 增加 `max_delete_percent: 30`，并确保旧任务缺少该字段时返回默认值 30
- [x] 1.2 在 `plugins/rsyncd/index.py::lsyncdAdd` 中接收 `max_delete_percent`，校验为 0 到 100 的整数；缺失或非法时使用默认值 30，并保存到任务 `info` 中

## 2. preflight 脚本生成

- [x] 2.1 新增共享脚本 `plugins/rsyncd/tool_run.py`，通过 `preflight`/`notify_fail` 子命令承载 dry-run、stats 解析、删除比例计算、中止日志写入以及失败邮件通知等核心逻辑
- [x] 2.2 在 `plugins/rsyncd/index.py::makeLsyncdConf` 中把 preflight/通知的调用简化为 `python3 tool_run.py preflight <task_name>` 和 `python3 tool_run.py notify_fail <task_name> <exit_code> <phase>` 两行；任务字段由 `tool_run.py` 自行从 `/www/server/rsyncd/config.json` 加载，不生成独立的 `send/<name>/preflight` 或 `preflight.json`，`cmd` 内也不再嵌入 JSON
- [x] 2.3 `tool_run.py preflight` 根据任务名从 `/www/server/rsyncd/config.json` 加载配置，构造 dry-run 命令时必须保留真实同步的 source、target、exclude-from、password-file、SSH 参数和 bwlimit，并额外包含 `--dry-run --stats`，同时确保递归扫描开启
- [x] 2.4 解析 `--stats` 输出中的总文件数 X 与删除文件数 D；删除文件数缺失时按 0 处理，总文件数缺失时写明解析失败并非零退出
- [x] 2.5 计算 `D / X * 100`；当 X 为 0 时比例按 0 处理；当比例大于 `max_delete_percent` 时，写入 `send/<name>/logs/preflight_<timestamp>.log` 并非零退出，否则正常退出
- [x] 2.6 在生成的 `send/<name>/cmd` 中，把 `python3 tool_run.py preflight <task_name>` 内联到挂载检查之后、真实 rsync 命令之前，并支持 `-f` 跳过

## 3. 前端任务弹窗

- [x] 3.1 在 `plugins/rsyncd/js/rsyncd.js` 的添加/编辑任务弹窗中增加数值输入框 `max_delete_percent`，默认值 30，最小 0，最大 100，并补充 tooltip 说明“删除比例超过该值则终止同步”
- [x] 3.2 编辑已有任务时从 `data.max_delete_percent` 回填输入框，字段不存在时回填 30
- [x] 3.3 提交任务时读取该输入值，转换为整数并限制在 0 到 100 之间，然后随 `lsyncd_add` 请求一并提交

## 4. 验证

- [ ] 4.1 手动验证：通过 UI 新建任务，确认输入框默认显示 30，保存后 `/www/server/rsyncd/config.json` 写入 `max_delete_percent`
- [ ] 4.2 手动验证：打开一个没有该字段的旧任务编辑，确认弹窗显示 30，保存后字段被持久化
- [ ] 4.3 手动验证：`delete=false` 任务执行 `lsyncdRun` 时，preflight 运行、不中止、真实 rsync 执行
- [ ] 4.4 手动验证：`delete=true` 且 dry-run 删除比例低于阈值时，同步继续执行且不写中止日志
- [ ] 4.5 手动验证：临时把 `max_delete_percent` 降到 1 以触发超阈值，确认真实 rsync 不执行、`send/<name>/logs/preflight_<timestamp>.log` 被写入、`cmd` 非零退出
- [ ] 4.6 确认实时同步不受影响：检查 `/www/server/rsyncd/lsyncd.conf` 中实时 `sync {}` 仍由 lsyncd 直接执行，不调用 `preflight`
