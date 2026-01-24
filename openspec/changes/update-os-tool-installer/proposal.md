# 变更：优化 os_tool 安装与更新入口

## 背景
当前缺少统一的 os_tool 安装与更新入口，脚本分发与运行路径不一致。

## 变更内容
- 新增 `scripts/os_tool/install.sh`，从仓库下载 `scripts/os_tool` 并安装到 `/www/server/os_tool`，同时注册 `jht` 命令
- `jht` 命令启动 `scripts/os_tool/index.sh` 菜单
- `scripts/os_tool/index.sh` 增加“更新”菜单项，按 `netEnvCn` 选择镜像更新脚本

## 影响范围
- 影响规格: os-tool-installer (新增)
- 影响代码: `scripts/os_tool/index.sh`, `scripts/os_tool/install.sh`
