# coding:utf-8

import sys
import io
import os
import time
import shutil
import uuid
import json
import traceback

# reload(sys)
#  sys.setdefaultencoding('utf-8')


from datetime import timedelta

from flask import Flask
from flask import render_template
from flask import make_response
from flask import Response
from flask import session
from flask import request
from flask import redirect
from flask import url_for
from flask import render_template_string, abort
from flask_caching import Cache
from flask_session import Session

sys.path.append(os.getcwd() + "/class/core")

import db
import mw
import config_api

app = Flask(__name__, template_folder='templates/default')
app.config.version = config_api.config_api().getVersion()

cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app, config={'CACHE_TYPE': 'simple'})

try:
    from flask_sqlalchemy import SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/mw_session.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['SESSION_TYPE'] = 'sqlalchemy'
    app.config['SESSION_SQLALCHEMY'] = sdb
    app.config['SESSION_SQLALCHEMY_TABLE'] = 'session'
    sdb = SQLAlchemy(app)
    sdb.create_all()
except:
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = '/tmp/py_mw_session_' + \
        str(sys.version_info[0])
    app.config['SESSION_FILE_THRESHOLD'] = 1024
    app.config['SESSION_FILE_MODE'] = 384
    mw.execShell("pip install flask_sqlalchemy &")

app.secret_key = uuid.UUID(int=uuid.getnode()).hex[-12:]
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'MW_:'
app.config['SESSION_COOKIE_NAME'] = "MW_VER_1"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
# Session(app)

# 设置BasicAuth
basic_auth_conf = 'data/basic_auth.json'
app.config['BASIC_AUTH_OPEN'] = False
if os.path.exists(basic_auth_conf):
    try:
        ba_conf = json.loads(mw.readFile(basic_auth_conf))
        print(ba_conf)
        app.config['BASIC_AUTH_USERNAME'] = ba_conf['basic_user']
        app.config['BASIC_AUTH_PASSWORD'] = ba_conf['basic_pwd']
        app.config['BASIC_AUTH_OPEN'] = ba_conf['open']
        app.config['BASIC_AUTH_FORCE'] = True
    except Exception as e:
        print(e)

# socketio
from flask_socketio import SocketIO, emit, send
socketio = SocketIO()
socketio.init_app(app)

# from gevent.pywsgi import WSGIServer
# from geventwebsocket.handler import WebSocketHandler
# http_server = WSGIServer(('0.0.0.0', '7200'), app,
#                          handler_class=WebSocketHandler)
# http_server.serve_forever()

# debug macosx dev
app.config.jhpanelVersion = app.config.version
if mw.isDebugMode():
    app.debug = True
    app.config.version = app.config.version + str(time.time())
    # app.config.version = app.config.version + ' / 开发模式; ' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

import common
common.init()


# ----------  error function start -----------------
def getErrorNum(key, limit=None):
    key = mw.md5(key)
    num = cache.get(key)
    if not num:
        num = 0
    if not limit:
        return num
    if limit > num:
        return True
    return False


def setErrorNum(key, empty=False, expire=3600):
    key = mw.md5(key)
    num = cache.get(key)
    if not num:
        num = 0
    else:
        if empty:
            cache.delete(key)
            return True
    cache.set(key, num + 1, expire)
    return True
# ----------  error function end -----------------


def funConvert(fun):
    block = fun.split('_')
    func = block[0]
    for x in range(len(block) - 1):
        suf = block[x + 1].title()
        func += suf
    return func


def sendAuthenticated():
    # 发送http认证信息
    request_host = mw.getHostAddr()
    result = Response(
        '', 401, {'WWW-Authenticate': 'Basic realm="%s"' % request_host.strip()})
    if not 'login' in session and not 'admin_auth' in session:
        session.clear()
    return result


@app.before_request
def requestCheck():
    # Flask请求勾子
    if app.config['BASIC_AUTH_OPEN']:
        auth = request.authorization
        if request.path in ['/download', '/hook', '/down']:
            return

        if not auth:
            return sendAuthenticated()
        salt = '_md_salt'
        if mw.md5(auth.username.strip() + salt) != app.config['BASIC_AUTH_USERNAME'] \
                or mw.md5(auth.password.strip() + salt) != app.config['BASIC_AUTH_PASSWORD']:
            return sendAuthenticated()

    domain_check = mw.checkDomainPanel()
    if domain_check:
        return domain_check


def isLogined():
    # print('isLogined', session)
    if 'login' in session and 'username' in session and session['login'] == True:
        userInfo = mw.M('users').where(
            "id=?", (1,)).field('id,username,password').find()
        # print(userInfo)
        if userInfo['username'] != session['username']:
            return False

        now_time = int(time.time())

        if 'overdue' in session and now_time > session['overdue']:
            # 自动续期
            session['overdue'] = int(time.time()) + 7 * 24 * 60 * 60
            return False

        if 'tmp_login_expire' in session and now_time > int(session['tmp_login_expire']):
            session.clear()
            return False

        return True

    # if os.path.exists('data/api_login.txt'):
    #     content = mw.readFile('data/api_login.txt')
    #     session['login'] = True
    #     session['username'] = content
    #     os.remove('data/api_login.txt')
    return False


def publicObject(toObject, func, action=None, get=None):
    name = funConvert(func) + 'Api'
    try:
        if hasattr(toObject, name):
            efunc = 'toObject.' + name + '()'
            data = eval(efunc)
            return data
        data = {'msg': '404,not find api[' + name + ']', "status": False}
        return mw.getJson(data)
    except Exception as e:
        # API发生错误记录
        print(traceback.print_exc())
        data = {'msg': '访问异常:' + str(e) + '!', "status": False}
        return mw.getJson(data)


# @app.route("/debug")
# def debug():
#     print(sys.version_info)
#     print(session)
#     os = mw.getOs()
#     print(os)
#     return mw.getLocalIp()

# 仅针对webhook插件
@app.route("/hook")
def webhook():
    input_args = {
        'access_key': request.args.get('access_key', '').strip(),
        'params': request.args.get('params', '').strip()
    }

    wh_install_path = mw.getServerDir() + '/webhook'
    if not os.path.exists(wh_install_path):
        return mw.returnJson(False, '请先安装WebHook插件!')

    sys.path.append('plugins/webhook')
    import index
    return index.runShellArgs(input_args)


@app.route('/close')
def close():
    if not os.path.exists('data/close.pl'):
        return redirect('/')
    data = {}
    data['cmd'] = 'rm -rf ' + mw.getRunDir() + '/data/close.pl'
    return render_template('close.html', data=data)


@app.route("/code")
def code():
    import vilidate
    vie = vilidate.vieCode()
    codeImage = vie.GetCodeImage(80, 4)
    # try:
    #     from cStringIO import StringIO
    # except:
    #     from StringIO import StringIO

    out = io.BytesIO()
    codeImage[0].save(out, "png")

    # print(codeImage[1])

    session['code'] = mw.md5(''.join(codeImage[1]).lower())

    img = Response(out.getvalue(), headers={'Content-Type': 'image/png'})
    return make_response(img)


@app.route("/check_login", methods=['POST'])
def checkLogin():
    if isLogined():
        return "true"
    return "false"


@app.route("/do_login", methods=['POST'])
def doLogin():
    login_cache_count = 5
    login_cache_limit = cache.get('login_cache_limit')

    filename = 'data/close.pl'
    if os.path.exists(filename):
        return mw.returnJson(False, '面板已经关闭!')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    code = request.form.get('code', '').strip()
    # print(session)
    if 'code' in session:
        if session['code'] != mw.md5(code):
            if login_cache_limit == None:
                login_cache_limit = 1
            else:
                login_cache_limit = int(login_cache_limit) + 1

            if login_cache_limit >= login_cache_count:
                mw.writeFile(filename, 'True')
                return mw.returnJson(False, '面板已经关闭!')

            cache.set('login_cache_limit', login_cache_limit, timeout=10000)
            login_cache_limit = cache.get('login_cache_limit')
            code_msg = mw.getInfo("验证码错误,您还可以尝试[{1}]次!", (str(
                login_cache_count - login_cache_limit)))
            mw.writeLog('用户登录', code_msg)
            return mw.returnJson(False, code_msg)

    userInfo = mw.M('users').where(
        "id=?", (1,)).field('id,username,password').find()

    # print(userInfo)
    # print(password)
    password = mw.md5(password)
    # print('md5-pass', password)

    if userInfo['username'] != username or userInfo['password'] != password:
        msg = "<a style='color: red'>密码错误</a>,帐号:{1},密码:{2},登录IP:{3}", ((
            '****', '******', request.remote_addr))

        if login_cache_limit == None:
            login_cache_limit = 1
        else:
            login_cache_limit = int(login_cache_limit) + 1

        if login_cache_limit >= login_cache_count:
            mw.writeFile(filename, 'True')
            return mw.returnJson(False, '面板已经关闭!')

        cache.set('login_cache_limit', login_cache_limit, timeout=10000)
        login_cache_limit = cache.get('login_cache_limit')
        mw.writeLog('用户登录', mw.getInfo(msg))
        return mw.returnJson(False, mw.getInfo("用户名或密码错误,您还可以尝试[{1}]次!", (str(login_cache_count - login_cache_limit))))

    cache.delete('login_cache_limit')
    session['login'] = True
    session['username'] = userInfo['username']
    session['overdue'] = int(time.time()) + 7 * 24 * 60 * 60
    # session['overdue'] = int(time.time()) + 7

    # # fix 跳转时,数据消失，可能是跨域问题
    # mw.writeFile('data/api_login.txt', userInfo['username'])
    return mw.returnJson(True, '登录成功,正在跳转...')


@app.errorhandler(404)
def page_unauthorized(error):
    return render_template_string('404 not found', error_info=error), 404


def get_admin_safe():
    path = 'data/admin_path.pl'
    if os.path.exists(path):
        cont = mw.readFile(path)
        cont = cont.strip().strip('/')
        return (True, cont)
    return (False, '')


def admin_safe_path(path, req, data, pageFile):
    if path != req and not isLogined():
        return render_template('path.html')

    if not isLogined():
        return render_template('login.html', data=data)

    if not req in pageFile:
        return redirect('/')

    return render_template(req + '.html', data=data)


def login_temp_user(token):
    if len(token) != 48:
        return '错误的参数!'

    skey = mw.getClientIp() + '_temp_login'
    if not getErrorNum(skey, 10):
        return '连续10次验证失败，禁止1小时'

    stime = int(time.time())
    data = mw.M('temp_login').where('state=? and expire>?',
                                    (0, stime)).field('id,token,salt,expire,addtime').find()
    if not data:
        setErrorNum(skey)
        return '验证失败!'

    if stime > int(data['expire']):
        setErrorNum(skey)
        return "过期"

    r_token = mw.md5(token + data['salt'])
    if r_token != data['token']:
        setErrorNum(skey)
        return '验证失败!'

    userInfo = mw.M('users').where(
        "id=?", (1,)).field('id,username').find()
    session['login'] = True
    session['username'] = userInfo['username']
    session['tmp_login'] = True
    session['tmp_login_id'] = str(data['id'])
    session['tmp_login_expire'] = int(data['expire'])
    session['uid'] = data['id']

    login_addr = mw.getClientIp() + ":" + str(request.environ.get('REMOTE_PORT'))
    mw.writeLog('用户登录', "登录成功,帐号:{1},登录IP:{2}",
                (userInfo['username'], login_addr))
    mw.M('temp_login').where('id=?', (data['id'],)).update(
        {"login_time": stime, 'state': 1, 'login_addr': login_addr})

    # print(session)
    return redirect('/')


@app.route('/api/<reqClass>/<reqAction>', methods=['POST', 'GET'])
def api(reqClass=None, reqAction=None, reqData=None):

    comReturn = common.local()
    if comReturn:
        return comReturn

    import config_api
    isOk, data = config_api.config_api().checkPanelToken()
    if not isOk:
        return mw.returnJson(False, '未开启API')

    request_time = request.form.get('request_time', '')
    request_token = request.form.get('request_token', '')
    request_ip = request.remote_addr

    token_md5 = mw.md5(str(request_time) + mw.md5(data['token_crypt']))

    if not (token_md5 == request_token):
        return mw.returnJson(False, '密钥错误')

    if not mw.inArray(data['limit_addr'], request_ip):
        return mw.returnJson(False, '非法请求')

    if reqClass == None:
        return mw.returnJson(False, '请指定请求方法类')

    if reqAction == None:
        return mw.returnJson(False, '请指定请求方法')

    classFile = ('config_api', 'crontab_api', 'files_api', 'firewall_api',
                 'plugins_api', 'system_api', 'site_api', 'task_api')
    className = reqClass + '_api'
    if not className in classFile:
        return "external api request error"

    eval_str = "__import__('" + className + "')." + className + '()'
    newInstance = eval(eval_str)

    try:
        return publicObject(newInstance, reqAction)
    except Exception as e:
        return mw.getTracebackInfo()


@app.route('/<reqClass>/<reqAction>', methods=['POST', 'GET'])
@app.route('/<reqClass>/', methods=['POST', 'GET'])
@app.route('/<reqClass>', methods=['POST', 'GET'])
@app.route('/', methods=['POST', 'GET'])
def index(reqClass=None, reqAction=None, reqData=None):

    comReturn = common.local()
    if comReturn:
        return comReturn

    # 页面请求
    if reqAction == None:
        import config_api
        data = config_api.config_api().get()

        if reqClass == None:
            reqClass = 'index'

        pageFile = ('config', 'control', 'crontab', 'files', 'firewall',
                    'index', 'plugins', 'login', 'system', 'site', 'cert', 'ssl', 'task', 'soft')

        if reqClass == 'login':
            token = request.args.get('tmp_token', '').strip()
            if token != '':
                return login_temp_user(token)

        # 设置了安全路径
        ainfo = get_admin_safe()

        # 登录页
        if reqClass == 'login':

            signout = request.args.get('signout', '')
            if signout == 'True':
                session.clear()
                session['login'] = False
                session['overdue'] = 0

            if ainfo[0]:
                return admin_safe_path(ainfo[1], reqClass, data, pageFile)

            return render_template('login.html', data=data)

        if ainfo[0]:
            return admin_safe_path(ainfo[1], reqClass, data, pageFile)

        if not reqClass in pageFile:
            return redirect('/')

        if not isLogined():
            return redirect('/login')

        return render_template(reqClass + '.html', data=data)

    if not isLogined():
        return 'error request!'

    # API请求
    classFile = ('config_api', 'crontab_api', 'files_api', 'firewall_api',
                 'plugins_api', 'system_api', 'site_api', 'task_api')
    className = reqClass + '_api'
    if not className in classFile:
        return "api error request"

    eval_str = "__import__('" + className + "')." + className + '()'
    newInstance = eval(eval_str)

    return publicObject(newInstance, reqAction)

##################### ssh  start ###########################
session_ssh_dict = {}
from gevent import monkey
monkey.patch_all()
import paramiko
import threading
class SSHSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.shell = None
        self.status = None
        self.connect()

    def connect(self):
        self.status = 'connecting'
        print("正在创建SSH终端连接", str(time.time()), self.session_id)
        port = mw.getSSHPort()
        try:
            ips = ['127.0.0.1', mw.getLocalIp(), mw.getHostAddr()]
            for ip in ips:
                print(f"尝试连接{ip}", port)
                self.ssh.connect(hostname=ip, port=port, username='root', timeout=2)
                break  # 如果连接成功，就退出循环
            else:  # 如果所有的IP地址都尝试失败，就返回False
                return False

            print("创建SSH终端连接成功", self.session_id)
            self.shell = self.ssh.invoke_shell(term='xterm', width=83, height=21)
            self.shell.setblocking(0)
            return True
        except Exception as e:
            print(f"连接{ip}失败: {e}")

    def get_shell(self):
        return self.shell

    def clear(self):
        self.ssh.close()
        self.shell = None

def get_ssh_session():
    global session_ssh_dict
    session_id = request.sid
    ssh_session = session_ssh_dict.get(session_id)
    print('- 获取ssh_session --->nsession_ssh_dict: %(session_ssh_dict)s\nsession_id: %(session_id)s\nssh_session: %(ssh_session)s\n------------' % {"session_ssh_dict": str(session_ssh_dict), "session_id": session_id, "ssh_session": ssh_session})
    return ssh_session

@socketio.on('connect_to_ssh')
def connect_to_ssh(msg):
    global session_ssh_dict
    print("=====> 开始连接SSH终端")
    if not isLogined():
        emit('server_response', {'data': '会话丢失，请重新登陆面板!\r\n'})
        return None
    session_id = request.sid
    ssh_session = session_ssh_dict.get(session_id)
    
    if ssh_session is None:
        
        ssh_session = SSHSession(session_id)
        session_ssh_dict[session_id] = ssh_session

    shell = ssh_session.get_shell()
    print("shell", shell)
    if shell:
        try:
            recv = shell.recv(8192)
            emit('server_response', {'data': recv.decode("utf-8")})
            ssh_session.status = 'connected'
            emit('connected', '')
        except Exception as e:
            pass


@socketio.on('webssh')
def webssh(msg):
    print("=====> webssh消息", msg)
    if not isLogined():
        emit('server_response', {'data': '会话丢失，请重新登陆面板!\r\n'})
        return None

    ssh_session = get_ssh_session()
    if ssh_session is None:
        emit('server_response', {'data': ''})
        return False
    try:
        shell = ssh_session.get_shell()
        if shell:
            shell.send(msg)
            time.sleep(0.005)
            recv = shell.recv(4096)
            emit('server_response', {'data': recv.decode("utf-8")})
    except Exception as ex:
        pass

@socketio.on('disconnect_to_ssh')
def disconnect_to_ssh(message):
    
    print("=====> 断开连接SSH终端")
    ssh_session = get_ssh_session()

    if ssh_session is not None:
        ssh_session.clear()
        session_ssh_dict.pop(session_id)


if not mw.isAppleSystem():
    try:
        # 在程序启动时预先创建RSA密钥
        if not os.path.exists('/root/.ssh/id_rsa') or not os.path.exists('/root/.ssh/id_rsa.pub'):
            os.system('ssh-keygen -q -t rsa -P "" -f /root/.ssh/id_rsa')
            os.system('cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys')
            os.system('chmod 600 /root/.ssh/authorized_keys')

        # 检查是否写入authorized_keys
        data = mw.execShell("cat /root/.ssh/id_rsa.pub | awk '{print $3}'")
        if data[0] != "":
            ak_data = mw.execShell(
                "cat /root/.ssh/authorized_keys | grep " + data[0])
            if ak_data[0] == "":
                mw.execShell(
                    'cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys')
                mw.execShell('chmod 600 /root/.ssh/authorized_keys')

    except Exception as e:
        print(e)

##################### ssh  end ###########################

