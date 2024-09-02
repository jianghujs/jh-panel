# coding:utf-8

# ---------------------------------------------------------------------------------
# 江湖面板
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-panel) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 核心方法库
# ---------------------------------------------------------------------------------


import os
import sys
import time
import string
import json
import hashlib
import shlex
import datetime
import subprocess
import socket
import re
import db
from random import Random
import tempfile

sys.path.append(os.getcwd() + "/class/plugin")
from retry_tool import retry


def execShell(cmdstring, cwd=None, timeout=None, shell=True, useTmpFile=False):

    if shell:
        cmdstring_list = cmdstring
    else:
        cmdstring_list = shlex.split(cmdstring)
    if timeout:
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
    
    if useTmpFile:
        with tempfile.TemporaryFile() as tempf:
            sub = subprocess.Popen(cmdstring_list, cwd=cwd, stdin=subprocess.PIPE,
                                shell=shell, bufsize=4096, stdout=tempf, stderr=subprocess.PIPE, preexec_fn=os.setsid)

            sub.wait()
            tempf.seek(0)
            data = tempf.read()
        # python3 fix 返回byte数据
        
        if isinstance(data, bytes):
            t = str(data, encoding='utf-8')
        

        return (t, '', sub.returncode)
    else:
        sub = subprocess.Popen(cmdstring_list, cwd=cwd, stdin=subprocess.PIPE,
                           shell=shell, bufsize=4096, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)

        while sub.poll() is None:
            time.sleep(0.1)
            if timeout:
                if end_time <= datetime.datetime.now():
                    raise Exception("Timeout：%s" % cmdstring)

        if sys.version_info[0] == 2:
            return sub.communicate()

        data = sub.communicate()
        # python3 fix 返回byte数据
        if isinstance(data[0], bytes):
            t1 = str(data[0], encoding='utf-8')

        if isinstance(data[1], bytes):
            t2 = str(data[1], encoding='utf-8')
        
        if sub.returncode != 0:
            t1 = t1 if t1 else t2

        return (t1, t2, sub.returncode)


def getTracebackInfo():
    import traceback
    errorMsg = traceback.format_exc()
    return errorMsg


def getRunDir():
    return os.getcwd()


def getRootDir():
    return os.path.dirname(os.path.dirname(getRunDir()))


def getPluginDir():
    return getRunDir() + '/plugins'

def getScriptDir():
    return getRunDir() + '/scripts'

def getPanelDataDir():
    return getRunDir() + '/data'

def getPanelTmp():
    return getRunDir() + '/tmp'

def getServerDir():
    return getRootDir() + '/server'

def getWebConfDir():
    return getServerDir() + '/web_conf'

def getCronDir():
    return getServerDir() + '/cron'

def getWebConfVhostDir():
    return getWebConfDir() + '/nginx/vhost'

def getWebConfSSLDir():
    return getWebConfDir() + '/ssl'

def getWebConfSSLLetsDir():
    return getWebConfDir() + '/letsencrypt'

def getLogsDir():
    return getRootDir() + '/wwwlogs'

def getWwwDir():
    file = getRunDir() + '/data/site.pl'
    if os.path.exists(file):
        return readFile(file).strip()
    return getRootDir() + '/wwwroot'


def setWwwDir(wdir):
    file = getRunDir() + '/data/site.pl'
    return writeFile(file, wdir)


def getBackupDir():
    file = getRunDir() + '/data/backup.pl'
    if os.path.exists(file):
        return readFile(file).strip()
    return getRootDir() + '/backup'
  
def getSiteSettingBackupDir():
    return getBackupDir() + '/site_setting'

def getPluginSettingBackupDir():
    return getBackupDir() + '/plugin_setting'


def setBackupDir(bdir):
    file = getRunDir() + '/data/backup.pl'
    return writeFile(file, bdir)


def getAcmeDir():
    acme = '/root/.acme.sh'
    if isAppleSystem():
        cmd = "who | sed -n '2, 1p' |awk '{print $1}'"
        user = execShell(cmd)[0].strip()
        acme = '/Users/' + user + '/.acme.sh'
    if not os.path.exists(acme):
        acme = '/.acme.sh'
    return acme


def triggerTask():
    isTask = getRunDir() + '/tmp/panelTask.pl'
    writeFile(isTask, 'True')

def addAndTriggerTask(
    name = '', 
    execstr = '',
    type = 'execshell', 
    status = '0', 
    addtime =  time.strftime('%Y-%m-%d %H:%M:%S')
):
    taskAdd = (name, type, status, addtime, execstr)
    M('tasks').add('name,type,status,addtime, execstr', taskAdd)
    triggerTask()


def systemdCfgDir():
    # ubuntu
    cfg_dir = '/lib/systemd/system'
    if os.path.exists(cfg_dir):
        return cfg_dir

    # debian,centos
    cfg_dir = '/usr/lib/systemd/system'
    if os.path.exists(cfg_dir):
        return cfg_dir

    # local test
    return "/tmp"


def getSslCrt():
    if os.path.exists('/etc/ssl/certs/ca-certificates.crt'):
        return '/etc/ssl/certs/ca-certificates.crt'
    if os.path.exists('/etc/pki/tls/certs/ca-bundle.crt'):
        return '/etc/pki/tls/certs/ca-bundle.crt'
    return ''


def getOs():
    return sys.platform


def getOsName():
    cmd = "cat /etc/*-release | grep PRETTY_NAME |awk -F = '{print $2}' | awk -F '\"' '{print $2}'| awk '{print $1}'"
    data = execShell(cmd)
    return data[0].strip().lower()


def getOsID():
    cmd = "cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F '\"' '{print $2}'"
    data = execShell(cmd)
    return data[0].strip()


def getFileSuffix(file):
    tmp = file.split('.')
    ext = tmp[len(tmp) - 1]
    return ext

def getDirSize(start_path='.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

def isAppleSystem():
    if getOs() == 'darwin':
        return True
    return False


def isDebugMode():
    if isAppleSystem():
        return True

    debugPath = getRunDir() + "/data/debug.pl"
    if os.path.exists(debugPath):
        return True

    return False


def isNumber(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


def deleteFile(file):
    if os.path.exists(file):
        os.remove(file)


def isInstalledWeb():
    path = getServerDir() + '/openresty/nginx/sbin/nginx'
    if os.path.exists(path):
        return True
    return False


# ------------------------------ openresty start -----------------------------
def restartWeb():
    return opWeb("reload")


def opWeb(method):
    if not isInstalledWeb():
        return False

    # systemd
    systemd = '/lib/systemd/system/openresty.service'
    if os.path.exists(systemd):
        execShell('systemctl ' + method + ' openresty')
        return True

    # initd
    initd = getServerDir() + '/openresty/init.d/openresty'

    if os.path.exists(initd):
        execShell(initd + ' ' + method)
        return True

    return False


def opLuaMake(cmd_name):
    path = getServerDir() + '/web_conf/nginx/lua/lua.conf'
    root_dir = getServerDir() + '/web_conf/nginx/lua/' + cmd_name
    dst_path = getServerDir() + '/web_conf/nginx/lua/' + cmd_name + '.lua'
    def_path = getServerDir() + '/web_conf/nginx/lua/empty.lua'

    if not os.path.exists(root_dir):
        execShell('mkdir -p ' + root_dir)

    files = []
    for fl in os.listdir(root_dir):
        suffix = getFileSuffix(fl)
        if suffix != 'lua':
            continue
        flpath = os.path.join(root_dir, fl)
        files.append(flpath)

    if len(files) > 0:
        def_path = dst_path
        content = ''
        for f in files:
            t = readFile(f)
            f_base = os.path.basename(f)
            content += '-- ' + '*' * 20 + ' ' + f_base + ' start ' + '*' * 20 + "\n"
            content += t
            content += "\n" + '-- ' + '*' * 20 + ' ' + f_base + ' end ' + '*' * 20 + "\n"
        writeFile(dst_path, content)
    else:
        if os.path.exists(dst_path):
            os.remove(dst_path)

    conf = readFile(path)
    conf = re.sub(cmd_name + ' (.*);',
                  cmd_name + " " + def_path + ";", conf)
    writeFile(path, conf)


def opLuaInitFile():
    opLuaMake('init_by_lua_file')


def opLuaInitWorkerFile():
    opLuaMake('init_worker_by_lua_file')


def opLuaInitAccessFile():
    opLuaMake('access_by_lua_file')


def opLuaMakeAll():
    opLuaInitFile()
    opLuaInitWorkerFile()
    opLuaInitAccessFile()

# ------------------------------ openresty end -----------------------------


def restartMw(restartAll=False):
    import system_api
    system_api.system_api().restartMw(restartAll)


def checkWebConfig():
    op_dir = getServerDir() + '/openresty/nginx'
    cmd = "ulimit -n 10240 && " + op_dir + \
        "/sbin/nginx -t -c " + op_dir + "/conf/nginx.conf"
    result = execShell(cmd)
    searchStr = 'test is successful'
    if result[1].find(searchStr) == -1:
        msg = getInfo('配置文件错误: {1}', (result[1],))
        writeLog("软件管理", msg)
        return result[1]
    return True


def M(table):
    sql = db.Sql()
    return sql.table(table)


def getPage(args, result='1,2,3,4,5,8'):
    data = getPageObject(args, result)
    return data[0]


def getPageObject(args, result='1,2,3,4,5,8'):
    # 取分页
    import page
    # 实例化分页类
    page = page.Page()
    info = {}

    info['count'] = 0
    if 'count' in args:
        info['count'] = int(args['count'])

    info['row'] = 10
    if 'row' in args:
        info['row'] = int(args['row'])

    info['p'] = 1
    if 'p' in args:
        info['p'] = int(args['p'])
    info['uri'] = {}
    info['return_js'] = ''
    if 'tojs' in args:
        info['return_js'] = args['tojs']

    return (page.GetPage(info, result), page)


def md5(content):
    # 生成MD5
    try:
        m = hashlib.md5()
        m.update(content.encode("utf-8"))
        return m.hexdigest()
    except Exception as ex:
        return False


def getFileMd5(filename):
    # 文件的MD5值
    if not os.path.isfile(filename):
        return False

    myhash = hashlib.md5()
    f = file(filename, 'rb')
    while True:
        b = f.read(8096)
        if not b:
            break
        myhash.update(b)
    f.close()
    return myhash.hexdigest()


def getRandomString(length):
    # 取随机字符串
    str = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    chrlen = len(chars) - 1
    random = Random()
    for i in range(length):
        str += chars[random.randint(0, chrlen)]
    return str


def getUniqueId():
    """
    根据时间生成唯一ID
    :return:
    """
    current_time = datetime.datetime.now()
    str_time = current_time.strftime('%Y%m%d%H%M%S%f')[:-3]
    unique_id = "{0}".format(str_time)
    return unique_id


def getJson(data):
    import json
    return json.dumps(data)


def returnData(status, msg, data=None):
    return {'status': status, 'msg': msg, 'data': data}


def returnJson(status, msg, data=None):
    # if data == None:
    #     return {'status': status, 'msg': msg}
    # return {'status': status, 'msg': msg, 'data': data}
    if data == None:
        return getJson({'status': status, 'msg': msg})
    return getJson({'status': status, 'msg': msg, 'data': data})


def getLanguage():
    path = 'data/language.pl'
    if not os.path.exists(path):
        return 'Simplified_Chinese'
    return readFile(path).strip()


def getStaticJson(name="public"):
    file = 'static/language/' + getLanguage() + '/' + name + '.json'
    if not os.path.exists(file):
        file = 'route/static/language/' + getLanguage() + '/' + name + '.json'
    return file


def returnMsg(status, msg, args=()):
    # 取通用字曲返回
    pjson = getStaticJson('public')
    logMessage = json.loads(readFile(pjson))
    keys = logMessage.keys()

    if msg in keys:
        msg = logMessage[msg]
        for i in range(len(args)):
            rep = '{' + str(i + 1) + '}'
            msg = msg.replace(rep, args[i])
    return {'status': status, 'msg': msg, 'data': args}


def getInfo(msg, args=()):
    # 取提示消息
    for i in range(len(args)):
        rep = '{' + str(i + 1) + '}'
        msg = msg.replace(rep, args[i])
    return msg


def getMsg(key, args=()):
    # 取提示消息
    try:
        pjson = getStaticJson('public')
        logMessage = json.loads(pjson)
        keys = logMessage.keys()
        msg = None
        if key in keys:
            msg = logMessage[key]
            for i in range(len(args)):
                rep = '{' + str(i + 1) + '}'
                msg = msg.replace(rep, args[i])
        return msg
    except:
        return key


def getLan(key):
    # 取提示消息
    pjson = getStaticJson('public')
    logMessage = json.loads(pjson)
    keys = logMessage.keys()
    msg = None
    if key in keys:
        msg = logMessage[key]
    return msg


def readFile(filename):
    # 读文件内容
    try:
        fp = open(filename, 'r')
        fBody = fp.read()
        fp.close()
        return fBody
    except Exception as e:
        # print(e)
        return False


def getDate():
    # 取格式时间
    import time
    return time.strftime('%Y-%m-%d %X', time.localtime())

def getDateFromNow(tf_format="%Y-%m-%d %H:%M:%S", time_zone="Asia/Shanghai"):
    # 取格式时间
    import time
    os.environ['TZ'] = time_zone
    time.tzset()
    return time.strftime(tf_format, time.localtime())

def getDataFromInt(val):
    time_format = '%Y-%m-%d %H:%M:%S'
    time_str = time.localtime(val)
    return time.strftime(time_format, time_str)

def writeLog(stype, msg, args=()):
    # 写日志
    try:
        import time
        import db
        import json
        from flask import session
        uid = 1
        if 'uid' in session:
            uid = session['uid']
        sql = db.Sql()
        mdate = time.strftime('%Y-%m-%d %X', time.localtime())
        wmsg = getInfo(msg, args)
        data = (stype, wmsg, uid, mdate)
        result = sql.table('logs').add('type,log,uid,addtime', data)
        return True
    except Exception as e:
        return False


def writeFileLog(msg, path=None, limit_size=50 * 1024 * 1024, save_limit=3):
    log_file = getServerDir() + '/jh-panel/logs/debug.log'
    if path != None:
        log_file = path

    if os.path.exists(log_file):
        size = os.path.getsize(log_file)
        if size > limit_size:
            log_file_rename = log_file + "_" + \
                time.strftime("%Y-%m-%d_%H%M%S") + '.log'
            os.rename(log_file, log_file_rename)
            logs = sorted(glob.glob(log_file + "_*"))
            count = len(logs)
            save_limit = count - save_limit
            for i in range(count):
                if i > save_limit:
                    break
                os.remove(logs[i])
                # print('|---多余日志[' + logs[i] + ']已删除!')

    f = open(log_file, 'ab+')
    msg += "\n"
    if __name__ == '__main__':
        print(msg)
    f.write(msg.encode('utf-8'))
    f.close()
    return True


def writeDbLog(stype, msg, args=(), uid=1):
    try:
        import time
        import db
        import json
        sql = db.Sql()
        mdate = time.strftime('%Y-%m-%d %X', time.localtime())
        wmsg = getInfo(msg, args)
        data = (stype, wmsg, uid, mdate)
        result = sql.table('logs').add('type,log,uid,addtime', data)
        return True
    except Exception as e:
        return False

def writeFile(filename, content, mode='w+'):
    # 写文件内容
    try:
        fp = open(filename, mode)
        fp.write(content)
        fp.close()
        return True
    except Exception as e:
        return False


def backFile(file, act=None):
    """
        @name 备份配置文件
        @param file 需要备份的文件
        @param act 如果存在，则备份一份作为默认配置
    """
    file_type = "_bak"
    if act:
        file_type = "_def"

    # print("cp -p {0} {1}".format(file, file + file_type))
    execShell("cp -p {0} {1}".format(file, file + file_type))


def restoreFile(file, act=None):
    """
        @name 还原配置文件
        @param file 需要还原的文件
        @param act 如果存在，则还原默认配置
    """
    file_type = "_bak"
    if act:
        file_type = "_def"
    execShell("cp -p {1} {0}".format(file, file + file_type))


def enPunycode(domain):
    if sys.version_info[0] == 2:
        domain = domain.encode('utf8')
    tmp = domain.split('.')
    newdomain = ''
    for dkey in tmp:
        if dkey == '*':
            continue
        # 匹配非ascii字符
        match = re.search(u"[\x80-\xff]+", dkey)
        if not match:
            match = re.search(u"[\u4e00-\u9fa5]+", dkey)
        if not match:
            newdomain += dkey + '.'
        else:
            if sys.version_info[0] == 2:
                newdomain += 'xn--' + \
                    dkey.decode('utf-8').encode('punycode') + '.'
            else:
                newdomain += 'xn--' + \
                    dkey.encode('punycode').decode('utf-8') + '.'
    if tmp[0] == '*':
        newdomain = "*." + newdomain
    return newdomain[0:-1]


def dePunycode(domain):
    # punycode 转中文
    tmp = domain.split('.')
    newdomain = ''
    for dkey in tmp:
        if dkey.find('xn--') >= 0:
            newdomain += dkey.replace('xn--',
                                      '').encode('utf-8').decode('punycode') + '.'
        else:
            newdomain += dkey + '.'
    return newdomain[0:-1]


def enCrypt(key, strings):
    # 加密字符串
    try:
        if type(strings) != bytes:
            strings = strings.encode('utf-8')
        from cryptography.fernet import Fernet
        f = Fernet(key)
        result = f.encrypt(strings)
        return result.decode('utf-8')
    except:
        # print(get_error_info())
        return strings


def deCrypt(key, strings):
    # 解密字符串
    try:
        if type(strings) != bytes:
            strings = strings.decode('utf-8')
        from cryptography.fernet import Fernet
        f = Fernet(key)
        result = f.decrypt(strings).decode('utf-8')
        return result
    except:
        # print(get_error_info())
        return strings


def enDoubleCrypt(key, strings):
    # 加密字符串
    try:
        import base64
        _key = md5(key).encode('utf-8')
        _key = base64.urlsafe_b64encode(_key)

        if type(strings) != bytes:
            strings = strings.encode('utf-8')
        import cryptography
        from cryptography.fernet import Fernet
        f = Fernet(_key)
        result = f.encrypt(strings)
        return result.decode('utf-8')
    except:
        writeFileLog(getTracebackInfo())
        return strings


def deDoubleCrypt(key, strings):
    # 解密字符串
    try:
        import base64
        _key = md5(key).encode('utf-8')
        _key = base64.urlsafe_b64encode(_key)

        if type(strings) != bytes:
            strings = strings.encode('utf-8')
        from cryptography.fernet import Fernet
        f = Fernet(_key)
        result = f.decrypt(strings).decode('utf-8')
        return result
    except:
        writeFileLog(getTracebackInfo())
        return strings


def aesEncrypt(data, key='ABCDEFGHIJKLMNOP', vi='0102030405060708'):
    # aes加密
    # @param data 被加密的数据
    # @param key 加解密密匙 16位
    # @param vi 16位

    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    if not isinstance(data, bytes):
        data = data.encode()

    # AES_CBC_KEY = os.urandom(32)
    # AES_CBC_IV = os.urandom(16)

    AES_CBC_KEY = key.encode()
    AES_CBC_IV = vi.encode()

    # print("AES_CBC_KEY:", AES_CBC_KEY)
    # print("AES_CBC_IV:", AES_CBC_IV)

    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data) + padder.finalize()

    cipher = Cipher(algorithms.AES(AES_CBC_KEY),
                    modes.CBC(AES_CBC_IV),
                    backend=default_backend())
    encryptor = cipher.encryptor()

    edata = encryptor.update(padded_data)

    # print(edata)
    # print(str(edata))
    # print(edata.decode())
    return edata


def aesDecrypt(data, key='ABCDEFGHIJKLMNOP', vi='0102030405060708'):
    # aes加密
    # @param data 被解密的数据
    # @param key 加解密密匙 16位
    # @param vi 16位

    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    if not isinstance(data, bytes):
        data = data.encode()

    AES_CBC_KEY = key.encode()
    AES_CBC_IV = vi.encode()

    cipher = Cipher(algorithms.AES(AES_CBC_KEY),
                    modes.CBC(AES_CBC_IV),
                    backend=default_backend())
    decryptor = cipher.decryptor()

    ddata = decryptor.update(data)

    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    data = unpadder.update(ddata)

    try:
        uppadded_data = data + unpadder.finalize()
    except ValueError:
        raise Exception('无效的加密信息!')

    return uppadded_data


def aesEncrypt_Crypto(data, key, vi):
    # 该方法保留，暂时不使用
    # aes加密
    # @param data 被加密的数据
    # @param key 加解密密匙 16位
    # @param vi 16位

    from Crypto.Cipher import AES
    cryptor = AES.new(key.encode('utf8'), AES.MODE_CBC, vi.encode('utf8'))
    # 判断是否含有中文
    zhmodel = re.compile(u'[\u4e00-\u9fff]')
    match = zhmodel.search(data)
    if match == None:
        # 无中文时
        add = 16 - len(data) % 16
        pad = lambda s: s + add * chr(add)
        data = pad(data)
        enctext = cryptor.encrypt(data.encode('utf8'))
    else:
        # 含有中文时
        data = data.encode()
        add = 16 - len(data) % 16
        data = data + add * (chr(add)).encode()
        enctext = cryptor.encrypt(data)
    encodestrs = base64.b64encode(enctext).decode('utf8')
    return encodestrs


def aesDecrypt_Crypto(data, key, vi):
    # 该方法保留，暂时不使用
    # aes加密
    # @param data 被加密的数据
    # @param key 加解密密匙 16位
    # @param vi 16位

    from crypto.Cipher import AES
    data = data.encode('utf8')
    encodebytes = base64.urlsafe_b64decode(data)
    cipher = AES.new(key.encode('utf8'), AES.MODE_CBC, vi.encode('utf8'))
    text_decrypted = cipher.decrypt(encodebytes)
    # 判断是否含有中文
    zhmodel = re.compile(u'[\u4e00-\u9fff]')
    match = zhmodel.search(text_decrypted)
    if match == False:
        # 无中文时补位
        unpad = lambda s: s[0:-s[-1]]
        text_decrypted = unpad(text_decrypted)
    text_decrypted = text_decrypted.decode('utf8').rstrip()  # 去掉补位的右侧空格
    return text_decrypted

def buildSoftLink(src, dst, force=False):
    '''
    建立软连接
    '''
    if not os.path.exists(src):
        return False

    if os.path.exists(dst) and force:
        os.remove(dst)

    if not os.path.exists(dst):
        execShell('ln -sf "' + src + '" "' + dst + '"')
        return True
    return False


def HttpGet(url, timeout=10):
    """
    发送GET请求
    @url 被请求的URL地址(必需)
    @timeout 超时时间默认60秒
    return string
    """
    if sys.version_info[0] == 2:
        try:
            import urllib2
            import ssl
            if sys.version_info[0] == 2:
                reload(urllib2)
                reload(ssl)
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except:
                pass
            response = urllib2.urlopen(url, timeout=timeout)
            return response.read()
        except Exception as ex:
            return str(ex)
    else:
        try:
            import urllib.request
            import ssl
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except:
                pass
            response = urllib.request.urlopen(url, timeout=timeout)
            result = response.read()
            if type(result) == bytes:
                result = result.decode('utf-8')
            return result
        except Exception as ex:
            return str(ex)


def HttpGet2(url, timeout):
    import urllib.request

    try:
        import ssl
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass
        req = urllib.request.urlopen(url, timeout=timeout)
        result = req.read().decode('utf-8')
        return result

    except Exception as e:
        return str(e)


def httpGet(url, timeout=10):
    return HttpGet2(url, timeout)


def HttpPost(url, data, timeout=10):
    """
    发送POST请求
    @url 被请求的URL地址(必需)
    @data POST参数，可以是字符串或字典(必需)
    @timeout 超时时间默认60秒
    return string
    """
    if sys.version_info[0] == 2:
        try:
            import urllib
            import urllib2
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            data = urllib.urlencode(data)
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=timeout)
            return response.read()
        except Exception as ex:
            return str(ex)
    else:
        try:
            import urllib.request
            import ssl
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except:
                pass
            data = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data)
            response = urllib.request.urlopen(req, timeout=timeout)
            result = response.read()
            if type(result) == bytes:
                result = result.decode('utf-8')
            return result
        except Exception as ex:
            return str(ex)


def httpPost(url, data, timeout=10):
    return HttpPost(url, data, timeout)


def writeSpeed(title, used, total, speed=0):
    # 写进度
    if not title:
        data = {'title': None, 'progress': 0,
                'total': 0, 'used': 0, 'speed': 0}
    else:
        progress = int((100.0 * used / total))
        data = {'title': title, 'progress': progress,
                'total': total, 'used': used, 'speed': speed}
    writeFile('/tmp/panelSpeed.pl', json.dumps(data))
    return True


def getSpeed():
    # 取进度
    path = getRootDir()
    data = readFile(path + '/tmp/panelSpeed.pl')
    if not data:
        data = json.dumps({'title': None, 'progress': 0,
                           'total': 0, 'used': 0, 'speed': 0})
        writeFile(path + '/tmp/panelSpeed.pl', data)
    return json.loads(data)


def getLastLineBk(inputfile, lineNum):
    # 读文件指定倒数行数
    try:
        fp = open(inputfile, 'rb')
        lastLine = ""
        lines = fp.readlines()
        count = len(lines)
        if count > lineNum:
            num = lineNum
        else:
            num = count
        i = 1
        lastre = []
        for i in range(1, (num + 1)):
            n = -i
            try:
                lastLine = lines[n].decode("utf-8", "ignore").strip()
            except Exception as e:
                lastLine = ""
            lastre.append(lastLine)

        fp.close()
        result = ''
        num -= 1
        while num >= 0:
            result += lastre[num] + "\n"
            num -= 1
        return result
    except Exception as e:
        return str(e)
        # return getMsg('TASK_SLEEP')


def getLastLine(path, num, p=1):
    pyVersion = sys.version_info[0]
    try:
        import html
        if not os.path.exists(path):
            return ""
        start_line = (p - 1) * num
        count = start_line + num
        fp = open(path, 'rb')
        buf = ""

        fp.seek(0, 2)
        if fp.read(1) == "\n":
            fp.seek(0, 2)
        data = []
        b = True
        n = 0

        for i in range(count):
            while True:
                newline_pos = str.rfind(str(buf), "\n")
                pos = fp.tell()
                if newline_pos != -1:
                    if n >= start_line:
                        line = buf[newline_pos + 1:]
                        try:
                            data.insert(0, html.escape(line))
                        except Exception as e:
                            pass
                    buf = buf[:newline_pos]
                    n += 1
                    break
                else:
                    if pos == 0:
                        b = False
                        break
                    to_read = min(4096, pos)
                    fp.seek(-to_read, 1)
                    t_buf = fp.read(to_read)
                    if pyVersion == 3:
                        if type(t_buf) == bytes:
                            t_buf = t_buf.decode("utf-8", "ignore").strip()
                    buf = t_buf + buf
                    fp.seek(-to_read, 1)
                    if pos - to_read == 0:
                        buf = "\n" + buf
            if not b:
                break
        fp.close()
    except Exception as e:
        return str(e)

    return "\n".join(data)


def downloadFile(url, filename):
    import urllib
    urllib.urlretrieve(url, filename=filename, reporthook=downloadHook)


def downloadHook(count, blockSize, totalSize):
    speed = {'total': totalSize, 'block': blockSize, 'count': count}
    print('%02d%%' % (100.0 * count * blockSize / totalSize))

def getLocalIp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    local_ip = None
    try:
        # The IP address isn't really important here, we just need to select a valid IP address
        # to allow the socket to be bound correctly
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
    finally:
        sock.close()
    return local_ip

def setHostAddr(addr):
    file = getRunDir() + '/data/iplist.txt'
    return writeFile(file, addr)


def getHostPort():
    if os.path.exists('data/port.pl'):
        return readFile('data/port.pl').strip()
    return '7200'


def setHostPort(port):
    file = getRunDir() + '/data/port.pl'
    return writeFile(file, port)

def getLocalIpBack():
    # 取本地外网IP
    try:
        import re
        filename = 'data/iplist.txt'
        ipaddress = readFile(filename)
        if not ipaddress or ipaddress == '127.0.0.1':
            import urllib
            url = 'http://pv.sohu.com/cityjson?ie=utf-8'
            req = urllib.request.urlopen(url, timeout=10)
            content = req.read().decode('utf-8')
            ipaddress = re.search('\d+.\d+.\d+.\d+', content).group(0)
            writeFile(filename, ipaddress)

        ipaddress = re.search('\d+.\d+.\d+.\d+', ipaddress).group(0)
        return ipaddress
    except Exception as ex:
        # print(ex)
        return '127.0.0.1'


def getClientIp():
    from flask import request
    return request.remote_addr.replace('::ffff:', '')


def initPanelIp():
    filename = 'data/iplist.txt'
    ipaddress = readFile(filename)
    if not ipaddress or ipaddress == '127.0.0.1':
        result = getLocalIp()
        setHostAddr(result)
        return result
    return ipaddress

def inArray(arrays, searchStr):
    # 搜索数据中是否存在
    for key in arrays:
        if key == searchStr:
            return True

    return False


def formatDate(format="%Y-%m-%d %H:%M:%S", times=None):
    # 格式化指定时间戳
    if not times:
        times = int(time.time())
    time_local = time.localtime(times)
    return time.strftime(format, time_local)


def checkIp(ip):
    # 检查是否为IPv4地址
    import re
    p = re.compile(
        '^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if p.match(ip):
        return True
    else:
        return False


def getHost(port=False):
    from flask import request
    host_tmp = request.headers.get('host')
    if not host_tmp:
        if request.url_root:
            tmp = re.findall(r"(https|http)://([\w:\.-]+)", request.url_root)
            if tmp:
                host_tmp = tmp[0][1]
    if not host_tmp:
        host_tmp = getLocalIp() + ':' + readFile('data/port.pl').strip()
    try:
        if host_tmp.find(':') == -1:
            host_tmp += ':80'
    except:
        host_tmp = "127.0.0.1:8888"
    h = host_tmp.split(':')
    if port:
        return h[-1]
    return ':'.join(h[0:-1])


def getClientIp():
    from flask import request
    return request.remote_addr.replace('::ffff:', '')


def checkDomainPanel():
    tmp = getHost()
    domain = readFile('data/bind_domain.pl')
    port = readFile('data/port.pl').strip()

    npid = getServerDir() + "/openresty/nginx/logs/nginx.pid"
    if not os.path.exists(npid):
        return False

    nconf = getServerDir() + "/web_conf/nginx/vhost/panel.conf"
    if os.path.exists(nconf):
        port = "80"

    if domain:
        client_ip = getClientIp()
        if client_ip in ['127.0.0.1', 'localhost', '::1']:
            return False
        if tmp.strip().lower() != domain.strip().lower():
            from flask import Flask, redirect, request, url_for
            to = "http://" + domain + ":" + str(port)
            return redirect(to, code=302)
    return False


def createLinuxUser(user, group):
    execShell("groupadd {}".format(group))
    execShell('useradd -s /sbin/nologin -g {} {}'.format(user, group))
    return True


def setOwn(filename, user, group=None):
    if isAppleSystem():
        return True

    # 设置用户组
    if not os.path.exists(filename):
        return False
    from pwd import getpwnam
    try:
        user_info = getpwnam(user)
        user = user_info.pw_uid
        if group:
            user_info = getpwnam(group)
        group = user_info.pw_gid
    except:
        if user == 'www':
            createLinuxUser(user)
        # 如果指定用户或组不存在，则使用www
        try:
            user_info = getpwnam('www')
        except:
            createLinuxUser(user)
            user_info = getpwnam('www')
        user = user_info.pw_uid
        group = user_info.pw_gid
    os.chown(filename, user, group)
    return True


def checkPort(port):
    # 检查端口是否合法
    ports = ['21', '443', '888']
    if port in ports:
        return False
    intport = int(port)
    if intport < 1 or intport > 65535:
        return False
    return True


def getStrBetween(startStr, endStr, srcStr):
    # 字符串取中间
    start = srcStr.find(startStr)
    if start == -1:
        return None
    end = srcStr.find(endStr)
    if end == -1:
        return None
    return srcStr[start + 1:end]


def getCpuType():
    cpuType = ''
    if isAppleSystem():
        cmd = "system_profiler SPHardwareDataType | grep 'Processor Name' | awk -F ':' '{print $2}'"
        cpuinfo = execShell(cmd)
        return cpuinfo[0].strip()

    # 取CPU类型
    cpuinfo = open('/proc/cpuinfo', 'r').read()
    rep = "model\s+name\s+:\s+(.+)"
    tmp = re.search(rep, cpuinfo, re.I)
    if tmp:
        cpuType = tmp.groups()[0]
    else:
        cpuinfo = execShell('LANG="en_US.UTF-8" && lscpu')[0]
        rep = "Model\s+name:\s+(.+)"
        tmp = re.search(rep, cpuinfo, re.I)
        if tmp:
            cpuType = tmp.groups()[0]
    return cpuType


def isRestart():
    # 检查是否允许重启
    num = M('tasks').where('status!=?', ('1',)).count()
    if num > 0:
        return False
    return True


def isUpdateLocalSoft():
    num = M('tasks').where('status!=?', ('1',)).count()
    if os.path.exists('jh-panel.zip'):
        return True

    if num > 0:
        data = M('tasks').where('status!=?', ('1',)).field(
            'id,type,execstr').limit('1').select()
        argv = data[0]['execstr'].split('|dl|')
        if data[0]['type'] == 'download' and argv[1] == 'jh-panel.zip':
            return True

    return False


def hasPwd(password):
    # 加密密码字符
    import crypt
    return crypt.crypt(password, password)


def getTimeout(url):
    start = time.time()
    result = httpGet(url)
    if result != 'True':
        return False
    return int((time.time() - start) * 1000)


def makeConf():
    file = getRunDir() + '/data/json/config.json'
    if not os.path.exists(file):
        c = {}
        c['title'] = '江湖面板'
        c['home'] = 'http://github/jianghujs/jh-panel'
        c['recycle_bin'] = True
        c['template'] = 'default'
        writeFile(file, json.dumps(c))
        return c
    c = readFile(file)
    return json.loads(c)


def getConfig(k):
    c = makeConf()
    return c[k]


def setConfig(k, v):
    c = makeConf()
    c[k] = v
    file = getRunDir() + '/data/json/config.json'
    return writeFile(file, json.dumps(c))


def getHostAddr():
    if os.path.exists('data/iplist.txt'):
        return readFile('data/iplist.txt').strip()
    return '127.0.0.1'

def getServerIp(version = 4):
    ip = execShell(
        "curl -{} -sS --connect-timeout 5 -m 60 https://api.ipify.org/?format=text".format(version))
    return ip[0] if ip[2] == 0 else ""

def auth_decode(data):
    # 解密数据
    token = GetToken()
    # 是否有生成Token
    if not token:
        return returnMsg(False, 'REQUEST_ERR')

    # 校验access_key是否正确
    if token['access_key'] != data['btauth_key']:
        return returnMsg(False, 'REQUEST_ERR')

    # 解码数据
    import binascii
    import hashlib
    import urllib
    import hmac
    import json
    tdata = binascii.unhexlify(data['data'])

    # 校验signature是否正确
    signature = binascii.hexlify(
        hmac.new(token['secret_key'], tdata, digestmod=hashlib.sha256).digest())
    if signature != data['signature']:
        return returnMsg(False, 'REQUEST_ERR')

    # 返回
    return json.loads(urllib.unquote(tdata))


# 数据加密
def auth_encode(data):
    token = GetToken()
    pdata = {}

    # 是否有生成Token
    if not token:
        return returnMsg(False, 'REQUEST_ERR')

    # 生成signature
    import binascii
    import hashlib
    import urllib
    import hmac
    import json
    tdata = urllib.quote(json.dumps(data))
    # 公式  hex(hmac_sha256(data))
    pdata['signature'] = binascii.hexlify(
        hmac.new(token['secret_key'], tdata, digestmod=hashlib.sha256).digest())

    # 加密数据
    pdata['btauth_key'] = token['access_key']
    pdata['data'] = binascii.hexlify(tdata)
    pdata['timestamp'] = time.time()

    # 返回
    return pdata


def checkToken(get):
    # 检查Token
    tempFile = 'data/tempToken.json'
    if not os.path.exists(tempFile):
        return False
    import json
    import time
    tempToken = json.loads(readFile(tempFile))
    if time.time() > tempToken['timeout']:
        return False
    if get.token != tempToken['token']:
        return False
    return True


def checkInput(data):
    # 过滤输入
    if not data:
        return data
    if type(data) != str:
        return data
    checkList = [
        {'d': '<', 'r': '＜'},
        {'d': '>', 'r': '＞'},
        {'d': '\'', 'r': '‘'},
        {'d': '"', 'r': '“'},
        {'d': '&', 'r': '＆'},
        {'d': '#', 'r': '＃'},
        {'d': '<', 'r': '＜'}
    ]
    for v in checkList:
        data = data.replace(v['d'], v['r'])
    return data


def checkCert(certPath='ssl/certificate.pem'):
    # 验证证书
    openssl = '/usr/local/openssl/bin/openssl'
    if not os.path.exists(openssl):
        openssl = 'openssl'
    certPem = readFile(certPath)
    s = "\n-----BEGIN CERTIFICATE-----"
    tmp = certPem.strip().split(s)
    for tmp1 in tmp:
        if tmp1.find('-----BEGIN CERTIFICATE-----') == -1:
            tmp1 = s + tmp1
        writeFile(certPath, tmp1)
        result = execShell(openssl + " x509 -in " +
                           certPath + " -noout -subject")
        if result[1].find('-bash:') != -1:
            return True
        if len(result[1]) > 2:
            return False
        if result[0].find('error:') != -1:
            return False
    return True


def getPathSize(path):
    # 取文件或目录大小
    if not os.path.exists(path):
        return 0
    if not os.path.isdir(path):
        return os.path.getsize(path)
    size_total = 0
    for nf in os.walk(path):
        for f in nf[2]:
            filename = nf[0] + '/' + f
            size_total += os.path.getsize(filename)
    return size_total

# 字节数转大小文本
def toSize(size):
    # 字节单位转换
    d = ('b', 'KB', 'MB', 'GB', 'TB')
    s = d[0]
    for b in d:
        if size < 1024:
            return str(round(size, 2)) + ' ' + b
        size = float(size) / 1024.0
        s = b
    return str(round(size, 2)) + ' ' + b

# 时间戳转时间文本
def toTime(timestamp, format='%Y-%m-%d %H:%M:%S'):
    t = time.localtime(timestamp)
    t = time.strftime(format, t)
    return t

def getMacAddress():
    # 获取mac
    import uuid
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[e:e + 2] for e in range(0, 11, 2)])


def get_string(t):
    if t != -1:
        max = 126
        m_types = [{'m': 122, 'n': 97}, {'m': 90, 'n': 65}, {'m': 57, 'n': 48}, {
            'm': 47, 'n': 32}, {'m': 64, 'n': 58}, {'m': 96, 'n': 91}, {'m': 125, 'n': 123}]
    else:
        max = 256
        t = 0
        m_types = [{'m': 255, 'n': 0}]
    arr = []
    for i in range(max):
        if i < m_types[t]['n'] or i > m_types[t]['m']:
            continue
        arr.append(chr(i))
    return arr


def get_string_find(t):
    if type(t) != list:
        t = [t]
    return_str = ''
    for s1 in t:
        return_str += get_string(int(s1[0]))[int(s1[1:])]
    return return_str


def get_string_arr(t):
    s_arr = {}
    t_arr = []
    for s1 in t:
        for i in range(6):
            if not i in s_arr:
                s_arr[i] = get_string(i)
            for j in range(len(s_arr[i])):
                if s1 == s_arr[i][j]:
                    t_arr.append(str(i) + str(j))
    return t_arr

 # 转换时间


def strfDate(sdate):
    return time.strftime('%Y-%m-%d', time.strptime(sdate, '%Y%m%d%H%M%S'))


# 获取证书名称
def getCertName(certPath):
    if not os.path.exists(certPath):
        return None
    try:
        import OpenSSL
        result = {}
        x509 = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_PEM, readFile(certPath))
        # 取产品名称
        issuer = x509.get_issuer()
        result['issuer'] = ''
        if hasattr(issuer, 'CN'):
            result['issuer'] = issuer.CN
        if not result['issuer']:
            is_key = [b'0', '0']
            issue_comp = issuer.get_components()
            if len(issue_comp) == 1:
                is_key = [b'CN', 'CN']
            for iss in issue_comp:
                if iss[0] in is_key:
                    result['issuer'] = iss[1].decode()
                    break
        if not result['issuer']:
            if hasattr(issuer, 'O'):
                result['issuer'] = issuer.O
        # 取到期时间
        result['notAfter'] = strfDate(
            bytes.decode(x509.get_notAfter())[:-1])
        # 取申请时间
        result['notBefore'] = strfDate(
            bytes.decode(x509.get_notBefore())[:-1])
        # 取可选名称
        result['dns'] = []
        for i in range(x509.get_extension_count()):
            s_name = x509.get_extension(i)
            if s_name.get_short_name() in [b'subjectAltName', 'subjectAltName']:
                s_dns = str(s_name).split(',')
                for d in s_dns:
                    result['dns'].append(d.split(':')[1])
        subject = x509.get_subject().get_components()
        # 取主要认证名称
        if len(subject) == 1:
            result['subject'] = subject[0][1].decode()
        else:
            if not result['dns']:
                for sub in subject:
                    if sub[0] == b'CN':
                        result['subject'] = sub[1].decode()
                        break
                if 'subject' in result:
                    result['dns'].append(result['subject'])
            else:
                result['subject'] = result['dns'][0]
        result['endtime'] = int(int(time.mktime(time.strptime(
            result['notAfter'], "%Y-%m-%d")) - time.time()) / 86400)
        return result
    except Exception as e:
        # print(getTracebackInfo())
        return None


def createSSL():
    # 自签证书
    if os.path.exists('ssl/input.pl'):
        return True
    import OpenSSL
    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
    cert = OpenSSL.crypto.X509()
    cert.set_serial_number(0)
    cert.get_subject().CN = getLocalIp()
    cert.set_issuer(cert.get_subject())
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(86400 * 3650)
    cert.set_pubkey(key)
    cert.sign(key, 'md5')
    cert_ca = OpenSSL.crypto.dump_certificate(
        OpenSSL.crypto.FILETYPE_PEM, cert)
    private_key = OpenSSL.crypto.dump_privatekey(
        OpenSSL.crypto.FILETYPE_PEM, key)
    if len(cert_ca) > 100 and len(private_key) > 100:
        writeFile('ssl/cert.pem', cert_ca, 'wb+')
        writeFile('ssl/private.pem', private_key, 'wb+')
        return True
    return False


def getSSHPort():
    try:
        file = '/etc/ssh/sshd_config'
        conf = readFile(file)
        rep = "(#*)?Port\s+([0-9]+)\s*\n"
        port = re.search(rep, conf).groups(0)[1]
        return int(port)
    except:
        return 22


def getSSHStatus():
    if os.path.exists('/usr/bin/apt-get'):
        status = execShell("service ssh status | grep -P '(dead|stop)'")
    else:
        import system_api
        version = system_api.system_api().getSystemVersion()
        if version.find(' Mac ') != -1:
            return True
        if version.find(' 7.') != -1:
            status = execShell("systemctl status sshd.service | grep 'dead'")
        else:
            status = execShell(
                "/etc/init.d/sshd status | grep -e 'stopped' -e '已停'")
    if len(status[0]) > 3:
        status = False
    else:
        status = True
    return status

def checkExistHostInKnownHosts(host):
    known_hosts_file = os.path.expanduser('~/.ssh/known_hosts')
    # 检查文件是否存在
    if os.path.exists(known_hosts_file):
        with open(known_hosts_file, 'r') as f:
            for line in f:
                if host in line:
                    return True
    return False

def addHostToKnownHosts(host):
    if checkExistHostInKnownHosts(host):
        return
    command = f'ssh-keyscan {host}'
    output = os.popen(command).read()
    known_hosts_file = os.path.expanduser('~/.ssh/known_hosts')
    with open(known_hosts_file, 'a') as f:
        f.write(output)

def requestFcgiPHP(sock, uri, document_root='/tmp', method='GET', pdata=b''):
    # 直接请求到PHP-FPM
    # version php版本
    # uri 请求uri
    # filename 要执行的php文件
    # args 请求参数
    # method 请求方式
    sys.path.append(os.getcwd() + "/class/plugin")

    import fpm
    p = fpm.fpm(sock, document_root)

    if type(pdata) == dict:
        pdata = url_encode(pdata)
    result = p.load_url_public(uri, pdata, method)
    return result


def getMyORM():
    '''
    获取MySQL资源的ORM
    '''
    sys.path.append(os.getcwd() + "/class/plugin")
    import orm
    o = orm.ORM()
    return o


def getMyORMDb():
    '''
    获取MySQL资源的ORM pip install mysqlclient==2.0.3 | pip install mysql-python
    '''
    sys.path.append(os.getcwd() + "/class/plugin")
    import ormDb
    o = ormDb.ORM()
    return o

def getDDB(db_dir):
    '''
    获取dictdatabase资源
    '''
    sys.path.append(os.getcwd() + "/class/plugin")
    import ddb
    return ddb.DDB(db_dir)

def getAllVms():
    result = subprocess.run(['VBoxManage', 'list', 'vms'], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')


    
##################### notify  start #########################################


def initNotifyConfig():
    p = getNotifyPath()
    if not os.path.exists(p):
        writeFile(p, '{}')
    return True


def getNotifyPath():
    path = 'data/notify.json'
    return path


def getNotifyData(is_parse=False):
    initNotifyConfig()
    notify_file = getNotifyPath()
    notify_data = readFile(notify_file)

    data = json.loads(notify_data)

    if is_parse:
        tag_list = ['tgbot', 'email']
        for t in tag_list:
            if t in data and 'cfg' in data[t]:
                data[t]['data'] = json.loads(deDoubleCrypt(t, data[t]['cfg']))
    return data


def writeNotify(data):
    p = getNotifyPath()
    return writeFile(p, json.dumps(data))


def tgbotNotifyChatID():
    data = getNotifyData(True)
    if 'tgbot' in data and 'enable' in data['tgbot']:
        if data['tgbot']['enable']:
            t = data['tgbot']['data']
            return t['chat_id']
    return ''


def tgbotNotifyObject():
    data = getNotifyData(True)
    if 'tgbot' in data and 'enable' in data['tgbot']:
        if data['tgbot']['enable']:
            t = data['tgbot']['data']
            import telebot
            bot = telebot.TeleBot(app_token)
            return True, bot
    return False, None


def tgbotNotifyMessage(app_token, chat_id, msg):
    import telebot
    bot = telebot.TeleBot(app_token)
    try:
        data = bot.send_message(chat_id, msg)
        return True
    except Exception as e:
        writeFileLog(str(e))
    return False


def tgbotNotifyHttpPost(app_token, chat_id, msg):
    try:
        url = 'https://api.telegram.org/bot' + app_token + '/sendMessage'
        post_data = {
            'chat_id': chat_id,
            'text': msg,
        }
        rdata = httpPost(url, post_data)
        return True
    except Exception as e:
        writeFileLog(str(e))
    return False


def tgbotNotifyTest(app_token, chat_id):
    msg = 'MW-通知验证测试OK'
    return tgbotNotifyHttpPost(app_token, chat_id, msg)


def emailNotifyMessage(data):
    '''
    邮件通知
    '''
    sys.path.append(os.getcwd() + "/class/plugin")
    import memail
    if data['smtp_ssl'] == 'ssl':
        memail.sendSSL(data['smtp_host'], data['smtp_port'],
                        data['username'], data['password'],
                        data['to_mail_addr'], data['subject'], data['content'], data.get('contentType', 'text'))
    else:
        memail.send(data['smtp_host'], data['smtp_port'],
                    data['username'], data['password'],
                    data['to_mail_addr'], data['subject'], data['content'], data.get('contentType', 'text'))
    return True


def emailNotifyTest(data):
    # print(data)
    data['subject'] = '江湖面板通知测试'
    data['content'] = data['mail_test']
    return emailNotifyMessage(data)

def getLockData(lock_type):
    lock_file = getPanelTmp() + '/lock.json'
    try:
        if not os.path.exists(lock_file):
            writeFile(lock_file, '{}')
        lock_data = json.loads(readFile(lock_file))
        if lock_type in lock_data:
            return lock_data[lock_type]
    except Exception as e:
        writeFile(lock_file, '{}')
    return {}

def updateLockData(lock_type):
    lock_file = getPanelTmp() + '/lock.json'
    try:
      if not os.path.exists(lock_file):
          writeFile(lock_file, '{}')

      lock_data = json.loads(readFile(lock_file))
      lock_data[lock_type] = {'do_time': time.time()}
      writeFile(lock_file, json.dumps(lock_data))
    except Exception as e:
        writeFile(lock_file, '{}')

def checkLockValid(lock_type, cycle_type = 'day'):
    lock_data = getLockData(lock_type)
    if lock_data is None:
        return False
    if lock_data.get('do_time', None) is None:
        return False
    now = datetime.datetime.now()
    diff_time = time.time() - lock_data['do_time']
    if cycle_type == 'day' and diff_time >= (24 * 60 * 60):
        return False
    elif cycle_type == 'day_start' and diff_time >= (23 * 60 * 60) and now.hour >= 0 and now.hour <= 1:
        return False
    elif cycle_type == 'minute' and diff_time >= (1 * 60):
        return False
    else: 
        return True

@retry(max_retry=3, delay=3)
def notifyMessageTry(msg, msgtype='text', title='江湖面板通知', stype='common', trigger_time=300, is_write_log=True):
  try:
    lock_file = getPanelTmp() + '/notify_lock.json'
    if not os.path.exists(lock_file):
        writeFile(lock_file, '{}')

    lock_data = json.loads(readFile(lock_file))
    if stype in lock_data:
        diff_time = time.time() - lock_data[stype]['do_time']
        if diff_time >= trigger_time:
            lock_data[stype]['do_time'] = time.time()
        else:
            return False
    else:
        lock_data[stype] = {'do_time': time.time()}

    writeFile(lock_file, json.dumps(lock_data))

    if is_write_log:
        writeLog("通知管理[" + stype + "]", msg)

    data = getNotifyData(True)
    # tag_list = ['tgbot', 'email']
    # tagbot
    do_notify = False
    if 'tgbot' in data and 'enable' in data['tgbot']:
        if data['tgbot']['enable']:
            t = data['tgbot']['data']
            i = sys.version_info

            # telebot 在python小于3.7无法使用
            if i[0] < 3 or i[1] < 7:
                do_notify = tgbotNotifyHttpPost(
                    t['app_token'], t['chat_id'], msg)
            else:
                do_notify = tgbotNotifyMessage(
                    t['app_token'], t['chat_id'], msg)

    if 'email' in data and 'enable' in data['email']:
        if data['email']['enable']:
            t = data['email']['data']
            t['subject'] = title
            t['content'] = msg
            t['contentType'] = msgtype
            do_notify = emailNotifyMessage(t)
    return do_notify
  except Exception as e:
    print(getTracebackInfo())
    raise e


# 发送消息通知
# msg 消息内容
# stype 通知类型
# trigger_time 间隔时间（秒）
# is_write_log 是否写入日志
def notifyMessage(msg, msgtype='text', title='江湖面板通知', stype='common', trigger_time=300, is_write_log=True):
    try:
        return notifyMessageTry(msg, msgtype, title, stype, trigger_time, is_write_log)
    except Exception as e:
        writeFileLog(getTracebackInfo())
        return False

def generateCommonNotifyMessage(content):
    panel_title = getConfig('title')
    ip = getHostAddr()
    now_time = getDateFromNow()
    notify_msg = now_time + '|节点[' + panel_title + ':' + ip + ']\n'
    notify_msg += content
    return notify_msg

##################### notify  end #########################################
# 根据配置的服务器报告频率获取报告开始时间
def getReportCycleStartTime(end_datetime):
    control_report_cycle_file = 'data/control_report_cycle.conf'
    if not os.path.exists(control_report_cycle_file):
        writeFile(control_report_cycle_file, '{}')
    report_cycle_config = json.loads(readFile(control_report_cycle_file))
    cycle_type = report_cycle_config.get('type', 'week')
    start_datetime = None
    if cycle_type == "day":
        start_datetime = end_datetime - datetime.timedelta(days=1)            
    elif cycle_type == "day-n":
        cycle_where1 = int(report_cycle_config.get('where1', '0'))
        start_datetime = end_datetime - datetime.timedelta(days=cycle_where1)  
    elif cycle_type == "hour":
        start_datetime = end_datetime - datetime.timedelta(hours=1)  
    elif cycle_type == "hour-n":
        cycle_where1 = int(report_cycle_config.get('where1', '0'))
        start_datetime = end_datetime - datetime.timedelta(hours=cycle_where1)  
    elif cycle_type == "minute-n":
        cycle_where1 = int(report_cycle_config.get('where1', '0'))
        start_datetime = end_datetime - datetime.timedelta(minutes=cycle_where1)  
    elif cycle_type == "week":
        start_datetime = end_datetime - datetime.timedelta(days=7)
    elif cycle_type == "month":
        start_datetime = end_datetime - datetime.timedelta(days=30)
    return start_datetime
    
def getControlNotifyConfig():
    control_notify_config = {}
    control_notify_config['notifyStatus'] = 'close'
    # 开启异常通知
    control_notify_pl = 'data/control_notify.pl'
    if os.path.exists(control_notify_pl):
        control_notify_config['notifyStatus'] = 'open'
    # 监控阈值
    control_notify_value_file = 'data/control_notify_value.conf'
    if not os.path.exists(control_notify_value_file):
        writeFile(control_notify_value_file, '{}')
    
    control_notify_value_data = json.loads(readFile(control_notify_value_file))
    control_notify_config['cpu'] = control_notify_value_data['cpu'] if 'cpu' in control_notify_value_data else 80
    control_notify_config['memory'] = control_notify_value_data['memory'] if 'memory' in control_notify_value_data else 80 
    control_notify_config['disk'] = control_notify_value_data['disk'] if 'disk' in control_notify_value_data else 80 
    control_notify_config['ssl_cert'] = control_notify_value_data['ssl_cert'] if 'ssl_cert' in control_notify_value_data else 14 
    return control_notify_config


def generateMonitorReportAndNotify(cpuInfo, networkInfo, diskInfo, siteInfo):
    control_notify_pl = 'data/control_notify.pl'

    control_notify_config = getControlNotifyConfig()
    if control_notify_config['notifyStatus'] == 'open':
        # 推送需要的内容
        now_time = getDateFromNow()
        now_day = now_time.split(' ')[0]

        # writeFile('/root/test.txt', '\nCPU状态:' + str(cpuInfo) + '\n网络状态:' + str(networkInfo) + '\n磁盘状态:' + str(diskInfo) + '\n站点状态:' + str(siteInfo) + '\n')
        cpu_percent = cpuInfo['used'] 
        mem_percent = cpuInfo['mem']
        network_up = networkInfo['up'] # MB
        network_down = networkInfo['down'] # MB
        disk_list = diskInfo['disk_list']
        site_list = siteInfo['site_list']
        
        error_msg_arr = []
        # CPU
        if (control_notify_config['cpu'] != -1) and (cpu_percent > control_notify_config['cpu']):
            error_msg_arr.append('CPU负载过高[' + str(cpu_percent) + '%' + ']')
        # 内存
        if (control_notify_config['memory'] != -1) and (mem_percent > control_notify_config['memory']):
            error_msg_arr.append('内存负载过高[' + str(mem_percent) + '%' + ']')
        # 磁盘容量
        if (control_notify_config['disk'] != -1) and len(disk_list) > 0:
            for disk in disk_list:
                disk_size_percent = int(disk['size'][3].replace('%', ''))

                if disk_size_percent > control_notify_config['disk']:
                    error_msg_arr.append('磁盘[' + disk['path'] + ']占用过高[' + str(disk_size_percent) + '%' + ']')
        
        # 网站SSL证书
        site_ssl_lock_data_key = '网站SSL证书异常通知'
        if (control_notify_config['ssl_cert'] != -1) and not checkLockValid(site_ssl_lock_data_key, 'day_start') and len(site_list) > 0:
            for site in site_list:
                site_name = site['name']
                cert_data = site['cert_data']
                ssl_type = site['ssl_type']
                # 网站名称 + 当前日期
                # site_notify_lock_key = str(site_name) + '_' + str(now_day) 
                if site['status'] == '1' and cert_data is not None:
                    cert_endtime = int(cert_data['endtime'])
                    site_error_msg = ''
                    if ssl_type == 'custom':
                        if cert_endtime >= 0 and cert_endtime < control_notify_config['ssl_cert']:
                            site_error_msg = '网站[' + site['name'] + ']SSL证书还有[' + str(cert_endtime) + '天' + ']过期'
                        elif cert_endtime < 0:
                            site_error_msg = '网站[' + site['name'] + ']SSL证书已过期[' + str(cert_endtime) + '天' + ']'
                    elif ssl_type == 'lets' or ssl_type == 'acme':
                        if cert_endtime < 0:
                            site_error_msg = '网站[' + site['name'] + ']SSL证书已过期[' + str(cert_endtime) + '天' + ']，未正常续签'
                    
                    if site_error_msg != '':
                        error_msg_arr.append(site_error_msg)
        
        # 发送异常报告
        if (len(error_msg_arr) > 0):
            notify_msg = generateCommonNotifyMessage('\n'.join(error_msg_arr) + '\n请注意!')
            notifyMessage(title='服务器异常通知', msg=notify_msg, stype='面板监控', trigger_time=600)
            updateLockData(site_ssl_lock_data_key)


def getBackupPluginList():
  return [
    { "name": 'jianghujs', "path": "/www/server/jianghujs", "ps": 'JianghuJS管理器项目数据' },
    { "name": 'docker', "path": "/www/server/docker", "ps": 'Docker管理器项目数据' }
  ]