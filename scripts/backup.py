# coding: utf-8
#-----------------------------
# 网站备份工具
#-----------------------------

import sys
import os
import json
import datetime
import re
import shutil
import zipfile
import shlex
import importlib.util
import tempfile

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

    def _zip_dir(self, source_dir, filename, backup_exclude=None):
        backup_exclude = backup_exclude or ['logs', '*.log']
        with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(source_dir):
                dirs[:] = [item for item in dirs if not self._isExcludedPath(item, backup_exclude)]
                for file_name in files:
                    rel_path = os.path.relpath(os.path.join(root, file_name), source_dir)
                    if self._isExcludedPath(rel_path, backup_exclude) or self._isExcludedPath(file_name, backup_exclude):
                        continue
                    file_path = os.path.join(root, file_name)
                    zip_file.write(file_path, rel_path)

    def _isExcludedPath(self, rel_path, backup_exclude):
        rel_path = rel_path.strip('/')
        for rule in backup_exclude:
            rule = str(rule).strip('/')
            if rule == '':
                continue
            if rule.startswith('*.') and rel_path.endswith(rule[1:]):
                return True
            if rel_path == rule or rel_path.startswith(rule + '/') or ('/' + rule + '/') in ('/' + rel_path + '/'):
                return True
        return False

    def _copy_path(self, source, target):
        if not os.path.exists(source):
            return 0
        if os.path.isdir(source):
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            target_dir = os.path.dirname(target)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(source, target)
        return 1

    def _buildIncludedPluginBackup(self, plugin_path, tmp_plugin_path, backup_include):
        item_count = 0
        for item in backup_include:
            item = str(item).strip('/')
            if item == '':
                continue
            item_count += self._copy_path(os.path.join(plugin_path, item), os.path.join(tmp_plugin_path, item))
        return item_count

    def _backupPluginSettingToFile(self, plugin, filename):
        name = plugin.get('name')
        plugin_path = plugin.get('path')
        backup_include = plugin.get('backup_include', [])
        backup_exclude = plugin.get('backup_exclude', ['logs', '*.log'])
        random_str = mw.getRandomString(8).lower()
        tmp_path = '/tmp/pluginSetting/' + random_str
        if os.path.exists(tmp_path):
            mw.execShell('rm -rf ' + tmp_path)
        os.makedirs(tmp_path, exist_ok=True)
        tmp_plugin_path = os.path.join(tmp_path, name)

        try:
            if backup_include:
                os.makedirs(tmp_plugin_path, exist_ok=True)
                item_count = self._buildIncludedPluginBackup(plugin_path, tmp_plugin_path, backup_include)
                if item_count == 0:
                    print(f"插件[{name}]没有可备份的配置文件或目录")
                    return False
            else:
                shutil.copytree(plugin_path, tmp_plugin_path, dirs_exist_ok=True)

            self._zip_dir(tmp_plugin_path, filename, backup_exclude)
            return os.path.exists(filename)
        finally:
            mw.execShell('rm -rf ' + tmp_path)

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
        site_status = sql.table('sites').where('name=?', (name,)).getField('status')
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

        # 将备份时的网站运行状态一并写入配置包，恢复时按原状态还原。
        status_file = tmp_path + '/' + name + '/site_status.json'
        mw.execShell('mkdir -p ' + tmp_path + '/' + name)
        with open(status_file, 'w') as f:
            json.dump({'name': name, 'status': str(site_status)}, f)

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
        if not path or not os.path.exists(path):
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

        self._backupPluginSettingToFile(plugin, filename)
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
        

    def _databasePlugin(self, engine):
        plugin_name = 'mysql-apt' if engine == 'mysql' else 'postgresql'
        path = os.path.join(mw.getPluginDir(), plugin_name, 'index.py')
        spec = importlib.util.spec_from_file_location('backup_plugin_' + plugin_name, path)
        plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin)
        return plugin

    def _databaseError(self, engine, stage, error, name=None):
        log = '[{}]{}{}失败: {}'.format(engine, '[' + str(name) + ']' if name is not None else '',
                                      stage, str(error)[:1200])
        print(log)
        mw.writeLog('计划任务', log)
        return False

    def _backupLiveDatabases(self, engine, save, exec_type='mysqldump', name=None):
        try:
            plugin = self._databasePlugin(engine)
            context = plugin.prepareDatabaseBackup()
            if context is None:
                if name is not None:
                    raise ValueError('插件未安装或缺少配置库')
                print('|----{} 未安装，跳过全部备份'.format(engine))
                return True
            names = plugin.getServerDatabases(include_system=name is not None)
            if name is not None:
                if name not in names:
                    raise ValueError('指定数据库不存在: ' + name)
                names = [name]
        except Exception as exc:
            return self._databaseError(engine, '查询名单', exc, name)
        print('|----{} 本次实时备份名单: {} 个数据库'.format(engine, len(names)))
        successes = sum(self._backupLiveDatabase(plugin, engine, context, target, save, exec_type)
                        for target in names)
        print('|----{} 备份汇总: 成功 {}，失败 {}'.format(engine, successes, len(names) - successes))
        return successes == len(names)

    def _backupLiveDatabase(self, plugin, engine, context, name, save, exec_type):
        started = time.time()
        stage = '登记数据库'
        filename = None
        try:
            if name in ('.', '..') or '/' in name or chr(92) in name or chr(0) in name:
                raise ValueError('数据库名称包含不支持的路径字符')
            pid = plugin.ensureBackupDatabase(name)
            backup_path = os.path.join(mw.getRootDir(), 'backup/database')
            os.makedirs(backup_path, exist_ok=True)
            stage = '导出/压缩'
            with tempfile.TemporaryDirectory(prefix='.database-backup-', dir=backup_path) as work:
                output = os.path.join(work, 'archive')
                suffix = plugin.exportDatabaseBackup(name, output, work, context, exec_type)
                if not os.path.isfile(output) or os.path.getsize(output) == 0:
                    raise ValueError('未生成非空备份文件')
                stage = '发布备份文件'
                prefix = 'mysql_' if engine == 'mysql' else 'postgres_'
                stamp = datetime.datetime.now()
                while True:
                    candidate = os.path.join(backup_path, prefix + name + '_' + stamp.strftime('%Y%m%d_%H%M%S') + suffix)
                    try:
                        # No-overwrite publication on the same filesystem.
                        os.link(output, candidate)
                        filename = candidate
                        break
                    except FileExistsError:
                        stamp += datetime.timedelta(seconds=1)
            stage = '登记备份记录'
            end_date = time.strftime('%Y/%m/%d %X')
            result = mw.M('backup').add('type,name,pid,filename,addtime,size',
                (1, os.path.basename(filename), pid, filename, end_date, os.path.getsize(filename)))
            if not isinstance(result, int) or isinstance(result, bool) or result <= 0:
                raise ValueError('备份记录写入失败')
            stage = '清理本库历史'
            self.cleanBackupByHistory('1', pid, save, engine=engine, name=name)
            log = '[{}]数据库[{}]备份成功,用时[{}]秒'.format(engine, name, round(time.time() - started, 2))
            mw.writeLog('计划任务', log)
            print(log)
            print('|---文件名:' + filename)
            return True
        except Exception as exc:
            if filename:
                print('|---完整备份文件已保留: ' + filename)
            return self._databaseError(engine, stage, exc, name)

    def backupSiteAll(self, save):
        sites = mw.M('sites').field('name').select()
        for site in sites:
            self.backupSite(site['name'], save)
        print('|----备份所有网站任务完成')

    def backupSiteSettingAll(self, save):
        sites = mw.M('sites').field('name').select()
        if not sites:
            print('|----没有可备份的网站配置，跳过本次备份')
            return
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
        if not plugin_list:
            print('|----没有可备份的插件配置，跳过本次备份')
            return
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
        packaged_count = 0
        for plugin in plugin_list:
            name = plugin['name']
            plugin_path = plugin['path']
            if not os.path.exists(plugin_path):
                print(f"插件[{name}]不存在，跳过all包打包")
                continue
            self._backupPluginSettingToFile(plugin, f"{tmp_path}/{name}.zip")
            if os.path.exists(f"{tmp_path}/{name}.zip"):
                packaged_count += 1
        if packaged_count == 0:
            mw.execShell('rm -rf ' + tmp_path)
            print('|----没有可打包的插件配置，跳过all包生成')
            return
        mw.execShell(f'pushd {tmp_path} > /dev/null && zip -r {filename} . && popd > /dev/null', useTmpFile=True)
        print('|----备份所有插件配置任务完成')
    
    def _isDatabaseBackup(self, filename, engine, name):
        root = os.path.realpath(os.path.join(mw.getRootDir(), 'backup/database'))
        if os.path.dirname(os.path.realpath(filename)) != root:
            return False
        prefixes = ['mysql_', 'db_'] if engine == 'mysql' else ['postgres_']
        suffix = r'\d{8}_\d{6}\.(?:sql\.(?:gz|zst)|mydumper\.tar\.zst)$'
        return any(re.fullmatch(re.escape(prefix + name + '_') + suffix,
                                os.path.basename(filename)) for prefix in prefixes)

    def cleanBackupByHistory(self, type, pid, save, engine=None, name=None):
        # 清理多余备份
        saveAllDay = int(save.get('saveAllDay'))
        saveOther = int(save.get('saveOther'))
        saveMaxDay = int(save.get('saveMaxDay'))

        # saveAllDay天内全部保留，其余只保留saveOther份，最长保留saveMaxDay天
        print("|---[" + str(saveAllDay) + "]天内全部保留，其余只保留[" + str(saveOther) + "]份，最长保留[" + str(saveMaxDay) + "]天")

        backups = mw.M('backup').where('type=? and pid=?', (type, pid)).field('id,filename,addtime').order('addtime desc').select()

        if str(type) == '1':
            if engine not in ('mysql', 'postgresql') or name is None:
                raise ValueError('数据库历史清理缺少引擎或库名')
            backups = [item for item in backups if self._isDatabaseBackup(item['filename'], engine, name)]

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
            if str(type) == '1':
                if not self._isDatabaseBackup(backup['filename'], engine, name):
                    continue
                try:
                    os.remove(backup['filename'])
                except FileNotFoundError:
                    pass
            else:
                os.system("rm -f " + backup['filename'])
            mw.M('backup').where('id=?', (backup['id'],)).delete()
            print("|---已清理过期备份文件：" + backup['filename'])

def runDatabaseBackup(backup, backup_type, name, save, exec_type='mysqldump'):
    if name.startswith('postgresql:'):
        backup_type, name = 'pg_database', name.split(':', 1)[1]
    elif name.startswith('mysql:'):
        backup_type, name = 'mysql_database', name.split(':', 1)[1]
    elif name.startswith('all:'):
        backup_type, name = 'database', name.split(':', 1)[1]
    if name in ('backupAll', 'ALL'):
        if backup_type == 'pg_database':
            return backup._backupLiveDatabases('postgresql', save)
        if backup_type == 'mysql_database':
            return backup._backupLiveDatabases('mysql', save, exec_type)
        return (backup._backupLiveDatabases('mysql', save, exec_type)
                and backup._backupLiveDatabases('postgresql', save))
    engine = 'postgresql' if backup_type == 'pg_database' else 'mysql'
    return backup._backupLiveDatabases(engine, save, exec_type, name=name)


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
    elif type in ('database', 'mysql_database', 'pg_database'):
        execType = sys.argv[4] if len(sys.argv) > 4 else 'mysqldump'
        success = runDatabaseBackup(backup, type, name, save, execType)
        sys.exit(0 if success else 1)
