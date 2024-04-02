# coding: utf-8
#-----------------------------
# 网站备份工具
#-----------------------------

import sys
import os
import json
import datetime
import re

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')


chdir = os.getcwd()
sys.path.append(chdir + '/class/core')
sys.path.append(chdir + '/class/plugin')
# reload(sys)
# sys.setdefaultencoding('utf-8')


import mw
import db
import time
import clean_tool
import system_api
import site_api
systemApi = system_api.system_api()
siteApi = site_api.site_api()


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
        self.cleanBackupByHistory('0', pid, save)

    
    def backupSiteSetting(self, name, save):
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

        backup_path = mw.getSiteSettingBackupDir()
        if not os.path.exists(backup_path):
            mw.execShell("mkdir -p " + backup_path)

        filename = backup_path + "/" + name + "_" + \
            time.strftime('%Y%m%d_%H%M%S', time.localtime()) + '.tar.gz'

        random_str = mw.getRandomString(8).lower()
        tmp_path = '/tmp/site_setting/' + random_str
        if os.path.exists(tmp_path):
            mw.execShell('rm -rf ' + tmp_path)
        mw.execShell('mkdir -p ' + tmp_path)

        print(tmp_path)

        backup_cmd = f"""
set -e
site_name={name}
filename={filename}
tmp_path={tmp_path}
tmp_site_path=$tmp_path/$site_name

mkdir -p ${{tmp_site_path}}/web_conf/nginx/rewrite
mkdir -p ${{tmp_site_path}}/web_conf/nginx/vhost

cp /www/server/web_conf/nginx/rewrite/$site_name.conf ${{tmp_site_path}}/web_conf/nginx/rewrite/
cp /www/server/web_conf/nginx/vhost/$site_name.conf ${{tmp_site_path}}/web_conf/nginx/vhost/

cd $tmp_site_path
zip -r $filename .

rm -rf $tmp_path
        """
        
        # 写入临时文件用于执行
        tempFilePath = tmp_path + '/zip.sh'
        mw.writeFile(tempFilePath, backup_cmd)
        mw.execShell('chmod 750 ' + tempFilePath)
        mw.execShell('source /root/.bashrc && ' + tempFilePath, useTmpFile=True)

        endDate = time.strftime('%Y/%m/%d %X', time.localtime())

        print(filename)
        if not os.path.exists(filename):
            log = "网站[" + name + "]备份配置失败!"
            print("★[" + endDate + "] " + log)
            print(
                "----------------------------------------------------------------------------")
            return

        outTime = time.time() - startTime
        pid = sql.table('sites').where('name=?', (name,)).getField('id')
        sql.table('backup').add('type,name,pid,filename,addtime,size', ('2', os.path.basename(
            filename), pid, filename, endDate, os.path.getsize(filename)))
        log = "网站[" + name + "]备份配置成功,用时[" + str(round(outTime, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        print("★[" + endDate + "] " + log)
        
    
    def backupPluginSetting(self, name, save):
        sql = db.Sql()
        
        plugin_list = mw.getBackupPluginList()
        find_plugin_list = [data for data in plugin_list if data.get('name') == name]
        if len(find_plugin_list) == 0:
            print(f"插件[{name}]不存在!")
            return
        plugin = find_plugin_list[0]
        path = plugin.get('path')

        startTime = time.time()
        if not path:
            endDate = time.strftime('%Y/%m/%d %X', time.localtime())
            log = "插件[" + name + "]不存在!"
            print("★[" + endDate + "] " + log)
            print(
                "----------------------------------------------------------------------------")
            return

        backup_path = mw.getPluginSettingBackupDir()
        if not os.path.exists(backup_path):
            mw.execShell("mkdir -p " + backup_path)

        filename = backup_path + "/" + name + "_" + \
            time.strftime('%Y%m%d_%H%M%S', time.localtime()) + '.tar.gz'

        random_str = mw.getRandomString(8).lower()
        tmp_path = '/tmp/pluginSetting/' + random_str
        if os.path.exists(tmp_path):
            mw.execShell('rm -rf ' + tmp_path)
        mw.execShell('mkdir -p ' + tmp_path)

        backup_cmd = f"""
set -e
plugin_name={name}
plugin_path={path}
tmp_path={tmp_path}
tmp_plugin_path=$tmp_path/$plugin_name

cp -r ${{plugin_path}} ${{tmp_plugin_path}} 
cd $tmp_plugin_path
zip -r {filename} .

rm -rf $tmp_path
        """
        
        # 写入临时文件用于执行
        tempFilePath = tmp_path + '/zip.sh'
        mw.writeFile(tempFilePath, backup_cmd)
        mw.execShell('chmod 750 ' + tempFilePath)
        mw.execShell('source /root/.bashrc && ' + tempFilePath, useTmpFile=True)
        endDate = time.strftime('%Y/%m/%d %X', time.localtime())

        if not os.path.exists(filename):
            log = "插件[" + name + "]备份配置失败!"
            print("★[" + endDate + "] " + log)
            print(
                "----------------------------------------------------------------------------")
            return

        outTime = time.time() - startTime
        sql.table('backup').add('type,name,filename,addtime,size', ('3', os.path.basename(
            filename), filename, endDate, os.path.getsize(filename)))
        log = "插件[" + name + "]备份配置成功,用时[" + str(round(outTime, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        print("★[" + endDate + "] " + log)
        

    def getConf(self):
        path = mw.getServerDir() + '/mysql-apt/etc/my.cnf'
        return path

    def getMyPort(self):
        file = self.getConf()
        content = mw.readFile(file)
        rep = 'port\s*=\s*(.*)'
        tmp = re.search(rep, content)
        return tmp.groups()[0].strip()

    def backupDatabase(self, name, save, exec_type='mysqldump'):
        # 检查 mydumper, zstd 是否安装
        mw.execShell(f"""
source {mw.getScriptDir()}/util/apt.sh
check_and_install "mydumper"
check_and_install "zstd"
                     """)

        db_path = mw.getServerDir() + '/mysql-apt'
        db_name = 'mysql'

        # 检查数据库是否存在
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

        # 密码
        mysql_root = mw.M('config').dbPos(db_path, db_name).where(
            "id=?", (1,)).getField('mysql_root')
        # 端口
        port = self.getMyPort()
        filename = ''

        print(exec_type)
        if exec_type == 'mysqldump':
            filename = backup_path + "/db_" + name + "_" + \
                time.strftime('%Y%m%d_%H%M%S', time.localtime()) + ".sql.zst"
            # 执行备份（优化cpu占用）
            cmd = "nice -n 19 ionice -c2 -n7 " + db_path + "/bin/usr/bin/mysqldump --single-transaction --quick --default-character-set=utf8 " + \
                name + " -uroot -p" + mysql_root + " | zstd > " + filename
            mw.execShell(cmd)
        elif exec_type == 'mydumper':
            filename = backup_path + "/db_" + name + "_" + \
                time.strftime('%Y%m%d_%H%M%S', time.localtime()) + ".mydumper.tar.zst"
            random_str = mw.getRandomString(8).lower()
            tmp_path = '/tmp/mydumper/mydumper_' + random_str
            if os.path.exists(tmp_path):
                mw.execShell('rm -rf ' + tmp_path)
            mw.execShell('mkdir -p ' + tmp_path)
            # 执行备份
            mw.execShell('/usr/bin/mydumper -u root -p ' + mysql_root + ' -h 127.0.0.1 -P ' + port + ' -B ' + name + ' -o ' + tmp_path + '/' + name + ' --trx-consistency-only')
            mw.execShell('cd ' + tmp_path + ' && ' + 'tar -c ' + name + ' | zstd -o ' + filename)
            # 删除临时文件
            mw.execShell('rm -rf ' + tmp_path)

        # 检查备份情况并记录
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

        # 记录日志
        log = "数据库[" + name + "]备份成功,用时[" + str(round(outTime, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        print("★[" + endDate + "] " + log)
        print("|---文件名:" + filename)
        self.cleanBackupByHistory('1', pid, save)


    def backupDatabaseAll(self, save, exec_type='mysqldump'):
        db_path = mw.getServerDir() + '/mysql-apt'
        db_name = 'mysql'
        databases = mw.M('databases').dbPos(
            db_path, db_name).field('name').select()
        for database in databases:
            self.backupDatabase(database['name'], save, exec_type)
        print('|----备份所有数据库任务完成')

    def backupSiteAll(self, save):
        sites = mw.M('sites').field('name').select()
        for site in sites:
            self.backupSite(site['name'], save)
        print('|----备份所有网站任务完成')

    def backupSiteSettingAll(self, save):
        sites = mw.M('sites').field('name').select()
        for site in sites:
            self.backupSiteSetting(site['name'], save)

        # 备份all包
        backup_path = mw.getSiteSettingBackupDir()
        filename = backup_path + "/all_" + \
            time.strftime('%Y%m%d_%H%M%S', time.localtime()) + '.zip'
        random_str = mw.getRandomString(8).lower()
        tmp_path = '/tmp/site_setting/' + random_str
        if os.path.exists(tmp_path):
            mw.execShell('rm -rf ' + tmp_path)
        mw.execShell('mkdir -p ' + tmp_path)

        site_info = systemApi.getSiteInfo()
        with open(tmp_path + "/site_info.json", 'w') as f:
          json.dump(site_info, f)
        mw.execShell(f'pushd /www/server/web_conf/ > /dev/null && zip -r {tmp_path}/web_conf.zip . && popd > /dev/null', useTmpFile=True)
        mw.execShell(f'cp -r /www/server/jh-panel/data/letsencrypt.json {tmp_path}/letsencrypt.json')
        mw.execShell(f'pushd {tmp_path} > /dev/null && zip -r {filename} . && popd > /dev/null', useTmpFile=True)
        print('|----备份所有网站配置任务完成')
    
    def backupPluginSettingAll(self, save):
        plugin_list = mw.getBackupPluginList()
        for plugin in plugin_list:
            self.backupPluginSetting(plugin['name'], save)

        # 备份all包
        backup_path = mw.getPluginSettingBackupDir()
        filename = backup_path + "/all_" + \
            time.strftime('%Y%m%d_%H%M%S', time.localtime()) + '.zip'
        random_str = mw.getRandomString(8).lower()
        tmp_path = '/tmp/plugin_setting/' + random_str
        if os.path.exists(tmp_path):
            mw.execShell('rm -rf ' + tmp_path)
        mw.execShell('mkdir -p ' + tmp_path)
        for plugin in plugin_list:
            name = plugin['name']
            plugin_path = plugin['path']
            mw.execShell(f'pushd {plugin_path}/ > /dev/null && zip -r {tmp_path}/{name}.zip . && popd > /dev/null', useTmpFile=True)        
        mw.execShell(f'pushd {tmp_path} > /dev/null && zip -r {filename} . && popd > /dev/null', useTmpFile=True)
        print('|----备份所有插件配置任务完成')
    
    def cleanBackupByHistory(self, type, pid, save):
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
        clean_tool.cleanPath("/www/backup/site", save, "*")
    elif type == 'siteSetting':
        if sys.argv[2].find('backupAll') >= 0:
            backup.backupSiteSettingAll(save)
        else:
            backup.backupSiteSetting(name, save)
        clean_tool.cleanPath("/www/backup/site_setting", save, "*")
    elif type == 'pluginSetting':
        if sys.argv[2].find('backupAll') >= 0:
            backup.backupPluginSettingAll(save)
        else:
            backup.backupPluginSetting(name, save)
        clean_tool.cleanPath(mw.getPluginSettingBackupDir(), save, "*")
    elif type == 'database':
        execType = 'mysqldump'
        if len(sys.argv) > 4:
            execType = sys.argv[4]
        if sys.argv[2].find('backupAll') >= 0:
            backup.backupDatabaseAll(save, execType)
        else:
            backup.backupDatabase(name, save, execType)
        clean_tool.cleanPath("/www/backup/database", save, "*")
