#!/bin/bash
# 检查mydumper是否安装
if ! command -v mydumper &> /dev/null; then
    echo "mydumper未安装，正在尝试自动安装..."
    apt-get update
    apt-get install mydumper -y
    if ! command -v mydumper &> /dev/null; then
        echo "安装mydumper失败，请手动安装后再运行脚本。"
        exit 1
    fi
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

# 连接本地mysql查询数据库列表
databases=$(mysql -u$db_user -p$db_password -h$db_host -P$db_port -e "SHOW DATABASES;" | awk '{if(NR>1) print $0}')

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

# 提示选择需要批量导出的数据库
default_selected_databases=${filtered_databases}
read -p "请选择需要批量导出的数据库（多个数据库用英文逗号隔开，默认为$default_selected_databases）: " selected_databases
selected_databases=${selected_databases:-$default_selected_databases}

# 选择存放备份的目录
read -p "请选择存放备份的目录（默认为：/www/backup/mydumper/）: " backup_dir
backup_dir=${backup_dir:-/www/backup/mydumper/}

if [ -d "$backup_dir" ]; then
    read -p "目录已存在，是否清空目录？（默认n）[y/n] " yn
    yn=${yn:-n}
    case $yn in
        [Yy]* ) rm -rf $backup_dir/*;;
        [Nn]* ) echo "已跳过清空目录";;
        * ) echo "请输入y或n";;
    esac
else
    mkdir -p $backup_dir
    echo "${backup_dir}目录已创建"
fi

# 循环需要导出的数据库，执行备份导出命令
for db in $(echo $selected_databases | tr ',' ' '); do
    echo "|- 正在备份数据库${db}..."
    mydumper -t 4 -u $db_user -p $db_password -h $db_host -P $db_port -B $db -o $backup_dir$db/
    echo "|- 数据库${db}备份完成✅ "
done
                                             
                                             

echo ""
echo "===========================批量导出完成✅=========================="
echo "- 数据库连接：${db_host}:${db_port}"
echo "- 忽略的数据库：$ignored_databases"
echo "- 导出的数据库：$selected_databases"
echo "- 导出数据库文件目录：$backup_dir"
echo "---------------------------后续操作指引❗❗----------------------------"
echo "请在${sqlFileDir}复制到目标服务器并执行批量导入工具进行批量导入"
echo "====================================================================="
