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


import mw
import db
import time
import system_api
import site_api
import crontab_api
systemApi = system_api.system_api()
siteApi = site_api.site_api()
crontabApi = crontab_api.crontab_api()


class reportTools:

    __START_TIME = None
    __END_TIME = None
    __START_TIMESTAMP = None
    __END_TIMESTAMP = None
    __START_DATE = None
    __END_DATE = None

    def __init__(self):
        now = datetime.datetime.now()
        self.__START_TIME = mw.getReportCycleStartTime(now)
        self.__END_TIME = now
        self.__START_TIMESTAMP = self.__START_TIME.timestamp()
        self.__END_TIMESTAMP = self.__END_TIME.timestamp()
        self.__START_DATE = datetime.datetime.fromtimestamp(self.__START_TIMESTAMP).date()
        self.__END_DATE = datetime.datetime.fromtimestamp(self.__END_TIMESTAMP).date()

    def analyzeMonitorData(self, data, key, over):
        """ 
        分析监控数据，统计异常次数(5分钟内的算1次)
        data: 监控数据list
        key: 统计字段
        over: 字段超过多少算异常
        """
        overCount = 0
        total = 0
        last_time = None

        sorted_data = sorted(data, key=lambda x: x['addtime'])
        for item in sorted_data:
            total += item.get(key, 0)
            if item.get(key, 0) > over:
                if last_time is None or item['addtime'] - last_time >= 300:
                    overCount += 1
                    last_time = item['addtime']
        return {
            "average": total / len(data) if data else 0,
            "overCount": overCount
        }


    # 生成并发送服务器报告
    def sendReport(self):
        sql = db.Sql().dbfile('system')
        csql = mw.readFile('data/sql/system.sql')
        csql_list = csql.split(';')
        for index in range(len(csql_list)):
            sql.execute(csql_list[index], ())

        print("报表：%s-%s" % (self.__START_TIME, self.__END_TIME))

        control_notify_config = mw.getControlNotifyConfig()
        if control_notify_config['notifyStatus'] == 'open':

            # 监控阈值
            cpu_notify_value = control_notify_config['cpu']
            mem_notify_value = control_notify_config['memory']
            disk_notify_value = control_notify_config['disk']
            ssl_cert_notify_value = control_notify_config['ssl_cert']

            # cpu(pro)、内存(mem)
            sysinfo_tips = []
            cpuIoData = mw.M('cpuio').dbfile('system') .where("addtime>=? AND addtime<=?", (self.__START_TIMESTAMP, self.__END_TIMESTAMP)).field('id,pro,mem,addtime').order('id asc') .select()
            cpuAnalyzeResult = self.analyzeMonitorData(cpuIoData, 'pro', cpu_notify_value)
            memAnalyzeResult = self.analyzeMonitorData(cpuIoData, 'mem', mem_notify_value)
            sysinfo_tips.append({
                "name": "CPU",
                "desc": "平均使用率%.2f%%%s" % (
                    cpuAnalyzeResult.get('average', 0), 
                    ('，<span style="color: red">异常（使用率超过%s%%）%s次</span>' % (str(cpu_notify_value), str(cpuAnalyzeResult.get('overCount', 0)))) if cpuAnalyzeResult.get('overCount', 0) > 0 else ''
                )
            })
            sysinfo_tips.append({
                "name": "内存",
                "desc": "平均使用率%.2f%%%s" % (
                    memAnalyzeResult.get('average', 0), 
                    ('，<span style="color: red">异常（使用率超过%s%%）%s次</span>' % (str(mem_notify_value), str(memAnalyzeResult.get('overCount', 0)))) if memAnalyzeResult.get('overCount', 0) > 0 else ''
                )
            })

            # 负载：资源使用率(pro)
            loadAverageData = mw.M('load_average').dbfile('system') .where("addtime>=? AND addtime<=?", ( self.__START_TIMESTAMP, self.__END_TIMESTAMP)).field('id,pro,one,five,fifteen,addtime').order('id asc').select()
            loadAverageAnalyzeResult = self.analyzeMonitorData(loadAverageData, 'pro', cpu_notify_value)
            sysinfo_tips.append({
                "name": "资源使用率",
                "desc": "平均使用率%.2f%%%s" % (
                    loadAverageAnalyzeResult.get('average', 0), 
                    ('，<span style="color: red">异常（使用率超过%s%%）%s次</span>' % (str(cpu_notify_value), str(loadAverageAnalyzeResult.get('overCount', 0)))) if loadAverageAnalyzeResult.get('overCount', 0) > 0 else ''
                )
            })

            # 磁盘
            diskInfo = systemApi.getDiskInfo()
            for disk in diskInfo:
                disk_size_percent = int(disk['size'][3].replace('%', ''))
                sysinfo_tips.append({
                    "name": "磁盘（%s）" % disk['path'],
                    "desc": "已使用%s（%s/%s）" % (
                        disk['size'][3],
                        disk['size'][1],
                        disk['size'][0]
                    )
                })

            # 网站
            siteinfo_tips = []
            siteInfo = systemApi.getSiteInfo()
            for site in siteInfo['site_list']:
                site_name = site['name']
                status = '<span>运行中</span>' if site['status'] == '1' else '<span style="color: red">已停止</span>'
                cert_status = '未配置'

                # 证书
                cert_data = site['cert_data']
                ssl_type = site['ssl_type']
                if cert_data is not None:
                    cert_not_after = cert_data.get('notAfter', '0000-00-00')
                    cert_endtime = int(cert_data.get('endtime', 0))
                    site_error_msg = ''
                    if cert_endtime < 0:
                        cert_status = '%s到期，已过期<span style="color: red">%s</span>天' % (cert_not_after, str(cert_endtime))
                    else:
                        cert_status = '将于%s到期，还有%s天%s到期' % (
                            cert_not_after,
                            ("<span style='color: red'>%s</span>" if cert_endtime < ssl_cert_notify_value else "<span>%s</span>") % str(cert_endtime), 
                            ('，到期后将自动续签' if ssl_type == 'lets' or ssl_type == 'acme' else '')
                        )
                siteinfo_tips.append({
                    "name": site_name,
                    "desc": "%s（SSL证书%s）" % (
                        status,
                        cert_status
                    )
                })

            # JianghuJS管理器
            jianghujsinfo_tips = []
            jianghujs_Info = systemApi.getJianghujsInfo()
            if(jianghujs_Info['status'] == 'start'):
                project_list = jianghujs_Info['project_list']
                for project in project_list:
                    jianghujsinfo_tips.append({
                        "name": project['name'],
                        "desc": "%s" % (
                            '<span>已启动</span>' if project['status'] == 'start' else '<span style="color: red">已停止</span>'
                        )
                    })

            # Docker管理器
            dockerinfo_tips = []
            docker_Info = systemApi.getDockerInfo()
            if(docker_Info['status'] == 'start'):
                project_list = docker_Info['project_list']
                for project in project_list:
                    dockerinfo_tips.append({
                        "name": project['name'],
                        "desc": "%s" % (
                            '<span>已启动</span>' if project['status'] == 'start' else '<span style="color: red">已停止</span>'
                        )
                    })

            # 数据库表 
            mysqlinfo_tips = []
            mysql_info = systemApi.getMysqlInfo()
            # 开始的数据库情况
            start_mysql_info = mw.M('database').dbfile('system').where("addtime>=? AND addtime<=?", (self.__START_TIMESTAMP, self.__END_TIMESTAMP)).field('id,total_size,total_bytes,list,addtime').order('id asc').limit('0,1').select()
            start_database_list = '[]'
            if len(start_mysql_info) > 0:
                start_database_list = start_mysql_info[0].get('list', '[]')
            start_database_list_dict = {item.get('name', ''): item for item in json.loads(start_database_list)}
            
            if(mysql_info['status'] == 'start'):
                database_list = mysql_info['database_list']
                for database in database_list:
                    start_database = start_database_list_dict.get(database.get('name', ''), {})
                    size_change = database.get('size_bytes', 0) - start_database.get('size_bytes', 0)
                    mysqlinfo_tips.append({
                        "name": database['name'],
                        "desc": "变化：%s<br/>总大小：%s" % (
                            (('<span style="color: green">+%s</span>' if size_change > 0 else '<span>%s</span>') % mw.toSize(size_change)),
                            database['size']
                        )
                    })

            # 备份相关
            # xtrabackup
            xtrabackup_tips = []
            xtrabackup_info = systemApi.getXtrabackupInfo()
            if(xtrabackup_info['status'] =='start'):
                xtrabackup_ddb = mw.getDDB('/www/server/xtrabackup/data/')
                xtrabackup_history = xtrabackup_ddb.getAll('backup_history')
                print(xtrabackup_history)


            # 生成概要信息
            summary_tips = []
            # 系统资源概要信息
            sysinfo_summary_tips = []
            if cpuAnalyzeResult.get('average', 0) > cpu_notify_value:
                sysinfo_summary_tips.append("CPU")
            if memAnalyzeResult.get('average', 0) > mem_notify_value:
                sysinfo_summary_tips.append("内存")
            if loadAverageAnalyzeResult.get('average', 0) > cpu_notify_value:
                sysinfo_summary_tips.append("资源使用率")
            for disk in diskInfo:
                disk_size_percent = int(disk['size'][3].replace('%', ''))
                if disk_size_percent > disk_notify_value:
                    sysinfo_summary_tips.append("磁盘（%s）" % disk['path'])
            if len(sysinfo_summary_tips) > 0:
                summary_tips.append("、".join(sysinfo_summary_tips) + '平均使用率过高，有服务中断停机风险')
           # 网站概要信息
            siteinfo_summary_tips = []
            for site in siteInfo['site_list']:
                site_name = site['name']
                cert_data = site['cert_data']
                ssl_type = site['ssl_type']
                if cert_data is not None:
                    cert_not_after = cert_data.get('notAfter', '0000-00-00')
                    cert_endtime = int(cert_data.get('endtime', 0))
                    site_error_msg = ''
                    if not (ssl_type == 'lets' or ssl_type == 'acme') and cert_endtime < ssl_cert_notify_value:
                        siteinfo_summary_tips.append(site_name)
            if len(siteinfo_summary_tips) > 0:
                summary_tips.append("域名（" + "、".join(siteinfo_summary_tips) + '）证书需要及时更新')
            # 无异常默认信息
            if len(summary_tips) == 0:
                summary_tips.append("服务运行正常，继续保持！")


            report_content = """
<style>
h3 { font-size: bold; }
table {
    border-top: 1px solid #999;
    border-left: 1px solid #999;
    border-spacing: 0;
    width: 100%%;
}
table tr td {
    padding: 5px;
    line-height: 20px;
}
table tr td:first-child {
    width: 30%%;
}
table tr td:nth-child(2) {
    width: 70%%;
}
.project-table tr td:first-child {
    width: 70%%;
}
.project-table tr td:nth-child(2) {
    width: 30%%;
}

</style>

<h2>%(title)s(%(ip)s)-服务器运行报告 </h2>
<h3 style="color: #cecece">日期：%(start_date)s至%(end_date)s</h3>
<div style="display: flex; flex-direction: column;align-items: center;">
    <h3>概要信息：</h3>
    <ul>
    %(summary_content)s
    </ul>
</div>

<h3>系统资源：</h3>
<table border>
%(sysinfo_tips)s
</table>

<h3>网站：</h3>

<table border>
%(siteinfo_tips)s
</table>


<h3>JianghuJS项目：</h3>

<table border class="project-table">
%(jianghujsinfo_tips)s
</table>

<h3>Docker项目：</h3>

<table border class="project-table">
%(dockerinfo_tips)s
</table>

<h3>数据库：</h3>

<table border>
%(mysqlinfo_tips)s
</table>
            """ % {
                "title": mw.getConfig('title'),
                "ip": mw.getHostAddr(),
                "start_date": self.__START_DATE,
                "end_date": self.__END_DATE,
                "sysinfo_tips":''.join(f"<tr><td>{item.get('name', '')}</td><td>{item.get('desc', '')}</td></tr>\n" for item in sysinfo_tips),
                "siteinfo_tips": ''.join(f"<tr><td>{item.get('name', '')}</td><td>{item.get('desc', '')}</td></tr>\n" for item in sorted(siteinfo_tips, key=lambda x: x.get('name', ''))),
                "jianghujsinfo_tips": ''.join(f"<tr><td>{item.get('name', '')}</td><td>{item.get('desc', '')}</td></tr>\n" for item in sorted(jianghujsinfo_tips, key=lambda x: x.get('name', ''))),
                "dockerinfo_tips": ''.join(f"<tr><td>{item.get('name', '')}</td><td>{item.get('desc', '')}</td></tr>\n" for item in sorted(dockerinfo_tips, key=lambda x: x.get('name', ''))),
                "mysqlinfo_tips": ''.join(f"<tr><td>{item.get('name', '')}</td><td>{item.get('desc', '')}</td></tr>\n" for item in sorted(mysqlinfo_tips, key=lambda x: x.get('name', ''))),
                "summary_content": ''.join(f"<li>{item}</li>\n" for item in summary_tips)

            }
            mw.notifyMessage(
                msg=report_content, 
                msgtype="html", 
                title="%(title)s(%(ip)s)服务器报告" % {"title": mw.getConfig('title'), "ip": mw.getHostAddr(), "start_date": self.__START_DATE, "end_date": self.__END_DATE}, 
                stype='服务器报告', 
                trigger_time=0
            )
        return mw.returnJson(True, '设置成功!')
    
    def getBackupReport(self):
        # xtrabackup
        xtrabackup_info = None
        xtrabackup_tips = []
        if os.path.exists('/www/server/xtrabackup/'):
            xtrabackup_ddb = mw.getDDB('/www/server/xtrabackup/data/')
            xtrabackup_history = xtrabackup_ddb.getAll('backup_history')
            # 初始化统计数据
            total_count = len(xtrabackup_history)
            total_size = sum(item['size_bytes'] for item in xtrabackup_history)
            average_size_bytes = total_size / total_count if total_count != 0 else 0
            
            # 获取最后备份时间
            last_backup_time = max(item['add_time'] for item in xtrabackup_history) if total_count > 0 else None
            # 获取在指定时间段内的备份
            backups_in_timeframe = [item for item in xtrabackup_history if self.__START_TIMESTAMP <= item['add_timestamp'] <= self.__END_TIMESTAMP]
            count_in_timeframe = len(backups_in_timeframe)
            average_size_bytes_in_timeframe = sum(item['size_bytes'] for item in backups_in_timeframe) / count_in_timeframe if count_in_timeframe != 0 else 0

            xtrabackup_info = {
                'last_backup_time': last_backup_time,
                # 'backups_in_timeframe': backups_in_timeframe,
                'count_in_timeframe': count_in_timeframe,
                'average_size_bytes_in_timeframe': average_size_bytes_in_timeframe,
                'average_size_in_timeframe': mw.toSize(average_size_bytes_in_timeframe),
                # 'backups': xtrabackup_history,
                'total_count': total_count,
                'average_size_bytes': average_size_bytes,
                'average_size': mw.toSize(average_size_bytes)
            }
        # xtrabackup-inc
        xtrabackup_inc_info = None
        xtrabackup_inc_tips = []
        if os.path.exists('/www/server/xtrabackup-inc/'):
            xtrabackup_inc_ddb = mw.getDDB('/www/server/xtrabackup-inc/data/')
            xtrabackup_inc_history = xtrabackup_inc_ddb.getAll('backup_history')
            # 全量备份相关
            full_history = [item for item in xtrabackup_inc_history if item['backup_type'] == 'full']
            full_total_count = len(full_history)
            full_total_size = sum(item['size_bytes'] for item in full_history)
            full_average_size_bytes = full_total_size / full_total_count if full_total_count != 0 else 0
            full_last_backup_time = max(item['add_time'] for item in full_history) if full_total_count > 0 else None
            full_backups_in_timeframe = [item for item in full_history if self.__START_TIMESTAMP <= item['add_timestamp'] <= self.__END_TIMESTAMP]
            full_count_in_timeframe = len(full_backups_in_timeframe)
            full_average_size_bytes_in_timeframe = sum(item['size_bytes'] for item in full_backups_in_timeframe) / full_count_in_timeframe if full_count_in_timeframe != 0 else 0
            # 增量备份相关
            inc_history = [item for item in xtrabackup_inc_history if item['backup_type'] == 'inc']
            inc_total_count = len(inc_history)
            inc_total_size = sum(item['size_bytes'] for item in inc_history)
            inc_average_size_bytes = inc_total_size / inc_total_count if inc_total_count != 0 else 0
            inc_last_backup_time = max(item['add_time'] for item in inc_history) if inc_total_count > 0 else None
            inc_backups_in_timeframe = [item for item in inc_history if self.__START_TIMESTAMP <= item['add_timestamp'] <= self.__END_TIMESTAMP]
            inc_count_in_timeframe = len(inc_backups_in_timeframe)
            inc_average_size_bytes_in_timeframe = sum(item['size_bytes'] for item in inc_backups_in_timeframe) / inc_count_in_timeframe if inc_count_in_timeframe != 0 else 0

            xtrabackup_inc_info = {
                'full_last_backup_time': full_last_backup_time,
                'full_count_in_timeframe': full_count_in_timeframe,
                'full_average_size_bytes_in_timeframe': full_average_size_bytes_in_timeframe,
                'full_average_size_in_timeframe': mw.toSize(full_average_size_bytes_in_timeframe),
                'full_total_count': full_total_count,
                'full_average_size_bytes': full_average_size_bytes,
                'full_average_size': mw.toSize(full_average_size_bytes),
                'inc_last_backup_time': inc_last_backup_time,
                'inc_count_in_timeframe': inc_count_in_timeframe,
                'inc_average_size_bytes_in_timeframe': inc_average_size_bytes_in_timeframe,
                'inc_average_size_in_timeframe': mw.toSize(inc_average_size_bytes_in_timeframe),
                'inc_total_count': inc_total_count,
                'inc_average_size_bytes': inc_average_size_bytes,
                'inc_average_size': mw.toSize(inc_average_size_bytes)
            }
        return xtrabackup_info, xtrabackup_inc_info
        
        

if __name__ == "__main__":
    report = reportTools()
    print(report.getBackupReport())

    type = sys.argv[1]

    if type == 'send':
        report.sendReport()