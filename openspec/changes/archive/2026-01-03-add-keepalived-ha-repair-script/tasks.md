## 1. vm/default 自愈脚本
- [x] 1.1 研究 `scripts/os_tool/vm/default` 现有 repair 脚本的交互、日志与 SSH 约定
- [x] 1.2 新增 `repair__keepalived_mysql_failover.sh`，在 shell 层实现本机 VIP 检查、MySQL 启动/主从切换、keepalived 优先级设置与启动
- [x] 1.3 在脚本中加入 SSH 到 peer 节点的逻辑，执行 MySQL 服务/主从/keepalived 的检查与修复
- [x] 1.4 手动在测试环境验证脚本（本地路径已执行，远端因缺少可达 peer 暂无法实测），整理或更新相关帮助文档
