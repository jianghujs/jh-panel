# coding: utf-8
#-----------------------------
# MySQL 工具
#-----------------------------

import sys
import os
import subprocess

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')

chdir = os.getcwd()
sys.path.append(chdir + '/class/core')

import mw


PANEL_DIR = '/www/server/jh-panel'
SERVER_DIR = '/www/server'
MYSQL_PLUGINS = ('mysql-apt', 'mysql-yum', 'mysql', 'mariadb')
SERVICE_CANDIDATES = ('mysql-apt', 'mysqld', 'mysql', 'mariadb')
DRY_RUN = os.environ.get('HA_MANAGER_SWITCH_DRY_RUN') == '1'


class mysqlTools:

    def _quote(self, value):
        return "'" + str(value).replace("'", "'\\''") + "'"

    def _runShell(self, cmd, step, check=True):
        print('|- ' + step)
        if DRY_RUN:
            print('|- dry-run: ' + cmd)
            return 0, ''
        out, err, code = mw.execShell(cmd, cwd=PANEL_DIR)
        output = out or err or ''
        if output.strip():
            print(output.strip())
        if check and code != 0:
            raise RuntimeError('{0} 失败 exit_code={1}: {2}'.format(step, code, output.strip()[-500:]))
        return code, output

    def _getPluginName(self):
        for name in MYSQL_PLUGINS:
            if os.path.exists(os.path.join(SERVER_DIR, name)):
                return name
        return 'mysql-apt'

    def _getServiceName(self, plugin=None):
        plugin = plugin or self._getPluginName()
        candidates = []
        if plugin:
            candidates.append(plugin)
        candidates.extend(SERVICE_CANDIDATES)
        seen = set()
        for service in candidates:
            if not service or service in seen:
                continue
            seen.add(service)
            if mw.systemctlExists(service):
                return service
        return plugin or 'mysql-apt'

    def _getPluginIndex(self, plugin=None):
        plugin = plugin or self._getPluginName()
        return os.path.join(PANEL_DIR, 'plugins', plugin, 'index.py')

    def _getPluginStatus(self, plugin=None):
        plugin = plugin or self._getPluginName()
        index = self._getPluginIndex(plugin)
        if not os.path.exists(index):
            return ''
        proc = subprocess.run(['python3', index, 'status', '{}'], cwd=PANEL_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            return ''
        return proc.stdout.strip()

    def _fixOwner(self):
        plugin = self._getPluginName()
        mysql_dir = os.path.join(SERVER_DIR, plugin)
        if not os.path.isdir(mysql_dir):
            print('|- MySQL目录不存在，跳过权限修复: ' + mysql_dir)
            return
        self._runShell('chown -R mysql:mysql {0}'.format(self._quote(mysql_dir)), '修复 MySQL 目录属主')
        data_dir = os.path.join(mysql_dir, 'data')
        tmp_dir = os.path.join(mysql_dir, 'tmp')
        if os.path.isdir(data_dir):
            self._runShell('chmod 755 {0}'.format(self._quote(data_dir)), '修复 MySQL 数据目录权限', check=False)
        if os.path.isdir(tmp_dir):
            self._runShell('chmod 750 {0}'.format(self._quote(tmp_dir)), '修复 MySQL 临时目录权限', check=False)

    def _start(self):
        plugin = self._getPluginName()
        service = self._getServiceName(plugin)
        if mw.systemctlExists(service):
            self._runShell('systemctl daemon-reload', '刷新 systemd 配置', check=False)
            self._runShell('systemctl enable {0}'.format(self._quote(service)), '启用 MySQL 自启动', check=False)
            if mw.systemctlIsActive(service):
                print('|- MySQL 服务已运行')
                return
            self._runShell('systemctl start {0}'.format(self._quote(service)), '启动 MySQL 服务')
            if not DRY_RUN and mw.systemctlIsActive(service):
                return
        index = self._getPluginIndex(plugin)
        if not os.path.exists(index):
            raise RuntimeError('未找到 MySQL systemd 服务，也未找到插件入口: ' + index)
        self._runShell('python3 {0} start'.format(self._quote(index)), '通过数据库插件启动 MySQL')

    def ensureRunning(self, reason=''):
        plugin = self._getPluginName()
        service = self._getServiceName(plugin)
        print('|- 检查 MySQL 服务：plugin={0}, service={1}, reason={2}'.format(plugin, service, reason or '未指定'))
        self._fixOwner()
        self._start()
        if not DRY_RUN and mw.systemctlExists(service) and not mw.systemctlIsActive(service):
            raise RuntimeError('MySQL 服务启动后仍未运行: ' + service)
        if not DRY_RUN:
            status = self._getPluginStatus(plugin)
            if status and status != 'start':
                raise RuntimeError('MySQL 插件状态异常: ' + status)
        print('|- MySQL 服务检查完成')

    def status(self):
        plugin = self._getPluginName()
        service = self._getServiceName(plugin)
        active = mw.systemctlIsActive(service) if mw.systemctlExists(service) else False
        plugin_status = self._getPluginStatus(plugin)
        print('plugin={0}'.format(plugin))
        print('service={0}'.format(service))
        print('systemd_active={0}'.format('true' if active else 'false'))
        print('plugin_status={0}'.format(plugin_status or 'unknown'))


if __name__ == "__main__":
    mysql = mysqlTools()
    if len(sys.argv) < 2:
        print('用法: python3 scripts/mysql.py <ensureRunning|status> [args]')
        sys.exit(1)

    type = sys.argv[1]
    try:
        if type == 'ensureRunning':
            reason = ''
            if '--reason' in sys.argv:
                idx = sys.argv.index('--reason')
                if len(sys.argv) > idx + 1:
                    reason = sys.argv[idx + 1]
            elif len(sys.argv) > 2:
                reason = sys.argv[2]
            mysql.ensureRunning(reason)
        elif type == 'status':
            mysql.status()
        else:
            print('未知方法: ' + type)
            sys.exit(1)
    except Exception as e:
        print('|- MySQL 工具执行失败: ' + str(e), file=sys.stderr)
        sys.exit(1)
