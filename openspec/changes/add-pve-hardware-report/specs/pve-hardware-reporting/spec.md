## ADDED Requirements
### Requirement: PVE 硬件健康报告入口
PVE OS 工具 SHALL 暴露“硬件健康报告”入口，允许管理员从 `index__monitor.sh` 触发脚本生成一次性报告，并复用 `tools.sh` 的本地/远程下载机制以保持与其他监控工具一致的体验。

#### Scenario: 交互式入口
- **WHEN** 用户运行 `scripts/os_tool/pve/index__monitor.sh`
- **THEN** 菜单中展示“硬盘健康检查”“硬件健康报告”两个选项，默认光标位于第二项，选择后通过 `download_and_run_py` 执行新脚本。

#### Scenario: 面板/远程共用
- **WHEN** PVE 工具在 `USE_PANEL_SCRIPT=true` 与默认下载模式下执行
- **THEN** “硬件健康报告”入口自动使用相同的脚本目录、权限检测、Python 依赖安装流程，并向用户打印脚本所在路径和日志保存路径。

### Requirement: 硬件全量巡检
硬件报告脚本 SHALL 聚合 CPU、内存、磁盘容量、磁盘 SMART、磁盘 IO、网络接口、温度（CPU/主板/磁盘/NVMe）、风扇、电源等信息，复用 `monitor__disk_health_check.py` 中的 SMART/NVMe 解析逻辑，并为缺失的传感器提供“未知”提示。

#### Scenario: 资源与容量
- **WHEN** 脚本运行
- **THEN** 它收集以下数据并记录采集命令：
  1. CPU：`mpstat`/`top` 的平均使用率、负载、TOP5 进程。
  2. 内存：总量、使用量、swap、buffer/cache。
  3. 磁盘占用：`df -h`、ZFS/LVM/ceph（若存在）汇总，并指明 >512G 的数据盘。
  4. 磁盘 IO：`iostat -dx` 或 `nvme smart-log` 的 I/O 响应时间、队列深度、饱和度。

#### Scenario: SMART 与 NVMe 健康
- **WHEN** 系统含 SATA/SAS/NVMe 盘
- **THEN** 脚本遍历 `/dev/sd*`、`/dev/nvme*`，重用现有 SMART 解析函数，输出寿命、重新分配扇区、温度等关键指标，并在 SMART 报告不可访问时写入原因并标记 Unknown。

#### Scenario: 网络/传感器/风扇/电源
- **WHEN** 脚本运行
- **THEN** 它：
  1. 调用 `ip -s link` + `ethtool`（可用时）统计各网卡的 up/down 状态、速率、错误计数。
  2. 使用 `sensors`、`ipmitool sensor`（存在时）读取 CPU、主板、VRM、风扇转速、电源温度/电压。
  3. 从 `ipmitool chassis` or `/sys/class/hwmon` 提取风扇/电源状态，缺失命令时说明“IPMI unavailable”。
  4. 记录网卡是否绑定、高可用链路状态，并合并入最终 JSON。

### Requirement: 风险分级与输出
硬件报告 SHALL 计算 Normal/Warning/Critical 三级状态（绿色/橙色/红色），可通过配置/参数覆盖默认阈值（默认警告 80%、异常 90%，温度警告 70℃、异常 80℃），并输出 ANSI 彩色终端报告 + 无色日志/JSON，帮助管理员追踪历史。

#### Scenario: 阈值判定与颜色
- **WHEN** 采集到任一指标
- **THEN** 脚本根据默认阈值或 `--warn-*`/`--crit-*` 参数判断状态，使用 `color_text` 输出彩色文本，同时在结构化 JSON 中写入 `status`, `value`, `thresholds`，以便后续程序消费。

#### Scenario: 隐患提示与摘要
- **WHEN** 任意指标处于 Warning 或 Critical
- **THEN** 脚本在报告顶部生成“硬件隐患”摘要列表，按照严重度排序，并引用对应指标的详情链接（节标题 + 设备名），使管理员无需翻阅原始命令即可定位。

#### Scenario: 容错与持久化
- **WHEN** 某个命令缺失或超时
- **THEN** 执行 fallback（例如跳过风扇读数）并在报告中写入 `status=unknown` 和错误信息；脚本仍然生成报告文件 `logs/pve/hardware_report_<timestamp>.log` 与 `logs/pve/hardware_report.json`，旧日志按日期滚动保留至少最近 5 份。
