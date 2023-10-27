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
default_db_password=""
read -p "请输入数据库密码（默认为空）：" db_password
db_password=${db_password:-${default_db_password}}

# 选择存放备份的目录
read -p "请选择存放备份的目录（默认为：/www/backup/mydumper/）: " backup_dir
backup_dir=${backup_dir:-/www/backup/mydumper/}

if [ ! -d "$backup_dir" ]; then
  echo "${backup_dir}目录不存在"
  exit -1
fi

while true; do
    echo "请选择需要恢复的数据库："
    i=1
    db_folders=()
    for db_folder in $(ls -d ${backup_dir}*/); do
        db_name=$(basename "$db_folder")
        echo "$i. $db_name"
        db_folders+=("$db_folder")
        i=$((i+1))
    done

    read -p "请输入要导入的数据库编号（输入 a 导入所有数据库，输入 q 退出）：" db_index

    if [ "$db_index" = "q" ]; then
        break
    fi

    if [ "$db_index" = "a" ]; then
        read -p "确定要将导入${backup_dir}下的全部数据库吗？（默认n）[y/n] " import_all_choice
        import_all_choice=${import_all_choice:-n}
        if [[ "$import_all_choice" == "y" ]]; then
            for db_folder in "${db_folders[@]}"; do
                db_name=$(basename "$db_folder")
                myloader -t 4 -u $db_user -p $db_password -h $db_host -P $db_port -B $db_name -d $db_folder --overwrite-tables
                echo "数据库${db_name}导入完成✅"
            done
            break
        fi
    fi

    # 检查输入的编号是否有效
    if ! [[ "$db_index" =~ ^[0-9]+$ ]] || (( db_index < 1 || db_index > i-1 )); then
        echo "无效的数据库编号，请重新输入。"
        continue
    fi

    selected_db_folder="${db_folders[db_index-1]}"
    db_name=$(basename "$selected_db_folder")

    read -p "确定要将${selected_db_folder}的文件导入到${db_name}吗？（默认y）[y/n] " import_choice
    import_choice=${import_choice:-y}

    if [[ "$import_choice" == "y" ]]; then
        myloader -t 4 -u $db_user -p $db_password -h $db_host -P $db_port -B $db_name -d $selected_db_folder --overwrite-tables
        echo "数据库${db_name}导入完成✅"
    fi
done

