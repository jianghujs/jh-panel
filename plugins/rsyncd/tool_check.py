# coding:utf-8
#-----------------------------
# Rsyncd 同步状态检查工具
#-----------------------------

import sys
import os
import re
import json
import traceback
from datetime import datetime

_PANEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(_PANEL_DIR, 'class/core'))
import mw


RSYNCD_SERVER_DIR = '/www/server/rsyncd'
RSYNCD_CONFIG_FILE = RSYNCD_SERVER_DIR + '/config.json'
LSYNCD_STATUS_FILE = RSYNCD_SERVER_DIR + '/logs/lsyncd.status'


def _check_realtime_sync_status(content):
    """
    通过 lsyncd.status 判断实时同步是否正常。正常的状态文件形如：
        Lsyncd status report at Wed Jul  1 09:26:43 2026

        Sync1 source=/mnt/mdext/wwwstorage/
        There are 0 delays
        Filtering:
          nothing.

    返回 (is_ok: bool, reason: str)。reason 为面向运维的中文说明。
    """
    if content is None or not content.strip():
        return False, "lsyncd 状态文件为空，可能 lsyncd 进程未启动或刚重启还未刷新状态"
    if not re.search(r"Lsyncd status report at\s+\w+\s+\w+\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\d{4}", content):
        return False, "未找到 lsyncd 状态时间戳，可能 lsyncd 进程异常或状态文件被截断"
    if not re.search(r"Sync\d*\s+source=", content):
        return False, "未找到同步源(Sync source=)描述，可能 lsyncd 配置未加载同步任务"
    if not re.search(r"There are\s+\d+\s+delays", content):
        return False, "未找到 delays 统计，lsyncd 状态输出异常，建议检查 lsyncd 进程"
    if "Filtering:" not in content:
        return False, "状态文件缺少 Filtering 段，lsyncd 可能未正常运行到位"
    return True, ""


def _check_fixtime_sync_status(content):
    """
    通过定时同步单次运行日志判断本次同步是否正常。正常日志形如：
        sending incremental file list
        ...
        sent X bytes  received Y bytes  Z bytes/sec
        total size is N  speedup is M

    返回 (is_ok: bool, reason: str)。reason 说明疑似原因。
    """
    if content is None or not content.strip():
        return False, "本次同步日志为空，任务可能未执行或被中断"

    has_rsync_summary = bool(re.search(r"sent\s+[\d,]+\s+bytes\s+received\s+[\d,]+\s+bytes", content)) and bool(re.search(r"total size is\s+[\d,]+", content))
    if "rsync warning: some files vanished before they could be transferred (code 24)" in content and has_rsync_summary:
        return True, ""
    if "rsync warning ignored: exit 24" in content and has_rsync_summary:
        return True, ""

    explicit_reasons = [
        ("rsync目标目录检查失败", "目标目录检查失败，可能挂载丢失或目录不可写"),
        ("目录访问超时", "目标目录访问超时，可能网络/挂载(NFS等)异常"),
        ("abort: delete ratio exceeds threshold", "本次待删除文件比例超过阈值，rsync 被主动中止以防误删，请人工确认源目录变化"),
        ("real rsync skipped", "预检失败导致本次 rsync 被跳过，请查看 preflight 日志"),
        ("rsync: connection unexpectedly closed", "rsync 连接被意外关闭，可能是对端进程/网络断开"),
        ("Connection refused", "连接被拒绝，目标 rsync/ssh 服务可能未运行或端口不通"),
        ("Connection timed out", "连接超时，网络不通或对端负载过高"),
        ("Permission denied", "权限被拒绝，检查 SSH 密钥或目标目录权限"),
        ("No route to host", "路由不可达，检查目标 IP/网络"),
        ("rsync error", "rsync 报错退出，请查看完整日志定位具体错误码"),
        ("failed:", "同步过程中出现失败提示，请查看完整日志"),
    ]
    for kw, reason in explicit_reasons:
        if kw in content:
            return False, reason
    if "sending incremental file list" not in content:
        return False, "未看到 rsync 开始传输(sending incremental file list)，任务可能启动即失败或被中断"
    if not re.search(r"sent\s+[\d,]+\s+bytes\s+received\s+[\d,]+\s+bytes", content):
        return False, "未看到 rsync 传输汇总(sent/received)，任务可能中途中断"
    if not re.search(r"total size is\s+[\d,]+", content):
        return False, "未看到 rsync 完成汇总(total size)，任务可能未正常结束"
    return True, ""


def _inspect_sync_task(send_item):
    """读取任务最新运行日志并写回 last_sync_at/latest_log_file/同步状态。"""
    send_item['log_format_ok'] = True
    send_item['log_format_reason'] = ""
    send_item['latest_log_file'] = ""

    task_name = send_item.get('name', '')
    sync_task_logs_dir = f'{RSYNCD_SERVER_DIR}/send/{task_name}/logs/'
    if not os.path.isdir(sync_task_logs_dir):
        return None

    sync_task_logs_files = [
        (f, os.path.getmtime(os.path.join(sync_task_logs_dir, f)))
        for f in os.listdir(sync_task_logs_dir)
        if os.path.isfile(os.path.join(sync_task_logs_dir, f)) and f.startswith('run_')
    ]
    if len(sync_task_logs_files) == 0:
        return None

    sync_task_logs_files.sort(key=lambda x: x[1], reverse=True)
    latest_file, latest_time = sync_task_logs_files[0]
    send_item['last_sync_at'] = mw.toTime(latest_time)
    send_item['latest_log_file'] = latest_file

    if send_item.get('realtime', 'false') == 'true':
        return None

    try:
        latest_log_path = os.path.join(sync_task_logs_dir, latest_file)
        latest_log_content = mw.readFile(latest_log_path) or ""
        is_ok, reason = _check_fixtime_sync_status(latest_log_content)
    except Exception as e:
        is_ok = False
        reason = f"读取本次同步日志失败：{e}"

    send_item['log_format_ok'] = is_ok
    send_item['log_format_reason'] = reason
    if not is_ok:
        return {
            "name": task_name,
            "reason": reason,
            "log_file": latest_file,
        }
    return None


def getRsyncdInfo(start_timestamp=None):
    """汇总 rsyncd/lsyncd 同步状态，返回 report.py 可直接消费的 rsyncd_info。"""
    if not os.path.exists(RSYNCD_SERVER_DIR + '/'):
        return None

    rsyncd_config_content = mw.readFile(RSYNCD_CONFIG_FILE)
    if not rsyncd_config_content:
        return None
    rsyncd_config = json.loads(rsyncd_config_content)
    send_list = rsyncd_config.get('send', {}).get('list', [])

    send_open_list = []
    send_open_realtime_list = []
    send_open_fixtime_list = []
    send_close_list = []
    last_realtime_sync_date = None
    last_realtime_sync_timestamp = None
    realtime_delays = 0
    realtime_format_ok = True
    realtime_format_reason = ""
    fixtime_abnormal_tasks = []

    for send_item in send_list:
        if send_item.get('status', 'enabled') == 'enabled':
            abnormal_task = _inspect_sync_task(send_item)
            if abnormal_task is not None:
                fixtime_abnormal_tasks.append(abnormal_task)
            send_open_list.append(send_item)
            if send_item.get('realtime', 'false') == 'true':
                send_open_realtime_list.append(send_item)
            else:
                send_open_fixtime_list.append(send_item)
        else:
            send_close_list.append(send_item)

    if os.path.exists(LSYNCD_STATUS_FILE):
        real_time_status_file = mw.readFile(LSYNCD_STATUS_FILE) or ""
        last_sync_match = re.search(r"Lsyncd status report at ([\w\s:]+).*Sync", real_time_status_file)
        if last_sync_match:
            last_realtime_sync_date_str = last_sync_match.group(1).replace('\n', '')
            try:
                last_realtime_sync_date = datetime.strptime(last_realtime_sync_date_str, "%a %b %d %H:%M:%S %Y")
                last_realtime_sync_timestamp = datetime.timestamp(last_realtime_sync_date)
            except Exception:
                last_realtime_sync_date = None
                last_realtime_sync_timestamp = None
        realtime_delays_match = re.search(r"There are ([\d.]+) delays", real_time_status_file)
        if realtime_delays_match:
            realtime_delays = int(float(realtime_delays_match.group(1)))
        realtime_format_ok, realtime_format_reason = _check_realtime_sync_status(real_time_status_file)
    else:
        if len(send_open_realtime_list) > 0:
            realtime_format_ok = False
            realtime_format_reason = f"未找到 lsyncd 状态文件({LSYNCD_STATUS_FILE})，lsyncd 进程可能未运行"

    return {
        "last_realtime_sync_date": last_realtime_sync_date,
        "last_realtime_sync_timestamp": last_realtime_sync_timestamp,
        "realtime_delays": realtime_delays,
        "realtime_format_ok": realtime_format_ok,
        "realtime_format_reason": realtime_format_reason,
        "fixtime_abnormal_tasks": fixtime_abnormal_tasks,
        "send_list": send_list,
        "send_count": len(send_list),
        "send_open_list": send_open_list,
        "send_open_realtime_list": send_open_realtime_list,
        "send_open_fixtime_list": send_open_fixtime_list,
        "send_open_count": len(send_open_list),
        "send_close_count": len(send_close_list)
    }


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


if __name__ == "__main__":
    try:
        action = sys.argv[1] if len(sys.argv) > 1 else 'get_info'
        if action == 'get_info':
            start_timestamp = int(sys.argv[2]) if len(sys.argv) > 2 else None
            print(json.dumps(getRsyncdInfo(start_timestamp), ensure_ascii=False, default=_json_default, indent=2))
        else:
            print(json.dumps({"status": False, "msg": "unknown action: " + action}, ensure_ascii=False))
    except Exception as e:
        traceback.print_exc()
        print(json.dumps({"status": False, "msg": str(e)}, ensure_ascii=False))
