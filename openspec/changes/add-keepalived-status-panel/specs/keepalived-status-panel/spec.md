## ADDED Requirements
### Requirement: Keepalived 状态面板
Keepalived 插件 SHALL 提供一个“状态面板”标签页，类似 rsyncd 实时服务面板的布局，集中展示服务运行状态。

#### Scenario: 菜单入口
- **当** 用户打开 Keepalived 插件窗口
- **则** 在“服务/配置面板/配置修改”等菜单旁出现“状态面板”入口，点击后加载状态视图。

#### Scenario: VIP 归属检测
- **当** 状态面板渲染时
- **则** 面板显示当前 VRRP 虚拟 IP 是否归属本机（通过 `ip addr | grep <VIP>` 等方式检测），并在 VIP 变动后刷新状态。

#### Scenario: 日志展示
- **当** 状态面板渲染时
- **则** 面板展示 keepalived 服务日志（最近若干行），并允许用户点击刷新获取最新日志。

#### Scenario: 扩展状态信息
- **当** 后端可获取其它运行指标（如 keepalived 进程状态、配置摘要、VRRP 角色等）
- **则** 状态面板可以同步展示这些信息，每项使用清晰标签/描述，保持布局与 rsyncd 面板一致。
