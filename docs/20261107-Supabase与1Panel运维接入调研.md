# Supabase 与 1Panel 运维接入调研

调研日期：2026-11-07。目标：验证不修改 1Panel 源码的情况下，项目级 `ops.sh` 能否管理站点、Node.js 运行环境、脚本库和计划任务，并衔接备份、文件同步及主备切换。本文记录已执行的调查，不表示生产运维项目已经实现。

## 1. 调研范围与结论

目标机器通过 SSH 访问，运行 1Panel v2.4.1 stable、Docker 29.9.2、Compose v5.6.1。源码依据为官方 v2.4.1，提交 `f9f9169a4d8cba736b0761e828b3df574e242918`。最初通过 root 专用本地 Agent 通道测试，随后使用用户创建的密钥，通过正式 HTTP API 重验。两种通道的证据不混用。

用户授权仅操作 `supabase-ops-research-` 前缀测试资源；未修改现有业务配置，未重启共享 OpenResty 容器。正常站点配置应用会触发配置检查及热重载。NAS 实测按用户要求暂不进行，改为本机两个独立目录模拟挂载和文件同步。

| 能力 | 证据状态 | 结论 |
| --- | --- | --- |
| 正式 API 鉴权 | 实机通过 | HMAC-SHA256、MD5 兼容签名均可用，限制为回环来源 |
| 站点管理 | 实机通过 | 创建、备注修改、域名增删、启停、删除可用 |
| Node.js 管理 | 实机通过 | 创建、环境变量更新、down/up/restart、删除可用 |
| 脚本库 | 正式 API 实机通过 | 创建、更新、查询、删除，及被计划任务调用均可用 |
| 计划任务 | 实机通过 | 创建、修改、启禁用、手动执行、任务日志可用 |
| HTTPS | 实机通过 | 自签名证书导入、绑定、访问、关闭、清理可用；不等于公网 ACME 验证 |
| 站点备份恢复 | 同机实机通过 | 能备份恢复站点和运行环境，但不包含外部项目代码 |
| Compose 可见性 | 实机查询、源码确认 | 可通过 Compose 标签发现项目，不要求先制作商店包；未创建自定义商店应用 |
| 文件目录 | 临时工具容器实机通过 | 双目录隔离挂载、双向同步、容器重建后数据保留；未启动完整 Supabase |
| 跨机器重建、恢复与证书分发 | 未实测 | 当前仅一台机器，不能以单机验证替代 |
| 公网证书签发、续签 | 仅源码确认 | 需要受控域名、验证方式和账号后再测试 |
| Supabase 整体切换 | 本轮未执行 | 数据库、文件、站点、任务的组合流程需要另行双节点演练 |

## 2. 正式 API 与密钥边界

用途：让宿主机 CLI 调用面板能力，不是让业务应用访问 Supabase。Supabase API 使用其项目密钥和用户令牌，直连 PostgreSQL 使用数据库凭据，二者与面板密钥不同。

实测地址为目标机器本地 `http://127.0.0.1:20411/api/v2`。这不代表跨网络可以明文传输，跨机应采用可信 HTTPS 或 SSH 隧道。

| 请求情形 | HTTP 状态 | 业务 code |
| --- | --- | --- |
| 有效 HMAC-SHA256 | 200 | 200 |
| 有效 MD5 兼容签名 | 200 | 200 |
| 错误签名 | 200 | 401 |
| 过期时间戳 | 200 | 401 |
| 未携带凭据 | 200 | 401 |
| 有效签名，但从本机非回环地址连接 | 200 | 401，来源不在白名单 |
| API Key 尝试管理 API Key | 200 | 401，需要管理员会话 |

签名头包括 `1Panel-Timestamp`、`1Panel-Token`、`1Panel-Signature-Version`。HMAC 内容为 `1panel:<Unix秒时间戳>`，密钥为 API Key；MD5 兼容格式为 `md5(1panel + APIKey + 时间戳)`。`1Panel-Key-ID` 应是系统 ID，不是密钥名称；本次文件填写名称后，采用省略该头的官方签名匹配方式成功验证，未修改用户文件内容。

API 客户端必须分别检查 HTTP 状态、JSON 业务 code、异步任务状态和服务实际可用性。不能把 HTTP 200 当成成功。

该版本新版独立密钥可在旧版全局 API 关闭时使用，不能仅凭 `ApiInterfaceStatus=Disable` 判断全部 API Key 均不可用。创建和撤销密钥需要管理员会话；普通密钥不能自我撤销，也不能通过 root Agent 通道绕过这项限制。

当前技能 `1panel-skills` 提供查询客户端，未修改其源码。它的计划任务查询默认排序字段 `created_at` 在目标版本被拒绝，需使用 `createdAt`；这是待修复兼容项。本次操作测试采用与官方源码一致的临时测试请求，不是生产适配层实现。

## 3. 站点和 Node.js 运行环境

用途：每个 Supabase 项目拥有自己的站点与 Node.js 服务，但资源仍显示在同一个 1Panel 列表中。

| 功能 | 接口（省略 `/api/v2`） | 已确认的细节 |
| --- | --- | --- |
| 站点查询、创建 | `GET /websites/list`、`POST /websites` | 创建带 taskID，等待任务完成后验证域名响应 |
| 站点修改、启停 | `POST /websites/update`、`POST /websites/operate` | 备注与域名、代理、原始配置分别管理 |
| 域名管理 | `GET /websites/domains/:id`、`POST /websites/domains`、`POST /websites/domains/del` | 别名域名请求能到达测试应用 |
| 读取配置 | `GET /websites/:id/config/openresty` | type 应是 openresty，不能猜 nginx |
| 更新配置 | `POST /websites/nginx/update` | 非法配置被拒绝，原有效配置保持可用 |
| HTTPS | `POST /websites/ssl/upload`、`GET/POST /websites/:id/https` | 访问时必须使用正确 SNI；自签名仅用于隔离测试 |
| Node.js 创建、修改 | `POST /runtimes`、`POST /runtimes/update` | 创建自动启动；依赖安装可显式关闭 |
| Node.js 启停 | `POST /runtimes/operate` | 请求使用 ID 和 operate；down 会移除容器，up 会重建 |
| Node.js 删除 | `POST /runtimes/del` | 先删关联站点；不删除共享镜像，外部代码目录仍保留 |

测试使用已安装 Node.js 版本 26.12.1、无第三方依赖 HTTP 示例，端口仅绑定 `127.0.0.1:18764`。创建请求的 appDetailId 来自本机目录，不能原样跨面板同步。环境变量从 initial 更新为 updated 后，应用响应已实际变化。

### 3.1 就绪检查不能依赖“停用站点”

实测站点停用后返回 HTTP 200 停站页面。本站点独立 `/__ops/ready` 路径配置 `return 503` 后，确实返回 503。

建议备用、隔离、切换中返回 503；只有数据库角色、必要文件目录和业务服务验证通过后返回 200。沿用外部 DNS 故障转移，不开发 DNS 操作。DNS 切换不是数据库选主或旧主隔离。

Node.js 创建会自动启动，因此备用端必须使用无副作用的启动限制，不能让其意外运行迁移、定时任务、队列消费者或写入逻辑。此处是设计约束，不声称已实现启动限制。

## 4. 脚本库、计划任务和日志

用途：面板负责调度，真正操作放在本项目 CLI，便于之后增加界面而不重写逻辑。

脚本库 `POST /core/script`、`/update`、`/search`、`/del` 已通过正式 API 验证。非交互脚本进入 `/cronjobs/script/options`；计划任务以 library 模式引用脚本 ID，执行日志确认输出更新后的测试标记。交互脚本运行是 WebSocket 通道，不能用普通 GET 请求成功来证明脚本执行。

计划任务：

- 创建后立即处于 Enable；测试先采用远期调度，再禁用，避免误触发。
- 五段表达式 `0 2 * * *` 通过；六段表达式被拒绝。
- 禁用的任务仍可手动执行。
- 实测正在执行的 15 秒测试任务，在禁用调度后仍成功执行结束。
- 停止在途任务的 `/cronjobs/stop` 使用执行记录 ID，不是计划任务 ID（源码确认，未实测取消）。
- 查询执行记录应传合理的 startTime/endTime；省略后本次查询未返回已有记录。
- `/cronjobs/records/log` 未读到测试输出，但 `/logs/tasks/read` 通过 taskID 成功读到。

推荐计划任务只调用绝对路径的 `ops.sh`，非交互执行，入口再次检查实际角色、隔离标记、操作锁和重复运行。切换时禁用未来调度与处理在途任务是两步。只影响当前项目，不能禁用整个面板调度器。

异步状态查询：`POST /logs/tasks/search`，按 taskID 筛选；日志读取：`POST /logs/tasks/read`，参数含 taskID、page、pageSize；成功后仍验证容器和业务响应。

## 5. 备份恢复、证书与跨机边界

用途：确定原生能力能复用到哪里，避免把站点备份误当完整业务备份。

`POST /backups/backup`、`/backups/recover` 同机恢复测试通过。type 使用 website，detailName 使用站点 alias。使用本地备份账户时，recover 的 file 传相对该备份根目录的路径；绝对路径会被重复拼接并导致任务失败，不能因接口接收成功就认为恢复成功。失败样例回滚成功，修正路径后恢复任务 Success。

实际备份包包含：站点 JSON、OpenResty 配置、站点目录压缩包、运行环境 JSON 和运行环境目录压缩包。继续检查内层压缩包，包含 Compose、启动脚本、环境文件等，但不包含外部 codeDir 下的 server.js。恢复任务成功后，运行环境还可能短暂显示 Starting，稍后同步状态和请求验证正常。恢复会启动运行环境，不能当作安全的“备用端静默还原”。

源码 `checkValidOfWebsite` 检查 alias/type、源 AppInstallID、RuntimeID 和 WebsiteSSLID 是否存在，没有跨机器 ID 重映射。因此跨机应同步可移植定义、独立代码/文件/密钥，再通过目标端 API 创建资源并建立本机映射；不要同步面板 SQLite 或整个共享 OpenResty 配置树。

证书导入绑定实测通过；公网签发与自动续签未实测。源码确认自动续签是面板内置任务，不在用户计划任务列表里；成功后更新关联站点证书并重载 OpenResty。手工导入证书不会因此自动获得 ACME 续签。官方证书跨节点推送需要 XPack。续签后执行脚本可作为自有分发集成点，但安全分发、目标端导入和失败重试仍待验证。

自建 PostgreSQL 可登记为 remote 数据库（源码确认），不等于自动成为商店安装实例。该版本远程 PG 客户端使用 sslmode=disable，不应直接用于跨公网管理；Supabase 系统角色、扩展和备份兼容性尚未实测。

## 6. 两个本地目录的挂载与同步

用途：按用户要求替代当前 NAS 实测，只验证文件链路。

使用两个独立 Compose 项目和 storage 目录，挂载到临时容器 `/var/lib/storage`；容器无外部网络、不发布端口、不启动 PostgreSQL。临时工具镜像基于机器已有 postgres:18.6-alpine，加装 rsync 3.5.2；没有在宿主机安装软件。bind 使用 create_host_path=false，避免源目录不存在时静默创建。

结果：独立挂载可读到不同标记；源端只读、目标端可写的临时 rsync 容器完成 A→B 和 B→A；校验 SHA-256 一致；移除并重建容器后文件仍存在。

重要异常：测试文件大小及修改时间相同但内容不同，`rsync -a` 跳过，带 `--checksum` 后正确更新。最终切换校验不能只依赖大小和时间。`--delete` 是镜像删除，不是备份，仅可对显式授权目标使用。

本次没有启动完整 Supabase，没有验证 Storage API、UID/GID 权限、跨主机传输、NFS 掉线、重新挂载或数据库与对象文件的一致恢复点。两目录模拟不能支撑这些结论。

## 7. 建议项目设计与下一步

1Panel 管基础设施；每个项目的宿主机 ops.sh 管本站点、Node.js 项目、数据库、文件和主备流程。数据库镜像加入匹配版本 pgBackRest，文件同步独立容器。PGDATA 放本机磁盘，Storage 等通过显式路径挂载。面板密钥只供宿主机运维使用，不注入普通业务应用或数据库容器。

| 模块 | 建议职责 |
| --- | --- |
| panel 适配层 | 封装鉴权、版本差异、业务 code、异步任务及资源归属检查 |
| site / project | 可移植定义 + 目标端创建；SQLite 只存本机资源 ID 映射 |
| schedule | 安装本项目薄入口，角色检查与在途任务处理 |
| replication | 初始化、连接修复、rewind/rebuild 分场景处理 |
| backup | 数据库备份与项目恢复集分开，包含代码/文件/密钥对应关系 |
| files | 显式单向同步、状态、校验；不 rsync 活跃 PGDATA 或本机 SQLite |
| ha | 计划切换、故障接管、旧主回归分别提供入口 |

后续验证按顺序：第二台独立面板重建站点/运行环境 → 可控域名的证书续签与分发 → Supabase 数据库和文件组合切换 → 故障隔离及恢复演练。当前没有第二台独立面板，不将同机资源重建表述为跨机通过。NAS 测试按用户要求延期。

## 8. 清理与未完成事项

两轮站点/Node/任务测试及目录实验资源已删除：测试站点、运行环境、脚本库脚本、计划任务、证书、备份记录及文件、临时目录、挂载实验镜像和已识别测试卷。面板任务历史与正常构建缓存不作全局清理。测试临时文件不可恢复，但不含用户业务数据。

最终核对：原有 1 个站点和 2 个 Node.js 环境列表及状态一致；原有 9 个容器 ID 未变；OpenResty 配置检查通过；测试前缀的站点、运行环境、任务、脚本、证书、备份记录及容器均为零。

密钥文件 `/root/1panel-research-api.json` 已删除，读取前权限由 700 收紧为 600，密钥未写入文档或日志。用户创建的“AI调研测试用”密钥仍 Enable，仅允许 127.0.0.1，无到期时间；旧版全局 API 仍 Disable。删除文件不等于撤销密钥，需管理员在面板撤销，尚未完成。

本轮不能宣称“全部生产能力完成”：密钥撤销待管理员处理，独立双机与公网证书相关验证仍待环境；Supabase 项目本身尚未进入开发。

## 9. 官方源码定位

源码基准：[1Panel v2.4.1](https://github.com/1Panel-dev/1Panel/tree/v2.4.1)。

| 位置 | 用于核对 |
| --- | --- |
| core/app/auth/api_auth.go、api_key.go | 签名、白名单、独立密钥、管理员会话边界 |
| core/app/service/script_library.go | 交互/非交互脚本及同步机制 |
| agent/app/service/runtime.go、runtime_utils.go | 运行环境创建、启停和自动启动 |
| agent/app/service/website_utils.go | 停站行为、配置和代理 |
| agent/app/service/cronjob.go、cronjob_helper.go | 调度、手动执行、在途任务和日志 |
| agent/app/service/backup_website.go、backup_runtime.go | 备份覆盖、恢复及 ID 约束 |
| agent/app/service/website_ssl.go、agent/cron/job/ssl.go | 续签、站点更新及 XPack 分发限制 |
| agent/app/service/container_compose.go | Compose 标签发现机制 |
| agent/app/service/disk.go、disk_utils.go | 本地磁盘检查与格式化边界，不用于 NFS |
