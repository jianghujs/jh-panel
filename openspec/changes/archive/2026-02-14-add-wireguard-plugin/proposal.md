# Change: Add WireGuard Plugin for HA Networking

## Why
当前 WireGuard 配置依赖手工安装与手写配置，操作易出错且难以复用。需要一个面板化插件，完成 WireGuard 安装、密钥初始化、点对点配置向导与配置列表管理，降低异地组网 + Keepalived 联动的配置门槛。

## What Changes
- 新增 WireGuard 插件：提供安装/卸载/状态、密钥初始化、配置列表、点对点向导等功能。
- 提供向导化配置生成：输入对端公网 IP/端口/公钥等参数，自动生成本地与对端配置片段。
- 支持配置文件管理与应用：可在面板内维护 `/etc/wireguard/*.conf` 并一键生效。
- 补充文档与操作提示：在现有 WireGuard + Keepalived 方案中新增插件使用说明与注意事项。

## Impact
- Affected specs: `wireguard-management-panel` (new)
- Affected code: `plugins/wireguard/*`（新建），以及插件菜单与文档（`plugins/keepalived/docs/...`）。
