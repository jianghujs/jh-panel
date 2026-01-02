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
TOOLS_SH="/www/server/jh-panel/scripts/os_tool/tools.sh"

if [ ! -f "$TOOLS_SH" ]; then
  echo "缺少通用工具脚本：$TOOLS_SH"
  exit 1
fi
source "$TOOLS_SH"

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

confirm() {
  local prompt="$1"
  local default="${2:-n}"
  local choice
  if [ "$ASSUME_YES" -eq 1 ]; then
    echo "$prompt -> 自动确认 YES"
    return 0
  fi
  if [ "$default" = "y" ]; then
    prompt+=" (Y/n): "
  else
    prompt+=" (y/N): "
  fi
  while true; do
    read -r -p "$prompt" choice
    choice=${choice:-$default}
    case "$choice" in
      y|Y)
        return 0
        ;;
      n|N)
        return 1
        ;;
      *)
        echo "请输入 y 或 n。"
        ;;
    esac
  done
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

echo "=== Keepalived + MySQL 双节点修复脚本 ==="
if [ "$vip_owned" = "true" ]; then
  echo "VIP: $vip (当前节点持有)"
else
  echo "VIP: $vip (当前节点未持有)"
fi
echo "本地单播 IP: ${local_ip:-无}"
if [ -n "$peer_list_raw" ]; then
  echo "对端候选列表:"
  printf '%s\n' "$peer_list_raw"
else
  echo "对端候选列表: 无"
fi
if [ -n "$peer_ip" ]; then
  echo "将尝试对端 IP: $peer_ip"
else
  echo "无法解析对端 IP，远程修复步骤将被跳过。"
fi

echo
echo ">>> 检查 mysql-apt 服务"
if systemctl_is_active "mysql-apt"; then
  echo "mysql-apt 服务已在运行。"
else
  echo "检测到 mysql-apt 未运行。"
  if confirm "是否执行 mysql-apt 启动？" "y"; then
    start_output=$(panel_python_call "启动 mysql-apt" plugins/mysql-apt/index.py start)
    echo "启动 mysql-apt 输出：$start_output"
  else
    echo "已跳过 mysql-apt 启动。"
  fi
fi
show_local_service "mysql-apt"

echo
echo ">>> 检查本机主从状态"
slave_json=$(panel_python_call "获取从库列表" plugins/mysql-apt/index.py get_slave_list)
slave_count=$(echo "$slave_json" | jq -r '.data | length')
if [ "$slave_count" -gt 0 ]; then
  echo "检测到本机仍为从库："
  echo "$slave_json" | jq -r '.data[] | "  - 主库IP: \(.Master_Host) 端口: \(.Master_Port) IO: \(.Slave_IO_Running) SQL: \(.Slave_SQL_Running) 错误: \(.Last_Error // .Last_IO_Error // "-")"'
  if confirm "是否删除从配置并切换为主？" "y"; then
    delete_result=$(panel_python_call "删除从配置" plugins/mysql-apt/index.py delete_slave)
    delete_ok=$(echo "$delete_result" | jq -r '.status // empty')
    if [ "$delete_ok" = "true" ]; then
      msg=$(echo "$delete_result" | jq -r '.msg // "删除成功"')
      echo "$msg"
    else
      echo "删除从配置失败：$delete_result"
      exit 1
    fi
  else
    echo "已跳过删除从配置。"
  fi
else
  echo "未检测到从库配置，本机视为主库。"
fi

echo
echo ">>> 设置 keepalived 优先级"
keepalived_version="2.2.8"
if [ -f "/www/server/keepalived/version.pl" ]; then
  keepalived_version=$(cat /www/server/keepalived/version.pl | tr -d ' \t\r\n')
fi
priority_payload='{"priority":"100"}'
priority_result=$(panel_python_call "设置 keepalived 优先级" plugins/keepalived/index.py set_priority "$keepalived_version" "$priority_payload")
priority_ok=$(echo "$priority_result" | jq -r '.status // empty')
if [ "$priority_ok" = "true" ]; then
  msg=$(echo "$priority_result" | jq -r '.msg // "设置成功"')
  echo "$msg"
else
  echo "设置优先级失败：$priority_result"
  exit 1
fi

echo
echo ">>> 检查 keepalived 服务"
if systemctl_is_active "keepalived"; then
  echo "keepalived 服务已在运行。"
else
  echo "检测到 keepalived 未运行。"
  if confirm "是否启动 keepalived？" "y"; then
    start_output=$(panel_python_call "启动 keepalived" plugins/keepalived/index.py start)
    echo "启动 keepalived 输出：$start_output"
  else
    echo "已跳过 keepalived 启动。"
  fi
fi
show_local_service "keepalived"

handle_remote() {
  local host="$1"
  local port="$2"

  echo
  echo ">>> 对端 $host 检查 mysql-apt 服务"
  if remote_is_active "$host" "$port" "mysql-apt"; then
    echo "[对端 $host] mysql-apt 服务已在运行。"
  else
    echo "[对端 $host] mysql-apt 未运行。"
    if confirm "是否在对端启动 mysql-apt？" "y"; then
      start_output=$(remote_panel_cmd "$host" "$port" "启动 mysql-apt" plugins/mysql-apt/index.py start)
      echo "[对端 $host] 启动 mysql-apt 输出：$start_output"
    else
      echo "已跳过对端 mysql-apt 启动。"
    fi
  fi
  show_remote_service "$host" "$port" "mysql-apt"

  echo
  echo ">>> 对端 $host 主从检查"
  peer_slave_json=$(remote_panel_cmd "$host" "$port" "获取对端从库列表" plugins/mysql-apt/index.py get_slave_list)
  peer_slave_count=$(echo "$peer_slave_json" | jq -r '.data | length')
  if [ "$peer_slave_count" -gt 0 ]; then
    echo "[对端 $host] 已存在从库配置。"
  else
    echo "[对端 $host] 未检测到主从同步。"
    if confirm "是否执行 init_slave_status 初始化从库？" "y"; then
      init_result=$(remote_panel_cmd "$host" "$port" "初始化从库" plugins/mysql-apt/index.py init_slave_status)
      init_ok=$(echo "$init_result" | jq -r '.status // empty')
      msg=$(echo "$init_result" | jq -r '.msg // "无返回信息"')
      if [ "$init_ok" = "true" ]; then
        echo "[对端 $host] 初始化从库成功：$msg"
      else
        echo "[对端 $host] 初始化从库失败：$msg"
        exit 1
      fi
    else
      echo "已跳过对端从库初始化。"
    fi
  fi

  echo
  echo ">>> 对端 $host 设置 keepalived 优先级"
  remote_version=$(ssh -p "$port" "${SSH_BASE_OPTS[@]}" "root@$host" "cat /www/server/keepalived/version.pl" 2>/dev/null | tr -d ' \t\r\n')
  if [ -z "$remote_version" ]; then
    remote_version="$keepalived_version"
  fi
  remote_priority_result=$(remote_panel_cmd "$host" "$port" "设置对端 keepalived 优先级" plugins/keepalived/index.py set_priority $remote_version '{"priority":"90"}')
  remote_priority_ok=$(echo "$remote_priority_result" | jq -r '.status // empty')
  if [ "$remote_priority_ok" = "true" ]; then
    msg=$(echo "$remote_priority_result" | jq -r '.msg // "设置成功"')
    echo "[对端 $host] $msg"
  else
    echo "[对端 $host] 设置优先级失败：$remote_priority_result"
    exit 1
  fi

  echo
  echo ">>> 对端 $host 检查 keepalived 服务"
  if remote_is_active "$host" "$port" "keepalived"; then
    echo "[对端 $host] keepalived 服务已在运行。"
  else
    echo "[对端 $host] keepalived 未运行。"
    if confirm "是否在对端启动 keepalived？" "y"; then
      start_output=$(remote_panel_cmd "$host" "$port" "启动对端 keepalived" plugins/keepalived/index.py start)
      echo "[对端 $host] 启动 keepalived 输出：$start_output"
    else
      echo "已跳过对端 keepalived 启动。"
    fi
  fi
  show_remote_service "$host" "$port" "keepalived"
}

if [ -n "$peer_ip" ] && [ "$SKIP_REMOTE" -eq 0 ]; then
  echo
  echo ">>> 远程节点处理"
  if [ "$ASSUME_YES" -eq 0 ]; then
    read -r -p "请输入对端 SSH 端口(默认: $PEER_PORT): " port_input
    port_input=$(echo "$port_input" | xargs)
    if [ -n "$port_input" ]; then
      PEER_PORT="$port_input"
    fi
  fi
  if confirm "是否继续处理对端节点？" "y"; then
    handle_remote "$peer_ip" "$PEER_PORT"
  else
    echo "已根据用户选择跳过对端节点。"
  fi
else
  echo
  echo "跳过对端节点步骤。"
fi

echo
echo ">>> 最终状态"
final_status=$(fetch_status_panel)
final_vip_owned=$(echo "$final_status" | jq -r '.data.vip_owned // false')
final_priority=$(echo "$final_status" | jq -r '.data.priority // ""')
if [ "$final_vip_owned" = "true" ]; then
  echo "当前 VIP $vip 已持有。"
else
  echo "当前 VIP $vip 未被本机持有。"
fi
echo "keepalived 优先级：$final_priority"
echo "修复流程完成。"
