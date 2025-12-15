# 任务

- [x] **后端 VRRP 配置辅助**
  - 在 keepalived 的 index.py 中新增安全读取 `vrrp_instance VI_MYSQL` 区块的辅助函数，解析接口/虚拟 IP/单播/优先级/验证码并提供 `get_vrrp_form`、`save_vrrp_form` 两个返回 JSON 的插件动作。
  - 验证：执行 `python3 plugins/keepalived/index.py get_vrrp_form {}` 能输出默认模板的结构；保存后再次读取可成功回读。
- [x] **UI 面板与数据绑定**
  - 在 `index.html` 中插入“配置面板”标签，在 `js/keepalived.js` 中渲染表单、调用后端接口、绑定复选框与输入框，整体样式参考 xtrabackup-inc/jianghujs。
  - 验证：打开 keepalived 插件页面，进入新标签页，表单应填充当前配置数据且默认勾选单播。
- [x] **提交流程与提示**
  - 实现前端校验（必填、优先级数字、单播开启时校验 IP），展示保存成功/失败信息，并说明是否需要重载服务。
  - 验证：修改字段后提交，确认提示信息，再次打开面板确认文件内容一致。
