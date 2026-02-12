#!/bin/bash
source /www/server/jh-panel/scripts/util/msg.sh

KEEPALIVED_INIT="/www/server/keepalived/init.d/keepalived"
KEEPALIVED_CONF="/www/server/keepalived/etc/keepalived/keepalived.conf"
NOTIFY_MASTER="/www/server/keepalived/scripts/notify_master.py"
NOTIFY_BACKUP="/www/server/keepalived/scripts/notify_backup.py"
DEFAULT_REMOTE_PORT="10022"
PANEL_DIR="/www/server/jh-panel"

print_plan() {
  echo "=========================="
  echo "即将执行以下流程："
  echo "1. 确保本地、对端的 keepalived 启动"
  echo "2. 确认 VIP 在本地还是对端"
  echo "3. 如果当前为备，执行对端的 keepalived 脚本确保漂移到本地"
  # echo "4. 在本地执行 /www/server/keepalived/scripts/notify_master.py"
  # echo "5. 在对端执行 /www/server/keepalived/scripts/notify_backup.py"
  echo "=========================="
}

remote_exec() {
  local cmd="$1"
  ssh -p "${remote_port}" root@"${remote_ip}" "${cmd}"
}

ensure_local_keepalived() {
  echo "|- 检查本地 keepalived 状态..."
  if ! pgrep -x keepalived >/dev/null; then
    echo "|- 本地 keepalived 未运行，正在启动..."
    bash "${KEEPALIVED_INIT}" start
    sleep 1
  fi
  if ! pgrep -x keepalived >/dev/null; then
    show_error "错误: 本地 keepalived 启动失败"
    exit 1
  fi
  show_info "|- 本地 keepalived 运行中✅"
}

ensure_remote_keepalived() {
  echo "|- 检查对端 keepalived 状态..."
  remote_exec "pgrep -x keepalived >/dev/null || bash ${KEEPALIVED_INIT} start"
  if [ $? -ne 0 ]; then
    show_error "错误: 对端 keepalived 启动失败"
    exit 1
  fi
  remote_exec "pgrep -x keepalived >/dev/null"
  if [ $? -ne 0 ]; then
    show_error "错误: 对端 keepalived 未运行"
    exit 1
  fi
  show_info "|- 对端 keepalived 运行中✅"
}

update_local_priority() {
  echo "|- 设置本地 keepalived priority=100..."
  local update_output
  update_output=$(python3 "${PANEL_DIR}/plugins/keepalived/tool.py" update_priority VI_1 100)
  if [ $? -ne 0 ]; then
    show_error "错误: 本地 keepalived priority 修改失败"
    exit 1
  fi
  echo "${update_output}" | grep -q '\"status\"[[:space:]]*:[[:space:]]*true'
  if [ $? -ne 0 ]; then
    show_error "错误: 本地 keepalived priority 修改失败: ${update_output}"
    exit 1
  fi
  show_info "|- 本地 keepalived priority 已设置为 100✅"
}

update_remote_priority() {
  echo "|- 设置对端 keepalived priority=90..."
  local update_output
  update_output=$(remote_exec "python3 ${PANEL_DIR}/plugins/keepalived/tool.py update_priority VI_1 90")
  if [ $? -ne 0 ]; then
    show_error "错误: 对端 keepalived priority 修改失败"
    exit 1
  fi
  echo "${update_output}" | grep -q '\"status\"[[:space:]]*:[[:space:]]*true'
  if [ $? -ne 0 ]; then
    show_error "错误: 对端 keepalived priority 修改失败: ${update_output}"
    exit 1
  fi
  show_info "|- 对端 keepalived priority 已设置为 90✅"
}

get_vips() {
  if [ ! -f "${KEEPALIVED_CONF}" ]; then
    show_error "错误: keepalived 配置文件不存在: ${KEEPALIVED_CONF}"
    exit 1
  fi
  awk '/virtual_ipaddress/{flag=1;next} /}/{if(flag){flag=0}} flag {print $1}' "${KEEPALIVED_CONF}" | cut -d/ -f1 | sed '/^$/d'
}

detect_vip_location() {
  local_has_vip=0
  remote_has_vip=0
  for vip in ${vip_list}; do
    if ip -o addr show | grep -w "${vip}" >/dev/null; then
      local_has_vip=1
    fi
    remote_exec "ip -o addr show | grep -w '${vip}' >/dev/null"
    if [ $? -eq 0 ]; then
      remote_has_vip=1
    fi
  done
}

check_vip_location() {
  detect_vip_location
  echo "|- VIP 列表: ${vip_list}"
  if [ ${local_has_vip} -eq 1 ] && [ ${remote_has_vip} -eq 1 ]; then
    show_error "警告: VIP 同时存在于本地与对端"
  elif [ ${local_has_vip} -eq 1 ]; then
    show_info "|- VIP 在本地✅"
  elif [ ${remote_has_vip} -eq 1 ]; then
    show_info "|- VIP 在对端✅"
  else
    show_error "错误: 未检测到 VIP"
    exit 1
  fi
}

wait_for_local_vip() {
  local retry=0
  local max_retry=5
  while [ ${retry} -lt ${max_retry} ]; do
    detect_vip_location
    if [ ${local_has_vip} -eq 1 ]; then
      return 0
    fi
    sleep 1
    retry=$((retry + 1))
  done
  return 1
}

print_plan
prompt "确认执行修复 keepalived 并确保本机为主吗？（默认n）[y/n]: " choice "n"
if [ "${choice}" != "y" ]; then
  echo "已取消"
  exit 0
fi

if ! command -v ssh >/dev/null; then
  show_error "错误: 未找到 ssh 命令"
  exit 1
fi

pushd /www/server/jh-panel > /dev/null
default_remote_ip=$(python3 /www/server/jh-panel/tools.py getStandbyIp)
popd > /dev/null
remote_ip_tip="请输入对端服务器IP"
if [ -n "${default_remote_ip}" ]; then
  remote_ip_tip+="（默认为：${default_remote_ip}）"
fi
prompt "${remote_ip_tip}: " remote_ip "${default_remote_ip}"
if [ -z "${remote_ip}" ]; then
  show_error "错误: 未指定对端服务器IP"
  exit 1
fi

prompt "请输入对端服务器SSH端口(默认: ${DEFAULT_REMOTE_PORT}): " remote_port "${DEFAULT_REMOTE_PORT}"

if [ ! -x "${KEEPALIVED_INIT}" ]; then
  show_error "错误: keepalived 启动脚本不存在: ${KEEPALIVED_INIT}"
  exit 1
fi

ensure_local_keepalived
ensure_remote_keepalived
update_local_priority
update_remote_priority

vip_list=$(get_vips)
if [ -z "${vip_list}" ]; then
  show_error "错误: 未能从 keepalived 配置中获取 VIP"
  exit 1
fi

check_vip_location

if [ ${remote_has_vip} -eq 1 ]; then
  if [ ${local_has_vip} -eq 1 ]; then
    echo "|- 检测到 VIP 同时在对端，正在清理对端以保证本机为主..."
  else
    echo "|- 当前本机为备，正在执行对端 keepalived 脚本以漂移 VIP 到本地..."
  fi
  remote_exec "bash ${KEEPALIVED_INIT} stop"
  if [ $? -ne 0 ]; then
    show_error "错误: 对端 keepalived 停止失败"
    exit 1
  fi
  sleep 2
  ensure_local_keepalived

  if ! wait_for_local_vip; then
    check_vip_location
    show_error "错误: VIP 未漂移到本地"
    exit 1
  fi

  remote_exec "cd ${PANEL_DIR} && python3 ${PANEL_DIR}/plugins/keepalived/index.py stop"
  sleep 2
  remote_exec "cd ${PANEL_DIR} && python3 ${PANEL_DIR}/plugins/keepalived/index.py start"
  if [ $? -ne 0 ]; then
    show_error "错误: 对端 keepalived 启动失败"
    exit 1
  fi
  show_info "|- 对端 keepalived 重启完成✅"
fi

if [ ! -f "${NOTIFY_MASTER}" ]; then
  show_error "错误: notify_master.py 不存在: ${NOTIFY_MASTER}"
  exit 1
fi

# echo "|- 执行本地 notify_master.py..."
# python3 "${NOTIFY_MASTER}"
# if [ $? -ne 0 ]; then
#   show_error "错误: notify_master.py 执行失败"
#   exit 1
# fi
# show_info "|- notify_master.py 执行完成✅"

# if ! remote_exec "[ -f '${NOTIFY_BACKUP}' ]"; then
#   show_error "错误: 对端 notify_backup.py 不存在: ${NOTIFY_BACKUP}"
#   exit 1
# fi

# echo "|- 执行对端 notify_backup.py..."
# remote_exec "python3 ${NOTIFY_BACKUP}"
# if [ $? -ne 0 ]; then
#   show_error "错误: 对端 notify_backup.py 执行失败"
#   exit 1
# fi
# show_info "|- 对端 notify_backup.py 执行完成✅"

echo ""
echo "|- 最终检查 VIP 是否在本机..."
detect_vip_location
if [ ${local_has_vip} -eq 0 ]; then
  show_error "错误: VIP 未在本机"
  exit 1
fi
show_info "|- VIP 已在本机✅"

echo ""
echo "==========================修复 keepalived 主节点完成✅=========================="
