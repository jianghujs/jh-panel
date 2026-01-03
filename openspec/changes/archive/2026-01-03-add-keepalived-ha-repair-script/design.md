## 背景
双节点 Keepalived+MySQL 集群的维护人员需要一个脚本化的 runbook，串联 keepalived 插件和 mysql-apt 插件提供的 API，并在必要时远程 SSH 至 peer 节点完成对称操作。脚本位于 `scripts/os_tool/vm/default`，遵循现有 repair 工具的交互风格。

## 目标
- 自动检测当前节点是否持有 VIP，并在缺失 VIP 时也能继续流程以确保最终晋升
- 统一调用 `plugins/keepalived/index.py` 和 `plugins/mysql-apt/index.py` 的现有动作，避免重复造轮子
- 封装远程 SSH 步骤，通过 `unicast_src_ip` / `unicast_peer_list` 自动发现对端 IP
- 在执行任何具破坏性的操作（启动服务、删除从配置）之前提示确认

## 非目标
- 不改动现有 keepalived / mysql 插件接口或配置格式
- 不负责自动化生成 SSH 密钥或互信，脚本假定可以免密访问 peer

## 设计决策
1. **数据源**：所有集群元数据都来自 keepalived 表单接口（VIP、单播 IP）和 mysql-apt 接口（从库列表）。避免直接解析配置文件。
2. **交互**：复用 bash `read -p` 方式让用户确认敏感操作；脚本只在用户确认后执行。
3. **远程执行**：使用 `ssh` + `bash -c` 组合，在单命令内执行与本机相同的 python3 调用，保持逻辑一致。
4. **日志**：使用 `echo` + `tee`（如有必要）记录关键步骤，方便回溯。

## 风险与取舍
- 如果 SSH 互信不完善，脚本会失败，需要在文档中强调依赖
- 远程命令执行失败时需要清晰的错误输出和退出码，避免误以为已修复

## 未决问题
- 是否需要支持多 peer？目前根据 `unicast_peer_list` 只取第一个 IP，如需多节点需要后续扩展
