# coding: utf-8
#-----------------------------
# 文件夹清理工具
# 清理文件:
# python3 /www/server/jh-panel/scripts/clean.py /root/test '{"saveAllDay": "3", "saveOther": "1", "saveMaxDay": "30"}'
# python3 /www/server/jh-panel/scripts/clean.py /root/test '{"saveAllDay": "3", "saveOther": "1", "saveMaxDay": "30"}' 'jianghujs.*.js'
# 清理目录并从目录名提取日期:
# python3 /www/server/jh-panel/scripts/clean.py /root/backup '{"saveAllDay": "3", "saveOther": "1", "saveMaxDay": "30"}' 'xtrabackup_inc_data_*' --dir --date-pattern '.*_(\d{8})_.*$'
# python3 /www/server/jh-panel/scripts/clean.py /root/backup '{"saveAllDay": "3", "saveOther": "0", "saveMaxDay": "3"}' 'xtrabackup_inc_data_*' --dir --date-pattern '.*_(\d{8})_.*$'
#-----------------------------

import sys
import os
import argparse

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')

chdir = os.getcwd()
sys.path.append(chdir + '/class/core')
sys.path.append(chdir + '/class/plugin')

import mw
import db
import time
import json
import clean_tool

def parse_arguments():
    parser = argparse.ArgumentParser(description='清理文件或目录工具')
    parser.add_argument('path', help='要清理的路径')
    parser.add_argument('save', help='保存规则的JSON字符串')
    parser.add_argument('pattern', nargs='?', default='*', help='文件或目录匹配模式')
    parser.add_argument('--dir', action='store_true', help='是否清理目录而不是文件')
    parser.add_argument('--date-pattern', help='从文件或目录名称中提取日期的正则表达式模式')
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    try:
        save = json.loads(args.save)
    except json.JSONDecodeError:
        print("错误：保存规则必须是有效的JSON字符串")
        sys.exit(1)

    path = args.path
    dir = args.dir
    
    if dir and not mw.checkDir(path):
        print(f"错误：目录{path}不允许删除")
        sys.exit(1)

    clean_tool.cleanPath(
        path=path,
        save=save,
        pattern=args.pattern,
        is_dir=dir,
        date_pattern=args.date_pattern
    )
