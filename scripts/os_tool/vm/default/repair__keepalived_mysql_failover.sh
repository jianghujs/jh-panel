#!/bin/bash

set -euo pipefail

PANEL_DIR="/www/server/jh-panel"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DEFAULT_SSH_PORT=10022
ASSUME_YES=0
SKIP_REMOTE=0
PEER_IP_OVERRIDE=""
PEER_PORT=""
SSH_BASE_OPTS=(-o StrictHostKeyChecking=no -o ConnectTimeout=5)
TOOLS_SH="${OS_TOOL_ROOT:-/www/server/jh-panel/scripts/os_tool}/tools.sh"
MSG_SH="/www/server/jh-panel/scripts/util/msg.sh"
declare -a PLANNED_STEPS=()
declare -a COMPLETED_STEPS=()
REMOTE_STEPS_PLANNED=0
REMOTE_EXECUTED=0

if [ ! -f "$TOOLS_SH" ]; then
  echo "缺少通用工具脚本：$TOOLS_SH"
  exit 1
fi
source "$TOOLS_SH"
if [ -f "$MSG_SH" ]; then
  source "$MSG_SH"
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --skip-remote)
      SKIP_REMOTE=1
      ;;
    --assume-yes)
      ASSUME_YES=1
      ;;
    --peer-ip)
      PEER_IP_OVERRIDE="$2"
      shift
      ;;
    --peer-port)
      PEER_PORT="$2"
      shift
      ;;
    -*)
      echo "未知参数: $1"
      exit 1
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
  shift
done

if [ -z "$PEER_PORT" ]; then
  PEER_PORT="$DEFAULT_SSH_PORT"
fi

record_step() {
  local desc="$1"
  COMPLETED_STEPS+=("$desc")
}

ensure_jq_installed || exit 1

if [ ! -d "$PANEL_DIR" ]; then
  echo "未找到面板目录 $PANEL_DIR"
  exit 1
fi

fetch_status_panel() {
  local json
  json=$(panel_python_call "获取 keepalived 状态" plugins/keepalived/index.py get_status_panel)
  local ok
  ok=$(echo "$json" | jq -r '.status')
  if [ "$ok" != "true" ]; then
    local msg
    msg=$(echo "$json" | jq -r '.msg // "未知错误"')
    echo "获取 keepalived 状态失败：$msg"
    exit 1
  fi
  echo "$json"
}

fetch_vrrp_form() {
  local json
  json=$(panel_python_call "获取 VRRP 表单" plugins/keepalived/index.py get_vrrp_form)
  local ok
  ok=$(echo "$json" | jq -r '.status')
  if [ "$ok" != "true" ]; then
    local msg
    msg=$(echo "$json" | jq -r '.msg // "未知错误"')
    echo "获取 VRRP 表单失败：$msg"
    exit 1
  fi
  echo "$json"
}

systemctl_is_active() {
  local service="$1"
  systemctl is-active "$service" >/dev/null 2>&1
}

show_local_service() {
  local service="$1"
  echo
  echo "[本机] systemctl status $service"
  systemctl status "$service" --no-pager || true
}

show_remote_service() {
  local host="$1"
  local port="$2"
  local service="$3"
  echo
  echo "[对端 $host] systemctl status $service"
  ssh -p "$port" "${SSH_BASE_OPTS[@]}" "root@$host" "systemctl status $service --no-pager" || true
}

remote_panel_cmd() {
  local host="$1"
  local port="$2"
  local label="$3"
  shift 3
  local cmd="cd $(printf '%q' "$PANEL_DIR") && $(printf '%q' "$PYTHON_BIN")"
  local arg
  for arg in "$@"; do
    cmd+=" $(printf '%q' "$arg")"
  done
  local output
  if ! output=$(ssh -p "$port" "${SSH_BASE_OPTS[@]}" "root@$host" "$cmd" 2>&1); then
    echo "[对端 $host] $label 失败：$output" >&2
    exit 1
  fi
  echo "$output"
}

remote_is_active() {
  local host="$1"
  local port="$2"
  local service="$3"
  ssh -p "$port" "${SSH_BASE_OPTS[@]}" "root@$host" "systemctl is-active $service" >/dev/null 2>&1
}

status_json=$(fetch_status_panel)
vip=$(echo "$status_json" | jq -r '.data.vip // .data.pure_vip // "-"')
vip_owned=$(echo "$status_json" | jq -r '.data.vip_owned // false')
priority=$(echo "$status_json" | jq -r '.data.priority // ""')

form_json=$(fetch_vrrp_form)
local_ip=$(echo "$form_json" | jq -r '.data.unicast_src_ip // ""')
peer_list_raw=$(echo "$form_json" | jq -r '.data.unicast_peer_list // ""')

peer_ip=""
if [ -n "$PEER_IP_OVERRIDE" ]; then
  peer_ip="$PEER_IP_OVERRIDE"
else
  while IFS= read -r line; do
    line=$(echo "$line" | xargs)
    if [ -n "$line" ] && [ "$line" != "$local_ip" ]; then
      peer_ip="$line"
      break
    fi
  done < <(printf '%s\n' "$peer_list_raw")
fi

echo "============================================"
echo "|- Keepalived + MySQL 双节点修复脚本启动"
echo "============================================"
if [ "$vip_owned" = "true" ]; then
  echo "|- 当前节点持有 VIP: $vip ✅"
else
  echo "|- 当前节点未持有 VIP: $vip ❌"
fi
echo "|- 本地单播 IP: ${local_ip:-无}"
if [ -n "$peer_list_raw" ]; then
  echo "|- 对端候选列表:"
  printf '   %s\n' "$peer_list_raw"
else
  echo "|- 对端候选列表: 无"
fi
if [ -n "$peer_ip" ]; then
  echo "|- 将尝试对端 IP: $peer_ip"
else
  echo "|- 无法解析对端 IP，远程步骤将被跳过"
fi

PLANNED_STEPS=(
  "本机：检测 mysql-apt 服务"
  "本机：确保 MySQL 角色为主库"
  "本机：设置 keepalived 优先级为 100"
  "本机：确保 keepalived 服务运行"
)
if [ -n "$peer_ip" ] && [ "$SKIP_REMOTE" -eq 0 ]; then
  REMOTE_STEPS_PLANNED=1
  PLANNED_STEPS+=(
    "对端：检测 mysql-apt 服务"
    "对端：初始化/确认主从配置"
    "对端：设置 keepalived 优先级为 90 并确保服务运行"
  )
fi

echo "--------------------------------------------"
echo "|- 本次将执行以下步骤："
for step in "${PLANNED_STEPS[@]}"; do
  echo "|  - $step"
done
proceed="y"
if [ "$ASSUME_YES" -eq 0 ]; then
  prompt "确认执行上述步骤吗？（默认y）[y/n]: " proceed "y"
fi
if [ "$proceed" != "y" ]; then
  echo "已取消执行。"
  exit 0
fi

echo "|- 正在检测本机 mysql-apt 服务..."
if systemctl_is_active "mysql-apt"; then
  echo "|- mysql-apt 服务已在运行 ✅"
else
  echo "|- 检测到 mysql-apt 未运行 ❌"
  choice="y"
  if [ "$ASSUME_YES" -eq 0 ]; then
    prompt "是否执行 mysql-apt 启动？（默认y）[y/n]: " choice "y"
  fi
  if [ "$choice" = "y" ]; then
    echo "|- 正在启动 mysql-apt..."
    start_output=$(panel_python_call "启动 mysql-apt" plugins/mysql-apt/index.py start)
    echo "$start_output"
  else
    echo "|- 已跳过 mysql-apt 启动 ❌"
  fi
fi
show_local_service "mysql-apt"
record_step "本机：mysql-apt 服务已确认"

echo "|- 正在确认本机主从状态..."
slave_json=$(panel_python_call "获取从库列表" plugins/mysql-apt/index.py get_slave_list)
slave_count=$(echo "$slave_json" | jq -r '.data | length')
if [ "$slave_count" -gt 0 ]; then
  echo "|- 检测到本机仍为从库 ❌"
  echo "$slave_json" | jq -r '.data[] | "  - 主库IP: \(.Master_Host) 端口: \(.Master_Port) IO: \(.Slave_IO_Running) SQL: \(.Slave_SQL_Running) 错误: \(.Last_Error // .Last_IO_Error // "-")"'
  choice="y"
  if [ "$ASSUME_YES" -eq 0 ]; then
    prompt "是否删除从配置并切换为主？（默认y）[y/n]: " choice "y"
  fi
  if [ "$choice" = "y" ]; then
    echo "|- 正在删除从配置并切换为主..."
    delete_result=$(panel_python_call "删除从配置" plugins/mysql-apt/index.py delete_slave)
    delete_ok=$(echo "$delete_result" | jq -r '.status // empty')
    if [ "$delete_ok" = "true" ]; then
      msg=$(echo "$delete_result" | jq -r '.msg // "删除成功"')
      echo "|- $msg ✅"
    else
      echo "|- 删除从配置失败：$delete_result ❌"
      exit 1
    fi
  else
    echo "|- 已跳过删除从配置 ❌"
  fi
else
  echo "|- 未检测到从库配置，本机视为主库 ✅"
fi
record_step "本机：MySQL 主库状态已确认"

echo "|- 正在设置本机 keepalived 优先级=100..."
keepalived_version="2.2.8"
if [ -f "/www/server/keepalived/version.pl" ]; then
  keepalived_version=$(cat /www/server/keepalived/version.pl | tr -d ' \t\r\n')
fi
priority_payload='priority:100'
priority_result=$(panel_python_call "设置 keepalived 优先级" plugins/keepalived/index.py set_priority "$keepalived_version" "$priority_payload")
priority_ok=$(echo "$priority_result" | jq -r '.status // empty')
if [ "$priority_ok" = "true" ]; then
  msg=$(echo "$priority_result" | jq -r '.msg // "设置成功"')
  echo "|- $msg ✅"
else
  echo "|- 设置优先级失败：$priority_result ❌"
  exit 1
fi
record_step "本机：keepalived 优先级已设为 100"

echo "|- 正在检测本机 keepalived 服务..."
if systemctl_is_active "keepalived"; then
  echo "|- keepalived 服务已在运行 ✅"
else
  echo "|- 检测到 keepalived 未运行 ❌"
  choice="y"
  if [ "$ASSUME_YES" -eq 0 ]; then
    prompt "是否启动 keepalived？（默认y）[y/n]: " choice "y"
  fi
  if [ "$choice" = "y" ]; then
    echo "|- 正在启动 keepalived..."
    start_output=$(panel_python_call "启动 keepalived" plugins/keepalived/index.py start)
    echo "$start_output"
  else
    echo "|- 已跳过 keepalived 启动 ❌"
  fi
fi
show_local_service "keepalived"
record_step "本机：keepalived 服务运行状态已确认"

handle_remote() {
  local host="$1"
  local port="$2"

  echo
  echo "|- 正在检查对端 $host mysql-apt 服务..."
  if remote_is_active "$host" "$port" "mysql-apt"; then
    echo "|- [对端 $host] mysql-apt 服务已在运行 ✅"
else
    echo "|- [对端 $host] mysql-apt 未运行 ❌"
    choice="y"
    if [ "$ASSUME_YES" -eq 0 ]; then
      prompt "是否在对端启动 mysql-apt？（默认y）[y/n]: " choice "y"
    fi
    if [ "$choice" = "y" ]; then
      echo "|- 正在对端 $host 启动 mysql-apt..."
      start_output=$(remote_panel_cmd "$host" "$port" "启动 mysql-apt" plugins/mysql-apt/index.py start)
      echo "[对端 $host] $start_output"
    else
      echo "|- 已跳过对端 mysql-apt 启动 ❌"
    fi
  fi
  show_remote_service "$host" "$port" "mysql-apt"
  record_step "对端：mysql-apt 服务已确认 ($host)"

  echo
  echo "|- 正在检查对端 $host 主从状态..."
  peer_slave_json=$(remote_panel_cmd "$host" "$port" "获取对端从库列表" plugins/mysql-apt/index.py get_slave_list)
  peer_slave_count=$(echo "$peer_slave_json" | jq -r '.data | length')
  if [ "$peer_slave_count" -gt 0 ]; then
    echo "|- [对端 $host] 已存在从库配置 ✅"
else
    echo "|- [对端 $host] 未检测到主从同步 ❌"
    choice="y"
    if [ "$ASSUME_YES" -eq 0 ]; then
      prompt "是否执行 init_slave_status 初始化从库？（默认y）[y/n]: " choice "y"
    fi
    if [ "$choice" = "y" ]; then
      echo "|- 正在对端 $host 初始化从库..."
      init_result=$(remote_panel_cmd "$host" "$port" "初始化从库" plugins/mysql-apt/index.py init_slave_status)
      init_ok=$(echo "$init_result" | jq -r '.status // empty')
      msg=$(echo "$init_result" | jq -r '.msg // "无返回信息"')
      if [ "$init_ok" = "true" ]; then
        echo "|- [对端 $host] 初始化从库成功：$msg ✅"
      else
        echo "|- [对端 $host] 初始化从库失败：$msg ❌"
        exit 1
      fi
    else
      echo "|- 已跳过对端从库初始化 ❌"
    fi
  fi
  record_step "对端：主从配置已确认/初始化 ($host)"

  echo
  echo "|- 正在设置对端 $host keepalived 优先级=90..."
  remote_version=$(ssh -p "$port" "${SSH_BASE_OPTS[@]}" "root@$host" "cat /www/server/keepalived/version.pl" 2>/dev/null | tr -d ' \t\r\n')
  if [ -z "$remote_version" ]; then
    remote_version="$keepalived_version"
  fi
  remote_priority_result=$(remote_panel_cmd "$host" "$port" "设置对端 keepalived 优先级" plugins/keepalived/index.py set_priority "$remote_version" 'priority:90')
  remote_priority_ok=$(echo "$remote_priority_result" | jq -r '.status // empty')
  if [ "$remote_priority_ok" = "true" ]; then
    msg=$(echo "$remote_priority_result" | jq -r '.msg // "设置成功"')
    echo "|- [对端 $host] $msg ✅"
  else
    echo "|- [对端 $host] 设置优先级失败：$remote_priority_result ❌"
    exit 1
  fi

  echo
  echo "|- 正在检查对端 $host keepalived 服务..."
  if remote_is_active "$host" "$port" "keepalived"; then
    echo "|- [对端 $host] keepalived 服务已在运行 ✅"
else
    echo "|- [对端 $host] keepalived 未运行 ❌"
    choice="y"
    if [ "$ASSUME_YES" -eq 0 ]; then
      prompt "是否在对端启动 keepalived？（默认y）[y/n]: " choice "y"
    fi
    if [ "$choice" = "y" ]; then
      echo "|- 正在对端 $host 启动 keepalived..."
      start_output=$(remote_panel_cmd "$host" "$port" "启动对端 keepalived" plugins/keepalived/index.py start)
      echo "[对端 $host] $start_output"
    else
      echo "|- 已跳过对端 keepalived 启动 ❌"
    fi
  fi
  show_remote_service "$host" "$port" "keepalived"
  echo "|- 正在重启对端 $host keepalived，确保优先级生效..."
  restart_output=$(remote_panel_cmd "$host" "$port" "重启对端 keepalived" plugins/keepalived/index.py restart)
  echo "|- [对端 $host] keepalived 重启结果：$restart_output"
  record_step "对端：keepalived 服务已重启以保证漂移 ($host)"
  record_step "对端：keepalived 优先级与服务状态已确认 ($host)"
  REMOTE_EXECUTED=1
}

if [ -n "$peer_ip" ] && [ "$SKIP_REMOTE" -eq 0 ]; then
  echo
  echo "--------------------------------------------"
  echo "|- 准备处理远程节点 $peer_ip"
  peer_port_input="$PEER_PORT"
  if [ "$ASSUME_YES" -eq 0 ]; then
    prompt "请输入对端 SSH 端口(默认: $PEER_PORT): " peer_port_input "$PEER_PORT"
  fi
  peer_port_input=$(echo "$peer_port_input" | xargs)
  if [ -n "$peer_port_input" ]; then
    PEER_PORT="$peer_port_input"
  fi
  choice="y"
  if [ "$ASSUME_YES" -eq 0 ]; then
    prompt "是否继续处理对端节点？（默认y）[y/n]: " choice "y"
  fi
  if [ "$choice" = "y" ]; then
    handle_remote "$peer_ip" "$PEER_PORT"
  else
    echo "× 已根据用户选择跳过对端节点"
  fi
else
  echo
  echo "|- 跳过对端节点步骤 ❌"
fi

echo
echo "============================================"
echo "|- 最终状态汇总"
final_status=$(fetch_status_panel)
final_vip_owned=$(echo "$final_status" | jq -r '.data.vip_owned // false')
final_priority=$(echo "$final_status" | jq -r '.data.priority // ""')
  if [ "$final_vip_owned" = "true" ]; then
    show_info "|- 当前 VIP $vip 已被本机持有 ✅"
  else
    show_error "|- 当前 VIP $vip 仍未被本机持有，请继续排查 ❌"
  fi
echo "|- keepalived 优先级：$final_priority"
show_info "===================== 修复流程完成 ✅ ====================="
echo "|- 后续建议："
echo "|  1. 再次确认业务读写正常、VIP 可访问"
echo "|  2. 如远端节点被跳过，请手动执行脚本处理对端"
echo "=========================================================="
echo "|- 执行步骤回顾："
if [ "${#COMPLETED_STEPS[@]}" -eq 0 ]; then
  echo "|  （无步骤记录）"
else
  for step in "${COMPLETED_STEPS[@]}"; do
    show_info "|  $step ✅"
  done
fi
if [ "$REMOTE_STEPS_PLANNED" -eq 1 ] && [ "$REMOTE_EXECUTED" -eq 0 ]; then
  show_error "  × 对端节点步骤未执行（已跳过或失败）"
fi
