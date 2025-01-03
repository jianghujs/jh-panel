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
        site_domain = request.host.replace('.', '_')
        print("site_domain", site_domain)

        login_cache_count = 5
        login_cache_limit = session.get('site_login_cache_limit__' + site_domain, 0)

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        code = request.form.get('code', '').strip()

        if 'code' in session:
            if session['code'] != mw.md5(code.lower()):
                if login_cache_limit is None:
                    login_cache_limit = 1
                else:
                    login_cache_limit = int(login_cache_limit) + 1

                if login_cache_limit >= login_cache_count:
                    return mw.returnJson(False, '登录尝试过多，已暂时锁定!')

                # mw.cache.set('site_login_cache_limit', login_cache_limit, timeout=10000)
                code_msg = mw.getInfo("验证码错误,您还可以尝试[{1}]次!", (str(
                    login_cache_count - login_cache_limit)))
                return mw.returnJson(False, code_msg)

        # 假设站点用户信息以类似的方式存储
        # site_id = request.form.get('site_id', '').strip()
        # site_info = mw.M('sites').where("id=?", (site_id,)).field('auth_users').find()
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
            
            session['site_login_cache_limit__' + site_domain] = login_cache_limit
            return mw.returnJson(False, mw.getInfo("用户名或密码错误,您还可以尝试[{1}]次!", (str(login_cache_count - login_cache_limit))))

        session['site_login_cache_limit__' + site_domain] = None
        session['site_login__' + site_domain] = True
        session['site_username__' + site_domain] = username
        session['site_id__' + site_domain] = site_domain
        session['site_overdue__' + site_domain] = int(time.time()) + 7 * 24 * 60 * 60

        return mw.returnJson(True, '登录成功,正在跳转...')

    def checkSiteLoginApi(self):
        site_domain = request.host.replace('.', '_')
        site_login_key = 'site_login__' + site_domain

        print("当前session", session)

        if site_login_key in session and session[site_login_key]:
            return ("success", 200)
        return ("error", 401)