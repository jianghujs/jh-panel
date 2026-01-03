# keepalived-ha-repair-script Specification

## Purpose
TBD - created by archiving change add-keepalived-ha-repair-script. Update Purpose after archive.
## Requirements
### Requirement: 双节点 Keepalived/MySQL 本机修复脚本
`scripts/os_tool/vm/default` SHALL 提供一个 `repair__keepalived_mysql_failover.sh`（或同义命名、以 `repair__` 打头的 shell 脚本），引导维护者在当前节点上完成 VIP、MySQL、Keepalived 的恢复，使本机重新成为主节点。

#### Scenario: 发现当前节点元数据
- **WHEN** 执行脚本
- **THEN** 它在 `/www/server/jh-panel` 目录下运行 `python3 plugins/keepalived/index.py get_status_panel` 并解析 `vip_owned`，告知用户本机是否持有 VIP；随后运行 `python3 plugins/keepalived/index.py get_vrrp_form` 获取 `unicast_src_ip` 与 `unicast_peer_list`，用于确认本机/对端 IP。

#### Scenario: 修复本机 MySQL 服务
- **WHEN** 脚本检测到 `systemctl status mysql-apt` 或 `python3 plugins/mysql-apt/index.py start` 结果表明 MySQL 未运行
- **THEN** 它提示用户确认后调用 `python3 plugins/mysql-apt/index.py start` 启动服务，并再次执行 `systemctl status mysql-apt` 展示状态；若 MySQL 已启动，则跳过。

#### Scenario: 强制本机为主库
- **WHEN** `python3 plugins/mysql-apt/index.py get_slave_list` 返回的 `data` 列表不为空
- **THEN** 脚本提示用户并在确认后调用 `python3 plugins/mysql-apt/index.py delete_slave` 移除从配置；若列表为空则说明当前为主库，仅记录状态。

#### Scenario: 设置 keepalived 主角色
- **WHEN** 本机需要成为主节点
- **THEN** 脚本调用 `python3 plugins/keepalived/index.py set_priority '{"priority":100}'`（或等效参数）将优先级设为 100，并检查 keepalived 运行状态；若 `systemctl status keepalived` 显示服务未运行，则提示是否执行 `python3 plugins/keepalived/index.py start`，随后再次调用 `systemctl status keepalived` 打印结果。

### Requirement: 双节点远程修复操作
脚本 SHALL 复用 `get_vrrp_form` 中的 `unicast_peer_list`（至少包含一个 peer）自动登录对端节点，完成与主备切换相关的 MySQL 与 Keepalived 调整，确保对端保持备节点角色。

#### Scenario: 远程 MySQL 服务处理
- **WHEN** 脚本解析 `unicast_peer_list` 并获取首个对端 IP
- **THEN** 它通过 `ssh <peer> 'cd /www/server/jh-panel && python3 plugins/mysql-apt/index.py start'` 等命令检查对端 MySQL 状态，若服务未运行则提示并在获得确认后启动；随后运行 `python3 plugins/mysql-apt/index.py init_slave_status` 当对端未配置主从同步时进行初始化，确保其作为从库。

#### Scenario: 远程 Keepalived 设定
- **WHEN** 脚本完成对端 MySQL 检查
- **THEN** 它在对端执行 `python3 plugins/keepalived/index.py set_priority '{"priority":90}'` 之类命令，把优先级设为 90 并保持备节点定位；若对端 keepalived 未运行，则提示确认并执行 `python3 plugins/keepalived/index.py start`，最后调用 `systemctl status keepalived` 输出结果；
- **AND** 无论服务原本是否运行，脚本都要触发一次 `python3 plugins/keepalived/index.py restart`，以确保对端主动释放 VIP、漂移到本机。

