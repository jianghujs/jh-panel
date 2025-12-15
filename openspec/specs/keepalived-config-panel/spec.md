# keepalived-config-panel Specification

## Purpose
TBD - created by archiving change add-keepalived-config-panel. Update Purpose after archive.
## Requirements
### Requirement: Keepalived VRRP 配置面板
Keepalived 插件 SHALL 提供一个名为“配置面板”的标签页，其表单字段覆盖 `/www/server/keepalived/etc/keepalived/keepalived.conf` 中默认 VRRP 设置。

#### Scenario: 面板入口
- **当** Keepalived 插件窗口打开时
- **则** 在“服务/自启动/配置修改”等菜单旁出现新的入口，点击后进入与 xtrabackup-inc、jianghujs 等插件一致的表单界面。

#### Scenario: 字段填充
- **当** 面板通过 `plugins/run`（kpPost）调用新的 `get_vrrp_form` 动作获取数据时
- **则** 后端读取 `vrrp_instance VI_MYSQL` 块并返回 `interface`、`virtual_ipaddress`（单个 IP）、`unicast_enabled`、`unicast_src_ip`、`unicast_peer_list`（按行分隔）、`priority`、`auth_pass` 等字段；若字段缺失则使用模板默认值，且当配置中不存在单播相关项时默认勾选单播开关。

#### Scenario: 校验反馈
- **当** 必填字段为空、优先级非整数或单播已勾选但相关 IP 缺失时
- **则** 面板禁止提交并提示错误，且不修改配置文件。

### Requirement: 面板保存 VRRP 设置
Keepalived 插件 SHALL 提供 `save_vrrp_form` 动作，只修改 `vrrp_instance VI_MYSQL` 中对应字段，保持其他指令不动。

#### Scenario: 单播开启时保存
- **当** 用户在勾选单播的情况下提交表单
- **则** 后端写入 `interface`、`virtual_ipaddress`、`priority`、`auth_pass`、`unicast_src_ip` 以及 `unicast_peer { ... }` 块（包含所有非空的 peer IP 行），仅覆盖实例块内对应值。

#### Scenario: 单播关闭时保存
- **当** 单播开关为关闭
- **则** 后端移除 `unicast_src_ip` 与 `unicast_peer { ... }` 块，同时更新其余字段。

#### Scenario: 异常处理
- **当** 找不到 `vrrp_instance VI_MYSQL` 区块或文件不可读时
- **则** 新增的两个动作都返回明确的失败信息，不写入任何内容，前端面板需展示该错误。

