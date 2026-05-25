## Why

当前 `plugins/frp` 仅支持固定的 `frps.ini` / `frpc.ini` 单配置文件模式，无法满足一个服务端或客户端同时托管多条代理配置的场景，也不利于按业务拆分配置。需要在保持现有单文件用法兼容的前提下，为插件补充多配置文件管理能力，避免用户在“继续沿用旧配置”和“切换到多配置目录”之间二选一。

## What Changes

- 为 frp 插件增加配置模式兼容能力，同时支持现有单配置文件模式和新的多配置文件模式。
- 调整 frp 插件后端配置定位、模板读取、保存与启动逻辑，使其能够识别并处理“单文件入口”与“多文件目录”两类配置源。
- 调整 frp 插件前端配置入口，使用户可区分服务端/客户端配置，并在多配置模式下查看、编辑、创建和删除多个配置文件。
- 明确模式切换与兼容规则：已有 `frps.ini` / `frpc.ini` 用户无需迁移即可继续使用；启用多配置后，插件按约定目录和文件名启动。
- 补充帮助说明与验证清单，覆盖升级后兼容行为和多配置模式的基本操作。

## Capabilities

### New Capabilities
- `frp-config-mode-management`: frp 插件支持单配置文件与多配置文件两种配置管理和运行模式，并提供兼容的前后端操作入口。

### Modified Capabilities

None.

## Impact

- Affected specs: `frp-config-mode-management` (new)
- Affected code: `plugins/frp/index.py`, `plugins/frp/index.html`, `plugins/frp/js/frp.js`, `plugins/frp/init.d/*.tpl`, `plugins/frp/client_cfg/*`, `plugins/frp/server_cfg/*`
- Affected runtime paths: frp 插件配置文件存储目录、systemd/init.d 启动命令、配置模板读取逻辑
