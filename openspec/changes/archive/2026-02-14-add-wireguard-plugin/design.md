## Context
现有 WireGuard 配置主要通过手工命令与编辑 `/etc/wireguard/wg0.conf` 完成，缺少可视化、可复用、可审计的流程。Keepalived 方案依赖 WireGuard 隧道与 VIP，但缺少一体化的配置引导。

## Goals / Non-Goals
- Goals:
  - 提供一个可视化 WireGuard 插件，覆盖安装、密钥初始化、配置管理与点对点向导。
  - 面向“异地组网 + Keepalived”场景提供合理默认值（wg0、51820/51830、VIP AllowedIPs 等）。
  - 可安全地写入配置文件并一键应用，同时保留备份与回滚点。
- Non-Goals:
  - 不实现复杂的多站点网状网管理（本次仅覆盖点对点与少量 peer 管理）。
  - 不提供端口映射、复杂 ACL、防火墙管理的全托管（仅提供基础放行建议或一键执行）。

## Decisions
- 使用 `/etc/wireguard/*.conf` 作为事实来源，默认管理 `wg0.conf`，支持多接口列表展示。
- 安装方式优先使用系统包管理器（Debian/Ubuntu: `wireguard`；CentOS: `wireguard-tools` 或 EPEL），并检测 `wg`/`wg-quick` 是否可用。
- 密钥存储默认在 `/etc/wireguard/privatekey` 与 `/etc/wireguard/publickey`，权限强制 `600`；面板直接展示公私钥，重新生成需二次确认。
- 点对点向导放置在“配置列表”中，收集对端信息后自动创建本地配置，默认参数可编辑。
- 应用配置采用 `wg-quick down wg0` + `wg-quick up wg0`（或 systemd `wg-quick@wg0`），并在执行前提示可能中断隧道连接。

## Risks / Trade-offs
- 修改 WireGuard 配置可能导致链路中断 → 使用应用前确认弹窗 + 备份配置。
- 不同发行版包名差异 → 安装逻辑需兼容多发行版并回显检测结果。
- 私钥泄漏风险 → UI 默认隐藏、日志不输出私钥、接口权限校验。

## Migration Plan
- 新插件初始仅提供“读取现有配置”能力，不强制覆盖。
- 引导用户从现有 `/etc/wireguard/wg0.conf` 导入配置后再应用。

## Open Questions
- 是否需要支持 pre-shared key（PSK）与 QR 码导出（移动端接入）？
- 是否需要与 keepalived 插件互通，自动读取 VIP 并补齐 AllowedIPs？
- 默认端口选择是否跟随现网配置（如 51830）？
