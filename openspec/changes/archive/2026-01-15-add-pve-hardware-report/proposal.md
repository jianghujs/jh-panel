# 变更：添加 PVE 硬件全面健康报告

## 为什么
PVE 环境目前仅提供 SSD/M2 健康检查脚本，使管理员对 CPU、内存、IO、温度和电源风险一无所知。需要一个统一的硬件报告来在故障触发中断之前发现隐藏的问题。

## 变更内容
- 为 PVE 主机引入脚本驱动的硬件报告，聚合 CPU/内存/磁盘/网络/温度/风扇/电源信息并标记风险。
- 复用现有的 `monitor__disk_health_check.py` SMART 能力并扩展到其它监控项，输出结构化报告。
- 集成到 PVE OS 工具菜单，提供人机可读的橙色/红色风险提示。

## 影响范围
- 受影响的规格：`pve-hardware-reporting`
- 受影响的代码：`scripts/os_tool/pve/index__monitor.sh`、`scripts/os_tool/pve/monitor__disk_health_check.py`（复用）、新的报告脚本 + 共享工具、可能的系统 API。
