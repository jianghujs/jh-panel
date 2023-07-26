# coding:utf-8

import sys
import io
import os
import re
import time
import shutil
from urllib.parse import unquote, urlparse
import dictdatabase as DDB

sys.path.append(os.getcwd() + "/class/core")
import mw


app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():

    return 'nfs-util'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getInitDFile():
    if app_debug:
        return '/tmp/' + getPluginName()
    return '/etc/init.d/' + getPluginName()


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]

    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


# https://github.com/mkrd/DictDataBase
def initDb():
    db_dir = getServerDir() + '/data/'
    if not os.path.exists(db_dir):
        mw.execShell('mkdir -p ' + db_dir)
    DDB.config.storage_directory = db_dir

def getDb(table):
    DDB.config.storage_directory = getServerDir() + '/data/'
    if not DDB.at(table).exists():
        DDB.at(table).create({})
    return DDB.at(table)

def saveOne(table, id, data):
    if type(id) is not str:
        id = str(id)
    exist = getOne(table, id)
    if exist:
        data = {'id': id, **exist, **data}
    else:
        data = {'id': id, **data}
    with getDb(table).session() as (session, db):
        db[id] = data
        session.write()

def getAll(table):
    result = getDb(table).read()
    if result:
        return list(result.values())
    return []

def getOne(table, id):
    if type(id) is not str:
        id = str(id)
    for item in getAll(table):
        if item['id'] == id:
            return item
    return None

def deleteOne(table, id):
    if type(id) is not str:
        id = str(id)
    with getDb(table).session() as (session, db):
        del db[id]
        session.write()


def status():
    return 'start'

def start():
    initDb()
    mw.restartWeb()
    return 'ok'

def stop():
    return '暂不支持'

def restart():
    return 'ok'

def reload():
    return 'ok'
    
def mountList():
    data = getAll('mount')

    # autostartStatus
    autostartStatusCmd = "cat /etc/fstab"
    autostartStatusExec = mw.execShell(autostartStatusCmd)
    for item in data:
        serverIP = item.get('serverIP', '')
        mountServerPath = item.get('mountServerPath', '')
        mountPath = item.get('mountPath', '')
        automountFindStr = '%(serverIP)s:%(mountServerPath)s %(mountPath)s nfs ' % {"serverIP": serverIP, "mountServerPath": mountServerPath, "mountPath": mountPath}
        item['autostartStatus'] = 'start' if automountFindStr in autostartStatusExec[0] else 'stop' 
    
    # status
    mountExec = mw.execShell('mount')
    for item in data:
        mountPath = item.get('mountPath', '')
        item['status'] = 'start' if mountPath in mountExec[0] else 'stop'

    # statusMap = {}
    # for item in data:
    #     path = item.get('path', '') 
    #     statusCmd = "ps -ef|grep " + path + " |grep -v grep |grep -v python | awk '{print $0}'"
    #     statusExec = mw.execShell(statusCmd)
    #     statusMap[path] = 'start' if statusExec[0] != '' else 'stop'

    # for item in data:
    #     path = item.get('path', '') 
    #     echo = item.get('echo', '')
    #     item['autostartStatus'] = autostartStatusMap[echo]
    #     item['status'] = statusMap[path]

    return mw.returnJson(True, 'ok', data)

def getNfsSharePath():
    args = getArgs()
    data = checkArgs(args, ['serverIP'])
    if not data[0]:
        return data[1]
    serverIP = args['serverIP']
    cmd = "showmount -e " + serverIP
    # 从showmount -e中获取共享目录
    data = mw.execShell(cmd)
    if data[0] == '':
        return mw.returnJson(False, '获取共享目录失败!')
    pattern = r"(/[\w/]+)\s+([\d.,]+)"
    matches = re.findall(pattern, data[0])
    result = [{"path": m[0], "whiteIPs": m[1]} for m in matches]
    return mw.returnJson(True, 'ok', result)


def mountAdd():
    args = getArgs()
    data = checkArgs(args, ['serverIP', 'mountServerPath', 'name', 'mountPath', 'remark'])
    if not data[0]:
        return data[1]
    serverIP = unquote(args['serverIP'], 'utf-8')
    mountServerPath = unquote(args['mountServerPath'], 'utf-8')
    name = unquote(args['name'], 'utf-8')
    mountPath = unquote(args['mountPath'], 'utf-8')
    remark = unquote(args['remark'], 'utf-8')

    id = int(time.time())
    saveOne('mount', id, {
        'serverIP': serverIP,
        'mountServerPath': mountServerPath,
        'name': name,
        'mountPath': mountPath,
        'remark': remark,
        'createTime': int(time.time())
    })
    return mw.returnJson(True, '添加成功!')

def mountEdit():
    args = getArgs()
    data = checkArgs(args, ['serverIP', 'mountServerPath', 'name', 'mountPath', 'remark'])
    if not data[0]:
        return data[1]
    id = args['id']
    serverIP = unquote(args['serverIP'], 'utf-8')
    mountServerPath = unquote(args['mountServerPath'], 'utf-8')
    name = unquote(args['name'], 'utf-8')
    mountPath = unquote(args['mountPath'], 'utf-8')
    remark = unquote(args['remark'], 'utf-8')
    mount = getOne('mount', id)
    if not mount:
        return mw.returnJson(False, '挂载不存在!')
    saveOne('mount', id, {
        'serverIP': serverIP,
        'mountServerPath': mountServerPath,
        'name': name,
        'mountPath': mountPath,
        'remark': remark,
    })
    
    return mw.returnJson(True, '修改成功!')

def mountDelete():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]

    id = args['id']    
    deleteOne('mount', id)
    return mw.returnJson(True, '删除成功!')

def getMountScript():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']
    mount = getOne('mount', id)
    if not mount:
        return mw.returnJson(False, '挂载不存在!')
    serverIP = mount.get('serverIP', '')
    mountServerPath = mount.get('mountServerPath', '')
    mountPath = mount.get('mountPath', '')
    cmd = ""
    if not os.path.exists(mountPath):
        cmd += 'echo "正在创建%(mountPath)s文件夹..." \n mkdir -p %(mountPath)s\n echo "创建%(mountPath)s成功✅\n"' % {"mountPath": mountPath}
    cmd += 'echo "正在挂载%(serverIP)s:%(mountServerPath)s到%(mountPath)s..." \n mount -t nfs %(serverIP)s:%(mountServerPath)s %(mountPath)s\n echo "挂载成功✅"' % ({"serverIP": serverIP, "mountServerPath": mountServerPath, "mountPath": mountPath})
    return cmd

def getUnMountScript():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']
    mount = getOne('mount', id)
    if not mount:
        return mw.returnJson(False, '挂载不存在!')
    mountPath = mount.get('mountPath', '')
    cmd = 'echo "正在卸载%(mountPath)s..." \n umount %(mountPath)s\n echo "卸载成功✅"' % ({"mountPath": mountPath})
    return cmd


def mountToggleAutostart():
    args = getArgs()
    data = checkArgs(args, ['id'])
    if not data[0]:
        return data[1]
    id = args['id']
    mount = getOne('mount', id)
    if not mount:
        return mw.returnJson(False, '挂载不存在!')

    serverIP = mount.get('serverIP', '')
    mountServerPath = mount.get('mountServerPath', '')
    mountPath = mount.get('mountPath', '')
    
    autostartStatusCmd = "cat /etc/fstab"
    autostartStatusExec = mw.execShell(autostartStatusCmd)
    automountFindStr = '%(serverIP)s:%(mountServerPath)s %(mountPath)s nfs defaults 0 0' % {"serverIP": serverIP, "mountServerPath": mountServerPath, "mountPath": mountPath}
    autostartStatus = 'start' if automountFindStr in autostartStatusExec[0] else 'stop'
    
    if autostartStatus == 'start':
        cancelAutomountCmd = "sed -i '/%(automountFindStr)s/d' /etc/fstab" % {"automountFindStr": automountFindStr.replace('/', '\\/')}
        mw.execShell(cancelAutomountCmd)
        return mw.returnJson(True, '已关闭自启动!')
    else:
        automountCmd = "echo '%(automountFindStr)s' >> /etc/fstab" % {"automountFindStr": automountFindStr}
        mw.execShell(automountCmd)
        return mw.returnJson(True, '已开启自启动!')

if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'reload':
        print(reload())
    elif func == 'restart':
        print(restart())
    elif func == 'mount_list':
        print(mountList())
    elif func == 'get_nfs_share_path':
        print(getNfsSharePath())
    elif func == 'mount_add':
        print(mountAdd())
    elif func == 'mount_edit':
        print(mountEdit())
    elif func == 'mount_delete':
        print(mountDelete())
    elif func == 'get_mount_script':
        print(getMountScript())
    elif func == 'get_unmount_script':
        print(getUnMountScript())
    elif func == 'mount_toggle_autostart':
        print(mountToggleAutostart())
    else:
        print('error')
