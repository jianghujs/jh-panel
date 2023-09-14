# coding: utf-8
import sys
import os
import json
import datetime
import fnmatch
import time

def cleanPath(path, save, pattern):
    if not os.path.exists(path):
        print("|---[" + path + "]不存在")
        return

    print("|---开始清理过期文件")
    print("path:", path)
    print('pattern:', pattern)
    # 清理多余备份
    saveAllDay = int(save.get('saveAllDay'))
    saveOther = int(save.get('saveOther'))
    saveMaxDay = int(save.get('saveMaxDay'))

    # saveAllDay天内全部保留，其余只保留saveOther份，最长保留saveMaxDay天
    print("|---清理规则：[" + str(saveAllDay) + "]天内全部保留，其余只保留[" + str(saveOther) + "]份，最长保留[" + str(saveMaxDay) + "]天")

    # 获取目录下的所有文件
    files = []
    for filename in fnmatch.filter(os.listdir(path), pattern):
        files.append({
            'filename': path + '/' + filename,
            'addtime': time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(os.path.getctime(path + '/' + filename)))
        })

    print("|---共有[" + str(len(files)) + "]个文件")

    # 获取当前日期
    now = datetime.datetime.now()

    # 将备份按日期分组
    files_by_date = {}
    for f in files:
        f_time = datetime.datetime.strptime(f['addtime'], '%Y/%m/%d %H:%M:%S')
        date = f_time.date()
        if date not in files_by_date:
            files_by_date[date] = []
        files_by_date[date].append(f)

    # 保存需要删除的备份
    to_delete = []

    for date, files_on_date in files_by_date.items():
        # 计算备份距离现在的天数
        days = (now.date() - date).days

        # saveAllDay天内全部保留
        if days <= saveAllDay:
            continue

        # 其余只保留saveOther份
        if len(files_on_date) > saveOther:
            # 对备份按时间排序，然后只保留最新的saveOther份
            files_on_date.sort(key=lambda x: x['addtime'], reverse=True)
            to_delete.extend(files_on_date[saveOther:])

        # 最长保留saveMaxDay天
        if days > saveMaxDay:
            to_delete.extend(files_on_date)
    if len(to_delete) == 0:
        print("|---没有需要清理的文件")
        return

    # 删除需要删除的备份
    for f in to_delete:
        os.system("rm -f " + f['filename'])
        print("|---已清理过期文件：" + f['filename'])
