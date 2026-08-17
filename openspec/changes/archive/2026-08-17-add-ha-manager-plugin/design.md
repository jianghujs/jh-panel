## Context

当前 keepalived 插件已经覆盖了 VIP、配置编辑、日志和切换脚本，但没有一个稳定的“主备关系管理层”。主备关系、对端探测、SSH 互信和状态输出分散在脚本和人工操作中，不利于后续云监控采集和联动。

首版只支持 `mysql-apt`，可以显著降低状态判断复杂度，也便于先把主备插件的配置面和状态面打通，再扩展到更多数据库实现。

## Goals / Non-Goals

**Goals:**
- 提供独立的 `ha_manager` 插件入口。
- 管理两机主备关系配置与 SSH 互信。
- 输出结构化状态，供页面和后续采集复用。
- 统一暴露 `switch_role` 接口，给切换脚本写状态。
- 首版只支持 `mysql-apt`。

**Non-Goals:**
- 不实现云监控页面、回调和数据同步系统联动。
- 不支持多个数据库插件并行判断。
- 不重写 keepalived 的 VIP 漂移逻辑。
- 不在首版里做复杂的 rsync 延迟计算或多机拓扑。

## Decisions

### 独立插件而不是改造 keepalived
`ha_manager` 作为单独插件，避免把关系配置、状态聚合和切换状态写入混进 keepalived 的 VIP 配置面板。

Alternatives considered:
- 把所有逻辑塞进 keepalived：实现快，但职责太重，后续云监控接入也会更乱。
- 新建独立插件：更清晰，接口也更稳定，适合承接后续联动。

### 只支持 mysql-apt
首版只读 `mysql-apt` 的状态，避免同时兼容多个 MySQL/MariaDB 插件带来的判定分叉。

Alternatives considered:
- 同时支持 `mysql-apt`、`mysql-yum`、`mariadb`：覆盖更广，但状态判定、命令路径和错误处理会复杂很多。

### SSH 密钥由插件自管
插件使用固定密钥路径 `/root/.ssh/ha_manager` 和 `/root/.ssh/ha_manager.pub`，便于页面展示、对端授权和连接测试都围绕同一套 key 运转。

Alternatives considered:
- 复用现有 standby_sync key：会和现有切换和同步流程耦合，边界不清晰。

### 状态模型使用可读枚举
连接状态、切换状态和汇总状态使用明确枚举值，避免前端和采集端对布尔状态做二次推导。

Alternatives considered:
- 只返回布尔值：页面简单，但对异常原因表达不够，后续云监控也难消费。

### keepalived 只消费接口，不拥有状态
keepalived 后续只调用 `switch_role` 写状态，不持有主备关系配置本身。配置源头保持在 `ha_manager`。

Alternatives considered:
- 让 keepalived 直接写 `config.json`：会把两个系统绑死，后期扩展困难。

## Risks / Trade-offs

- [Risk] SSH 互信配置失败会导致对端检查不可用。→ 通过显式连接状态和失败原因展示，避免静默失败。
- [Risk] `mysql-apt` 状态读取可能受 MySQL 启停阶段影响。→ 将读取失败归为 warning，并保留最近一次失败信息。
- [Risk] 双端同时配置错误会造成角色冲突误报。→ `ha_role_conflict` 作为明确异常项返回，避免自动掩盖问题。
- [Risk] 固定密钥路径可能与人工 SSH 配置冲突。→ 通过明确文件名与权限约束降低混用风险。

## Migration Plan

1. 新增 `ha_manager` 插件目录和基础页面。
2. 先实现本机配置保存、密钥生成和本地状态读取。
3. 再实现对端 SSH 测试和一主一备判断。
4. 保持 keepalived 现状不变，后续由切换脚本调用 `switch_role` 接口接入。
5. 预留状态 JSON 输出格式，后续云监控直接消费。

Rollback strategy:
- 删除插件目录和 `/www/server/ha_manager/` 数据目录即可回退到现状。
- keepalived 侧若尚未接入 `switch_role`，不会引入行为变化。

## Open Questions

- `ha_manager` 页面是否需要直接提供一键复制公钥按钮和重建密钥按钮。
- `switch_role` 的失败摘要是否要长期保留最近一次脚本错误，还是只保留时间戳。
- 后续接入 keepalived 时，是否统一从 `ha_manager` 读取当前配置角色作为唯一真值。
