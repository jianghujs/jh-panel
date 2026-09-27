# coding: utf-8
# -----------------------------
# 网站/插件 配置恢复工具
# -----------------------------
# 对应 backup.py 的 siteSetting / pluginSetting：
#   - restoreSiteSetting <site|restoreAll>       恢复单个站点 或 最新 all 包
#   - restorePluginSetting <plugin|restoreAll>   恢复单个插件 或 最新 all 包
# 计划任务统一以此入口运行，恢复永远使用对应类型下「最新」的备份包。
# -----------------------------

import sys
import os
import json
import time
import glob
import subprocess

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')

chdir = os.getcwd()
sys.path.append(chdir + '/class/core')
sys.path.append(chdir + '/class/plugin')

import mw
import site_api


SCRIPT_DIR = mw.getServerDir() + '/jh-panel/scripts'
SITE_WEB_CONF_DIR = '/www/server/web_conf'


def _log(msg):
    end_date = time.strftime('%Y/%m/%d %X', time.localtime())
    print("★[" + end_date + "] " + msg)


def _hr():
    print("----------------------------------------------------------------------------")


def _find_latest(backup_dir, pattern):
    if not os.path.isdir(backup_dir):
        return None
    candidates = glob.glob(os.path.join(backup_dir, pattern))
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def _make_tmp(prefix):
    tmp = '/tmp/' + prefix + '_restore_' + mw.getRandomString(8).lower()
    if os.path.exists(tmp):
        mw.execShell('rm -rf ' + tmp)
    mw.execShell('mkdir -p ' + tmp)
    return tmp


def _unzip(archive, dest):
    mw.execShell("unzip -o '" + archive + "' -d '" + dest + "' > /dev/null")


def _restart_openresty():
    openresty_index = mw.getPluginDir() + '/openresty/index.py'
    if os.path.exists(openresty_index):
        mw.execShell('pushd /www/server/jh-panel > /dev/null && python3 ' + openresty_index + ' restart && popd > /dev/null')
        _log("已重启 openresty")
    else:
        _log("未找到 openresty 插件，跳过重启")


def _normalize_site_status(status):
    value = str(status).strip().lower()
    if value in ('0', 'false', 'stop', 'stopped', 'disabled', '已停用', '已停止'):
        return '0'
    if value in ('1', 'true', 'start', 'started', 'enabled', '正在运行', '运行中'):
        return '1'
    return None


def _restore_site_status(site_status_list):
    """按备份记录恢复网站启停状态，并同步站点配置。"""
    if not isinstance(site_status_list, list):
        return

    api = site_api.site_api()
    for item in site_status_list:
        if not isinstance(item, dict):
            continue
        name = item.get('name')
        desired = _normalize_site_status(item.get('status'))
        if not name or desired is None:
            continue

        site = mw.M('sites').where('name=?', (name,)).field('id,name,path,status').find()
        if not site:
            _log("备份中的网站[" + str(name) + "]当前不存在，跳过状态恢复")
            continue
        if _normalize_site_status(site.get('status')) == desired:
            continue

        try:
            _set_site_status(api, site, desired)
            _log("已恢复网站[" + name + "]状态: " + ('启用' if desired == '1' else '停用'))
        except Exception as e:
            _log("恢复网站[" + name + "]状态失败: " + str(e))


def _set_site_status(api, site, desired):
    if desired == '0':
        api.stop(site.get('id'), site.get('name'))
        return

    # startApi 依赖 Web 请求上下文，恢复脚本直接复用其配置替换逻辑。
    name = site.get('name')
    site_path = site.get('path')
    stop_path = api.setupPath + '/stop'
    host_conf = api.getHostConf(name)
    conf = mw.readFile(host_conf)
    if conf:
        conf = conf.replace(stop_path, site_path)
        mw.writeFile(host_conf, conf)
    mw.M('sites').where('id=?', (site.get('id'),)).setField('status', '1')
    api.triggerSiteHook('start', site.get('id'), name)
    mw.restartWeb()
    reload_result = api.openrestyReload()
    if reload_result:
        _log("网站[" + name + "]启用配置重载失败: " + str(reload_result))


def _read_site_status(tmp, name=None):
    candidates = [os.path.join(tmp, 'site_status.json')]
    if name:
        candidates.append(os.path.join(tmp, name, 'site_status.json'))
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return [data]
        except Exception as e:
            _log("读取网站状态失败: " + str(e))
    return []


class restoreTools:

    # ---------- 网站配置 ----------

    def restoreSiteSetting(self, name):
        backup_dir = mw.getSiteSettingBackupDir()
        latest = _find_latest(backup_dir, name + '_*.tar.gz')
        start_time = time.time()
        if not latest:
            _log("未找到网站[" + name + "]的备份包，跳过")
            _hr()
            return False
        _log("使用备份包: " + latest)

        tmp = _make_tmp('site_setting')
        _unzip(latest, tmp)

        src_web_conf = os.path.join(tmp, 'web_conf')
        if os.path.isdir(src_web_conf):
            if not os.path.exists(SITE_WEB_CONF_DIR):
                mw.execShell('mkdir -p ' + SITE_WEB_CONF_DIR)
            mw.execShell("cp -rf '" + src_web_conf + "/.' '" + SITE_WEB_CONF_DIR + "/'")
            _log("已恢复网站[" + name + "]的 nginx 配置 -> " + SITE_WEB_CONF_DIR)

        _restore_site_status(_read_site_status(tmp, name))

        mw.execShell('rm -rf ' + tmp)
        _restart_openresty()
        out_time = time.time() - start_time
        log = "网站[" + name + "]配置恢复完成,用时[" + str(round(out_time, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        _log(log)
        return True

    def restoreSiteSettingAll(self):
        backup_dir = mw.getSiteSettingBackupDir()
        latest = _find_latest(backup_dir, 'all_*.zip')
        start_time = time.time()
        if not latest:
            _log("未找到网站配置 all_*.zip 备份包，恢复终止")
            _hr()
            return False
        _log("使用备份包: " + latest)

        tmp = _make_tmp('site_setting')
        _unzip(latest, tmp)

        # 1) 导入站点数据 (migrate.py importSiteInfo)
        site_info_file = os.path.join(tmp, 'site_info.json')
        if os.path.isfile(site_info_file):
            mw.execShell('python3 ' + SCRIPT_DIR + '/migrate.py importSiteInfo ' + site_info_file)
            _log("导入站点数据完成")
        else:
            _log("备份包内未找到 site_info.json，跳过站点导入")

        # 2) 合并 letsencrypt.json (migrate.py importLetsencryptOrder)
        le_file = os.path.join(tmp, 'letsencrypt.json')
        if os.path.isfile(le_file):
            mw.execShell('python3 ' + SCRIPT_DIR + '/migrate.py importLetsencryptOrder ' + le_file)
            _log("合并 letsencrypt.json 完成")
        else:
            _log("备份包内未找到 letsencrypt.json，跳过")

        # 3) 解压 web_conf.zip -> /www/server/web_conf
        web_conf_zip = os.path.join(tmp, 'web_conf.zip')
        if os.path.isfile(web_conf_zip):
            if not os.path.exists(SITE_WEB_CONF_DIR):
                mw.execShell('mkdir -p ' + SITE_WEB_CONF_DIR)
            _unzip(web_conf_zip, SITE_WEB_CONF_DIR)
            _log("已恢复 web_conf -> " + SITE_WEB_CONF_DIR)
        else:
            _log("备份包内未找到 web_conf.zip")

        # site_info.json 中包含每个网站备份时的 status，配置恢复后再同步启停状态。
        if os.path.isfile(site_info_file):
            try:
                with open(site_info_file, 'r') as f:
                    site_info = json.load(f)
                _restore_site_status(site_info.get('site_list', []))
            except Exception as e:
                _log("读取网站状态失败: " + str(e))

        mw.execShell('rm -rf ' + tmp)
        _restart_openresty()
        out_time = time.time() - start_time
        log = "所有网站配置恢复完成,用时[" + str(round(out_time, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        _log(log)
        return True

    # ---------- 插件配置 ----------

    def _plugin_path(self, name):
        for plugin in mw.getBackupPluginList():
            if plugin.get('name') == name:
                return plugin.get('path')
        return None

    def restorePluginSetting(self, name):
        target = self._plugin_path(name)
        if not target:
            _log("插件[" + name + "]不在可恢复列表，跳过")
            _hr()
            return False

        backup_dir = mw.getPluginSettingBackupDir()
        latest = _find_latest(backup_dir, name + '_*.tar.gz')
        start_time = time.time()
        if not latest:
            _log("未找到插件[" + name + "]的备份包，跳过")
            _hr()
            return False
        _log("使用备份包: " + latest)

        if not os.path.exists(target):
            mw.execShell('mkdir -p ' + target)
        _unzip(latest, target)
        out_time = time.time() - start_time
        log = "插件[" + name + "]配置恢复完成 -> " + target + ",用时[" + str(round(out_time, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        _log(log)
        return True

    def restorePluginSettingAll(self):
        backup_dir = mw.getPluginSettingBackupDir()
        latest = _find_latest(backup_dir, 'all_*.zip')
        start_time = time.time()
        if not latest:
            _log("未找到插件配置 all_*.zip 备份包，恢复终止")
            _hr()
            return False
        _log("使用备份包: " + latest)

        tmp = _make_tmp('plugin_setting')
        _unzip(latest, tmp)

        # 遍历每个 {name}.zip，解压到 /www/server/{name}
        for item in os.listdir(tmp):
            if not item.endswith('.zip'):
                continue
            name = item[:-4]
            server_dir = '/www/server/' + name
            if not os.path.exists(server_dir):
                mw.execShell('mkdir -p ' + server_dir)
            _unzip(os.path.join(tmp, item), server_dir)
            _log("已恢复插件[" + name + "] -> " + server_dir)

        mw.execShell('rm -rf ' + tmp)
        out_time = time.time() - start_time
        log = "所有插件配置恢复完成,用时[" + str(round(out_time, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        _log(log)
        return True


def _usage():
    print("用法: restore.py <restoreSiteSetting|restorePluginSetting> <name|restoreAll>")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        _usage()
        sys.exit(1)

    action = sys.argv[1]
    name = sys.argv[2]
    restore = restoreTools()

    is_all = (name.find('restoreAll') >= 0) or (name.find('backupAll') >= 0) or name == 'ALL'

    if action == 'restoreSiteSetting':
        if is_all:
            restore.restoreSiteSettingAll()
        else:
            restore.restoreSiteSetting(name)
    elif action == 'restorePluginSetting':
        if is_all:
            restore.restorePluginSettingAll()
        else:
            restore.restorePluginSetting(name)
    else:
        _usage()
        sys.exit(1)
