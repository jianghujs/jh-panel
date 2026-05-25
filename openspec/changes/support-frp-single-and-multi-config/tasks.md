## 1. Backend And Runtime

- [x] 1.1 在 `plugins/frp/index.py` 中新增配置模式元数据读写能力，并为服务端/客户端分别返回当前 `single` / `multi` 模式
- [x] 1.2 在 `plugins/frp/index.py` 中补充多配置目录的列表、新建、读取、保存、删除接口，同时保留 `frps.ini` / `frpc.ini` 单文件接口兼容
- [x] 1.3 重构 frp 启停与状态逻辑，改为通过统一 wrapper 按模式启动固定单文件或遍历 `frps.d/*.ini`、`frpc.d/*.ini`
- [x] 1.4 更新 `plugins/frp/init.d/*.tpl` 与安装流程，确保 systemd/init.d 都调用新的模式感知 wrapper，并在升级时刷新 service 文件

## 2. Frontend Config Panel

- [x] 2.1 调整 `plugins/frp/index.html`，将现有固定单文件入口改为服务端/客户端模式感知的配置管理入口
- [x] 2.2 在 `plugins/frp/js/frp.js` 中实现模式读取与切换交互，支持分别切换服务端/客户端的 `single` / `multi` 模式
- [x] 2.3 在 `plugins/frp/js/frp.js` 中实现多配置模式下的文件列表、模板新建、编辑、保存、删除与失败提示
- [x] 2.4 保持单配置文件模式下的编辑体验兼容，确保旧用户仍可直接编辑 `frps.ini` / `frpc.ini`

## 3. Validation And Docs

- [x] 3.1 补充 frp 插件帮助说明，写清单文件模式、多文件模式、切换规则和目录约定
- [x] 3.2 手动验证升级默认兼容路径：无模式文件时默认 single，旧 `frps.ini` / `frpc.ini` 可继续读取和启动
- [x] 3.3 手动验证多配置路径：创建多个 `.ini` 文件、列表展示、保存删除、按模式启动与停止
- [x] 3.4 手动验证模式切换与异常路径：空目录启动失败、非法文件名失败、从 multi 切回 single 后恢复旧配置运行
