# coding: utf-8

# ---------------------------------------------------------------------------------
# 开放接口
# ---------------------------------------------------------------------------------


import psutil
import time
import os
import sys
import mw
import re
import json
import pwd

from flask import request, session

class pub_api:
    
    def getHostAddrApi(self):
        return jh.returnJson(True, 'ok', jh.getHostAddr())

    def doSiteLoginApi(self):
        site_name = request.host
        site_key = site_name.replace('.', '_')

        login_cache_count = 5
        login_cache_limit = session.get('site_login_cache_limit__' + site_key, 0)

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        code = request.form.get('code', '').strip()

        if 'code' in session:
            if session['code'] != mw.md5(code.lower()):
                if login_cache_limit is None:
                    login_cache_limit = 1
                else:
                    login_cache_limit = int(login_cache_limit) + 1

                login_cache_limit_timeout = session.get('site_login_cache_limit_timeout__' + site_key, 0)
                if login_cache_limit >= login_cache_count and login_cache_limit_timeout > int(time.time()):
                    return mw.returnJson(False, '登录尝试过多，已暂时锁定!')
                
                # mw.cache.set('site_login_cache_limit', login_cache_limit, timeout=10000)
                session['site_login_cache_limit__' + site_key] = login_cache_limit
                session['site_login_cache_limit_timeout__' + site_key] = int(time.time()) + 10000
                code_msg = mw.getInfo("验证码错误,您还可以尝试[{1}]次!", (str(
                    login_cache_count - login_cache_limit)))
                return mw.returnJson(False, code_msg)

        # 假设站点用户信息以类似的方式存储
        site_info = mw.M('sites').where("name=?", (site_name,)).field('auth_users').find()
        print("site_info", site_info)
        # auth_users = json.loads(site_info['auth_users']) if site_info['auth_users'] else []
        auth_users = [{"username": "admin", "password": "a41d89cecd11b2586c65ae1c6edb2145"}]

        user_match = next((user for user in auth_users if user['username'] == username and user['password'] == mw.md5(password)), None)

        if not user_match:
            msg = "<a style='color: red'>密码错误</a>,帐号:{0},登录IP:{1}".format(username, request.remote_addr)

            if login_cache_limit is None:
                login_cache_limit = 1
            else:
                login_cache_limit = int(login_cache_limit) + 1

            if login_cache_limit >= login_cache_count:
                return mw.returnJson(False, '登录尝试过多，已暂时锁定!')
            
            session['site_login_cache_limit__' + site_key] = login_cache_limit
            return mw.returnJson(False, mw.getInfo("用户名或密码错误,您还可以尝试[{1}]次!", (str(login_cache_count - login_cache_limit))))

        session['site_login_cache_limit__' + site_key] = None
        session['site_login_cache_limit_timeout__' + site_key] = None
        session['site_login__' + site_key] = True
        session['site_username__' + site_key] = username
        session['site_id__' + site_key] = site_key
        session['site_overdue__' + site_key] = int(time.time()) + 7 * 24 * 60 * 60

        return mw.returnJson(True, '登录成功,正在跳转...')

    def checkSiteLoginApi(self):
        print("当前session", session)

        site_name = request.host
        site_key = site_name.replace('.', '_')
        site_login_key = 'site_login__' + site_key

        # 未开启身份认证自动调整
        site_info = mw.M('sites').where("name=?", (site_name,)).field('auth_enabled').find()
        print("site_info", site_info)
        # auth_enabled = site_info['auth_enabled']
        auth_enabled = True
        if not auth_enabled:
            return ("success", 200)

        # 已登录
        if site_login_key in session and session[site_login_key]:
            return ("success", 200)
        return ("error", 401)
