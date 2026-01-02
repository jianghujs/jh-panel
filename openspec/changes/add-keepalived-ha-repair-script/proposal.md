# 变更：新增双节点 Keepalived+MySQL 修复脚本

## 背景原因
- 当前 vm/default 工具集中缺少一键脚本来修复双节点 keepalived+mysql 场景下的异常，值班同学只能手动执行 `plugins/keepalived` 与 `plugins/mysql-apt` 的分散命令，步骤多且容易遗漏。
- 当 VIP 漂移或主从失衡时，需要保证本机重新晋升为主、把 peer 拉回备机，缺少合规的操作手册会放大恢复风险。

## 计划变更
- 在 `scripts/os_tool/vm/default` 下新增一个 `repair__` 脚本，串联 Keepalived/MySQL 检查、服务启动、优先级调整及远程 SSH 操作，帮助维护者在双节点场景中快速自愈。
- 新脚本需要读取现有 keepalived 表单接口、MySQL 插件接口，自动化地确认 VIP 归属、MySQL 主从状态、keepalived 运行状态，并在必要时提示确认后执行恢复命令。
- 脚本应通过 SSH 登录同一个 VRRP 对的另一台机器，完成同样的 MySQL/keepalived 检查与从库初始化，最终形成“本机主、对端备”的稳定状态。

## 影响范围
- 规格：keepalived-ha-repair-script（新增能力，描述恢复脚本的行为）
- 代码：`scripts/os_tool/vm/default/repair__*.sh` 新增脚本文件，可能引用现有 index 脚本
