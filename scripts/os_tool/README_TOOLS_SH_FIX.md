# tools.sh 远程加载修复说明

## 问题描述

当通过远程下载方式运行脚本时（如 `wget ... | bash`），子脚本中的 `source /www/server/jh-panel/scripts/os_tool/tools.sh` 会失败，因为该路径在远程执行环境中不存在。

## 解决方案（推荐）

**在父脚本 `index.sh` 中统一下载 `tools.sh`**，避免每个子脚本重复下载。

### 1. 修改父脚本 `{osType}/index.sh`

在脚本开头添加 tools.sh 下载逻辑：

```bash
#!/bin/bash
set -e

# 在远程模式下，预先下载 tools.sh 供子脚本使用
if [ "$USE_PANEL_SCRIPT" != "true" ]; then
    if [ ! -f "/tmp/vm_tools.sh" ]; then
        toolsURL=$(echo $URLBase | sed 's|/{osType}/.*$|/tools.sh|')
        echo "正在下载 tools.sh 从 ${toolsURL}"
        wget -nv -O /tmp/vm_tools.sh ${toolsURL}
    fi
fi

# ... 其余代码
```

### 2. 修改子脚本（如 `index__monitor.sh`）

简化 source 逻辑：

```bash
#!/bin/bash
set -e

# 加载 tools.sh（已由父脚本 index.sh 下载）
if [ "$USE_PANEL_SCRIPT" == "true" ]; then
    source /www/server/jh-panel/scripts/os_tool/tools.sh
else
    source /tmp/vm_tools.sh
fi

# ... 其余代码
```

## 工作原理

1. **本地模式** (`USE_PANEL_SCRIPT=true`): 直接 source 本地文件
2. **远程模式**: 
   - 从 `URLBase` 环境变量推导出 `tools.sh` 的 URL
   - 下载到 `/tmp/vm_tools.sh`（使用缓存，避免重复下载）
   - source 下载的文件

## URL 转换示例

| URLBase | toolsURL |
|---------|----------|
| `https://.../os_tool/pve/default` | `https://.../os_tool/tools.sh` |
| `https://.../os_tool/vm/jammy` | `https://.../os_tool/tools.sh` |
| `https://.../os_tool/host/focal` | `https://.../os_tool/tools.sh` |

## 已修复的脚本

### PVE
- [x] `scripts/os_tool/pve/index.sh` - 统一下载 tools.sh
- [x] `scripts/os_tool/pve/index__monitor.sh` - 简化 source 逻辑

## 待修复的脚本

以下脚本也有同样的问题，建议使用相同的修复方案：

- [ ] `scripts/os_tool/vm/default/index__repair.sh`
- [ ] `scripts/os_tool/vm/default/index__other.sh`
- [ ] `scripts/os_tool/vm/default/index__backup.sh`
- [ ] `scripts/os_tool/vm/default/index__resize.sh`
- [ ] `scripts/os_tool/vm/default/index__monitor.sh`
- [ ] `scripts/os_tool/vm/default/index__ssh_keygen.sh`
- [ ] `scripts/os_tool/vm/default/index__arrange.sh`
- [ ] `scripts/os_tool/vm/default/index__switch.sh`
- [ ] `scripts/os_tool/vm/default/index__migrate.sh`
- [ ] `scripts/os_tool/vm/default/switch__generate_online.sh`

## 注意事项

1. 确保 `URLBase` 环境变量在父脚本中正确设置
2. 使用 `/tmp/vm_tools.sh` 作为缓存文件名，避免重复下载
3. 在远程模式下，第一次下载后会缓存，后续调用直接使用缓存

