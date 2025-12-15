# 变更：Keepalived 插件新增 VRRP 配置面板

## 原因
- 现在管理员只能手动或通过模板直接修改 `/www/server/keepalived/etc/keepalived/keepalived.conf`，在调整默认 VRRP 参数时容易出错。
- 通过一个专用面板提供表单控件，可以让用户快速修改网络接口、虚拟 IP、单播参数、优先级和验证码，而无需手动定位配置文件。

## 变更内容
- 新增后端辅助函数（类似 `getMyDbPos` 的解析方式），读取/写入 `vrrp_instance VI_MYSQL` 区块，并提供获取与保存字段的 API。
- 在 Keepalived 插件 UI 中添加新的菜单项，展示表单界面（样式可参考 xtrabackup-inc、jianghujs 等插件），并与上述 API 打通。
- 加入前端校验与默认值（单播默认勾选、优先级必须为数字），保存后给出提示，无需用户手动控制服务。

## 影响
- 受影响的规范：keepalived-config-panel（新增能力）
- 受影响的代码：`plugins/keepalived/index.py`、`plugins/keepalived/index.html`、`plugins/keepalived/js/keepalived.js` 及相关模板/静态资源。
- 用户仍可通过原有编辑器修改高级配置；新面板仅覆盖默认实例里的特定 VRRP 字段。

## 假设 / 待确认
- 默认存在 `vrrp_instance VI_MYSQL` 配置块；若缺失则友好报错，不做侵入式修改。
- `unicast_peer` 按行输入，每行一个 IP；多 IP 通过换行分隔，再写回块中。
