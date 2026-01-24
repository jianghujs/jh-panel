## ADDED Requirements
### Requirement: 安装 os_tool 到系统目录
系统 SHALL 提供 `scripts/os_tool/install.sh` 安装脚本，优先使用本地 `/www/server/jh-panel/scripts/os_tool`，若不存在则从仓库下载 `scripts/os_tool` 下的全部脚本并安装到 `/www/server/os_tool`，且不覆盖该目录中的其他无关文件。

#### Scenario: 安装脚本
- **WHEN** 用户运行 `bash scripts/os_tool/install.sh`
- **THEN** 若存在 `/www/server/jh-panel/scripts/os_tool` 则从本地复制，否则从仓库下载 `scripts/os_tool` 内容并复制到 `/www/server/os_tool`
- **AND** `/www/server/os_tool` 下与 os_tool 无关的文件保持不变

### Requirement: 提供 jht 命令入口
系统 SHALL 安装 `jht` 命令并启动 `scripts/os_tool/index.sh`，在无参数时自动按系统类型选择脚本库：PVE 系统执行 `pve` 脚本库，其他 Linux 系统默认执行 `vm` 脚本库；使用 `jht menu` 可进入带“更新”选项的菜单。

#### Scenario: 运行 jht
- **WHEN** 用户运行 `jht`
- **THEN** os_tool 根据系统类型直接执行对应脚本库
- **AND** 脚本从 `/www/server/os_tool` 运行

### Requirement: 更新菜单刷新本地脚本
系统 SHALL 在 `scripts/os_tool/index.sh` 中提供“更新”菜单项，使用 `netEnvCn` 镜像选择规则，将最新的 `scripts/os_tool` 内容覆盖更新到 `/www/server/os_tool`。

#### Scenario: 从镜像更新脚本
- **WHEN** 用户选择“更新”菜单
- **THEN** 默认从 GitHub 拉取，`netEnvCn=cn` 时从 Gitee 拉取
- **AND** `/www/server/os_tool` 下的脚本更新为最新版本
- **AND** `/www/server/os_tool` 下无关文件保持不变
