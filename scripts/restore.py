# coding: utf-8
# -----------------------------
# 网站/插件 配置恢复工具
# -----------------------------
# 对应 backup.py 的 siteSetting / pluginSetting：
#   - restoreSiteSetting <site|backupAll>       恢复单个站点 或 最新 all 包
#   - restorePluginSetting <plugin|backupAll>   恢复单个插件 或 最新 all 包
# 计划任务统一以此入口运行，恢复永远使用对应类型下「最新」的备份包。
# -----------------------------

import sys
import os
import json
import time
import glob

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')

chdir = os.getcwd()
sys.path.append(chdir + '/class/core')
sys.path.append(chdir + '/class/plugin')

import mw


SITE_WEB_CONF_DIR = '/www/server/web_conf'
LETSENCRYPT_FILE = '/www/server/jh-panel/data/letsencrypt.json'


def _log(msg):
    end_date = time.strftime('%Y/%m/%d %X', time.localtime())
    print("★[" + end_date + "] " + msg)


def _hr():
    print("----------------------------------------------------------------------------")


def _find_latest(backup_dir, pattern):
    """在 backup_dir 中按 mtime 取最新匹配 pattern 的文件"""
    if not os.path.isdir(backup_dir):
        return None
    candidates = glob.glob(os.path.join(backup_dir, pattern))
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def _make_tmp(prefix):
    tmp = '/tmp/' + prefix + '/' + mw.getRandomString(8).lower()
    if os.path.exists(tmp):
        mw.execShell('rm -rf ' + tmp)
    mw.execShell('mkdir -p ' + tmp)
    return tmp


def _unzip(archive, dest):
    """解压 zip / 备份脚本生成的 .tar.gz(实际是 zip 容器)，统一用 unzip"""
    mw.execShell("unzip -o '" + archive + "' -d '" + dest + "' > /dev/null")


def _reload_nginx():
    if os.path.exists('/etc/init.d/nginx'):
        mw.execShell('/etc/init.d/nginx reload >/dev/null 2>&1 || true')
    else:
        mw.execShell('command -v systemctl >/dev/null 2>&1 && systemctl reload nginx >/dev/null 2>&1 || true')


class restoreTools:

    # ---------- 网站配置 ----------

    def restoreSiteSetting(self, name):
        backup_dir = mw.getSiteSettingBackupDir()
        # 单站包名称规则: {site}_YYYYmmdd_HHMMSS.tar.gz (实为 zip 容器)
        latest = _find_latest(backup_dir, name + '_*.tar.gz')
        start_time = time.time()
        if not latest:
            _log("未找到网站[" + name + "]的备份包，跳过")
            _hr()
            return False
        _log("使用备份包: " + latest)

        tmp = _make_tmp('restore_site_setting')
        _unzip(latest, tmp)

        # 期望布局：web_conf/nginx/{rewrite,vhost}/{site}.conf
        src_web_conf = os.path.join(tmp, 'web_conf')
        if os.path.isdir(src_web_conf):
            if not os.path.exists(SITE_WEB_CONF_DIR):
                mw.execShell('mkdir -p ' + SITE_WEB_CONF_DIR)
            # 用 cp -rf 覆盖，保留无关文件
            mw.execShell("cp -rf '" + src_web_conf + "/.' '" + SITE_WEB_CONF_DIR + "/'")
            _log("已恢复网站[" + name + "]的 nginx 配置 -> " + SITE_WEB_CONF_DIR)
        else:
            _log("备份包内未找到 web_conf 目录")

        mw.execShell('rm -rf ' + tmp)
        _reload_nginx()
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

        tmp = _make_tmp('restore_site_setting')
        _unzip(latest, tmp)

        # 1) web_conf.zip -> /www/server/web_conf
        web_conf_zip = os.path.join(tmp, 'web_conf.zip')
        if os.path.isfile(web_conf_zip):
            if not os.path.exists(SITE_WEB_CONF_DIR):
                mw.execShell('mkdir -p ' + SITE_WEB_CONF_DIR)
            _unzip(web_conf_zip, SITE_WEB_CONF_DIR)
            _log("已恢复 web_conf -> " + SITE_WEB_CONF_DIR)
        else:
            _log("备份包内未找到 web_conf.zip")

        # 2) letsencrypt.json -> data 目录
        le = os.path.join(tmp, 'letsencrypt.json')
        if os.path.isfile(le):
            mw.execShell('mkdir -p ' + os.path.dirname(LETSENCRYPT_FILE))
            mw.execShell("cp -f '" + le + "' '" + LETSENCRYPT_FILE + "'")
            _log("已恢复 letsencrypt.json -> " + LETSENCRYPT_FILE)

        mw.execShell('rm -rf ' + tmp)
        _reload_nginx()
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

        tmp = _make_tmp('restore_plugin_setting')
        _unzip(latest, tmp)

        for plugin in mw.getBackupPluginList():
            pname = plugin.get('name')
            ppath = plugin.get('path')
            inner = os.path.join(tmp, pname + '.zip')
            if not os.path.isfile(inner):
                _log("跳过插件[" + pname + "]：备份包内未找到 " + pname + ".zip")
                continue
            if not ppath:
                _log("跳过插件[" + pname + "]：缺少目标路径")
                continue
            if not os.path.exists(ppath):
                mw.execShell('mkdir -p ' + ppath)
            _unzip(inner, ppath)
            _log("已恢复插件[" + pname + "] -> " + ppath)

        mw.execShell('rm -rf ' + tmp)
        out_time = time.time() - start_time
        log = "所有插件配置恢复完成,用时[" + str(round(out_time, 2)) + "]秒"
        mw.writeLog('计划任务', log)
        _log(log)
        return True


def _usage():
    print("用法: restore.py <restoreSiteSetting|restorePluginSetting> <name|backupAll>")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        _usage()
        sys.exit(1)

    action = sys.argv[1]
    name = sys.argv[2]
    restore = restoreTools()

    is_all = (name.find('backupAll') >= 0) or name == 'ALL'

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
