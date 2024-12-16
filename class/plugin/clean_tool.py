# coding: utf-8
import sys
import os
import json
import datetime
import fnmatch
import time
import re

def extract_date_from_name(name, date_pattern):
    """从文件或目录名称中提取日期
    :param name: 文件或目录名称
    :param date_pattern: 日期匹配模式，如：r'.*_(\d{8}).*'
    :return: datetime.date对象或None
    """
    if not date_pattern:
        return None
    
    match = re.search(date_pattern, name)
    if match:
        try:
            date_str = match.group(1)
            return datetime.datetime.strptime(date_str, '%Y%m%d').date()
        except (ValueError, IndexError):
            return None
    return None

def cleanPath(path, save, pattern, is_dir=False, date_pattern=None):
    if not os.path.exists(path):
        print("|---[" + path + "]不存在")
        return
    # 防止误删根目录
    if path == '/':
        print("|---不能清理根目录")
        return

    print("|---开始清理过期文件")
    print("|---清理目录:", path)
    print('|---文件通配符:', pattern)
    # 清理多余备份
    saveAllDay = int(save.get('saveAllDay'))
    saveOther = int(save.get('saveOther'))
    saveMaxDay = int(save.get('saveMaxDay'))

    # saveAllDay天内全部保留，其余只保留saveOther份，最长保留saveMaxDay天
    print("|---清理规则：[" + str(saveAllDay) + "]天内全部保留，其余只保留[" + str(saveOther) + "]份，最长保留[" + str(saveMaxDay) + "]天")

    # 获取目录下的所有文件或目录
    items = []
    for name in fnmatch.filter(os.listdir(path), pattern):
        full_path = os.path.join(path, name)
        # 根据is_dir参数判断是否只处理目录
        if is_dir and not os.path.isdir(full_path):
            continue
        if not is_dir and not os.path.isfile(full_path):
            continue
            
        # 如果提供了日期模式，则从名称中提取日期，否则使用创建时间
        if date_pattern:
            extracted_date = extract_date_from_name(name, date_pattern)
            if extracted_date:
                items.append({
                    'filename': full_path,
                    'addtime': extracted_date.strftime('%Y/%m/%d %H:%M:%S')
                })
            else:
                continue
        else:
            items.append({
                'filename': full_path,
                'addtime': time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(os.path.getctime(full_path)))
            })

    print("|---共有[" + str(len(items)) + "]个" + ("目录" if is_dir else "文件"))

    # 获取当前日期
    now = datetime.datetime.now()

    # 将备份按日期分组
    items_by_date = {}
    for item in items:
        item_time = datetime.datetime.strptime(item['addtime'], '%Y/%m/%d %H:%M:%S')
        date = item_time.date()
        if date not in items_by_date:
            items_by_date[date] = []
        items_by_date[date].append(item)

    # 保存需要删除的备份
    to_delete = []

    for date, items_on_date in items_by_date.items():
        # 计算备份距离现在的天数
        days = (now.date() - date).days

        # saveAllDay天内全部保留
        if days <= saveAllDay:
            continue

        # 其余只保留saveOther份
        if len(items_on_date) > saveOther:
            # 对备份按时间排序，然后只保留最新的saveOther份
            items_on_date.sort(key=lambda x: x['addtime'], reverse=True)
            to_delete.extend(items_on_date[saveOther:])

        # 最长保留saveMaxDay天
        if days > saveMaxDay:
            to_delete.extend(items_on_date)
    if len(to_delete) == 0:
        print("|---没有需要清理的文件")
        return

    # 删除需要删除的备份
    for item in to_delete:
        if is_dir:
            os.system("rm -rf " + item['filename'])
            print("|---已清理过期目录：" + item['filename'])
        else:
            os.system("rm -f " + item['filename'])
            print("|---已清理过期文件：" + item['filename'])
