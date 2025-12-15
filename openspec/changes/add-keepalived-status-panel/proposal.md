# 变更：Keepalived 插件新增状态面板

## 原因
- 当前 Keepalived 插件缺少状态总览，管理员无法直接在面板内确认 VIP 归属、服务日志或关键运行指标，排查故障需要登录系统执行命令。
- 参考 rsyncd 的“实时服务”面板体验，为 Keepalived 提供状态面板可提升可观测性和运维效率。

## 变更内容
- 新增“状态面板”菜单页，展示与 rsyncd 插件类似的服务状态卡片：VIP 是否归属本机、 keepalived 服务日志滚动视图及后续可扩展的运行信息（如进程状态、配置摘要等）。
- 扩展后端接口获取 VIP 状态、日志片段及其它指标，前端轮询/刷新展示，保持样式与现有插件一致。

## 影响
- 规格：keepalived-status-panel（新能力）
- 代码：`plugins/keepalived/index.py`、`plugins/keepalived/index.html`、`plugins/keepalived/js/keepalived.js` 以及可能新增的模板资源。

## 开放问题
- 日志展示是否限制行数或支持下载？
- 是否需要控制刷新频率/自动刷新间隔？默认可采用手动刷新+轻量自动轮询。
