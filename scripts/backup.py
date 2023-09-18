# coding: utf-8
#-----------------------------
# 网站备份工具
#-----------------------------

import sys
import os
import json
import datetime

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')


chdir = os.getcwd()
sys.path.append(chdir + '/class/core')

# reload(sys)
# sys.setdefaultencoding('utf-8')


import mw
import db
import time


class backupTools:

    def backupSite(self, name, save):
        sql = db.Sql()
        path = sql.table('sites').where('name=?', (name,)).getField('path')
        startTime = time.time()
        if not path:
            endDate = time.strftime('%Y/%m/%d %X', time.localtime())
            log = "网站[" + name + "]不存在!"
            print("★[" + endDate + "] " + log)
            print(
                "----------------------------------------------------------------------------")
            return

        backup_path = mw.getBackupDir() + '/site'
        if not os.path.exists(backup_path):
            mw.execShell("mkdir -p " + backup_path)

        filename = backup_path + "/web_" + name + "_" + \
            time.strftime('%Y%m%d_%H%M%S', time.localtime()) + '.tar.gz'

        cmd = "cd " + os.path.dirname(path) + " && tar zcvf '" + \
            filename + "' '" + os.path.basename(path) + "' > /dev/null"

        # print(cmd)
        mw.execShell(cmd)

        endDate = time.strftime('%Y/%m/%d %X', time.localtime())

        print(filename)
        if not os.path.exists(filename):
            log = "网站[" + name + "]备份失败!"
            print("★[" + endDate + "] " + log)
            print(
                "----------------------------------------------------------------------------")
            return

        outTime = time.time() - startTime
        pid = sql.table('sites').where('name=?', (name,)).getField('id')
        sql.table('backup').add('type,name,pid,filename,addtime,size', ('0', os.path.basename(
            filename), pid, filename, endDate, os.path.getsize(filename)))
        log = "网站[" + name + "]备份成功,用时[" + str(round(outTime, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        print("★[" + endDate + "] " + log)
        
        print("|---文件名:" + filename)
        self.cleanBackup('0', pid, save)

    def backupDatabase(self, name, save):
        db_path = mw.getServerDir() + '/mysql-apt'
        db_name = 'mysql'
        find_name = mw.M('databases').dbPos(db_path, 'mysql').where(
            'name=?', (name,)).getField('name')
        startTime = time.time()
        if not find_name:
            endDate = time.strftime('%Y/%m/%d %X', time.localtime())
            log = "数据库[" + name + "]不存在!"
            print("★[" + endDate + "] " + log)
            print(
                "----------------------------------------------------------------------------")
            return

        backup_path = mw.getRootDir() + '/backup/database'
        if not os.path.exists(backup_path):
            mw.execShell("mkdir -p " + backup_path)

        filename = backup_path + "/db_" + name + "_" + \
            time.strftime('%Y%m%d_%H%M%S', time.localtime()) + ".sql.gz"

        mysql_root = mw.M('config').dbPos(db_path, db_name).where(
            "id=?", (1,)).getField('mysql_root')

        cmd = db_path + "/bin/usr/bin/mysqldump --single-transaction --quick --default-character-set=utf8 " + \
            name + " -uroot -p" + mysql_root + " | gzip > " + filename

        mw.execShell(cmd)

        if not os.path.exists(filename):
            endDate = time.strftime('%Y/%m/%d %X', time.localtime())
            log = "数据库[" + name + "]备份失败!"
            print("★[" + endDate + "] " + log)
            print(
                "----------------------------------------------------------------------------")
            return

        endDate = time.strftime('%Y/%m/%d %X', time.localtime())
        outTime = time.time() - startTime
        pid = mw.M('databases').dbPos(db_path, db_name).where(
            'name=?', (name,)).getField('id')

        mw.M('backup').add('type,name,pid,filename,addtime,size', (1, os.path.basename(
            filename), pid, filename, endDate, os.path.getsize(filename)))
        log = "数据库[" + name + "]备份成功,用时[" + str(round(outTime, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        print("★[" + endDate + "] " + log)
        print("|---文件名:" + filename)
        self.cleanBackup('1', pid, save)


    def backupDatabaseAll(self, save):
        db_path = mw.getServerDir() + '/mysql-apt'
        db_name = 'mysql'
        databases = mw.M('databases').dbPos(
            db_path, db_name).field('name').select()
        for database in databases:
            self.backupDatabase(database['name'], save)
        print('|----备份所有数据库任务完成')

    def backupSiteAll(self, save):
        sites = mw.M('sites').field('name').select()
        for site in sites:
            self.backupSite(site['name'], save)
        print('|----备份所有网站任务完成')
    
    def cleanBackup(self, type, pid, save):
        # 清理多余备份
        saveAllDay = int(save.get('saveAllDay'))
        saveOther = int(save.get('saveOther'))
        saveMaxDay = int(save.get('saveMaxDay'))

        # saveAllDay天内全部保留，其余只保留saveOther份，最长保留saveMaxDay天
        print("|---[" + str(saveAllDay) + "]天内全部保留，其余只保留[" + str(saveOther) + "]份，最长保留[" + str(saveMaxDay) + "]天")

        backups = mw.M('backup').where('type=? and pid=?', (type, pid)).field('id,filename,addtime').order('addtime desc').select()

        # 获取当前日期
        now = datetime.datetime.now()

        # 将备份按日期分组
        backups_by_date = {}
        for backup in backups:
            backup_time = datetime.datetime.strptime(backup['addtime'], '%Y/%m/%d %H:%M:%S')
            date = backup_time.date()
            if date not in backups_by_date:
                backups_by_date[date] = []
            backups_by_date[date].append(backup)

        # 保存需要删除的备份
        to_delete = []

        for date, backups_on_date in backups_by_date.items():
            # 计算备份距离现在的天数
            days = (now.date() - date).days

            # saveAllDay天内全部保留
            if days <= saveAllDay:
                continue

            # 其余只保留saveOther份
            if len(backups_on_date) > saveOther:
                # 对备份按时间排序，然后只保留最新的saveOther份
                backups_on_date.sort(key=lambda x: x['addtime'], reverse=True)
                to_delete.extend(backups_on_date[saveOther:])

            # 最长保留saveMaxDay天
            if days > saveMaxDay:
                to_delete.extend(backups_on_date)
        if len(to_delete) == 0:
            print("|---没有需要清理的备份")
            return

        # 删除需要删除的备份
        for backup in to_delete:
            os.system("rm -f " + backup['filename'])
            mw.M('backup').where('id=?', (backup['id'],)).delete()
            print("|---已清理过期备份文件：" + backup['filename'])

if __name__ == "__main__":
    backup = backupTools()
    type = sys.argv[1]
    name = sys.argv[2]
    save = {"saveAllDay": "3", "saveOther": "1", "saveMaxDay": "30"}
    if len(sys.argv) > 3:
        save = json.loads(sys.argv[3])

    if type == 'site':
        if sys.argv[2].find('backupAll') >= 0:
            backup.backupSiteAll(save)
        else:
            backup.backupSite(name, save)
    elif type == 'database':
        if sys.argv[2].find('backupAll') >= 0:
            backup.backupDatabaseAll(save)
        else:
            backup.backupDatabase(name, save)
