#!/usr/bin/env bash
set -uo pipefail

CONFIG="/etc/filebeat/filebeat.yml"
SERVICE="filebeat"
SINCE="2 hours ago"
ES_HOST=""
ES_USER=""
ES_PASS=""
TEMPLATE_NAME=""
TEMPLATE_PATTERN=""
FIELDS=()
TYPES=()
APPLY=0
ASK_CONFIRM=1
YES=0
ROLLOVER=1
DELETE_DATA_STREAMS=0
DELETE_INDICES=0
AUTO_FIX_INDICES=0
INDEX_MODE=""
CONFLICT_INDICES=""
RESET_REGISTRY=0
START_FILEBEAT=1
TRIGGER_TEST=1
WAIT_SECONDS=15
LOG_FILE="/tmp/log__fix_filebeat_es_mapping_conflict_$(date +%Y%m%d%H%M%S).log"
COMPONENT_TEMPLATE=""
PVE_MODE=0
DISABLE_TEMPLATE_OVERWRITE=0
NUM_USER_ARGS=$#
EXIT_CODE=0

RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
BLUE=$'\033[34m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

usage() {
  cat <<USAGE
用法: $0 [选项]

修复 Filebeat 写入 ES 时的 mapping 字段类型冲突，例如:
  mapper [mysql.tables.size_bytes] cannot be changed from type [float] to [long]

默认先检测并生成修复计划；如果发现可修复项，会询问是否立即修复。
加 --apply 可跳过交互确认直接执行。
删除 ES 数据流/索引仍必须额外加 --yes。

选项:
  -c, --config PATH          Filebeat 配置文件。默认: /etc/filebeat/filebeat.yml
  --since TIME              从 journal 中检测冲突的时间范围。默认: "2 hours ago"
  --es HOST                 覆盖 ES 地址，例如 http://192.168.200.201:9200
  --user USER               覆盖 ES 用户名
  --password PASS           覆盖 ES 密码
  --template NAME           覆盖要更新的 ES index template 名称
  --pattern PATTERN         覆盖索引/data stream 匹配模式，例如 host-debian-h-dev03-dc207-g1ov-*
  --field FIELD             手动指定冲突字段，可重复。例如 --field mysql.tables.size_bytes
  --type TYPE               指定上一个 --field 的目标类型。默认自动推断；常用: double/long/keyword
  --apply                   跳过最后确认，直接执行 template 更新、rollover、删除、registry 清理
  --dry-run                  只预检和生成计划，不在最后询问执行
  --yes                     允许执行删除 data stream/index 的危险动作
  --no-rollover             只更新 template，不 rollover data stream
  --delete-data-streams     删除匹配的 data stream。危险，会删除 ES 中对应数据
  --delete-indices          删除匹配的普通索引。危险，会删除 ES 中对应数据
  --auto-fix-indices        自动检测并删除有 mapping 冲突的普通索引（需要 --apply 和 --yes）
  --reset-registry          执行 registry 清理脚本，让本机监控文件重新采集
  --no-start                reset-registry 后不自动启动 Filebeat
  --trigger-test            修复后复制最新一条监控数据为新文件，触发 Filebeat 写入。默认开启
  --no-trigger-test         修复后不触发测试写入
  --wait-seconds N          触发测试写入后等待秒数。默认: 15
  --pve                      自动检测 PVE 数据模式，添加已知易冲突字段
  --create-component-template NAME  创建/更新组件模板并加入 index template 的 composed_of。默认: pve-data-mappings
  --disable-template-overwrite      设置 filebeat.yml 中 setup.template.overwrite: false
  --log-file PATH           指定脚本日志文件。默认写入 /tmp
  --no-color                禁用彩色输出
  -h, --help                显示帮助

推荐流程 (最简单, 推荐):
  $0
  # 无参数运行。脚本会自动:
  #   - 解析 filebeat.yml (ES 地址/template/pattern)
  #   - 检测 mapping 冲突 + 自动识别 PVE 数据模式
  #   - 在 PVE 模式下自动启用: component template / delete indices(或 data streams) /
  #     reset registry / disable template overwrite
  #   - 列出计划后, 由你输入 y/N 一次性确认是否执行

更细粒度控制 (按需使用):
  $0 --since '4 hours ago'           # 只看更长时间窗的 mapping 冲突
  $0 --dry-run                       # 只检测不询问

手动指定字段 (脚本未能自动识别时):
  $0 --field mysql.tables.size_bytes --type double --apply

Debian/data-stream 机器一般也可直接:
  $0

如果 rollover 后仍然写不进去，并且确认可以删除该机器对应 ES 数据:
  systemctl stop filebeat
  $0 --apply --yes --delete-data-streams --reset-registry
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    -c|--config) shift; CONFIG="${1:-}" ;;
    --since) shift; SINCE="${1:-}" ;;
    --es) shift; ES_HOST="${1:-}" ;;
    --user) shift; ES_USER="${1:-}" ;;
    --password) shift; ES_PASS="${1:-}" ;;
    --template) shift; TEMPLATE_NAME="${1:-}" ;;
    --pattern) shift; TEMPLATE_PATTERN="${1:-}" ;;
    --field) shift; FIELDS+=("${1:-}"); TYPES+=("") ;;
    --type) shift; if [ "${#TYPES[@]}" -eq 0 ]; then echo "--type 必须跟在 --field 后面" >&2; exit 2; fi; TYPES[$((${#TYPES[@]}-1))]="${1:-}" ;;
    --apply) APPLY=1; ASK_CONFIRM=0 ;;
    --dry-run) APPLY=0; ASK_CONFIRM=0 ;;
    --yes) YES=1 ;;
    --no-rollover) ROLLOVER=0 ;;
    --delete-data-streams) DELETE_DATA_STREAMS=1 ;;
    --delete-indices) DELETE_INDICES=1 ;;
    --auto-fix-indices) AUTO_FIX_INDICES=1 ;;
    --reset-registry) RESET_REGISTRY=1 ;;
    --no-start) START_FILEBEAT=0 ;;
    --trigger-test) TRIGGER_TEST=1 ;;
    --no-trigger-test) TRIGGER_TEST=0 ;;
    --wait-seconds) shift; WAIT_SECONDS="${1:-15}" ;;
    --log-file) shift; LOG_FILE="${1:-}" ;;
    --pve) PVE_MODE=1 ;;
    --create-component-template) shift; COMPONENT_TEMPLATE="${1:-pve-data-mappings}" ;;
    --disable-template-overwrite) DISABLE_TEMPLATE_OVERWRITE=1 ;;
    --no-color) RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; RESET='' ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知选项: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

: > "$LOG_FILE" 2>/dev/null || { echo "无法写入日志文件: $LOG_FILE" >&2; exit 2; }

section() { printf '\n%b== %s ==%b\n' "${BOLD}${BLUE}" "$1" "$RESET"; printf '\n== %s ==\n' "$1" >> "$LOG_FILE"; }
info() { printf '[INFO] %s\n' "$1"; printf '[INFO] %s\n' "$1" >> "$LOG_FILE"; }
ok() { printf '%b[OK]%b %s\n' "$GREEN" "$RESET" "$1"; printf '[OK] %s\n' "$1" >> "$LOG_FILE"; }
warn() { printf '%b[WARN]%b %s\n' "$YELLOW" "$RESET" "$1"; printf '[WARN] %s\n' "$1" >> "$LOG_FILE"; [ "$EXIT_CODE" -lt 1 ] && EXIT_CODE=1; }
fail() { printf '%b[FAIL]%b %s\n' "$RED" "$RESET" "$1"; printf '[FAIL] %s\n' "$1" >> "$LOG_FILE"; EXIT_CODE=2; }
run_note() { if [ "$APPLY" -eq 1 ]; then printf '%b[APPLY]%b %s\n' "$GREEN" "$RESET" "$1"; else printf '%b[DRY-RUN]%b %s\n' "$YELLOW" "$RESET" "$1"; fi; printf '[ACTION] %s\n' "$1" >> "$LOG_FILE"; }

mask() {
  local s="$1"
  if [ -z "$s" ]; then printf ''; elif [ "${#s}" -le 2 ]; then printf '**'; else printf '%s***' "${s:0:2}"; fi
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
  [ -f "$CONFIG" ] || { fail "配置文件不存在: $CONFIG"; return 1; }
  if [ -z "$ES_HOST" ]; then
    ES_HOST=$(awk '
      /^[[:space:]]*output.elasticsearch:/ {in_es=1; next}
      in_es && /^[^[:space:]]/ {in_es=0}
      in_es && /^[[:space:]]*hosts:/ {sub(/^[[:space:]]*hosts:[[:space:]]*/, ""); gsub(/[\"\[\],]/, ""); print $1; exit}
    ' "$CONFIG" 2>/dev/null)
  fi
  if [ -n "$ES_HOST" ] && ! printf '%s' "$ES_HOST" | grep -Eq '^https?://'; then ES_HOST="http://${ES_HOST}"; fi
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
  [ -n "$TEMPLATE_NAME" ] || TEMPLATE_NAME=$(first_yaml_scalar_after_key 'setup.template.name' "$CONFIG")
  [ -n "$TEMPLATE_PATTERN" ] || TEMPLATE_PATTERN=$(first_yaml_scalar_after_key 'setup.template.pattern' "$CONFIG")
}

curl_es() {
  local method="$1" path="$2" data_file="${3:-}" out_file="${4:-}"
  local url="${ES_HOST%/}${path}"
  local tmp code
  tmp=$(mktemp)
  if [ -n "$data_file" ]; then
    if [ -n "$ES_USER" ] || [ -n "$ES_PASS" ]; then
      code=$(curl -sS -o "$tmp" -w '%{http_code}' -u "${ES_USER}:${ES_PASS}" -H 'Content-Type: application/json' -X "$method" --data-binary "@$data_file" "$url" || true)
    else
      code=$(curl -sS -o "$tmp" -w '%{http_code}' -H 'Content-Type: application/json' -X "$method" --data-binary "@$data_file" "$url" || true)
    fi
  else
    if [ -n "$ES_USER" ] || [ -n "$ES_PASS" ]; then
      code=$(curl -sS -o "$tmp" -w '%{http_code}' -u "${ES_USER}:${ES_PASS}" -X "$method" "$url" || true)
    else
      code=$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" || true)
    fi
  fi
  if [ -n "$out_file" ]; then cp "$tmp" "$out_file"; else cat "$tmp"; fi
  rm -f "$tmp"
  printf '%s' "$code"
}

infer_type() {
  local field="$1" old="$2" new="$3"
  if printf '%s %s' "$old" "$new" | grep -Eq 'float|double|half_float|scaled_float|long|integer|short|byte'; then
    case "$field" in
      *.*_bytes|*_bytes|*.bytes|*bytes|*.size_bytes|*size_bytes) printf 'double' ;;
      *) printf 'double' ;;
    esac
  elif printf '%s %s' "$old" "$new" | grep -Eq 'keyword|text'; then
    printf 'keyword'
  else
    printf 'keyword'
  fi
}

add_field_once() {
  local field="$1" type="$2"
  local i
  [ -n "$field" ] || return 0
  for i in "${!FIELDS[@]}"; do
    if [ "${FIELDS[$i]}" = "$field" ]; then
      [ -n "${TYPES[$i]}" ] || TYPES[$i]="$type"
      return 0
    fi
  done
  FIELDS+=("$field")
  TYPES+=("$type")
}

detect_conflicts() {
  section "检测 mapping 冲突"
  local tmp conflicts line field old new type
  tmp=$(mktemp)
  journalctl -u "$SERVICE" --since "$SINCE" --no-pager -l > "$tmp" 2>/dev/null || true
  printf '\n== Filebeat journal since %s ==\n' "$SINCE" >> "$LOG_FILE"
  cat "$tmp" >> "$LOG_FILE"
  conflicts=$(grep -Eo 'mapper \[[^]]+\] cannot be changed from type \[[^]]+\] to \[[^]]+\]' "$tmp" | sort -u || true)
  rm -f "$tmp"

  if [ -z "$conflicts" ] && [ "${#FIELDS[@]}" -eq 0 ]; then
    warn "最近 '$SINCE' 没有自动识别到 mapping 冲突；可用 --field 手动指定"
    return 0
  fi

  while IFS= read -r line; do
    [ -n "$line" ] || continue
    field=$(printf '%s\n' "$line" | sed -n 's/mapper \[\([^]]*\)\] cannot be changed from type \[\([^]]*\)\] to \[\([^]]*\)\]/\1/p')
    old=$(printf '%s\n' "$line" | sed -n 's/mapper \[\([^]]*\)\] cannot be changed from type \[\([^]]*\)\] to \[\([^]]*\)\]/\2/p')
    new=$(printf '%s\n' "$line" | sed -n 's/mapper \[\([^]]*\)\] cannot be changed from type \[\([^]]*\)\] to \[\([^]]*\)\]/\3/p')
    type=$(infer_type "$field" "$old" "$new")
    add_field_once "$field" "$type"
    info "识别到冲突字段: $field，ES现有类型=$old，新数据类型=$new，建议固定为=$type"
  done <<EOF_CONFLICTS
$conflicts
EOF_CONFLICTS

  local i
  for i in "${!FIELDS[@]}"; do
    if [ -z "${TYPES[$i]}" ]; then TYPES[$i]=$(infer_type "${FIELDS[$i]}" '' ''); fi
    ok "待修复字段: ${FIELDS[$i]} -> ${TYPES[$i]}"
  done
}


detect_index_mode() {
  local out code ds_count idx_count
  out=$(mktemp)
  # Count data streams matching pattern
  code=$(curl_es GET "/_data_stream/${TEMPLATE_PATTERN}" '' "$out")
  if [ "$code" = "200" ]; then
    ds_count=$(python3 - "$out" <<'PY_DS'
import json, sys
try:
    print(len(json.load(open(sys.argv[1])).get('data_streams', [])))
except Exception:
    print(0)
PY_DS
)
  else
    ds_count=0
  fi
  rm -f "$out"

  # Count regular (non-.ds-) indices matching pattern
  out=$(mktemp)
  code=$(curl_es GET "/_cat/indices/${TEMPLATE_PATTERN}?h=index" '' "$out")
  if [ "$code" = "200" ]; then
    idx_count=$(grep -v '^\.ds-' "$out" 2>/dev/null | grep -cve '^[[:space:]]*$')
    idx_count=${idx_count:-0}
  else
    idx_count=0
  fi
  rm -f "$out"

  if [ "$ds_count" -gt 0 ] && [ "$idx_count" -eq 0 ]; then
    INDEX_MODE="data_stream"
    info "索引模式: data_stream (${ds_count} data stream, 0 普通索引)"
  elif [ "$idx_count" -gt 0 ] && [ "$ds_count" -eq 0 ]; then
    INDEX_MODE="regular_index"
    info "索引模式: regular_index (${idx_count} 普通索引, 0 data stream)"
  elif [ "$idx_count" -gt 0 ] && [ "$ds_count" -gt 0 ]; then
    INDEX_MODE="mixed"
    info "索引模式: mixed (${ds_count} data stream, ${idx_count} 普通索引)"
  else
    INDEX_MODE="unknown"
    info "索引模式: unknown (未找到匹配的 data stream 或普通索引)"
  fi
}

find_conflict_indices() {
  # List indices that contain any of the FIELDS with a mapping type different from target
  local out code idx field target_type current_type
  out=$(mktemp)
  code=$(curl_es GET "/_cat/indices/${TEMPLATE_PATTERN}?h=index,health,status" '' "$out")
  printf '\n== Conflict indices check %s ==\n' "$TEMPLATE_PATTERN" >> "$LOG_FILE"
  cat "$out" >> "$LOG_FILE"
  if [ "$code" != "200" ]; then
    rm -f "$out"
    return
  fi
  # Check each regular (non-ds) index for conflicting field mappings
  local conflict_indices=""
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    idx=$(printf '%s\n' "$line" | awk '{print $1}')
    # Skip data stream backing indices
    case "$idx" in .ds-*) continue ;; esac
    # Check each conflicting field
    for i in "${!FIELDS[@]}"; do
      field="${FIELDS[$i]}"
      target_type="${TYPES[$i]}"
      local mapping_out mcode
      mapping_out=$(mktemp)
      mcode=$(curl_es GET "/${idx}/_mapping/field/${field}" '' "$mapping_out")
      if [ "$mcode" = "200" ]; then
        current_type=$(python3 - "$mapping_out" "$field" <<'PY_MAP'
import json, sys
try:
    data = json.load(open(sys.argv[1]))
    field_name = sys.argv[2]
    for idx_name, idx_data in data.items():
        props = idx_data.get('mappings', {})
        # Walk dotted field name into nested properties
        parts = field_name.split('.')
        cur = props
        for p in parts[:-1]:
            cur = cur.get('properties', cur)
            if isinstance(cur, dict):
                cur = cur.get(p, {})
        leaf = cur.get(parts[-1], {}) if isinstance(cur, dict) else {}
        t = leaf.get('type', '')
        if t:
            print(t)
            sys.exit(0)
except Exception:
    pass
print('')
PY_MAP
)
        if [ -n "$current_type" ] && [ "$current_type" != "$target_type" ] && [ "$current_type" != "double" ]; then
          info "索引 $idx 字段 $field 当前类型=$current_type 目标类型=$target_type (冲突)"
          conflict_indices+="${idx}"$'\n'
        else
          info "索引 $idx 字段 $field 类型=$current_type (无冲突)"
        fi
      fi
      rm -f "$mapping_out"
    done
  done < "$out"
  rm -f "$out"
  if [ -n "$conflict_indices" ]; then
    printf '%b[INFO]%b 以下普通索引有 mapping 冲突，template 更新后仍有冲突:\n' "$YELLOW" "$RESET"
    printf '%s' "$conflict_indices"
    info "这些索引需要删除才能让新 mapping 生效（删除后 Filebeat 会自动重建）"
  fi
  CONFLICT_INDICES="$conflict_indices"
}


check_prerequisites() {
  section "预检"
  command -v curl >/dev/null 2>&1 || fail "curl 缺失"
  command -v python3 >/dev/null 2>&1 || fail "python3 缺失，无法安全合并 ES template JSON"
  command -v journalctl >/dev/null 2>&1 || warn "journalctl 缺失，无法自动检测冲突字段"
  extract_es_config || true
  [ -n "$ES_HOST" ] || fail "无法解析 ES 地址，请使用 --es 指定"
  [ -n "$TEMPLATE_NAME" ] || fail "无法解析 setup.template.name，请使用 --template 指定"
  [ -n "$TEMPLATE_PATTERN" ] || fail "无法解析 setup.template.pattern，请使用 --pattern 指定"
  info "配置文件: $CONFIG"
  info "ES: ${ES_HOST:-未知}"
  info "ES用户: ${ES_USER:-none} password: $(mask "$ES_PASS")"
  info "Index template: ${TEMPLATE_NAME:-未知}"
  info "匹配模式: ${TEMPLATE_PATTERN:-未知}"
  if [ "$APPLY" -eq 0 ]; then
    if [ "$ASK_CONFIRM" -eq 1 ]; then warn "当前是检测模式；发现可修复项后会询问是否修复"; else warn "当前是 dry-run，不会修改 ES"; fi
  else
    ok "当前是 apply 模式，会直接执行修改"
  fi
  if { [ "$DELETE_DATA_STREAMS" -eq 1 ] || [ "$DELETE_INDICES" -eq 1 ]; } && [ "$YES" -ne 1 ]; then
    fail "删除 ES data stream/index 必须同时加 --yes"
  fi
  # Detect index mode and advise user
  detect_index_mode
  if [ "$INDEX_MODE" = "regular_index" ] || [ "$INDEX_MODE" = "mixed" ]; then
    find_conflict_indices
    if [ -n "$CONFLICT_INDICES" ]; then
      warn "检测到普通索引有 mapping 冲突；仅更新 template 不会修改已有索引的 mapping"
      warn "需要删除冲突索引让新 mapping 生效。推荐使用: $0 --apply --yes --delete-indices"
      if [ "$AUTO_FIX_INDICES" -eq 1 ] && [ "$APPLY" -eq 1 ] && [ "$YES" -eq 1 ]; then
        DELETE_INDICES=1
        ROLLOVER=0
        info "--auto-fix-indices: 自动启用 --delete-indices 和 --no-rollover"
      fi
    fi
  elif [ "$INDEX_MODE" = "data_stream" ]; then
    info "数据写入走 data stream，template 更新 + rollover 可修复"
  fi
}

check_es_connection() {
  section "ES 连接检查"
  local body code
  body=$(mktemp)
  code=$(curl_es GET / '' "$body")
  cat "$body" >> "$LOG_FILE"
  if [ "$code" = "200" ] && grep -q 'cluster_name' "$body"; then ok "ES 可访问"; else fail "ES 不可访问，HTTP=$code，响应已写入 $LOG_FILE"; fi
  rm -f "$body"
}

build_template_body() {
  local src="$1" dst="$2" pairs_file="$3"
  python3 - "$src" "$dst" "$pairs_file" <<'PY'
import json, sys
src, dst, pairs_file = sys.argv[1:4]
raw = json.load(open(src))
items = raw.get('index_templates') or []
if not items:
    raise SystemExit('未找到 index template')
body = items[0]['index_template']
body.setdefault('template', {}).setdefault('mappings', {}).setdefault('properties', {})
props = body['template']['mappings']['properties']

def field_mapping(t):
    m = {'type': t}
    if t in {'long','integer','short','byte','double','float','half_float','scaled_float'}:
        m['coerce'] = True
        m['ignore_malformed'] = True
    if t == 'keyword':
        m['ignore_above'] = 1024
    return m

def put_mapping(root, dotted, typ):
    parts = [p for p in dotted.split('.') if p]
    cur = root
    for part in parts[:-1]:
        node = cur.setdefault(part, {})
        if 'type' in node and node.get('type') != 'object':
            node.pop('type', None)
        cur = node.setdefault('properties', {})
    cur[parts[-1]] = field_mapping(typ)

for line in open(pairs_file):
    line = line.strip()
    if not line:
        continue
    field, typ = line.split('\t', 1)
    put_mapping(props, field, typ)

json.dump(body, open(dst, 'w'), ensure_ascii=False, indent=2)
PY
}


resolve_template_name() {
  # When setup.template.name doesn't match any composable index template in ES,
  # search by index_patterns matching TEMPLATE_PATTERN and use the first match.
  # Also tries dropping the "-logs" / "-logs-*" suffix convention.
  # Sets TEMPLATE_NAME to the resolved name; returns 0 on success.
  local orig="$TEMPLATE_NAME"
  local out code prefix stripped

  # 1. Try exact name with common suffix variations
  for stripped in "${orig%-logs}" "${orig%-logs-*}" "${orig%logs}logs" "${orig%logs-}"; do
    [ "$stripped" = "$orig" ] && continue
    out=$(mktemp)
    code=$(curl_es GET "/_index_template/${stripped}" '' "$out")
    rm -f "$out"
    if [ "$code" = "200" ]; then
      info "index template '$orig' 不存在，使用匹配的 '$stripped' 代替"
      TEMPLATE_NAME="$stripped"
      return 0
    fi
  done

  # 2. Search all composable index templates for matching index_patterns
  out=$(mktemp)
  code=$(curl_es GET "/_index_template" '' "$out")
  if [ "$code" = "200" ]; then
    prefix="${TEMPLATE_PATTERN%\*}"
    local found
    found=$(python3 - "$out" "$prefix" <<'FINDPY'
import json, sys
try:
    data = json.load(open(sys.argv[1]))
    prefix = sys.argv[2]
    for tmpl in data.get('index_templates', []):
        name = tmpl.get('name', '')
        it = tmpl.get('index_template', {})
        patterns = it.get('index_patterns', [])
        for pat in patterns:
            pat_prefix = pat.rstrip('*')
            if prefix.startswith(pat_prefix) or pat_prefix.startswith(prefix):
                print(name)
                sys.exit(0)
except Exception:
    pass
FINDPY
)
    if [ -n "$found" ]; then
      info "index template '$orig' 不存在，自动发现匹配的 template: '$found' (pattern prefix: $prefix)"
      TEMPLATE_NAME="$found"
      rm -f "$out"
      return 0
    fi
  fi
  rm -f "$out"

  # 3. Give up
  fail "无法找到匹配的 index template: 尝试了 '$orig' 及常见后缀变体和 pattern 搜索"
  return 1
}

update_template() {
  section "更新 ES index template"
  local get_body put_body pairs code i backup
  get_body=$(mktemp)
  put_body=$(mktemp)
  pairs=$(mktemp)
  code=$(curl_es GET "/_index_template/${TEMPLATE_NAME}" '' "$get_body")
  if [ "$code" != "200" ]; then
    info "index template '${TEMPLATE_NAME}' 直接查找返回 HTTP=$code，尝试自动发现匹配 template"
    rm -f "$get_body"
    if ! resolve_template_name; then
      rm -f "$get_body" "$put_body" "$pairs"
      return
    fi
    # Retry with resolved template name
    get_body=$(mktemp)
    code=$(curl_es GET "/_index_template/${TEMPLATE_NAME}" '' "$get_body")
    if [ "$code" != "200" ]; then
      cat "$get_body" >> "$LOG_FILE"
      fail "读取 index template 失败: $TEMPLATE_NAME，HTTP=$code"
      rm -f "$get_body" "$put_body" "$pairs"
      return
    fi
    ok "已解析到 index template: $TEMPLATE_NAME"
  fi

  backup=$(mktemp "/tmp/${TEMPLATE_NAME}_index_template_backup_XXXXXX.json")
  cp -f "$get_body" "$backup"
  info "原始 template 已备份: $backup"

  for i in "${!FIELDS[@]}"; do printf '%s\t%s\n' "${FIELDS[$i]}" "${TYPES[$i]}" >> "$pairs"; done
  if ! build_template_body "$get_body" "$put_body" "$pairs" >> "$LOG_FILE" 2>&1; then
    fail "生成更新后的 template JSON 失败，详情见 $LOG_FILE"
    rm -f "$get_body" "$put_body" "$pairs"
    return
  fi

  printf '\n== Updated template body ==\n' >> "$LOG_FILE"
  cat "$put_body" >> "$LOG_FILE"

  if [ "$APPLY" -eq 1 ]; then
    local resp
    resp=$(mktemp)
    code=$(curl_es PUT "/_index_template/${TEMPLATE_NAME}" "$put_body" "$resp")
    printf '\n== PUT template response ==\n' >> "$LOG_FILE"
    cat "$resp" >> "$LOG_FILE"
    rm -f "$resp"
    if [ "$code" = "200" ]; then ok "index template 已更新: $TEMPLATE_NAME"; else fail "index template 更新失败: HTTP=$code，响应见 $LOG_FILE"; fi
  else
    run_note "将更新 index template: $TEMPLATE_NAME，把冲突字段写入 mappings.properties"
  fi
  rm -f "$get_body" "$put_body" "$pairs"
}

list_data_streams() {
  local out code names
  out=$(mktemp)
  # ES _data_stream supports wildcards in the URL path (e.g. host-pve-*)
  code=$(curl_es GET "/_data_stream/${TEMPLATE_PATTERN}" '' "$out")
  printf '\n== Data streams %s ==\n' "$TEMPLATE_PATTERN" >> "$LOG_FILE"
  cat "$out" >> "$LOG_FILE"
  if [ "$code" = "200" ]; then
    names=$(python3 - "$out" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
for ds in data.get('data_streams', []):
    name = ds.get('name')
    if name:
        print(name)
PY
)
    if [ -n "$names" ]; then
      printf '%s\n' "$names"
      rm -f "$out"
      return 0
    fi
  fi
  rm -f "$out"

  # Fallback: derive data stream names from .ds-* backing indices via _cat/indices
  # NOTE: info/printf must go to stderr here, since stdout is captured by the caller.
  printf '[INFO] _data_stream/%s 没有返回结果，尝试通过 _cat/indices 反推 backing indices\n' "$TEMPLATE_PATTERN" 1>&2
  printf '[INFO] _data_stream/%s 没有返回结果，尝试通过 _cat/indices 反推 backing indices\n' "$TEMPLATE_PATTERN" >> "$LOG_FILE"
  out=$(mktemp)
  code=$(curl_es GET "/_cat/indices/${TEMPLATE_PATTERN}?h=index" '' "$out")
  printf '\n== Cat indices %s ==\n' "$TEMPLATE_PATTERN" >> "$LOG_FILE"
  cat "$out" >> "$LOG_FILE"
  if [ "$code" = "200" ]; then
    # Extract original data stream names from .ds-<name>-<date>-<gen> pattern
    grep '^\.ds-' "$out" 2>/dev/null | sed -E 's|^\.ds-(.+)-[0-9]{4}\.[0-9]{2}\.[0-9]{2}-[0-9]+$|\1|' | sort -u
  fi
  rm -f "$out"
}

rollover_data_streams() {
  [ "$ROLLOVER" -eq 1 ] || return 0
  section "Rollover data stream"
  local streams ds code body qs
  streams=$(list_data_streams || true)
  if [ -z "$streams" ]; then warn "没有找到匹配 data stream: $TEMPLATE_PATTERN"; return 0; fi
  while IFS= read -r ds; do
    [ -n "$ds" ] || continue
    body=$(mktemp)
    if [ "$APPLY" -eq 1 ]; then qs=''; else qs='?dry_run=true'; fi
    run_note "rollover data stream: $ds"
    code=$(curl_es POST "/${ds}/_rollover${qs}" '' "$body")
    cat "$body" >> "$LOG_FILE"
    if [ "$code" = "200" ]; then ok "rollover 请求成功: $ds"; else warn "rollover 请求返回 HTTP=$code: $ds，详情见 $LOG_FILE"; fi
    rm -f "$body"
  done <<EOF_STREAMS
$streams
EOF_STREAMS
}

delete_data_streams() {
  [ "$DELETE_DATA_STREAMS" -eq 1 ] || return 0
  section "删除 data stream"
  local streams ds code body
  streams=$(list_data_streams || true)
  if [ -z "$streams" ]; then warn "没有找到可删除 data stream: $TEMPLATE_PATTERN"; return 0; fi
  while IFS= read -r ds; do
    [ -n "$ds" ] || continue
    if [ "$APPLY" -eq 1 ] && [ "$YES" -eq 1 ]; then
      run_note "删除 data stream: $ds"
      body=$(mktemp)
      code=$(curl_es DELETE "/_data_stream/${ds}" '' "$body")
      cat "$body" >> "$LOG_FILE"
      if [ "$code" = "200" ]; then ok "已删除 data stream: $ds"; else fail "删除 data stream 失败: $ds HTTP=$code"; fi
      rm -f "$body"
    else
      run_note "将删除 data stream: $ds"
    fi
  done <<EOF_STREAMS
$streams
EOF_STREAMS
}

list_regular_indices() {
  local out code
  out=$(mktemp)
  code=$(curl_es GET "/_cat/indices/${TEMPLATE_PATTERN}?h=index" '' "$out")
  printf '\n== Regular indices %s ==\n' "$TEMPLATE_PATTERN" >> "$LOG_FILE"
  cat "$out" >> "$LOG_FILE"
  if [ "$code" = "200" ]; then grep -v '^\.ds-' "$out" | sed '/^[[:space:]]*$/d'; fi
  rm -f "$out"
}

delete_indices() {
  [ "$DELETE_INDICES" -eq 1 ] || return 0
  section "删除普通索引"
  local indices idx code body target_indices
  # If AUTO_FIX_INDICES is set and we found specific conflict indices, only delete those
  if [ "$AUTO_FIX_INDICES" -eq 1 ] && [ -n "$CONFLICT_INDICES" ]; then
    target_indices="$CONFLICT_INDICES"
  else
    target_indices=$(list_regular_indices || true)
  fi
  if [ -z "$target_indices" ]; then warn "没有找到可删除普通索引: $TEMPLATE_PATTERN"; return 0; fi
  while IFS= read -r idx; do
    [ -n "$idx" ] || continue
    # Skip data stream backing indices
    case "$idx" in .ds-*) continue ;; esac
    if [ "$APPLY" -eq 1 ] && [ "$YES" -eq 1 ]; then
      run_note "删除普通索引: $idx"
      body=$(mktemp)
      code=$(curl_es DELETE "/${idx}" '' "$body")
      cat "$body" >> "$LOG_FILE"
      if [ "$code" = "200" ]; then ok "已删除普通索引: $idx"; else fail "删除普通索引失败: $idx HTTP=$code"; fi
      rm -f "$body"
    else
      run_note "将删除普通索引: $idx"
    fi
  done <<EOF_INDICES
$target_indices
EOF_INDICES
}

reset_registry_if_needed() {
  [ "$RESET_REGISTRY" -eq 1 ] || return 0
  section "Registry 清理"
  local script="/etc/filebeat/cleanup_filebeat_registry.sh"
  local reg_dir="/var/lib/filebeat/registry/filebeat"

  # Prefer external script if present (legacy Debian machines)
  if [ -x "$script" ]; then
    if [ "$APPLY" -eq 1 ]; then
      run_note "执行外部 registry 清理脚本: $script"
      if [ "$START_FILEBEAT" -eq 1 ]; then "$script" >> "$LOG_FILE" 2>&1; else "$script" --no-start >> "$LOG_FILE" 2>&1; fi
      if [ $? -eq 0 ]; then ok "registry 清理完成"; else fail "registry 清理失败，详情见 $LOG_FILE"; fi
    else
      run_note "将执行: $script --dry-run"
      "$script" --dry-run >> "$LOG_FILE" 2>&1 || true
    fi
    return 0
  fi

  # Fallback: inline registry cleanup (no external script required, works on any PVE/Debian box)
  if [ ! -d "$reg_dir" ]; then
    warn "registry 目录不存在: $reg_dir，跳过 registry 清理"
    return 0
  fi

  if [ "$APPLY" -eq 1 ]; then
    run_note "内联 registry 清理: 停止 filebeat，清空 registry，重启 filebeat"
    systemctl stop "$SERVICE" >> "$LOG_FILE" 2>&1 || warn "systemctl stop $SERVICE 失败，继续尝试清理"
    # Backup registry files before nuking them
    local ts backup_dir
    ts=$(date +%Y%m%d%H%M%S)
    backup_dir="/tmp/filebeat_registry_backup_${ts}"
    mkdir -p "$backup_dir"
    cp -a "$reg_dir"/. "$backup_dir/" 2>/dev/null || true
    info "registry 备份: $backup_dir"
    # Remove log.json (incremental event log) and active.dat (active session marker).
    # Keep meta.json so filebeat re-uses the same registry root.
    rm -f "$reg_dir"/log.json "$reg_dir"/active.dat 2>/dev/null || true
    # Clear the per-shard JSON snapshot files so all files get re-read from the start.
    local snap
    for snap in "$reg_dir"/*.json; do
      [ -e "$snap" ] || continue
      case "$(basename "$snap")" in
        meta.json) continue ;;
      esac
      cp -f "$snap" "${snap}.bak" 2>/dev/null || true
      echo '[]' > "$snap"
    done
    ok "registry 已清空: $reg_dir"
    if [ "$START_FILEBEAT" -eq 1 ]; then
      systemctl start "$SERVICE" >> "$LOG_FILE" 2>&1 && ok "已启动 $SERVICE" || fail "启动 $SERVICE 失败"
    else
      info "未启动 filebeat (--no-start)"
    fi
  else
    run_note "将停止 filebeat，备份并清空 registry 目录: $reg_dir，然后重启 filebeat"
  fi
}

count_es_docs() {
  local out code count
  out=$(mktemp)
  code=$(curl_es GET "/${TEMPLATE_PATTERN}/_count" '' "$out")
  printf '\n== ES count %s ==\n' "$TEMPLATE_PATTERN" >> "$LOG_FILE"
  cat "$out" >> "$LOG_FILE"
  if [ "$code" = "200" ]; then
    count=$(python3 - "$out" <<'PY_COUNT'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get('count', 0))
except Exception:
    print('unknown')
PY_COUNT
)
  else
    count="unknown"
  fi
  rm -f "$out"
  printf '%s' "$count"
}

latest_source_file() {
  find /home/ansible_user/jh-monitor-data /home/ansible/jh-monitor-data -maxdepth 1 -type f \( \
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

trigger_latest_ingest() {
  [ "$TRIGGER_TEST" -eq 1 ] || return 0
  [ "$APPLY" -eq 1 ] || return 0
  section "触发最新一条写入"
  local src dst before after last_line
  src=$(latest_source_file || true)
  if [ -z "$src" ] || [ ! -f "$src" ]; then warn "没有找到可用于触发写入的监控源文件"; return 0; fi
  last_line=$(grep -v '^[[:space:]]*$' "$src" 2>/dev/null | tail -n 1 || true)
  if [ -z "$last_line" ]; then warn "源文件没有非空记录: $src"; return 0; fi
  dst=$(retry_file_for_source "$src")
  before=$(count_es_docs)
  printf '%s\n' "$last_line" > "$dst"
  chmod 0644 "$dst" 2>/dev/null || true
  ok "已生成测试写入文件: $dst"
  info "来源最新记录: $src"
  info "触发前 ES 文档数(${TEMPLATE_PATTERN}): $before"
  info "等待 ${WAIT_SECONDS}s 让 Filebeat 采集"
  sleep "$WAIT_SECONDS"
  after=$(count_es_docs)
  info "触发后 ES 文档数(${TEMPLATE_PATTERN}): $after"
  if [ "$before" != "unknown" ] && [ "$after" != "unknown" ] && [ "$after" -gt "$before" ] 2>/dev/null; then
    ok "测试写入成功：ES 文档数从 $before 增长到 $after"
  else
    warn "暂未确认 ES 文档数增长；请查看 Filebeat 错误日志和完整日志: $LOG_FILE"
  fi
}

summary() {
  section "结论"
  if [ "${#FIELDS[@]}" -eq 0 ]; then
    fail "没有待修复字段；请先运行诊断脚本或使用 --field 指定字段"
  fi
  if [ "$EXIT_CODE" -eq 0 ]; then
    ok "修复流程完成"
  elif [ "$EXIT_CODE" -eq 1 ]; then
    warn "流程完成，但存在告警，请查看日志"
  else
    fail "流程存在失败项，请先修复 FAIL"
  fi
  echo
  echo "关键信息:"
  echo "  - 模式: $([ "$APPLY" -eq 1 ] && echo APPLY || echo DRY-RUN)"
  echo "  - ES: ${ES_HOST:-未知}"
  echo "  - Template: ${TEMPLATE_NAME:-未知}"
  echo "  - Pattern: ${TEMPLATE_PATTERN:-未知}"
  echo "  - 索引模式: ${INDEX_MODE:-未知}"
  echo "  - 字段修复:"
  local i
  for i in "${!FIELDS[@]}"; do echo "      ${FIELDS[$i]} -> ${TYPES[$i]}"; done
  echo "  - 完整日志: $LOG_FILE"
  echo
  if [ "$APPLY" -eq 0 ] && [ "$ASK_CONFIRM" -eq 1 ] && [ "${#FIELDS[@]}" -gt 0 ] && [ "$EXIT_CODE" -lt 2 ]; then
    if [ "$PVE_MODE" -eq 1 ] && [ "$NUM_USER_ARGS" -eq 0 ]; then
      echo "PVE 模式 (零参数): 上面列出的修复动作会一次性全部执行；接下来输入 y 确认。"
    else
      echo "发现可修复项。接下来会询问是否立即修复；直接回车则不修改。"
    fi
  elif [ "$APPLY" -eq 0 ]; then
    echo "当前仅预检，没有修改 ES。"
    echo "需要跳过确认直接修复时可使用:"
    echo "  $0 --apply --since '$SINCE'"
  fi
}

confirm_and_apply() {
  [ "$APPLY" -eq 0 ] || return 0
  [ "$ASK_CONFIRM" -eq 1 ] || return 0
  [ "${#FIELDS[@]}" -gt 0 ] || return 0
  [ "$EXIT_CODE" -lt 2 ] || return 0

  section "确认修复"
  echo "将执行以下修复动作:"
  echo "  - 更新 ES index template: ${TEMPLATE_NAME:-未知}"
  if [ "$DELETE_DATA_STREAMS" -eq 1 ]; then
    echo "  - 删除匹配 data stream: ${TEMPLATE_PATTERN:-未知}"
  elif [ "$ROLLOVER" -eq 1 ] && [ "$INDEX_MODE" != "regular_index" ]; then
    echo "  - rollover 匹配 data stream: ${TEMPLATE_PATTERN:-未知}"
  fi
  if [ "$INDEX_MODE" = "regular_index" ] || [ "$INDEX_MODE" = "mixed" ]; then
    echo "  - 注意: 数据写入普通索引(非 data stream)，template 更新仅对新建索引生效"
  fi
  if [ "$DELETE_INDICES" -eq 1 ]; then echo "  - 删除匹配普通索引: ${TEMPLATE_PATTERN:-未知}"; fi
  if [ "$RESET_REGISTRY" -eq 1 ]; then echo "  - 清理 Filebeat registry，让本机监控文件重新采集"; fi
  if [ "$TRIGGER_TEST" -eq 1 ]; then echo "  - 修复后触发最新一条监控数据重新写入，并检查 ES 是否增长"; fi
  echo "  - 字段修复:"
  local i answer
  for i in "${!FIELDS[@]}"; do echo "      ${FIELDS[$i]} -> ${TYPES[$i]}"; done
  echo
  if { [ "$DELETE_DATA_STREAMS" -eq 1 ] || [ "$DELETE_INDICES" -eq 1 ]; } && [ "$YES" -ne 1 ] && [ "$NUM_USER_ARGS" -ne 0 ]; then
    fail "涉及删除 ES 数据，但没有加 --yes；不会执行删除修复"
    return 0
  fi
  printf "是否立即执行修复？输入 y/yes/是 确认，直接回车取消: "
  IFS= read -r answer
  case "$answer" in
    y|Y|yes|YES|Yes|是|确认|fix|FIX) ;;
    *) warn "未确认，已取消修复；ES 未被修改"; return 0 ;;
  esac
  APPLY=1
  # In zero-arg PVE mode, the single y/N covers the destructive deletes too.
  if [ "$NUM_USER_ARGS" -eq 0 ]; then YES=1; fi
  EXIT_CODE=0
  section "执行修复"
  update_template
  create_component_template
  disable_template_overwrite
  if [ "$DELETE_DATA_STREAMS" -eq 1 ]; then
    delete_data_streams
  elif [ "$INDEX_MODE" = "regular_index" ]; then
    info "普通索引模式: 跳过 data stream rollover"
  else
    rollover_data_streams
  fi
  delete_indices
  reset_registry_if_needed
  trigger_latest_ingest
}


# =====================================================================
# PVE-specific improvements: component template + auto-detect + overwrite fix
# =====================================================================

PVE_KNOWN_DOUBLE_FIELDS=(
  "pve.data.sensors.temperatures.value"
  "pve.data.sensors.fans.value"
  "pve.data.sensors.voltages.value"
  "pve.data.cpu.top_processes.cpu"
  "pve.data.cpu.top_processes.mem"
  "pve.data.smart.devices.temperature"
)

detect_pve_fields() {
  # Auto-detect PVE data patterns and add known double-type conflict fields
  local pattern_lower="${TEMPLATE_PATTERN,,}"
  local config_lower
  config_lower=$(cat "$CONFIG" 2>/dev/null | tr '[:upper:]' '[:lower:]')
  if [[ "$pattern_lower" == *"pve"* ]] || [ "$PVE_MODE" -eq 1 ] || echo "$config_lower" | grep -q '"host-pve'; then
    if [ "$PVE_MODE" -eq 0 ]; then
      info "自动检测到 PVE 数据模式"
      PVE_MODE=1
    fi
    info "PVE 模式: 添加已知易冲突 double 字段 (6 个)"
    for field in "${PVE_KNOWN_DOUBLE_FIELDS[@]}"; do
      add_field_once "$field" "double"
    done
    # Auto-enable PVE-recommended settings if not explicitly set by user
    if [ -z "$COMPONENT_TEMPLATE" ]; then
      COMPONENT_TEMPLATE="pve-data-mappings"
      info "PVE 模式: 自动启用组件模板 ($COMPONENT_TEMPLATE)"
    fi
    if [ "$DISABLE_TEMPLATE_OVERWRITE" -eq 0 ]; then
      # PVE mode always needs this to prevent filebeat from overwriting custom mappings
      DISABLE_TEMPLATE_OVERWRITE=1
      info "PVE 模式: 自动启用 --disable-template-overwrite"
    fi
    # If the user ran with no arguments (zero-arg auto mode), enable all the
    # destructive actions PVE fixes always need. The confirm_and_apply() prompt
    # will still ask for explicit y/N before anything is actually changed.
    if [ "$NUM_USER_ARGS" -eq 0 ]; then
      if [ "$DELETE_DATA_STREAMS" -eq 0 ] && [ "$DELETE_INDICES" -eq 0 ]; then
        if [ "$INDEX_MODE" = "data_stream" ]; then
          DELETE_DATA_STREAMS=1
          info "PVE 零参数模式: 自动启用 --delete-data-streams (data stream 模式)"
        else
          DELETE_INDICES=1
          info "PVE 零参数模式: 自动启用 --delete-indices"
        fi
      fi
      if [ "$RESET_REGISTRY" -eq 0 ]; then
        RESET_REGISTRY=1
        info "PVE 零参数模式: 自动启用 --reset-registry"
      fi
      # YES will be auto-set inside confirm_and_apply() when the user types y.
    elif [ "$DELETE_DATA_STREAMS" -eq 0 ] && [ "$DELETE_INDICES" -eq 0 ] && [ "$APPLY" -eq 0 ]; then
      info "PVE 模式: 建议连同 --apply --yes --delete-indices 一起使用 (或直接无参数运行 $0)"
    fi
  fi
}

create_component_template() {
  [ -n "$COMPONENT_TEMPLATE" ] || return 0
  section "创建/更新组件模板 (component template)"
  local ct_body pairs_file
  ct_body=$(mktemp)
  pairs_file=$(mktemp)
  for i in "${!FIELDS[@]}"; do printf '%s\t%s\n' "${FIELDS[$i]}" "${TYPES[$i]}" >> "$pairs_file"; done

  python3 - "$COMPONENT_TEMPLATE" "$pairs_file" "$ct_body" <<'PY_CT'
import json, sys

ct_name = sys.argv[1]
pairs_file = sys.argv[2]
ct_body_file = sys.argv[3]

def field_mapping(t):
    m = {'type': t}
    if t in ('long','integer','short','byte','double','float','half_float','scaled_float'):
        m['coerce'] = True
        m['ignore_malformed'] = True
    if t == 'keyword':
        m['ignore_above'] = 1024
    return m

def put_mapping(root, dotted, typ):
    parts = [p for p in dotted.split('.') if p]
    cur = root
    for part in parts[:-1]:
        node = cur.setdefault(part, {})
        if 'type' in node and node.get('type') != 'object':
            node.pop('type', None)
        cur = node.setdefault('properties', {})
    cur[parts[-1]] = field_mapping(typ)

props = {}
for line in open(pairs_file):
    line = line.strip()
    if not line: continue
    field, typ = line.split('\t', 1)
    put_mapping(props, field, typ)

if not props:
    print("SKIP")
    sys.exit(0)

template = {
    "template": {
        "mappings": {
            "properties": props
        }
    }
}

with open(ct_body_file, 'w') as f:
    json.dump(template, f, ensure_ascii=False)
PY_CT

  rm -f "$pairs_file"

  if [ ! -s "$ct_body" ]; then
    warn "组件模板 JSON 为空，跳过创建"
    rm -f "$ct_body"
    return 0
  fi

  printf '\n== Component template body ==\n' >> "$LOG_FILE"
  cat "$ct_body" >> "$LOG_FILE"

  if [ "$APPLY" -eq 1 ]; then
    local resp code
    resp=$(mktemp)
    code=$(curl_es PUT "/_component_template/${COMPONENT_TEMPLATE}" "$ct_body" "$resp")
    printf '\n== PUT component template %s response ==\n' "$COMPONENT_TEMPLATE" >> "$LOG_FILE"
    cat "$resp" >> "$LOG_FILE"
    rm -f "$resp"
    if [ "$code" = "200" ]; then
      ok "组件模板已创建: $COMPONENT_TEMPLATE"
      add_component_to_template
    else
      fail "组件模板创建失败: $COMPONENT_TEMPLATE，HTTP=$code"
    fi
  else
    run_note "将创建组件模板: $COMPONENT_TEMPLATE"
  fi
  rm -f "$ct_body"
}

add_component_to_template() {
  # Add the component template to composed_of in the index template
  local get_body put_body code backup
  get_body=$(mktemp)
  code=$(curl_es GET "/_index_template/${TEMPLATE_NAME}" '' "$get_body")
  if [ "$code" != "200" ]; then
    warn "无法读取 index template $TEMPLATE_NAME 来添加 composed_of: HTTP=$code"
    rm -f "$get_body"
    return
  fi

  backup=$(mktemp "/tmp/${TEMPLATE_NAME}_composed_of_backup_XXXXXX.json")
  cp -f "$get_body" "$backup"
  info "模板备份 (composed_of 修改前): $backup"

  put_body=$(mktemp)
  python3 - "$get_body" "$put_body" "$COMPONENT_TEMPLATE" <<'PY_ADD'
import json, sys

src_file = sys.argv[1]
dst_file = sys.argv[2]
component_name = sys.argv[3]

raw = json.load(open(src_file))
body = raw['index_templates'][0]['index_template']
composed = body.get('composed_of', [])

if component_name not in composed:
    composed.append(component_name)
    body['composed_of'] = composed

json.dump(body, open(dst_file, 'w'), ensure_ascii=False, indent=2)
print(','.join(composed))
PY_ADD

  local composed_list
  composed_list=$(python3 - "$get_body" "$put_body" "$COMPONENT_TEMPLATE" 2>&1)
  info "index template composed_of: $composed_list"

  if [ "$APPLY" -eq 1 ]; then
    local resp
    resp=$(mktemp)
    code=$(curl_es PUT "/_index_template/${TEMPLATE_NAME}" "$put_body" "$resp")
    printf '\n== PUT template (composed_of) response ==\n' >> "$LOG_FILE"
    cat "$resp" >> "$LOG_FILE"
    rm -f "$resp"
    if [ "$code" = "200" ]; then ok "index template composed_of 已更新，包含组件模板 $COMPONENT_TEMPLATE"; else fail "index template composed_of 更新失败: HTTP=$code"; fi
  fi
  rm -f "$get_body" "$put_body"
}

disable_template_overwrite() {
  [ "$DISABLE_TEMPLATE_OVERWRITE" -eq 1 ] || return 0
  [ -f "$CONFIG" ] || { warn "Filebeat 配置文件不存在: $CONFIG"; return 0; }
  local current
  current=$(grep -c 'setup.template.overwrite:[[:space:]]*true' "$CONFIG" 2>/dev/null)
  current=${current:-0}
  if [ "$current" -gt 0 ]; then
    if [ "$APPLY" -eq 1 ]; then
      sed -i 's/setup.template.overwrite:[[:space:]]*true/setup.template.overwrite: false/' "$CONFIG"
      ok "已设置 setup.template.overwrite: false (原为 true)"
      info "注意: 修改后需要重启 filebeat 才能生效"
    else
      run_note "将设置 setup.template.overwrite: false (原为 true)"
    fi
  else
    info "setup.template.overwrite 已不是 true，无需修改"
  fi
}
check_prerequisites
check_es_connection
detect_conflicts
detect_pve_fields
if [ "${#FIELDS[@]}" -gt 0 ]; then
  update_template
  create_component_template
  disable_template_overwrite
  if [ "$DELETE_DATA_STREAMS" -eq 1 ]; then
    delete_data_streams
  elif [ "$INDEX_MODE" = "regular_index" ]; then
    info "普通索引模式: 跳过 data stream rollover（对普通索引无意义）"
  else
    rollover_data_streams
  fi
  delete_indices
  reset_registry_if_needed
  trigger_latest_ingest
fi
summary
confirm_and_apply
if [ "$APPLY" -eq 1 ]; then summary; fi
