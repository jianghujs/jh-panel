## 1. 实现
- [x] 1.1 新增 `scripts/os_tool/install.sh`，从仓库下载脚本安装到 `/www/server/os_tool`，并注册 `jht` 命令
- [x] 1.2 更新 `scripts/os_tool/index.sh` 增加“更新”菜单并实现覆盖式更新
- [x] 1.3 校验 `jht` 能启动菜单并能运行已安装的脚本

## 2. 验证
- [x] 2.1 运行 `bash scripts/os_tool/install.sh` 验证安装流程与命令注册
- [x] 2.2 运行 `jht` 进入菜单并执行任一子脚本验证可用性
- [x] 2.3 在菜单中执行“更新”验证 `/www/server/os_tool` 下脚本被刷新且保留其他文件
