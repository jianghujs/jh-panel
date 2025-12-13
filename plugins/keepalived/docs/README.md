# keepalived 插件原理与流程

本文梳理 `plugins/keepalived/` 内各组件的职责、运行原理与典型流程，便于快速上手与定制。

## 1. 目标与整体架构

- 该插件旨在通过 mdserver-web 面板一键安装、配置、启动 Keepalived，向业务导出 VRRP 虚拟 IP，从而实现 MySQL 等服务的主备高可用。
- 插件层由三部分组成：
  - **安装/卸载脚本**：`install.sh` 负责编译 Keepalived 并注册 systemd。
  - **后端控制器**：`index.py` 暴露 start/stop/config 等面板调用接口，同时准备 init.d、systemd、配置模板及健康检查脚本。
  - **前端页面**：`index.html` + `js/keepalived.js` 提供服务状态、配置模板、脚本模板与日志查看。

## 2. 目录结构速览

| 路径 | 作用 |
| --- | --- |
| `info.json` | 面板元数据，定义名称、版本、安装脚本等。 |
| `install.sh` | 安装/卸载入口脚本。 |
| `index.py` | 插件后端 API（start/stop/reload、配置模板、日志路径等）。 |
| `config/keepalived.conf` | 默认配置模板，初始化时写入 `$SERVER_PATH/keepalived/etc/keepalived/keepalived.conf`。 |
| `tpl/*.conf` | 示例配置模板（MySQL Master/Backup、说明版、LVS NAT）。 |
| `scripts/chk.sh`、`scripts/chk_mysql.sh` | 健康检查脚本，被 `vrrp_script` 调用或计划任务触发。 |
| `init.d/keepalived.tpl`、`init.d/keepalived.service.tpl` | init.d 和 systemd 模板，由 `index.py` 渲染生成。 |
| `index.html` + `js/keepalived.js` | 插件 UI：服务控制、自启动、配置/脚本模板、日志。 |

## 3. 安装/卸载流程（`install.sh`）

1. 解析路径、版本号，创建 `source/keepalived` 缓存目录。
2. 若本地不存在 tar 包则从 https://keepalived.org 下载，并通过预置 MD5（`8c26f75…`）校验完整性。
3. 解压至 `source/keepalived/keepalived-${VERSION}`，执行 `./configure --prefix=$serverPath/keepalived && make && make install`。
4. 安装完成后写入 `server/keepalived/version.pl`，随后调用 `plugins/keepalived/index.py` 的 `start` 与 `initd_install` 完成首次启动和 systemd 注册。
5. 清理源码目录，安装结束。
6. 卸载流程会删除 systemd service（`/usr/lib/systemd/system/keepalived.service` 或 `/lib/systemd/system/keepalived.service`）、停止服务并清空 `$serverPath/keepalived`。

## 4. 初始化与运行控制（`index.py`）

1. **入口与参数**：面板调用 `/plugins/run` -> `index.py`，`getArgs()` 解析参数，`func` 决定执行的操作。
2. **initD 准备（`initDreplace`）**：
   - 通过 `contentReplace` 将模板内的 `{$SERVER_PATH}`、`{$PLUGIN_PATH}`、`{$ETH_XX}` 等占位符替换为真实路径/网卡。
   - 渲染 `init.d/keepalived.tpl`，放至 `$SERVER_PATH/keepalived/init.d/keepalived` 并赋可执行权限。
   - 若配置文件不存在，则用 `config/keepalived.conf` 初始化 `$SERVER_PATH/keepalived/etc/keepalived/keepalived.conf`。
   - 复制 `plugins/keepalived/scripts` 到 `$SERVER_PATH/keepalived/scripts` 并替换占位符。
   - 检查 systemd 目录（`mw.systemdCfgDir()`），根据 `keepalived.service.tpl` 生成服务文件并 `systemctl daemon-reload`。
3. **服务控制（`kpOp`）**：标准 Linux 环境下通过 `systemctl <method> keepalived` 操作；macOS/FreeBSD 走对应分支。`start/stop/restart/reload` 均基于此封装。
4. **状态与自启动**：`status()` 检查进程，`initdStatus/initdInstall/initdUinstall` 用于面板的“自启动”开关。
5. **日志与其他接口**：`runLog()` 指向 `$SERVER_PATH/keepalived/keepalived.log`，前端通过 `pluginLogs` 拉取；`configTpl`/`defaultScriptsTpl` 等接口支撑配置与脚本模板页面。

## 5. 配置模板与占位符

- `config/keepalived.conf` 以及 `tpl/*.conf` 展示典型 VRRP 配置：`global_defs`、`vrrp_script`（引用 `chk.sh mysql`）、`vrrp_instance`（VIP、优先级、认证、`track_script` 等）。
- `contentReplace` 会按当前环境替换：
  - `{$SERVER_PATH}` → 面板 `server` 目录，例如 `/www/server`.
  - `{$PLUGIN_PATH}` → 插件目录。
  - `{$ETH_XX}` → 通过 `route -n | grep ^0.0.0.0` 自动探测默认网卡，找不到时兜底 `eth1`。
- 前端菜单中的“配置修改”调用 `configTpl`/`readConfigTpl`，以只读展示模板或者将其作为自定义配置的基底。

## 6. 健康检查与脚本模板

- `scripts/chk.sh` 是统一入口：`bash $SERVER_PATH/keepalived/scripts/chk.sh mysql` 会进入插件目录然后执行 `chk_mysql.sh`。
- `scripts/chk_mysql.sh` 以 `netstat -na | grep 3306` 判定 MySQL 监听情况：
  - 若端口关闭，记录日志后 `systemctl stop keepalived`，避免漂移到无效节点。
  - 若端口恢复且 Keepalived 未运行，则 `systemctl start keepalived` 自动拉起。
- 这些脚本既可被 Keepalived 配置中的 `vrrp_script` 引用，也可以作为计划任务周期执行，实现服务可用性联动。
- 通过前端“脚本模板”菜单可以查看 `$SERVER_PATH/keepalived/scripts` 下现有脚本，辅助二次开发。

## 7. 前端交互流程

1. 打开插件页面时载入 `index.html`，通过 `$.getScript` 引入 `js/keepalived.js`。
2. `keepalived.js` 内的 `kpPost`/`kpPostCallbak` 封装 AJAX，所有按钮最终调用 `/plugins/run` 或 `/plugins/callback`，由 `index.py` 接口处理。
3. 菜单项映射如下：
   - “服务” → `pluginService('keepalived')`，可 start/stop/restart。
   - “自启动” → `pluginInitD`，对应 `initdStatus/initd_install/initd_uninstall`。
   - “配置修改”与“脚本模板”分别通过 `pluginConfigTpl` 与 `pluginConfigListTpl` 读取模板。
   - “日志” → `pluginLogs('keepalived','','run_log')`，读取 `runLog()` 指定的日志文件。
4. 版本号由 `.plugin_version` 节点传入 JS，便于未来多版本共存。

## 8. 典型使用顺序

1. 在面板应用商店中点击安装 → 触发 `install.sh` 完成编译部署，并自动启动 Keepalived。
2. 通过“配置修改”选择匹配场景的模板（如 `keepalived.mysql.master.conf`），根据业务修改 VIP、优先级、认证等关键字段后保存到 `$SERVER_PATH/keepalived/etc/keepalived/keepalived.conf`。
3. 按需调整/扩展 `scripts/` 下的健康检查脚本，并在配置中的 `vrrp_script` 部分引用。
4. 在“服务”界面启动/重启并校验状态，确保 `keepalived.log` 中无异常；必要时开启“自启动”。
5. 结合计划任务定期运行 `chk.sh`，实现数据库/Keepalived 的自愈与高可用切换。

通过以上流程，插件把 Keepalived 的安装编译、配置模板、健康检查与面板 UI 管理串联为完整闭环，方便快速部署内网高可用能力。
