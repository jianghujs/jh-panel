# coding: utf-8
#-----------------------------
# 切换工具
#-----------------------------

import sys
import os
import json
import re
import datetime
import shlex

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')


chdir = os.getcwd()
sys.path.append(chdir + '/class/core')

# reload(sys)
# sys.setdefaultencoding('utf-8')


import mw
import db
import time
import system_api
import site_api
import crontab_api
systemApi = system_api.system_api()
siteApi = site_api.site_api()
crontabApi = crontab_api.crontab_api()

class switchTools:

    def openCrontab(self, name):
        cronInfo = mw.M('crontab').where(
            'name=?', (name,)).field(crontabApi.field).find()
        if not cronInfo:
            print("计划任务不存在")
            return
        if cronInfo['status'] == 1:
            print("计划任务已经启用了")
            return

        mw.M('crontab').where('id=?', (cronInfo['id'],)).setField('status', 1)
        cronInfo['status'] = 1
        crontabApi.syncToCrond(cronInfo)
        print("启用定时任务" + name + "成功!")
            
    def closeCrontab(self, name):
        cronInfo = mw.M('crontab').where(
            'name=?', (name,)).field(crontabApi.field).find()
        if not cronInfo:
            print("计划任务不存在")
            return
        if cronInfo['status'] == 0:
            print("计划任务已经停用了")
            return

        mw.M('crontab').where('id=?', (cronInfo['id'],)).setField('status', 0)
        crontabApi.removeCrond(cronInfo['echo'])
        print("停用定时任务" + name + "成功!")
            
    def openEmailNotify(self):
        data = mw.getNotifyData(False)
        data['email']['enable'] = True
        mw.writeNotify(data)
        print("启用邮件通知成功!")

    def closeEmailNotify(self):
        data = mw.getNotifyData(False)
        data['email']['enable'] = False
        mw.writeNotify(data)
        print("关闭邮件通知成功!")

        
    def closeMysqlSlaveNotify(self):
        control_notify_value_file = 'data/control_notify_value.conf'
        data = mw.getControlNotifyConfig()
        data['mysql_slave_status_notice'] = 0
        mw.writeFile(control_notify_value_file, json.dumps(data))
        print("关闭主从同步异常提醒成功!")

    def openMysqlSlaveNotify(self):
        control_notify_value_file = 'data/control_notify_value.conf'
        data = mw.getControlNotifyConfig()
        data['mysql_slave_status_notice'] = 1
        mw.writeFile(control_notify_value_file, json.dumps(data))
        print("开启主从同步异常提醒成功!")

    def closeRsyncStatusNotify(self):
        control_notify_value_file = 'data/control_notify_value.conf'
        data = mw.getControlNotifyConfig()
        data['rsync_status_notice'] = 0
        mw.writeFile(control_notify_value_file, json.dumps(data))
        print("关闭Rsync状态异常提醒成功!")
       
    def openRsyncStatusNotify(self):
        control_notify_value_file = 'data/control_notify_value.conf'
        data = mw.getControlNotifyConfig()
        data['rsync_status_notice'] = 1
        mw.writeFile(control_notify_value_file, json.dumps(data))
        print("开启Rsync状态异常提醒成功!")

    def addCrontab(self, cron_config):
        sid = cron_config.get('id', '')
        iname = cron_config.get('name', '')
        iname_reg_str = cron_config.get('name_reg', '').replace("[", "\\[").replace("]", "\\]")
        cron_type = cron_config.get('type', '')
        week = cron_config.get('week', '')
        hour = cron_config.get('hour', '')
        minute = cron_config.get('minute', '')
        where1 = cron_config.get('where1', '')
        saveAllDay = cron_config.get('saveAllDay', '')
        saveOther = cron_config.get('saveOther', '')
        saveMaxDay = cron_config.get('saveMaxDay', '')
        backup_to = cron_config.get('backup_to', '')
        stype = cron_config.get('stype', '')
        sname = cron_config.get('sname', '')
        dumpType = cron_config.get('dumpType', '')
        sbody = cron_config.get('sbody', '')

        urladdress = cron_config.get('urladdress', '')
        
        if stype == 'database':
          sbody = dumpType

        if len(iname) < 1:
            print("任务名称不能为空")
            return

        crontabList = mw.M('crontab').where('name=?', (iname,)).field('id').select()
        if len(crontabList) > 0:
            print("计划任务已经存在")
            return
        

        params = {
            'name': iname,
            'type': cron_type,
            'week': week,
            'where1': where1,
            'hour': hour,
            'minute': minute,
            'saveAllDay': saveAllDay,
            'saveOther': saveOther,
            'saveMaxDay': saveMaxDay,
            'backup_to': backup_to,
            'stype': stype,
            'sname': sname,
            'dumpType': dumpType,
            'sbody': sbody,
            'urladdress': urladdress,
        }

        is_check_pass, msg = crontabApi.cronCheck(params)
        if not is_check_pass:
            print(msg)
            return

        addData = crontabApi.add(params)
        if addData > 0:
            print("添加计划任务【" + iname + "】成功!")
        else:
            print("添加计划任务【" + iname + "】失败!")
        
    

    def modifyCrontabCron(self, cron_config):
        iname = cron_config.get('name', '')
        iname_reg_str = cron_config.get('name_reg', '').replace("[", "\\[").replace("]", "\\]")
        cron_type = cron_config.get('type', '')
        week = cron_config.get('week', '')
        hour = cron_config.get('hour', '')
        minute = cron_config.get('minute', '')
        where1 = cron_config.get('where1', '')

        params = {
            'name': iname,
            'type': cron_type,
            'week': week,
            'where1': where1,
            'hour': hour,
            'minute': minute
        }

        
        is_check_pass, msg = crontabApi.cronCheck(params)
        if not is_check_pass:
            print(msg)
            return

        cuonConfig, get, name = crontabApi.getCrondCycle(params)
        crontabList = mw.M('crontab').field(crontabApi.field).select()
        cronInfo = None
        iname_reg = re.compile("^" + iname_reg_str + "$")
        for cron in crontabList:
            if re.match(iname_reg, cron["name"]):
              cronInfo = cron

        if cronInfo is None:
            print("计划任务【" + iname_reg_str + "】不存在")
            return
        
        sid = cronInfo['id']
        name = cronInfo['name']
        cronInfo['type'] = get['type']
        cronInfo['where1'] = get['where1']
        cronInfo['where_hour'] = get['hour']
        cronInfo['where_minute'] = get['minute']
        
        addData = mw.M('crontab').where('id=?', (sid,)).save('type,where1,where_hour,where_minute', (cronInfo['type'], cronInfo['where1'], cronInfo['where_hour'], cronInfo['where_minute']))
        crontabApi.removeCrond(cronInfo['echo'])
        crontabApi.syncToCrond(cronInfo)
        print("修改计划任务【" + name + "】成功!")

    def modifyCrontabShell(self, params):
        iname_reg_str = params.get('name_reg', '').replace("[", "\\[").replace("]", "\\]")
        
        crontabList = mw.M('crontab').field(crontabApi.field).select()
        cronInfo = None
        iname_reg = re.compile("^" + iname_reg_str + "$")
        for cron in crontabList:
            if re.match(iname_reg, cron["name"]):
              cronInfo = cron

        if cronInfo is None:
            print("计划任务【" + iname_reg_str + "】不存在")
            return
        print(cronInfo)
        sid = cronInfo['id']
        name = cronInfo['name']
        cronInfo['sbody'] = params.get('sbody', '')
        print(cronInfo)
        addData = mw.M('crontab').where('id=?', (sid,)).save('sbody', (cronInfo['sbody'],))
        crontabApi.removeCrond(cronInfo['echo'])
        crontabApi.syncToCrond(cronInfo)
        print("修改计划任务【" + name + "】成功!")

    def setNotifyValue(self, params):
        systemApi.setNotifyValue(params)
        print("设置监控阈值完成!")  

    def enableStandbySync(self, standby_sync_pub="/root/.ssh/standby_sync.pub", authorized_keys="/root/.ssh/authorized_keys"):
        if not os.path.exists(standby_sync_pub):
            print("standby_sync.pub 不存在，跳过同步公钥")
            return True

        key_raw = mw.readFile(standby_sync_pub) or ""
        key = key_raw.strip()
        if not key:
            print("standby_sync.pub 为空，跳过同步公钥")
            return True

        try:
            os.makedirs(os.path.dirname(authorized_keys), 0o700)
        except OSError:
            if not os.path.isdir(os.path.dirname(authorized_keys)):
                print("创建 .ssh 目录失败")
                return False

        auth_raw = mw.readFile(authorized_keys) or ""
        for line in auth_raw.splitlines():
            if line.strip() == key:
                print("authorized_keys 已包含 standby_sync 公钥")
                return True

        try:
            with open(authorized_keys, "a") as f:
                if auth_raw and not auth_raw.endswith("\n"):
                    f.write("\n")
                f.write(key + "\n")
        except Exception as exc:
            print("写入 authorized_keys 失败: {}".format(exc))
            return False

        print("standby_sync 公钥已写入 authorized_keys")
        return True

    def disableStandbySync(self, standby_sync_pub="/root/.ssh/standby_sync.pub", authorized_keys="/root/.ssh/authorized_keys"):
        if not os.path.exists(standby_sync_pub):
            print("standby_sync.pub 不存在，跳过移除同步公钥")
            return True

        key_raw = mw.readFile(standby_sync_pub) or ""
        key = key_raw.strip()
        if not key:
            print("standby_sync.pub 为空，跳过移除同步公钥")
            return True

        auth_raw = mw.readFile(authorized_keys) or ""
        if not auth_raw:
            print("authorized_keys 不存在或为空，跳过移除同步公钥")
            return True

        lines = [line for line in auth_raw.splitlines() if line.strip() != key]
        if len(lines) == len(auth_raw.splitlines()):
            print("authorized_keys 未包含 standby_sync 公钥")
            return True

        try:
            with open(authorized_keys, "w") as f:
                if lines:
                    f.write("\n".join(lines) + "\n")
                else:
                    f.write("")
        except Exception as exc:
            print("移除同步公钥失败: {}".format(exc))
            return False

        print("已从 authorized_keys 移除 standby_sync 公钥")
        return True

    def disableAllLsyncdTask(self):
        try:
            lsyncd_cmd_res = mw.execShell("python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_list")
            if lsyncd_cmd_res[2] != 0:
                print("获取 lsyncd 列表失败: {}".format(lsyncd_cmd_res[1]))
                return False
            lsyncd_list_result = json.loads(lsyncd_cmd_res[0])
        except Exception as exc:
            print("获取 lsyncd 列表失败: {}".format(exc))
            return False

        if not lsyncd_list_result.get("status", False):
            print("获取 lsyncd 列表失败: {}".format(lsyncd_list_result.get("msg", "")))
            return False

        send_conf = lsyncd_list_result.get("data") or {}
        lsyncd_list = send_conf.get("list") or []
        names = [item.get("name", "").strip() for item in lsyncd_list if item.get("name")]
        if names:
            names_str = "|".join(names)
            res = mw.execShell(
                "python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_status_batch {} {}".format(
                    shlex.quote("names:{}".format(names_str)),
                    shlex.quote("status:disabled"),
                )
            )
            if res[2] != 0:
                print("关闭 lsyncd 任务失败: {}".format(res[1]))
                return False
        res = mw.execShell("systemctl stop lsyncd")
        if res[2] != 0:
            print("停止 lsyncd 服务失败: {}".format(res[1]))
            return False
        print("关闭 lsyncd 任务完成")
        return True

    def enableAllLsyncdTask(self):
        try:
            lsyncd_cmd_res = mw.execShell("python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_list")
            if lsyncd_cmd_res[2] != 0:
                print("获取 lsyncd 列表失败: {}".format(lsyncd_cmd_res[1]))
                return False
            lsyncd_list_result = json.loads(lsyncd_cmd_res[0])
        except Exception as exc:
            print("获取 lsyncd 列表失败: {}".format(exc))
            return False

        if not lsyncd_list_result.get("status", False):
            print("获取 lsyncd 列表失败: {}".format(lsyncd_list_result.get("msg", "")))
            return False

        send_conf = lsyncd_list_result.get("data") or {}
        lsyncd_list = send_conf.get("list") or []
        names = [item.get("name", "").strip() for item in lsyncd_list if item.get("name")]
        if names:
            names_str = "|".join(names)
            res = mw.execShell(
                "python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_status_batch {} {}".format(
                    shlex.quote("names:{}".format(names_str)),
                    shlex.quote("status:enabled"),
                )
            )
            if res[2] != 0:
                print("启用 lsyncd 任务失败: {}".format(res[1]))
                return False
        res = mw.execShell("systemctl restart lsyncd")
        if res[2] != 0:
            print("重启 lsyncd 服务失败: {}".format(res[1]))
            return False
        print("启用 lsyncd 任务完成")
        return True
   
if __name__ == "__main__":
    st = switchTools()
    type = sys.argv[1]

    if type == 'openCrontab':
      name = sys.argv[2]
      st.openCrontab(name)
    elif type == 'closeCrontab':
      name = sys.argv[2]
      st.closeCrontab(name)
    elif type == 'openEmailNotify':
      st.openEmailNotify()
    elif type == 'closeEmailNotify':
      st.closeEmailNotify()
    elif type == 'closeMysqlSlaveNotify':
      st.closeMysqlSlaveNotify()
    elif type == 'openMysqlSlaveNotify':
      st.openMysqlSlaveNotify()
    elif type == 'closeRsyncStatusNotify':
      st.closeRsyncStatusNotify()
    elif type == 'openRsyncStatusNotify':
      st.openRsyncStatusNotify()
    elif type == 'addCrontab':
      """
      python3 /www/server/jh-panel/scripts/switch.py addCrontab '{"name":"测试111","type":"day","hour":1,"minute":20,"stype":"toShell","backup_to":"localhost","sbody":"echo \"ok\""}'
      """
      cron_config = json.loads(sys.argv[2])
      st.addCrontab(cron_config)
    elif type == 'modifyCrontabCron':
      """
      python3 /www/server/jh-panel/scripts/switch.py modifyCrontabCron '{"name_reg":"[ 勿删]同步插件定时任务[.*wwwroot]","type":"day","hour":1,"minute":20}'
      """
      cron_config = json.loads(sys.argv[2])
      st.modifyCrontabCron(cron_config)
    elif type == 'modifyCrontabShell':
      """
      python3 /www/server/jh-panel/scripts/switch.py modifyCrontabShell '{"name_reg":"[勿删]lsyncd实时日志切割","sbody":"echo \"ok\""}'
      """
      params = json.loads(sys.argv[2])
      st.modifyCrontabShell(params)
    elif type == 'setNotifyValue':
      """
      python3 /www/server/jh-panel/scripts/switch.py setNotifyValue '{"cpu":80,"memory":80,"disk":80,"ssl_cert":14}'
      """
      params = json.loads(sys.argv[2])
      st.setNotifyValue(params)
    elif type == 'enableStandbySync':
      ok = st.enableStandbySync()
      if ok is False:
        sys.exit(1)
    elif type == 'disableStandbySync':
      ok = st.disableStandbySync()
      if ok is False:
        sys.exit(1)
    elif type == 'disableAllLsyncdTask':
      ok = st.disableAllLsyncdTask()
      if ok is False:
        sys.exit(1)
    elif type == 'enableAllLsyncdTask':
      ok = st.enableAllLsyncdTask()
      if ok is False:
        sys.exit(1)
