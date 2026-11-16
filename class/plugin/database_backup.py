# coding: utf-8
"""Shared mechanics for database plugins; engine-specific behavior stays in plugins."""

import os
import signal
import sqlite3
import subprocess
import time
from contextlib import closing


def runCommand(command, stage, timeout=None):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        raise RuntimeError(stage + '超时') from None
    if proc.returncode:
        raise RuntimeError(stage + ': ' + (stderr or stdout or '退出码 ' + str(proc.returncode)))
    return stdout


def ensureRecord(db_file, name, host):
    # Serialize backup discovery writers without changing the plugin schema.
    if not os.path.isfile(db_file):
        raise ValueError('插件配置库不存在')
    with closing(sqlite3.connect(db_file, timeout=10)) as conn:
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            rows = conn.execute('SELECT id FROM databases WHERE name=?', (name,)).fetchall()
            if not rows:
                conn.execute('INSERT INTO databases (name,username,password,accept,ps,addtime) '
                             'VALUES (?,?,?,?,?,?)',
                             (name, name, '', host, name, time.strftime('%Y-%m-%d %X')))
                rows = conn.execute('SELECT id FROM databases WHERE name=?', (name,)).fetchall()
            if len(rows) != 1 or type(rows[0][0]) is not int or rows[0][0] <= 0:
                raise ValueError('不能取得唯一有效的数据库记录 ID')
            return rows[0][0]


def safeError(error, password):
    # Never forward command traces (which may contain credentials) to task logs.
    detail = str(error)
    if isinstance(password, str) and password:
        detail = detail.replace(password, '***')
    return detail[:1200]
