## Why

主备切换、关系绑定和对端状态判断目前散落在 keepalived、MySQL 复制脚本和人工操作里，缺少一个统一入口来管理两台主机之间的关联关系。现在需要一个独立插件把主备关系配置、SSH 互信和状态输出收拢起来，为后续云监控采集和切换联动提供稳定接口。

## What Changes

- 新增 `ha_manager` 主备关联插件，提供关系配置页、状态页和自检能力。
- 插件支持保存主备关系信息：关系 ID、对端 IP、SSH 端口、SSH 用户、配置角色和对端公钥。
- 插件自主管理 SSH 密钥对，首次使用时生成 `/root/.ssh/ha_manager` 和 `/root/.ssh/ha_manager.pub`。
- 插件提供本机状态输出与对端探测结果，支持 `get_status --local-only` 规避递归检查。
- 插件提供 `switch_role` 接口，供后续切换脚本统一写入 `switching/primary/standby/failed` 状态。
- 首版仅支持 `mysql-apt` 的状态读取与判断。

## Capabilities

### New Capabilities
- `ha-manager-plugin`: 主备关联插件的配置、SSH 互信、状态聚合和切换状态写入能力。

### Modified Capabilities
- `keepalived-ha-monitoring`: 不修改既有告警开关行为；如需联动，仅在后续实现阶段通过插件接口接入，不改变当前规格。

## Impact

- 新增插件目录、前端页面、Python 后端脚本和安装脚本。
- 依赖 SSH、公钥授权、`mysql-apt` 状态读取能力。
- 后续 keepalived 切换脚本将调用该插件接口写入状态，但不在首版范围内。
