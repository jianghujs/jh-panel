#!/bin/bash
set -e

# 检查mysql客户端是否存在
if ! command -v mysql &> /dev/null; then
    echo "mysql客户端未安装，请先安装后再运行脚本。"
    exit 1
fi

# 提示输入数据库IP地址，默认为：127.0.0.1
default_db_host="127.0.0.1"
read -p "请输入数据库IP地址（默认为：${default_db_host}）：" db_host
db_host=${db_host:-$default_db_host}

# 提示输入数据库端口，默认为：33067
default_db_port="33067"
read -p "请输入数据库端口（默认为：${default_db_port}）：" db_port
db_port=${db_port:-$default_db_port}

# 提示输入数据库用户名，默认为：root
default_db_user="root"
read -p "请输入数据库用户名（默认为：${default_db_user}）：" db_user
db_user=${db_user:-${default_db_user}}

# 提示输入数据库密码，默认为空
read -p "请输入数据库密码（默认为空）：" db_password

mysql_exec() {
    if [ -n "$db_password" ]; then
        mysql -u"$db_user" -p"$db_password" -h"$db_host" -P"$db_port" "$@"
    else
        mysql -u"$db_user" -h"$db_host" -P"$db_port" "$@"
    fi
}

# 连接mysql查询数据库列表
databases=$(mysql_exec -e "SHOW DATABASES;" | awk '{if(NR>1) print $0}')

# 提示输入需要忽略的库，默认为：mysql,performance_schema,sys,information_schema
default_ignored_databases="mysql,performance_schema,sys,information_schema"
read -p "请输入需要忽略的库，多个用英文逗号隔开（默认为${default_ignored_databases}）：" ignored_databases
ignored_databases=${ignored_databases:-$default_ignored_databases}

# 将忽略的库转换为数组
IFS=',' read -r -a ignored_databases_arr <<< "$ignored_databases"

# 过滤掉用户输入的数据库
filtered_databases=""
for db in $databases; do
    ignore=false
    for ignored_db in "${ignored_databases_arr[@]}"; do
        if [[ "$db" == "$ignored_db" ]]; then
            ignore=true
            break
        fi
    done
    if [[ "$ignore" == false ]]; then
        filtered_databases+="$db,"
    fi
done
filtered_databases=${filtered_databases%,}

# 提示选择需要清理的数据库
default_selected_databases=${filtered_databases}
read -p "请选择需要清理的数据库（多个数据库用英文逗号隔开，默认为$default_selected_databases）：" selected_databases
selected_databases=${selected_databases:-$default_selected_databases}

# 保留天数
default_retention_days="90"
read -p "请输入保留天数（默认为：${default_retention_days}）：" retention_days
retention_days=${retention_days:-$default_retention_days}

# 时间字段候选列表（使用默认，不再提示）
default_time_columns="operationAt,operation_at,created_at,create_time,record_time,ctime,createdTime,createTime,recordTime"
time_columns=$default_time_columns
IFS=',' read -r -a time_columns_arr <<< "$time_columns"

# 整型时间戳单位（默认 seconds，不再提示）
ts_unit="seconds"

# 输出目录固定为 /tmp，文件直接放根目录
timestamp=$(date +%Y%m%d_%H%M%S)
sql_file="/tmp/cleanup_record_history_${timestamp}.sql"
report_file="/tmp/cleanup_record_history_report_${timestamp}.txt"

# 生成时间点
cutoff_datetime=$(date -d "${retention_days} days ago" "+%Y-%m-%d %H:%M:%S")
cutoff_iso=$(date -d "${retention_days} days ago" "+%Y-%m-%dT%H:%M:%S")
cutoff_ts=$(date -d "${retention_days} days ago" "+%s")
cutoff_ts_ms=$((cutoff_ts * 1000))

format_bytes() {
    local bytes=$1
    if [ "$bytes" -lt 1024 ]; then
        echo "${bytes} B"
    elif [ "$bytes" -lt $((1024 * 1024)) ]; then
        awk -v b="$bytes" 'BEGIN{printf "%.2f KB", b/1024}'
    elif [ "$bytes" -lt $((1024 * 1024 * 1024)) ]; then
        awk -v b="$bytes" 'BEGIN{printf "%.2f MB", b/1024/1024}'
    else
        awk -v b="$bytes" 'BEGIN{printf "%.2f GB", b/1024/1024/1024}'
    fi
}

trim() {
    echo "$1" | awk '{$1=$1;print}'
}

print_sql_with_highlight() {
    if [ -t 1 ]; then
        local color_kw=$'\033[1;36m'
        local color_comment=$'\033[0;90m'
        local color_reset=$'\033[0m'
        sed -E \
            -e "s#--.*#${color_comment}&${color_reset}#g" \
            -e "s#\\<(DELETE|FROM|WHERE|SET|SELECT|INSERT|UPDATE|CREATE|DROP|ALTER|TRUNCATE)\\>#${color_kw}\\1${color_reset}#g" \
            "$sql_file"
    else
        cat "$sql_file"
    fi
}

pick_time_column() {
    local db="$1"
    local table="$2"
    for col in "${time_columns_arr[@]}"; do
        col=$(trim "$col")
        if [ -z "$col" ]; then
            continue
        fi
        local col_lc
        col_lc=$(echo "$col" | tr 'A-Z' 'a-z')
        local res
        res=$(mysql_exec -N -e "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='${db}' AND table_name='${table}' AND LOWER(column_name)='${col_lc}' LIMIT 1;")
        if [ -n "$res" ]; then
            echo "$res"
            return 0
        fi
    done
    return 1
}

build_condition() {
    local col="$1"
    local data_type="$2"
    local condition=""
    local cutoff_display=""
    case "$data_type" in
        datetime|timestamp|date)
            condition="\`${col}\` < '${cutoff_datetime}'"
            cutoff_display="$cutoff_datetime"
            ;;
        int|bigint|mediumint|smallint|tinyint)
            if [ "$ts_unit" = "milliseconds" ]; then
                condition="\`${col}\` < ${cutoff_ts_ms}"
                cutoff_display="$cutoff_ts_ms"
            else
                condition="\`${col}\` < ${cutoff_ts}"
                cutoff_display="$cutoff_ts"
            fi
            ;;
        char|varchar|text|mediumtext|longtext)
            condition="SUBSTRING(\`${col}\`,1,19) < '${cutoff_iso}'"
            cutoff_display="$cutoff_iso"
            ;;
        *)
            condition=""
            cutoff_display=""
            ;;
    esac
    echo "${condition}|${cutoff_display}"
}

# 初始化输出文件
echo "-- Record history cleanup SQL" > "$sql_file"
echo "-- Generated at: $(date '+%Y-%m-%d %H:%M:%S')" >> "$sql_file"
echo "-- Retention days: ${retention_days}" >> "$sql_file"
echo "-- Databases: ${selected_databases}" >> "$sql_file"
echo "SET SQL_SAFE_UPDATES=0;" >> "$sql_file"
echo "" >> "$sql_file"

echo "Record history cleanup report" > "$report_file"
echo "Generated at: $(date '+%Y-%m-%d %H:%M:%S')" >> "$report_file"
echo "Retention days: ${retention_days}" >> "$report_file"
echo "Databases: ${selected_databases}" >> "$report_file"
echo "" >> "$report_file"

total_est_rows=0
total_est_bytes=0

# 循环需要清理的数据库
IFS=',' read -r -a selected_db_arr <<< "$selected_databases"

for db in "${selected_db_arr[@]}"; do
    db=$(trim "$db")
    if [ -z "$db" ]; then
        continue
    fi

    tables=$(mysql_exec -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='${db}' AND table_type='BASE TABLE' AND table_name LIKE '%\\_record_history%' ESCAPE '\\\\' ORDER BY table_name;")

    if [ -z "$tables" ]; then
        echo "未找到匹配 _record_history 的数据表。" >> "$report_file"
        continue
    fi

    for table in $tables; do
        time_info=$(pick_time_column "$db" "$table" || true)
        if [ -z "$time_info" ]; then
            read -p "未找到时间字段，请输入 ${db}.${table} 的时间字段（留空跳过）：" manual_col
            manual_col=$(trim "$manual_col")
            if [ -z "$manual_col" ]; then
                echo "跳过：${table}（未指定时间字段）" >> "$report_file"
                continue
            fi
            time_info=$(mysql_exec -N -e "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='${db}' AND table_name='${table}' AND column_name='${manual_col}' LIMIT 1;")
            if [ -z "$time_info" ]; then
                echo "跳过：${table}（字段不存在：${manual_col}）" >> "$report_file"
                continue
            fi
        fi

        time_col=$(echo "$time_info" | awk '{print $1}')
        time_type=$(echo "$time_info" | awk '{print $2}')

        condition_info=$(build_condition "$time_col" "$time_type")
        condition=$(echo "$condition_info" | awk -F'|' '{print $1}')
        cutoff_display=$(echo "$condition_info" | awk -F'|' '{print $2}')

        if [ -z "$condition" ]; then
            echo "跳过：${table}（不支持的类型：${time_type}）" >> "$report_file"
            continue
        fi

        if ! table_stats=$(mysql_exec -N -e "SELECT IFNULL(table_rows,0), IFNULL(data_length,0), IFNULL(index_length,0) FROM information_schema.tables WHERE table_schema='${db}' AND table_name='${table}' LIMIT 1;"); then
            echo "跳过：${table}（获取表信息失败）" >> "$report_file"
            continue
        fi

        total_rows=$(echo "$table_stats" | awk '{print $1}')
        data_length=$(echo "$table_stats" | awk '{print $2}')
        index_length=$(echo "$table_stats" | awk '{print $3}')
        total_bytes=$((data_length + index_length))

        if ! delete_rows=$(mysql_exec -N -e "SELECT COUNT(*) FROM \`${db}\`.\`${table}\` WHERE ${condition};"); then
            echo "跳过：${table}（统计删除行数失败）" >> "$report_file"
            continue
        fi
        delete_rows=${delete_rows:-0}

        if [ "$total_rows" -eq 0 ]; then
            est_bytes=0
        else
            est_bytes=$(awk -v c="$delete_rows" -v t="$total_rows" -v b="$total_bytes" 'BEGIN{if(t==0){print 0}else{printf "%.0f", (c/t)*b}}')
        fi

        total_est_rows=$((total_est_rows + delete_rows))
        total_est_bytes=$((total_est_bytes + est_bytes))

        est_size_human=$(format_bytes "$est_bytes")

        {
            echo "表：${table}"
            echo "- 时间字段：${time_col} (${time_type})"
            echo "- 截止值：${cutoff_display}"
            echo "- 预计删除行数：${delete_rows} / 总行数：${total_rows}"
            echo "- 预计清理大小：${est_size_human}"
            echo ""
        } >> "$report_file"

        {
            echo "-- Database: ${db}"
            echo "-- Table: ${table}"
            echo "-- Time column: ${time_col} (${time_type})"
            echo "-- Cutoff: ${cutoff_display}"
            echo "-- Estimated delete rows: ${delete_rows} / total ${total_rows}"
            echo "DELETE FROM \`${db}\`.\`${table}\` WHERE ${condition};"
            echo ""
        } >> "$sql_file"
    done
done

{
    echo "汇总："
    echo "- 预计删除总行数：${total_est_rows}"
    echo "- 预计清理总大小：$(format_bytes "$total_est_bytes")"
} >> "$report_file"

echo "预计清理总大小：$(format_bytes "$total_est_bytes")"
echo "清理 SQL 内容："
print_sql_with_highlight
read -p "是否执行清理 SQL？（默认n）[y/N] " execute_now
execute_now=${execute_now:-n}

case $execute_now in
    [Yy]* )
        mysql_exec < "$sql_file"
        ;;
    * )
        ;;
esac
