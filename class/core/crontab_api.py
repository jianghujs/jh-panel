# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖面板
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-panel) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 计划任务操作
# ---------------------------------------------------------------------------------


import psutil
import time
import os
import sys
import mw
import re
import json
import pwd

from flask import request


class crontab_api:

    field = 'id,name,type,where1,where_hour,where_minute,echo,addtime,status,saveAllDay,saveOther,saveMaxDay,backup_to,stype,sname,sbody,urladdress'

    def __init__(self):
        pass

    ##### ----- start ----- ###
    def listApi(self):
        # TODO 兼容旧版本，检查并添加saveAllDay,saveOther,saveMaxDay字段
        crontab_db = mw.M('crontab')
        crontab_columns = crontab_db.originExecute("PRAGMA table_info(crontab)").fetchall()
        saveAllDay_exists = any(column[1] == 'saveAllDay' for column in crontab_columns)
        if not saveAllDay_exists:
            crontab_db.originExecute("ALTER TABLE crontab ADD COLUMN saveAllDay INTEGER DEFAULT null")
        saveOther_exists = any(column[1] == 'saveOther' for column in crontab_columns)
        if not saveOther_exists:
            crontab_db.originExecute("ALTER TABLE crontab ADD COLUMN saveOther INTEGER DEFAULT null")
        saveMaxDay_exists = any(column[1] == 'saveMaxDay' for column in crontab_columns)
        if not saveMaxDay_exists:
            crontab_db.originExecute("ALTER TABLE crontab ADD COLUMN saveMaxDay INTEGER DEFAULT null")

        p = request.args.get('p', 1)
        psize = 10

        startPage = (int(p) - 1) * psize
        pageInfo = str(startPage) + ',' + str(psize)

        _list = mw.M('crontab').where('', ()).field(
            self.field).limit(pageInfo).order('id desc').select()

        data = []
        for i in range(len(_list)):
            tmp = _list[i]
            if _list[i].get('type', None) == "day":
                tmp['type'] = '每天'
                tmp['cycle'] = mw.getInfo('每天, {1}点{2}分 执行', (str(
                    _list[i]['where_hour']), str(_list[i]['where_minute'])))
            elif _list[i].get('type', None) == "day-n":
                tmp['type'] = mw.getInfo(
                    '每{1}天', (str(_list[i]['where1']),))
                tmp['cycle'] = mw.getInfo('每隔{1}天, {2}点{3}分 执行',  (str(
                    _list[i]['where1']), str(_list[i]['where_hour']), str(_list[i]['where_minute'])))
            elif _list[i].get('type', None) == "hour":
                tmp['type'] = '每小时'
                tmp['cycle'] = mw.getInfo(
                    '每小时, 第{1}分钟 执行', (str(_list[i]['where_minute']),))
            elif _list[i].get('type', None) == "hour-n":
                tmp['type'] = mw.getInfo(
                    '每{1}小时', (str(_list[i]['where1']),))
                tmp['cycle'] = mw.getInfo('每{1}小时, 第{2}分钟 执行', (str(
                    _list[i]['where1']), str(_list[i]['where_minute'])))
            elif _list[i].get('type', None) == "minute-n":
                tmp['type'] = mw.getInfo(
                    '每{1}分钟', (str(_list[i]['where1']),))
                tmp['cycle'] = mw.getInfo(
                    '每隔{1}分钟执行', (str(_list[i]['where1']),))
            elif _list[i].get('type', None) == "week":
                tmp['type'] = '每周'
                if not _list[i]['where1']:
                    _list[i]['where1'] = '0'
                tmp['cycle'] = mw.getInfo('每周{1}, {2}点{3}分执行', (self.toWeek(int(
                    _list[i]['where1'])), str(_list[i]['where_hour']), str(_list[i]['where_minute'])))
            elif _list[i].get('type', None) == "month":
                tmp['type'] = '每月'
                tmp['cycle'] = mw.getInfo('每月, {1}日 {2}点{3}分执行', (str(_list[i]['where1']), str(
                    _list[i]['where_hour']), str(_list[i]['where_minute'])))
            data.append(tmp)

        rdata = {}
        rdata['data'] = data

        count = mw.M('crontab').where('', ()).count()
        _page = {}
        _page['count'] = count
        _page['p'] = p
        _page['row'] = psize
        _page['tojs'] = "getCronData"

        rdata['list'] = mw.getPage(_page)
        rdata['p'] = p

        # backup hock
        bh_file = mw.getPanelDataDir() + "/hook_backup.json"
        if os.path.exists(bh_file):
            hb_data = mw.readFile(bh_file)
            hb_data = json.loads(hb_data)
            rdata['backup_hook'] = hb_data

        return mw.getJson(rdata)

    # 设置计划任务状态
    def setCronStatusApi(self):
        mid = request.form.get('id', '')
        cronInfo = mw.M('crontab').where(
            'id=?', (mid,)).field(self.field).find()
        status = 1
        if cronInfo['status'] == status:
            status = 0
            self.removeCrond(cronInfo['echo'])
        else:
            cronInfo['status'] = 1
            self.syncToCrond(cronInfo)

        mw.M('crontab').where('id=?', (mid,)).setField('status', status)
        mw.writeLog(
            '计划任务', '修改计划任务[' + cronInfo['name'] + ']状态为[' + str(status) + ']')
        return mw.returnJson(True, '设置成功')

    # 获取指定任务数据
    def getCrondFindApi(self):
        sid = request.form.get('id', '')
        data = mw.M('crontab').where(
            'id=?', (sid,)).field(self.field).find()
        return mw.getJson(data)

    # 参数校验
    def cronCheck(self, params):
        if params.get('stype', '') and (params['stype'] == 'site' or params['stype'] == 'database' or params['stype'] == 'logs'):
            if params.get('saveAllDay', '') == '':
                return False, '3天内保留份数不能为空!'
            if params.get('saveOther', '') == '':
                return False, '其余保留份数不能为空!'
            if params.get('saveMaxDay', '') == '':
                return False, '最长保留天数不能为空!'
        if params['type'] == 'day':
            if params['hour'] == '':
                return False, '小时不能为空!'
            if params['minute'] == '':
                return False, '分钟不能为空!'

        if params['type'] == 'day-n':
            if params['where1'] == '':
                return False, '天不能为空!'
            if params['hour'] == '':
                return False, '小时不能为空!'
            if params['minute'] == '':
                return False, '分钟不能为空!'
        if params['type'] == 'hour':
            if params['minute'] == '':
                return False, '分钟不能为空!'

        if params['type'] == 'hour-n':
            if params['where1'] == '':
                return False, '小时不能为空!'
            if params['minute'] == '':
                return False, '分钟不能为空!'

        if params['type'] == 'minute-n':
            if params['where1'] == '':
                return False, '分钟不能为空!'

        if params['type'] == 'week':
            if params['hour'] == '':
                return False, '小时不能为空!'
            if params['minute'] == '':
                return False, '分钟不能为空!'

        if params['type'] == 'month':
            if params['where1'] == '':
                return False, '日不能为空!'
            if params['hour'] == '':
                return False, '小时不能为空!'
            if params['minute'] == '':
                return False, '分钟不能为空!'

        return True, 'OK'

    def modifyCrondApi(self):
        sid = request.form.get('id', '')
        iname = request.form.get('name', '')
        field_type = request.form.get('type', '')
        week = request.form.get('week', '')
        where1 = request.form.get('where1', '')
        hour = request.form.get('hour', '')
        minute = request.form.get('minute', '')
        saveAllDay = request.form.get('saveAllDay', '')
        saveOther = request.form.get('saveOther', '')
        saveMaxDay = request.form.get('saveMaxDay', '')
        backup_to = request.form.get('backup_to', '')
        stype = request.form.get('stype', '')
        sname = request.form.get('sname', '')
        dumpType = request.form.get('dumpType', '')
        sbody = request.form.get('sbody', '')

        urladdress = request.form.get('urladdress', '')

        if stype == 'database':
          sbody = dumpType

        if len(iname) < 1:
            return mw.returnJson(False, '任务名称不能为空!')

        params = {
            'name': iname,
            'type': field_type,
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

        is_check_pass, msg = self.cronCheck(params)
        if not is_check_pass:
            return mw.returnJson(is_check_pass, msg)

        cuonConfig, get, name = self.getCrondCycle(params)
        print(str(get))
        cronInfo = mw.M('crontab').where(
            'id=?', (sid,)).field(self.field).find()
        del(cronInfo['id'])
        del(cronInfo['addtime'])
        cronInfo['name'] = get['name']
        cronInfo['type'] = get['type']
        cronInfo['where1'] = get['where1']
        cronInfo['where_hour'] = get['hour']
        cronInfo['where_minute'] = get['minute']
        cronInfo['saveAllDay'] = get['saveAllDay']
        cronInfo['saveOther'] = get['saveOther']
        cronInfo['saveMaxDay'] = get['saveMaxDay']
        cronInfo['backup_to'] = get['backup_to']
        cronInfo['sbody'] = get['sbody']
        cronInfo['urladdress'] = get['urladdress']
        cronInfo['dumpType'] = get['dumpType']

        addData = mw.M('crontab').where('id=?', (sid,)).save('name,type,where1,where_hour,where_minute,saveAllDay,saveOther,saveMaxDay,backup_to,sbody,urladdress', (get[
            'name'], field_type, get['where1'], get['hour'], get['minute'], get['saveAllDay'], get['saveOther'], get['saveMaxDay'], get['backup_to'], get['sbody'], get['urladdress']))
        self.removeCrond(cronInfo['echo'])
        self.syncToCrond(cronInfo)
        mw.writeLog('计划任务', '修改计划任务[' + cronInfo['name'] + ']成功')
        return mw.returnJson(True, '修改成功')

    def logsApi(self):
        sid = request.form.get('id', '')
        echo = mw.M('crontab').where("id=?", (sid,)).field('echo').find()
        logFile = mw.getCronDir() + '/' + echo['echo'] + '.log'
        if not os.path.exists(logFile):
            return mw.returnJson(False, '当前日志为空!')
        log = mw.getLastLine(logFile, 500)
        return mw.returnJson(True, log)

    def addApi(self):
        iname = request.form.get('name', '')
        field_type = request.form.get('type', '')
        week = request.form.get('week', '')
        where1 = request.form.get('where1', '')
        hour = request.form.get('hour', '')
        minute = request.form.get('minute', '')
        saveAllDay = request.form.get('saveAllDay', '')
        saveOther = request.form.get('saveOther', '')
        saveMaxDay = request.form.get('saveMaxDay', '')
        backup_to = request.form.get('backupTo', '')
        stype = request.form.get('sType', '')
        sname = request.form.get('sName', '')
        dumpType = request.form.get('dumpType', '')
        sbody = request.form.get('sBody', '')
        urladdress = request.form.get('urladdress', '')

        if len(iname) < 1:
            return mw.returnJson(False, '任务名称不能为空!')

        params = {
            'name': iname,
            'type': field_type,
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

        is_check_pass, msg = self.cronCheck(params)
        if not is_check_pass:
            return mw.returnJson(is_check_pass, msg)

        addData = self.add(params)
        if addData > 0:
            return mw.returnJson(True, '添加计划任务成功')
        return mw.returnJson(False, '添加计划任务失败')

    def add(self, params):

        stype = params["stype"]
        if stype == 'database':
          params["sbody"] = params.get("dumpType", "")
        iname = params["name"]
        field_type = params["type"]
        week = params["week"]
        where1 = params["where1"]
        hour = params["hour"]
        minute = params["minute"]
        saveAllDay = params.get('saveAllDay', '')
        saveOther = params.get('saveOther', '') 
        saveMaxDay = params.get('saveMaxDay', '') 
        backup_to = params["backup_to"]
        sname = params["sname"]
        dumpType = params.get('dumpType', '')
        sbody = params["sbody"]
        urladdress = params["urladdress"]

        # print params
        cronConfig, get, name = self.getCrondCycle(params)
        cronPath = mw.getCronDir()
        cronName = self.getShell(params)

        if type(cronName) == dict:
            return cronName

        cronConfig += ' ' + cronPath + '/' + cronName + \
            ' >> ' + cronPath + '/' + cronName + '.log 2>&1'
        
        # print(cronConfig)
        if not mw.isAppleSystem():
            wRes = self.writeCrond(cronConfig)
            if type(wRes) != bool:
                return wRes
            self.crondReload()

        add_time = time.strftime('%Y-%m-%d %X', time.localtime())
        task_id = mw.M('crontab').add('name,type,where1,where_hour,where_minute,echo,addtime,status,saveAllDay,saveOther,saveMaxDay,backup_to,stype,sname,sbody,urladdress',
                                      (iname, field_type, where1, hour, minute, cronName, add_time, 1, saveAllDay, saveOther, saveMaxDay, backup_to, stype, sname, sbody, urladdress,))
        return task_id

    def getApi(self):
        name = request.form.get('name', '')
        cronInfo = mw.M('crontab').where(
            'name=?', (name,)).field(self.field).find()
        if cronInfo:
            return mw.returnJson(True, '成功!', cronInfo)
        return mw.returnJson(False, name + ' 不存在')    

    def getCrontab(self, name):
        return mw.M('crontab').where('name=?', (name,)).field(self.field).find()
        
    def startTaskApi(self):
        sid = request.form.get('id', '')
        echo = mw.M('crontab').where('id=?', (sid,)).getField('echo')
        execstr = mw.getCronDir() + '/' + echo
        os.system('chmod +x ' + execstr)
        os.system('export IGNORE_STOPPED=1\nnohup ' + execstr + ' >> ' + execstr + '.log 2>&1 &')
        return mw.returnJson(True, '任务已执行!')

    def delApi(self):
        task_id = request.form.get('id', '')
        try:
            data = self.delete(task_id)
            if not data[0]:
                return mw.returnJson(False, data[1])
            return mw.returnJson(True, '删除计划任务成功')
        except Exception as e:
            return mw.returnJson(False, '删除计划任务失败:' + str(e))

    def delete(self, tid):

        find = mw.M('crontab').where("id=?", (tid,)).field('name,echo').find()

        if len(find) == 0:
            return (False, '任务不存在!')

        if not self.removeCrond(find['echo']):
            return (False, '无法写入文件，请检查是否开启了系统加固功能!')

        cronPath = mw.getCronDir()
        sfile = cronPath + '/' + find['echo']

        if os.path.exists(sfile):
            os.remove(sfile)
        sfile = cronPath + '/' + find['echo'] + '.log'
        if os.path.exists(sfile):
            os.remove(sfile)

        mw.M('crontab').where("id=?", (tid,)).delete()
        mw.writeLog('计划任务', mw.getInfo('删除计划任务[{1}]成功!', (find['name'],)))
        return (True, "OK")

    def delLogsApi(self):
        sid = request.form.get('id', '')
        try:
            echo = mw.M('crontab').where("id=?", (sid,)).getField('echo')
            logFile = mw.getCronDir() + '/' + echo + '.log'
            os.remove(logFile)
            return mw.returnJson(True, '任务日志已清空!')
        except:
            return mw.returnJson(False, '任务日志清空失败!')

    # 取数据列表
    def getDataListApi(self):
        
        stype = request.form.get('type', '')

        data = {}
        data['stype'] = stype

        bak_data = []
        
        # bak_data获取
        if stype == 'sites' or stype == 'databases':
            hookPath = mw.getPanelDataDir() + "/hook_backup.json"
            if os.path.exists(hookPath):
                t = mw.readFile(hookPath)
                bak_data = json.loads(t)
        
        # data获取
        if stype == 'sites' or stype == 'siteSetting' or stype == 'logs': 
            data['data'] = mw.M('sites').field('name,ps').select()

        if stype == 'pluginSetting':
            data['data'] = mw.getBackupPluginList()

        if stype == 'databases':
            db_list = {}
            db_list['orderOpt'] = bak_data

            # 获取的mysql目录
            path = ''
            if os.path.exists(mw.getServerDir() + '/mysql-apt'):
                path = '/www/server/mysql-apt'
            elif os.path.exists(mw.getServerDir() + '/mysql'):
                path = '/www/server/mysql'
            else:
                print('未检测到安装的mysql插件')
            
            if not os.path.exists(path + '/mysql.db'):
                db_list['data'] = []
            else:
                db_list['data'] = mw.M('databases').dbPos(
                    path, 'mysql').field('name,ps').select()
                
            return mw.getJson(db_list)

        data['orderOpt'] = bak_data
        return mw.getJson(data)
    ##### ----- start ----- ###

    # 转换大写星期
    def toWeek(self, num):
        wheres = {
            0:   '日',
            1:   '一',
            2:   '二',
            3:   '三',
            4:   '四',
            5:   '五',
            6:   '六'
        }
        try:
            return wheres[num]
        except:
            return ''

    def getCrondCycle(self, params):
        cuonConfig = ''
        name = ''
        if params['type'] == "day":
            cuonConfig = self.getDay(params)
            name = '每天'
        elif params['type'] == "day-n":
            cuonConfig = self.getDay_N(params)
            name = mw.getInfo('每{1}天', (params['where1'],))
        elif params['type'] == "hour":
            cuonConfig = self.getHour(params)
            name = '每小时'
        elif params['type'] == "hour-n":
            cuonConfig = self.getHour_N(params)
            name = '每小时'
        elif params['type'] == "minute-n":
            cuonConfig = self.minute_N(params)
        elif params['type'] == "week":
            params['week'] = params['where1']
            cuonConfig = self.week(params)
        elif params['type'] == "month":
            cuonConfig = self.month(params)
        return cuonConfig, params, name

    # 取任务构造Day
    def getDay(self, param):
        cuonConfig = "{0} {1} * * * ".format(param['minute'], param['hour'])
        return cuonConfig
    # 取任务构造Day_n

    def getDay_N(self, param):
        cuonConfig = "{0} {1} */{2} * * ".format(
            param['minute'], param['hour'], param['where1'])
        return cuonConfig

    # 取任务构造Hour
    def getHour(self, param):
        cuonConfig = "{0} * * * * ".format(param['minute'])
        return cuonConfig

    # 取任务构造Hour-N
    def getHour_N(self, param):
        cuonConfig = "{0} */{1} * * * ".format(
            param['minute'], param['where1'])
        return cuonConfig

    # 取任务构造Minute-N
    def minute_N(self, param):
        cuonConfig = "*/{0} * * * * ".format(param['where1'])
        return cuonConfig

    # 取任务构造week
    def week(self, param):
        cuonConfig = "{0} {1} * * {2}".format(
            param['minute'], param['hour'], param['week'])
        return cuonConfig

    # 取任务构造Month
    def month(self, param):
        cuonConfig = "{0} {1} {2} * * ".format(
            param['minute'], param['hour'], param['where1'])
        return cuonConfig

    # 取执行脚本
    def getShell(self, param):
        # try:
        stype = param['stype']
        if stype == 'toFile':
            shell = param.sFile
        else:
            head = "#!/bin/bash\nPATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin\nexport PATH\n"

            source_bin_activate = '''
export LANG=en_US.UTF-8
MW_PATH=%s/bin/activate
if [ -f $MW_PATH ];then
    source $MW_PATH
fi
            ''' % (mw.getRunDir(),)

            head = head + source_bin_activate + "\n"
            log = '.log'

            script_dir = mw.getServerDir() + "/jh-panel/scripts"

            save = json.dumps({
                "saveAllDay": param.get('saveAllDay', ''),
                "saveOther": param.get('saveOther', ''),
                "saveMaxDay": param.get('saveMaxDay', '')
            })

            wheres = {
                'path': head + "python3 " + script_dir + "/backup.py path " + param['sname'] + " '" + str(save) + "'",
                'site':   head + "python3 " + script_dir + "/backup.py site " + param['sname'] + " '" + str(save) + "'",
                'siteSetting':   head + "python3 " + script_dir + "/backup.py siteSetting " + param['sname'] + " '" + str(save) + "'",
                'pluginSetting':   head + "python3 " + script_dir + "/backup.py pluginSetting " + param['sname'] + " '" + str(save) + "'",
                'database': head + "python3 " + script_dir + "/backup.py database " + param['sname'] + " '" + str(save) + "'" + " " + param.get('dumpType', ''),
                'logs':   head + "python3 " + script_dir + "/logs_backup.py " + param['sname'] + log + " '" + str(save) + "'",
                'rememory': head + "/bin/bash " + script_dir + '/rememory.sh'
            }
            if param['backup_to'] != 'localhost':
                cfile = mw.getPluginDir() + "/" + \
                    param['backup_to'] + "/index.py"
                wheres = {
                    'path': head + "python3 " + cfile + " path " + param['sname'] + " '" + str(save) + "'",
                    'site':   head + "python3 " + cfile + " site " + param['sname'] + " '" + str(save) + "'",
                    'siteSetting':   head + "python3 " + cfile + " siteSetting " + param['sname'] + " '" + str(save) + "'",
                    'pluginSetting':   head + "python3 " + cfile + " pluginSetting " + param['sname'] + " '" + str(save) + "'",
                    'database': head + "python3 " + cfile + " database " + param['sname'] + " '" + str(save) + "'",
                    'logs':   head + "python3 " + script_dir + "/logs_backup.py " + param['sname'] + log + " '" + str(save) + "'",
                    'rememory': head + "/bin/bash " + script_dir + '/rememory.sh'
                }
            try:
                shell = wheres[stype]
            except:
                if stype == 'toUrl':
                    shell = head + "curl -sS --connect-timeout 10 -m 60 '" + \
                        param['urladdress'] + "'"
                else:
                    shell = head + param['sbody'].replace("\r\n", "\n")

                shell += '''
echo "----------------------------------------------------------------------------"
endDate=`date +"%Y-%m-%d %H:%M:%S"`
echo "★[$endDate] Successful"
echo "----------------------------------------------------------------------------"
'''
        cronPath = mw.getCronDir()
        if not os.path.exists(cronPath):
            mw.execShell('mkdir -p ' + cronPath)

        if not 'echo' in param:
            cronName = mw.md5(mw.md5(str(time.time()) + '_mw'))
        else:
            cronName = param['echo']
        file = cronPath + '/' + cronName

        # 检查stopped文件
        shell = f"""
if [ -z "$IGNORE_STOPPED" ] && [ -f {file + '_stopped'} ];then 
\techo "定时任务已停用"
\texit 0 
fi
        """ + shell 

        mw.writeFile(file, self.checkScript(shell))
        mw.execShell('chmod 750 ' + file)
        return cronName

    # 检查脚本
    def checkScript(self, shell):
        keys = ['shutdown', 'init 0', 'mkfs', 'passwd',
                'chpasswd', '--stdin', 'mkfs.ext', 'mke2fs']
        for key in keys:
            shell = shell.replace(key, '[***]')
        return shell

    # 将Shell脚本写到文件
    def writeCrond(self, config):
        u_file = '/var/spool/cron/crontabs/root'
        if not os.path.exists(u_file):
            # file = '/var/spool/cron/root'
            file = '/var/spool/cron/crontabs/root' # 20230715 如果在debian上，/var/spool/cron/crontabs/root被删掉了，会写到错误的目录，暂时改成同一个文件
            if mw.isAppleSystem():
                file = '/etc/crontab'
        else:
            file = u_file

        if not os.path.exists(file):
            mw.writeFile(file, '')
        conf = mw.readFile(file)
        conf += str(config) + "\n"
        if mw.writeFile(file, conf):
            if not os.path.exists(u_file):
                mw.execShell("chmod 600 '" + file +
                             "' && chown root.root " + file)
            else:
                mw.execShell("chmod 600 '" + file +
                             "' && chown root.crontab " + file)
            return True
        return mw.returnJson(False, '文件写入失败,请检查是否开启系统加固功能!')

    # 重载配置
    def crondReload(self):
        if mw.isAppleSystem():
            if os.path.exists('/etc/crontab'):
                pass
                # mw.execShell('/usr/sbin/cron restart')
        else:
            if os.path.exists('/etc/init.d/crond'):
                mw.execShell('/etc/init.d/crond reload')
            elif os.path.exists('/etc/init.d/cron'):
                mw.execShell('systemctl reset-failed')
                mw.execShell('service cron restart')
            else:
                mw.execShell("systemctl reload crond")

    # 从crond删除
    def removeCrond(self, echo):
        u_file = '/var/spool/cron/crontabs/root'
        if not os.path.exists(u_file):
            file = '/var/spool/cron/root'
            if mw.isAppleSystem():
                file = '/etc/crontab'

            if not os.path.exists(file):
                return False
        else:
            file = u_file

        if mw.isAppleSystem():
            return True

        conf = mw.readFile(file)
        rep = ".+" + str(echo) + ".+\n"
        conf = re.sub(rep, "", conf)
        if not mw.writeFile(file, conf):
            return False
        self.crondReload()
        # 在目录下增加标识文件
        statusPath = mw.getCronDir() + '/' + str(echo) + '_stopped'
        mw.execShell('echo "" > ' + statusPath)
        return True

    def syncToCrond(self, cronInfo):
        if 'where_hour' in cronInfo:
            cronInfo['hour'] = cronInfo['where_hour']
            cronInfo['minute'] = cronInfo['where_minute']
            cronInfo['week'] = cronInfo['where1']
        cuonConfig, cronInfo, name = self.getCrondCycle(cronInfo)
        cronPath = mw.getCronDir()
        cronName = self.getShell(cronInfo)
        if type(cronName) == dict:
            return cronName
        cuonConfig += ' ' + cronPath + '/' + cronName + \
            ' >> ' + cronPath + '/' + cronName + '.log 2>&1'
        wRes = self.writeCrond(cuonConfig)
        if type(wRes) != bool:
            return False
        if cronInfo.get('status', 1) == 0:
            # 在目录下增加标识文件
            statusPath = cronPath + '/' + str(cronName) + '_stopped'
            mw.execShell('echo "" > ' + statusPath)
            return False
        else:
            # 清除stopped文件
            statusPath = cronPath + '/' + str(cronName) + '_stopped'
            mw.execShell('rm ' + statusPath)
        self.crondReload()
