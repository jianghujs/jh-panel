#!/usr/bin/env bash
set -uo pipefail

CONFIG="/etc/filebeat/filebeat.yml"
SERVICE="filebeat"
REGISTRY="/var/lib/filebeat/registry/filebeat/log.json"
SINCE="30 minutes ago"
ES_HOST=""
ES_USER=""
ES_PASS=""
INDEX_PATTERN=""
SOURCE_ROOTS="/home/ansible_user/jh-monitor-data /home/ansible/jh-monitor-data"
SHOW_DOCS=0
VERBOSE=0
AUTO_DEBUG=1
DEBUG_SELECTORS="elasticsearch"
TRIGGER_TEST=1
WAIT_SECONDS=20
MAX_LOG_LINES=10
MAX_PREVIEW_CHARS=100
EXIT_CODE=0
ISSUES=()
WARNINGS=()
NOTES=()
SUMMARY_LINES=()
SERVICE_STATE="未知"
SUMMARY_NAME="未知"
CONFIG_TEST_STATE="未检查"
OUTPUT_TEST_STATE="未检查"
SOURCE_FILE_COUNT="未知"
REGISTRY_MATCH_COUNT="未知"
RECENT_ERROR_COUNT="未知"
ES_REACHABLE_STATE="未检查"
ES_INDEX_FOUND_STATE="未检查"
ES_INDEX_PATTERN_USED=""
DEFAULT_FILEBEAT_INDEX_STATE="未检查"
DEBUG_MODE_STATE="未检查"
MAPPING_CONFLICT_COUNT="0"
MAPPING_CONFLICTS=()
NO_COLOR=0
DETAIL_LOG="/tmp/log__diagnose_filebeat_es_$(date +%Y%m%d%H%M%S).log"
MATCHED_ERROR_LOG="${DETAIL_LOG%.log}_filebeat_errors.log"
DEBUG_DROPIN_DIR="/etc/systemd/system/${SERVICE}.service.d"
DEBUG_DROPIN_FILE="${DEBUG_DROPIN_DIR}/diagnose-debug.conf"

RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
ORANGE=$'\033[38;5;208m'
BLUE=$'\033[34m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

usage() {
  cat <<USAGE
用法: $0 [选项]

诊断 Filebeat -> Elasticsearch 常见写入问题。默认会通过 systemd drop-in 自动开启 Filebeat debug 日志并重启服务。

选项:
  -c, --config PATH          Filebeat 配置路径。默认: /etc/filebeat/filebeat.yml
  --since TIME              检查 journal 日志的时间范围。默认: "30 minutes ago"
  --es HOST                 覆盖 Elasticsearch 地址，例如 http://192.168.200.201:9200
  --user USER               覆盖 Elasticsearch 用户名
  --password PASS           覆盖 Elasticsearch 密码
  --index-pattern PATTERN   覆盖要检查的 ES 索引/数据流模式
  --show-docs               显示匹配索引中的最新文档
  --verbose                 在终端显示详细列表；默认详细内容只写入 /tmp 日志
  --no-auto-debug           不自动开启 Filebeat debug 模式
  --debug-selectors LIST    Filebeat debug selectors。默认: elasticsearch
  --trigger-test            重启 Filebeat 后复制最新一条监控数据为新文件，触发一次写入。默认开启
  --no-trigger-test         重启 Filebeat 后不触发测试写入
  --wait-seconds N          触发测试写入后等待秒数。默认: 20
  --no-color                禁用彩色输出
  --log-file PATH           指定完整诊断日志文件路径。默认写入 /tmp
  --max-preview-chars N     终端预览每行最多显示字符数。默认: 300
  -h, --help                显示帮助

示例:
  $0
  $0 --since '2 hours ago'
  $0 --index-pattern '.ds-host-debian-h-dev05-dc104-5eda-*'
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    -c|--config) shift; CONFIG="${1:-}" ;;
    --since) shift; SINCE="${1:-}" ;;
    --es) shift; ES_HOST="${1:-}" ;;
    --user) shift; ES_USER="${1:-}" ;;
    --password) shift; ES_PASS="${1:-}" ;;
    --index-pattern) shift; INDEX_PATTERN="${1:-}" ;;
    --show-docs) SHOW_DOCS=1 ;;
    --verbose) VERBOSE=1 ;;
    --no-auto-debug) AUTO_DEBUG=0 ;;
    --debug-selectors) shift; DEBUG_SELECTORS="${1:-}" ;;
    --trigger-test) TRIGGER_TEST=1 ;;
    --no-trigger-test) TRIGGER_TEST=0 ;;
    --wait-seconds) shift; WAIT_SECONDS="${1:-20}" ;;
    --no-color) NO_COLOR=1 ;;
    --log-file) shift; DETAIL_LOG="${1:-}" ;;
    --max-preview-chars) shift; MAX_PREVIEW_CHARS="${1:-300}" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知选项: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ "$NO_COLOR" -eq 1 ]; then
  RED=''; GREEN=''; YELLOW=''; ORANGE=''; BLUE=''; BOLD=''; RESET=''
fi

: > "$DETAIL_LOG" 2>/dev/null || { echo "无法写入日志文件: $DETAIL_LOG" >&2; exit 2; }
echo "诊断开始: $(date)" >> "$DETAIL_LOG"
echo "命令: $0 $*" >> "$DETAIL_LOG"

section() { printf '\n%b== %s ==%b\n' "${BOLD}${BLUE}" "$1" "$RESET"; printf '\n== %s ==\n' "$1" >> "$DETAIL_LOG"; }
pass() { printf "${GREEN}[OK]${RESET} %s\n" "$1"; printf '[OK] %s\n' "$1" >> "$DETAIL_LOG"; }
warn() { printf "${ORANGE}[WARN]${RESET} %s\n" "$1"; printf '[WARN] %s\n' "$1" >> "$DETAIL_LOG"; WARNINGS+=("$1"); [ "$EXIT_CODE" -lt 1 ] && EXIT_CODE=1; }
note() { printf "${YELLOW}[NOTE]${RESET} %s\n" "$1"; printf '[NOTE] %s\n' "$1" >> "$DETAIL_LOG"; NOTES+=("$1"); }
fail() { printf "${RED}[FAIL]${RESET} %s\n" "$1"; printf '[FAIL] %s\n' "$1" >> "$DETAIL_LOG"; ISSUES+=("$1"); EXIT_CODE=2; }
info() { printf "[INFO] %s\n" "$1"; printf '[INFO] %s\n' "$1" >> "$DETAIL_LOG"; }
add_summary() { SUMMARY_LINES+=("$1"); }
log_detail_section() { printf '\n== %s ==\n' "$1" >> "$DETAIL_LOG"; }
write_detail() {
  local title="$1" content="$2"
  log_detail_section "$title"
  printf '%s\n' "$content" >> "$DETAIL_LOG"
}
write_file_and_tail() {
  local title="$1" file="$2" lines="${3:-$MAX_LOG_LINES}"
  log_detail_section "$title"
  if [ -s "$file" ]; then
    cat "$file" >> "$DETAIL_LOG"
    info "$title 完整内容已写入: $file"
    echo "最近 ${lines} 行:"
    preview_file_tail "$file" "$lines"
  else
    : > "$file"
    info "$title 无匹配内容；空文件已创建: $file"
  fi
}
preview_file_tail() {
  local file="$1" lines="${2:-$MAX_LOG_LINES}" max_chars="${3:-$MAX_PREVIEW_CHARS}"
  tail -n "$lines" "$file" | awk -v max="$max_chars" '
    {
      if (max > 0 && length($0) > max) {
        print substr($0, 1, max) " ...[已截断，完整内容见日志文件]"
      } else {
        print
      }
    }
  '
}
preview_text_tail() {
  local lines="${1:-$MAX_LOG_LINES}" max_chars="${2:-$MAX_PREVIEW_CHARS}"
  tail -n "$lines" | awk -v max="$max_chars" '
    {
      if (max > 0 && length($0) > max) {
        print substr($0, 1, max) " ...[已截断，完整内容见日志文件]"
      } else {
        print
      }
    }
  '
}
emit_detail() {
  local title="$1" content="$2" mode="${3:-quiet}" lines="${4:-$MAX_LOG_LINES}"
  write_detail "$title" "$content"
  case "$mode" in
    tail)
      printf '%s\n' "$content" | preview_text_tail "$lines"
      ;;
    verbose)
      if [ "$VERBOSE" -eq 1 ]; then
        printf '%s\n' "$content" | preview_text_tail "$lines"
      else
        info "$title 明细已写入: $DETAIL_LOG"
      fi
      ;;
    quiet|*)
      info "$title 明细已写入: $DETAIL_LOG"
      ;;
  esac
}
state_color() {
  case "$1" in
    正常|active|未发现|已开启|0) printf "%s" "$GREEN" ;;
    异常|failed|inactive|deactivating|activating|unknown|未知) printf "%s" "$RED" ;;
    存在|未检查|跳过) printf "%s" "$YELLOW" ;;
    *) printf "%s" "" ;;
  esac
}
print_state_line() {
  local label="$1" value="$2" color
  color=$(state_color "$value")
  printf "  - %s: %b%s%b\n" "$label" "$color" "$value" "$RESET"
}
extract_mapping_conflicts() {
  local text="$1" line conflict
  while IFS= read -r line; do
    conflict=$(printf '%s\n' "$line" | sed -n 's/.*mapper \[\([^]]*\)\] cannot be changed from type \[\([^]]*\)\] to \[\([^]]*\)\].*/字段 \1: ES现有类型=\2, 新数据类型=\3/p')
    if [ -n "$conflict" ]; then
      MAPPING_CONFLICTS+=("$conflict")
    fi
  done <<EOF_CONFLICTS
$text
EOF_CONFLICTS
  MAPPING_CONFLICT_COUNT="${#MAPPING_CONFLICTS[@]}"
}

cmd_exists() { command -v "$1" >/dev/null 2>&1; }

systemd_escape_env_value() {
  local value="$1"
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  printf '%s' "$value"
}

mask() {
  local s="$1"
  if [ -z "$s" ]; then printf ''; return; fi
  if [ "${#s}" -le 2 ]; then printf '**'; else printf '%s***' "${s:0:2}"; fi
}

strip_quotes() {
  sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^\[//' -e 's/\]$//' -e 's/[",]//g'
}

first_yaml_scalar_after_key() {
  local key="$1" file="$2"
  awk -v key="$key" '
    $0 ~ "^[[:space:]]*" key ":[[:space:]]*" {
      sub("^[[:space:]]*" key ":[[:space:]]*", "")
      gsub(/[\"\[\],]/, "")
      print
      exit
    }
  ' "$file" 2>/dev/null
}

extract_es_config() {
  [ -f "$CONFIG" ] || return 0
  if [ -z "$ES_HOST" ]; then
    ES_HOST=$(awk '
      /^[[:space:]]*output.elasticsearch:/ {in_es=1; next}
      in_es && /^[^[:space:]]/ {in_es=0}
      in_es && /^[[:space:]]*hosts:/ {
        sub(/^[[:space:]]*hosts:[[:space:]]*/, "")
        gsub(/[\"\[\],]/, "")
        print $1
        exit
      }
    ' "$CONFIG" 2>/dev/null)
  fi
  if [ -n "$ES_HOST" ] && ! printf '%s' "$ES_HOST" | grep -Eq '^https?://'; then
    ES_HOST="http://${ES_HOST}"
  fi
  if [ -z "$ES_USER" ]; then
    ES_USER=$(awk '
      /^[[:space:]]*output.elasticsearch:/ {in_es=1; next}
      in_es && /^[^[:space:]]/ {in_es=0}
      in_es && /^[[:space:]]*username:/ {sub(/^[[:space:]]*username:[[:space:]]*/, ""); gsub(/[\"]/, ""); print; exit}
    ' "$CONFIG" 2>/dev/null)
  fi
  if [ -z "$ES_PASS" ]; then
    ES_PASS=$(awk '
      /^[[:space:]]*output.elasticsearch:/ {in_es=1; next}
      in_es && /^[^[:space:]]/ {in_es=0}
      in_es && /^[[:space:]]*password:/ {sub(/^[[:space:]]*password:[[:space:]]*/, ""); gsub(/[\"]/, ""); print; exit}
    ' "$CONFIG" 2>/dev/null)
  fi
  if [ -z "$INDEX_PATTERN" ]; then
    local tmpl
    tmpl=$(first_yaml_scalar_after_key 'setup.template.pattern' "$CONFIG")
    if [ -n "$tmpl" ]; then
      INDEX_PATTERN=".ds-${tmpl}"
    else
      local idx
      idx=$(awk '/^[[:space:]]*- index: / {sub(/^[[:space:]]*- index:[[:space:]]*/, ""); gsub(/[\"]/, ""); print; exit}' "$CONFIG" 2>/dev/null)
      if [ -n "$idx" ]; then INDEX_PATTERN=".ds-${idx%%%*}*"; fi
    fi
  fi
}

curl_es() {
  local path="$1"
  local url="${ES_HOST%/}${path}"
  if [ -n "$ES_USER" ] || [ -n "$ES_PASS" ]; then
    curl -sS -u "${ES_USER}:${ES_PASS}" "$url"
  else
    curl -sS "$url"
  fi
}

latest_source_file() {
  find '/home/ansible_user/jh-monitor-data' '/home/ansible/jh-monitor-data' -maxdepth 1 -type f \( \
    -name 'host-debian-system-status-*.json' -o \
    -name 'host-debian-backup-*.ndjson' -o \
    -name 'host-debian-xtrabackup-*.ndjson' -o \
    -name 'host-debian-xtrabackup-inc-*.ndjson' -o \
    -name 'host-pve-system-status-*.json' -o \
    -name 'host-pve-backup-*.ndjson' -o \
    -name 'host-pve-xtrabackup-*.ndjson' -o \
    -name 'host-pve-xtrabackup-inc-*.ndjson' -o \
    -name 'host-pve-hardware-report-*.json' \
  \) -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n 1 | sed 's/^[^ ]* //'
}

retry_file_for_source() {
  local src="$1" dir base ts
  dir=$(dirname "$src")
  base=$(basename "$src")
  ts=$(date +%Y%m%d%H%M%S)
  case "$base" in
    host-debian-system-status-*.json) printf '%s/host-debian-system-status-retry-%s.json' "$dir" "$ts" ;;
    host-debian-xtrabackup-inc-*.ndjson) printf '%s/host-debian-xtrabackup-inc-retry-%s.ndjson' "$dir" "$ts" ;;
    host-debian-xtrabackup-*.ndjson) printf '%s/host-debian-xtrabackup-retry-%s.ndjson' "$dir" "$ts" ;;
    host-debian-backup-*.ndjson) printf '%s/host-debian-backup-retry-%s.ndjson' "$dir" "$ts" ;;
    host-pve-system-status-*.json) printf '%s/host-pve-system-status-retry-%s.json' "$dir" "$ts" ;;
    host-pve-xtrabackup-inc-*.ndjson) printf '%s/host-pve-xtrabackup-inc-retry-%s.ndjson' "$dir" "$ts" ;;
    host-pve-xtrabackup-*.ndjson) printf '%s/host-pve-xtrabackup-retry-%s.ndjson' "$dir" "$ts" ;;
    host-pve-backup-*.ndjson) printf '%s/host-pve-backup-retry-%s.ndjson' "$dir" "$ts" ;;
    host-pve-hardware-report-*.json) printf '%s/host-pve-hardware-report-retry-%s.json' "$dir" "$ts" ;;
    *) printf '%s/host-debian-system-status-retry-%s.json' "$dir" "$ts" ;;
  esac
}

trigger_test_ingest() {
  [ "$TRIGGER_TEST" -eq 1 ] || return 0
  section "触发测试写入（等待日志产生）"
  local src dst last_line
  src=$(latest_source_file || true)
  if [ -z "$src" ] || [ ! -f "$src" ]; then
    warn "没有找到可用于触发写入的监控源文件，跳过测试写入"
    return 0
  fi
  last_line=$(grep -v '^[[:space:]]*$' "$src" 2>/dev/null | tail -n 1 || true)
  if [ -z "$last_line" ]; then
    warn "源文件没有非空记录: $src，跳过测试写入"
    return 0
  fi
  dst=$(retry_file_for_source "$src")
  printf '%s\n' "$last_line" > "$dst"
  chmod 0644 "$dst" 2>/dev/null || true
  pass "已生成测试写入文件: $dst"
  info "来源最新记录: $src"
  info "等待 ${WAIT_SECONDS}s 让 Filebeat 采集并产生日志"
  sleep "$WAIT_SECONDS"
  ok "等待完成，继续检查日志"
}

check_command_set() {
  section "工具检查"
  local missing=0
  for c in filebeat systemctl journalctl curl grep awk sed find; do
    if cmd_exists "$c"; then pass "$c 已找到"; else fail "$c 缺失"; missing=1; fi
  done
  if cmd_exists rg; then pass "rg 已找到"; else warn "rg 缺失；需要时会用 grep 兜底"; fi
  if cmd_exists jq; then pass "jq 已找到"; else warn "jq 缺失；JSON 输出解析能力会受限"; fi
  return "$missing"
}

enable_filebeat_debug() {
  section "Filebeat debug 模式"

  if [ "$AUTO_DEBUG" -ne 1 ]; then
    DEBUG_MODE_STATE="跳过"
    note "已按参数跳过自动开启 Filebeat debug 模式"
    return
  fi

  if ! cmd_exists systemctl; then
    DEBUG_MODE_STATE="异常"
    fail "systemctl 缺失，无法自动开启 Filebeat debug 模式"
    return
  fi

  if [ -z "$DEBUG_SELECTORS" ]; then
    DEBUG_SELECTORS="elasticsearch"
  fi

  local log_opts escaped_opts desired current_active restart_out
  log_opts="-d ${DEBUG_SELECTORS}"
  escaped_opts=$(systemd_escape_env_value "$log_opts")
  desired=$(printf '[Service]\nEnvironment="BEAT_LOG_OPTS=%s"\n' "$escaped_opts")

  if [ -f "$DEBUG_DROPIN_FILE" ] && [ "$(cat "$DEBUG_DROPIN_FILE" 2>/dev/null)" = "$desired" ]; then
    pass "Filebeat debug drop-in 已存在: $DEBUG_DROPIN_FILE"
  else
    if ! mkdir -p "$DEBUG_DROPIN_DIR" 2>/dev/null; then
      DEBUG_MODE_STATE="异常"
      fail "无法创建 systemd drop-in 目录: $DEBUG_DROPIN_DIR"
      return
    fi
    if ! printf '%s\n' "$desired" > "$DEBUG_DROPIN_FILE" 2>/dev/null; then
      DEBUG_MODE_STATE="异常"
      fail "无法写入 Filebeat debug drop-in: $DEBUG_DROPIN_FILE"
      return
    fi
    pass "已写入 Filebeat debug drop-in: $DEBUG_DROPIN_FILE"
  fi

  if ! systemctl daemon-reload >/dev/null 2>&1; then
    DEBUG_MODE_STATE="异常"
    fail "systemctl daemon-reload 失败，Filebeat debug 模式可能未生效"
    return
  fi
  pass "systemd daemon-reload 完成"

  current_active=$(systemctl is-active "$SERVICE" 2>/dev/null || true)
  restart_out=$(systemctl restart "$SERVICE" 2>&1)
  if [ $? -eq 0 ]; then
    DEBUG_MODE_STATE="已开启"
    if [ "$current_active" = "active" ]; then
      pass "已重启 $SERVICE，debug selectors: $DEBUG_SELECTORS"
    else
      pass "已启动 $SERVICE，debug selectors: $DEBUG_SELECTORS"
    fi
  else
    DEBUG_MODE_STATE="异常"
    fail "重启 $SERVICE 失败，debug 模式未确认生效: $restart_out"
  fi
}

check_config_summary() {
  section "配置摘要"
  if [ ! -f "$CONFIG" ]; then fail "配置文件不存在: $CONFIG"; return; fi
  pass "配置文件存在: $CONFIG"
  local beat_name template_name template_pattern host_id
  beat_name=$(first_yaml_scalar_after_key 'name' "$CONFIG")
  template_name=$(first_yaml_scalar_after_key 'setup.template.name' "$CONFIG")
  template_pattern=$(first_yaml_scalar_after_key 'setup.template.pattern' "$CONFIG")
  host_id=$(awk '
    /^[[:space:]]*host_id:/ {gsub(/[\"]/, ""); sub(/^[[:space:]]*host_id:[[:space:]]*/, ""); print; exit}
  ' "$CONFIG" 2>/dev/null)
  info "name: ${beat_name:-unknown}"
  info "host_id: ${host_id:-unknown}"
  info "template.name: ${template_name:-unknown}"
  info "template.pattern: ${template_pattern:-unknown}"
  info "ES host: ${ES_HOST:-unknown}"
  info "ES user: ${ES_USER:-none} password: $(mask "$ES_PASS")"
  info "inspect index pattern: ${INDEX_PATTERN:-unknown}"
  ES_INDEX_PATTERN_USED="${INDEX_PATTERN:-unknown}"
  SUMMARY_NAME="${beat_name:-unknown}"

  if [ -n "$beat_name" ] && [ -n "$host_id" ] && [ "$beat_name" != "$host_id" ]; then
    warn "name 和 processors.host_id 不一致: '$beat_name' vs '$host_id'"
  else
    pass "name 和 host_id 看起来一致"
  fi

  if [ -n "$template_pattern" ]; then
    local bad_count
    bad_count=$(awk -v pat_prefix="${template_pattern%\*}" '
      /^[[:space:]]*- index: / {
        line=$0
        gsub(/[\"]/, "", line)
        sub(/^[[:space:]]*- index:[[:space:]]*/, "", line)
        if (line !~ "^" pat_prefix) print line
      }
    ' "$CONFIG" | wc -l)
    if [ "$bad_count" -eq 0 ]; then pass "自定义 index 前缀和 template.pattern 匹配"; else warn "部分自定义 index 和 setup.template.pattern 前缀不匹配"; fi
  fi
}

check_filebeat() {
  section "Filebeat 状态"
  local version
  version=$(filebeat version 2>&1)
  if [ $? -eq 0 ]; then pass "$version"; else fail "filebeat version 执行失败: $version"; fi

  local cfg_out
  cfg_out=$(filebeat test config -c "$CONFIG" 2>&1)
  if printf '%s' "$cfg_out" | grep -q 'Config OK'; then CONFIG_TEST_STATE="正常"; pass "filebeat 配置检查通过: Config OK"; else CONFIG_TEST_STATE="异常"; fail "filebeat 配置检查失败: $cfg_out"; fi

  local out
  out=$(filebeat test output -c "$CONFIG" 2>&1)
  if printf '%s' "$out" | grep -q 'talk to server... OK'; then OUTPUT_TEST_STATE="正常"; pass "filebeat 输出检查通过: talk to server OK"; else OUTPUT_TEST_STATE="异常"; fail "filebeat 输出检查失败"; printf '%s\n' "$out" | sed -n '1,40p'; fi

  local active status
  active=$(systemctl is-active "$SERVICE" 2>/dev/null || true)
  SERVICE_STATE="${active:-unknown}"
  if [ "$active" = "active" ]; then pass "服务处于 active 状态"; else fail "服务不是 active 状态: ${active:-unknown}"; fi
  status=$(systemctl status "$SERVICE" --no-pager -l 2>&1)
  log_detail_section "systemctl status $SERVICE"
  printf '%s\n' "$status" >> "$DETAIL_LOG"
  info "systemctl status 明细已写入: $DETAIL_LOG"
}

check_sources() {
  section "源文件检查"
  local found=0
  for root in $SOURCE_ROOTS; do
    if [ -d "$root" ]; then
      info "源目录存在: $root"
      local count source_list
      count=$(find "$root" -maxdepth 1 -type f \( -name 'host-debian-system-status-*.json' -o -name 'host-debian-xtrabackup-*.ndjson' -o -name 'host-debian-backup-*.ndjson' -o -name 'host-pve-system-status-*.json' -o -name 'host-pve-xtrabackup-*.ndjson' -o -name 'host-pve-backup-*.ndjson' -o -name 'host-pve-hardware-report-*.json' \) 2>/dev/null | wc -l)
      info "$root 中监控文件数量: $count"
      if [ "$SOURCE_FILE_COUNT" = "未知" ]; then SOURCE_FILE_COUNT=0; fi
      SOURCE_FILE_COUNT=$((SOURCE_FILE_COUNT + count))
      if [ "$count" -gt 0 ]; then found=1; fi
      log_detail_section "源文件列表 $root"
      find "$root" -maxdepth 1 -type f \( -name 'host-debian-system-status-*.json' -o -name 'host-debian-xtrabackup-*.ndjson' -o -name 'host-debian-backup-*.ndjson' -o -name 'host-pve-system-status-*.json' -o -name 'host-pve-xtrabackup-*.ndjson' -o -name 'host-pve-backup-*.ndjson' -o -name 'host-pve-hardware-report-*.json' \) -printf '%TY-%Tm-%Td %TH:%TM %10s %p\n' 2>/dev/null | sort >> "$DETAIL_LOG"
      if [ "$VERBOSE" -eq 1 ]; then
        find "$root" -maxdepth 1 -type f \( -name 'host-debian-system-status-*.json' -o -name 'host-debian-xtrabackup-*.ndjson' -o -name 'host-debian-backup-*.ndjson' -o -name 'host-pve-system-status-*.json' -o -name 'host-pve-xtrabackup-*.ndjson' -o -name 'host-pve-backup-*.ndjson' -o -name 'host-pve-hardware-report-*.json' \) -printf '%TY-%Tm-%Td %TH:%TM %10s %p\n' 2>/dev/null | sort | tail -n 12
      else
        info "源文件明细已写入: $DETAIL_LOG"
      fi
    else
      note "源目录不存在: $root"
    fi
  done
  if [ "$found" -eq 1 ]; then pass "已找到监控源文件"; else fail "没有找到监控源文件"; fi
}

check_registry() {
  section "Registry 读取进度"
  if [ ! -f "$REGISTRY" ]; then fail "registry 文件不存在: $REGISTRY"; return; fi
  pass "registry 文件存在: $REGISTRY"
  local reg_size reg_matches
  reg_size=$(stat -c '%s' "$REGISTRY" 2>/dev/null || echo 0)
  reg_matches=$(grep -E -c 'host-(debian|pve)-(system-status|backup-|xtrabackup-|hardware-report-)' "$REGISTRY" || true)
  info "registry 大小: $reg_size bytes"
  info "监控相关 registry 记录数: $reg_matches"
  REGISTRY_MATCH_COUNT="$reg_matches"
  if [ "$reg_matches" -gt 0 ]; then pass "Filebeat 已经扫描/读取过监控文件"; else warn "没有监控相关 registry 记录；Filebeat 可能还没有扫描到这些文件"; fi
  local registry_matches_text
  registry_matches_text=$(grep -E 'host-(debian|pve)-(system-status|backup-|xtrabackup-|hardware-report-)' "$REGISTRY" 2>/dev/null || true)
  emit_detail "Registry 监控相关记录" "$registry_matches_text" "verbose" 8
}

check_logs() {
  section "最近 Filebeat 日志"
  local err_count cloud_count

  log_detail_section "完整 Filebeat journal 日志 since $SINCE"
  journalctl -u "$SERVICE" --since "$SINCE" --no-pager -l > "${DETAIL_LOG}.journal.tmp" 2>/dev/null || true
  cat "${DETAIL_LOG}.journal.tmp" >> "$DETAIL_LOG"

  if [ ! -s "${DETAIL_LOG}.journal.tmp" ]; then
    warn "从 '$SINCE' 到现在没有找到 journal 日志"
    : > "$MATCHED_ERROR_LOG"
    rm -f "${DETAIL_LOG}.journal.tmp"
    return
  fi

  echo "最近 3 行 Filebeat journal:"
  tail -n 3 "${DETAIL_LOG}.journal.tmp"

  cloud_count=$(grep -Eic 'add_cloud_metadata.*169\.254\.169\.254' "${DETAIL_LOG}.journal.tmp" || true)
  grep -Ei 'Cannot index event|status=400|status=401|status=403|Failed to connect|failed to publish|no route to host|connection refused|timeout|mapper|reject|unauthorized|forbidden' \
    "${DETAIL_LOG}.journal.tmp" > "$MATCHED_ERROR_LOG" 2>/dev/null || true
  err_count=$(wc -l < "$MATCHED_ERROR_LOG" | tr -d ' ')

  RECENT_ERROR_COUNT="$err_count"
  extract_mapping_conflicts "$(cat "$MATCHED_ERROR_LOG" 2>/dev/null)"

  if [ "$err_count" -eq 0 ]; then
    pass "从 '$SINCE' 到现在没有明显写入/输出错误"
  else
    fail "从 '$SINCE' 到现在发现 $err_count 条疑似写入/输出错误"
  fi

  if [ "$MAPPING_CONFLICT_COUNT" -gt 0 ]; then
    fail "检测到 $MAPPING_CONFLICT_COUNT 个 ES mapping 字段类型冲突"
    local conflict
    for conflict in "${MAPPING_CONFLICTS[@]}"; do printf "%b[MAPPING冲突]%b %s\n" "$RED" "$RESET" "$conflict"; done
  fi

  if [ "$cloud_count" -gt 0 ]; then
    info "cloud metadata 超时日志: $cloud_count 条（通常不影响写入 ES）"
  fi

  if [ "$err_count" -gt 0 ]; then
    log_detail_section "匹配到的 Filebeat 错误日志"
    cat "$MATCHED_ERROR_LOG" >> "$DETAIL_LOG"
    info "匹配到的 Filebeat 错误日志完整内容已写入: $MATCHED_ERROR_LOG"
  else
    write_detail "匹配到的 Filebeat 错误日志" ""
    info "匹配到的 Filebeat 错误日志为空；文件: $MATCHED_ERROR_LOG"
  fi

  rm -f "${DETAIL_LOG}.journal.tmp"
}

check_es() {
  section "Elasticsearch 检查"
  if [ -z "$ES_HOST" ]; then fail "无法解析 ES 地址；请使用 --es 指定"; return; fi
  local root
  root=$(curl_es "/" 2>&1)
  if printf '%s' "$root" | grep -q 'cluster_name'; then ES_REACHABLE_STATE="正常"; pass "ES 根接口可访问"; else ES_REACHABLE_STATE="异常"; fail "ES 根接口访问失败"; printf '%s\n' "$root" | sed -n '1,20p'; return; fi
  if [ -n "$INDEX_PATTERN" ]; then
    info "检查索引/数据流模式: $INDEX_PATTERN"
    local cats
    cats=$(curl_es "/_cat/indices/${INDEX_PATTERN}?v&s=index" 2>&1)
    log_detail_section "ES 索引列表 $INDEX_PATTERN"
    printf '%s\n' "$cats" >> "$DETAIL_LOG"
    if printf '%s' "$cats" | grep -Eq '(^health|\.ds-|filebeat-|host-debian-|host-pve-)'; then
      ES_INDEX_FOUND_STATE="正常"
      pass "已找到匹配的索引/数据流"
      if [ "$VERBOSE" -eq 1 ]; then
        printf '%s\n' "$cats" | sed -n '1,80p'
      else
        info "ES 索引列表明细已写入: $DETAIL_LOG"
      fi
    else
      ES_INDEX_FOUND_STATE="异常"
      warn "没有找到匹配的索引/数据流: $INDEX_PATTERN"
      if [ "$VERBOSE" -eq 1 ]; then printf '%s\n' "$cats" | sed -n '1,20p'; fi
    fi
  fi

  local default_indices
  default_indices=$(curl_es "/_cat/indices/filebeat-*?v&s=index" 2>&1)
  log_detail_section "ES 默认 filebeat-* 索引"
  printf '%s\n' "$default_indices" >> "$DETAIL_LOG"
  if printf '%s' "$default_indices" | grep -q '^yellow\|^green\|filebeat-'; then
    DEFAULT_FILEBEAT_INDEX_STATE="存在"
    note "存在默认 filebeat-* 索引；只有当新数据意外写到这里时才需要处理"
    if [ "$VERBOSE" -eq 1 ]; then
      printf '%s\n' "$default_indices" | tail -n 20
    else
      info "默认 filebeat-* 索引明细已写入: $DETAIL_LOG"
    fi
  else
    DEFAULT_FILEBEAT_INDEX_STATE="未发现"
    pass "未发现明显的 filebeat-* 默认索引问题"
  fi

  if [ "$SHOW_DOCS" -eq 1 ] && [ -n "$INDEX_PATTERN" ]; then
    info "$INDEX_PATTERN 中的最新文档"
    docs=$(curl_es "/${INDEX_PATTERN}/_search?size=5&sort=@timestamp:desc&_source=@timestamp,add_time,log_index,fields.log_type,log_type,host_id,host.host_id,agent.name,log.file.path")
    log_detail_section "ES 最新文档 $INDEX_PATTERN"
    printf '%s\n' "$docs" >> "$DETAIL_LOG"
    printf '%s\n' "$docs" | sed -n '1,80p'
  fi
}

ai_summary() {
  section "AI定位摘要"
  echo "下面这段适合直接复制给 AI 或运维同事定位问题："
  echo
  echo "主机/配置:"
  echo "  - 配置文件: $CONFIG"
  echo "  - name: ${SUMMARY_NAME:-未知}"
  echo "  - ES: ${ES_HOST:-未知}"
  echo "  - 检查索引模式: ${ES_INDEX_PATTERN_USED:-未知}"
  echo "  - Filebeat debug drop-in: $DEBUG_DROPIN_FILE"
  echo "  - 完整诊断日志: $DETAIL_LOG"
  echo "  - Filebeat错误日志: $MATCHED_ERROR_LOG"
  echo
  echo "关键状态:"
  print_state_line "Filebeat 服务" "$SERVICE_STATE"
  print_state_line "Filebeat debug 模式" "$DEBUG_MODE_STATE"
  print_state_line "配置检查" "$CONFIG_TEST_STATE"
  print_state_line "ES 输出连接" "$OUTPUT_TEST_STATE"
  echo "  - 源文件数量: $SOURCE_FILE_COUNT"
  echo "  - Registry 匹配记录: $REGISTRY_MATCH_COUNT"
  print_state_line "最近错误数($SINCE)" "$RECENT_ERROR_COUNT"
  print_state_line "ES 可访问" "$ES_REACHABLE_STATE"
  print_state_line "目标索引/数据流" "$ES_INDEX_FOUND_STATE"
  print_state_line "默认 filebeat-* 索引" "$DEFAULT_FILEBEAT_INDEX_STATE"
  print_state_line "Mapping 类型冲突" "$MAPPING_CONFLICT_COUNT"
  echo
  if [ "$MAPPING_CONFLICT_COUNT" -gt 0 ]; then
    echo
    printf "%bMapping 类型冲突:%b\n" "$RED" "$RESET"
    local conflict
    for conflict in "${MAPPING_CONFLICTS[@]}"; do printf "  - %s\n" "$conflict"; done
  fi

  if [ "${#ISSUES[@]}" -eq 0 ] && [ "${#WARNINGS[@]}" -eq 0 ]; then
    printf "%b异常汇总: 未发现 FAIL/WARN。%b\n" "$GREEN" "$RESET"
  else
    printf "%b异常汇总:%b\n" "$RED" "$RESET"
    local item
    for item in "${ISSUES[@]}"; do printf "  - %bFAIL%b: %s\n" "$RED" "$RESET" "$item"; done
    for item in "${WARNINGS[@]}"; do printf "  - %bWARN%b: %s\n" "$RED" "$RESET" "$item"; done
  fi
  if [ "${#NOTES[@]}" -gt 0 ]; then
    echo
    printf "%b提示信息:%b\n" "$YELLOW" "$RESET"
    local item
    for item in "${NOTES[@]}"; do printf "  - %bNOTE%b: %s\n" "$YELLOW" "$RESET" "$item"; done
  fi
}

conclusion() {
  section "结论"
  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "本次检查中，Filebeat -> Elasticsearch 写入链路看起来正常。"
    echo "总结：服务、配置、输出连接、源文件、registry、最近日志、ES 索引检查均通过。"
    echo "如果某一类日志仍看起来缺失，请对比源文件更新时间和 ES 最新文档时间，或使用 --show-docs 查看最新文档。"
  elif [ "$EXIT_CODE" -eq 1 ]; then
    warn "没有发现硬性失败，但有告警需要检查。"
    echo "最可能原因：部分配置不一致、文件未被扫描，或数据写入了非预期索引。"
  else
    fail "发现一个或多个硬性失败。"
    echo "请优先修复 FAIL 项；这些问题通常会阻塞写入。"
  fi

  if [ "$MAPPING_CONFLICT_COUNT" -gt 0 ]; then
    echo
    printf "%bMapping 类型冲突字段:%b\n" "$RED" "$RESET"
    local conflict
    for conflict in "${MAPPING_CONFLICTS[@]}"; do printf "  - %s\n" "$conflict"; done
    echo "建议：统一采集脚本输出类型，或在 ES index template 中固定该字段类型；旧 data stream 需要 rollover/重建后 mapping 才会完全生效。"
  fi

  if [ "${#ISSUES[@]}" -gt 0 ]; then
    echo
    echo "失败项:"
    local item
    for item in "${ISSUES[@]}"; do echo "  - $item"; done
  fi
  if [ "${#WARNINGS[@]}" -gt 0 ]; then
    echo
    echo "告警项:"
    local item
    for item in "${WARNINGS[@]}"; do echo "  - $item"; done
  fi
  echo
  echo "完整诊断日志已写入: $DETAIL_LOG"
  echo "Filebeat错误日志已写入: $MATCHED_ERROR_LOG"

  if [ "${#NOTES[@]}" -gt 0 ]; then
    echo
    echo "提示项:"
    local item
    for item in "${NOTES[@]}"; do echo "  - $item"; done
  fi
}

suggestions() {
  section "下一步建议"
  cat <<NEXT
如果服务、配置或输出连接失败:
  - 优先修复 /etc/filebeat/filebeat.yml、网络路由、ES 地址或账号密码。

如果源文件存在但 registry 没有记录:
  - Filebeat 可能还没扫描到路径；检查 paths、文件权限、input 是否 enabled。

如果 registry 有记录但 ES 文档数不增长:
  - 检查最近日志中是否有 status=400/401/403/no route。
  - 如果是修复配置后需要重读旧文件，在对应机器执行 registry 清理:
      /etc/filebeat/cleanup_filebeat_registry.sh --dry-run
      /etc/filebeat/cleanup_filebeat_registry.sh

如果数据写到了 filebeat-* 而不是 host-debian-*:
  - 检查 output.elasticsearch.indices 条件和 fields_under_root 设置。
  - 检查 name、host_id、setup.template.pattern、index 前缀是否属于当前机器。

如果出现 status=400:
  - 本脚本默认已通过 systemd drop-in 开启 Filebeat debug: $DEBUG_DROPIN_FILE
  - 查看 journalctl -u filebeat 中的 elasticsearch debug 日志，抓取 ES 拒收原因。
  - 定位完成后如需关闭 debug，可删除该 drop-in 后执行 systemctl daemon-reload && systemctl restart filebeat。

如果提示 Mapping 类型冲突:
  - 重点看字段名，例如 mysql.tables.size_bytes。
  - 让所有机器采集脚本输出统一类型，或在 ES template 中显式固定字段类型。
  - 已有旧 backing index 的 mapping 不会自动改变，必要时 rollover 或重建对应 data stream。
NEXT
}

extract_es_config
check_command_set
check_config_summary
enable_filebeat_debug
check_filebeat
check_sources
trigger_test_ingest
check_registry
check_logs
check_es
ai_summary
conclusion
suggestions

exit "$EXIT_CODE"
