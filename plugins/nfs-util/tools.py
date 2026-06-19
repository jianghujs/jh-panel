# coding:utf-8

import argparse
import os
import shlex
import subprocess
import sys


def _run(cmd, timeout=5):
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout
    )


def _normalize(path):
    try:
        return os.path.realpath(path)
    except Exception:
        return os.path.abspath(path)


def check_mount_dir(path, timeout=5, label='目录'):
    if not path:
        print('%s检查失败: 目录不能为空' % label)
        return 1

    raw_path = path
    path = os.path.abspath(path)

    try:
        exists = _run(['sh', '-c', 'test -d "$1"', 'sh', path], timeout=timeout)
    except subprocess.TimeoutExpired:
        print('%s检查失败: 目录访问超时 %s' % (label, raw_path))
        return 1

    if exists.returncode != 0:
        print('%s检查失败: 目录不存在或不可访问 %s' % (label, raw_path))
        return 1

    try:
        findmnt = _run(['findmnt', '-T', path, '-n', '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS'], timeout=timeout)
    except FileNotFoundError:
        return 0
    except subprocess.TimeoutExpired:
        print('%s检查失败: 获取挂载信息超时 %s' % (label, raw_path))
        return 1

    if findmnt.returncode != 0 or findmnt.stdout.strip() == '':
        return 0

    mount_info = findmnt.stdout.strip().split('\n')[0]
    mount_target = mount_info.split()[0]
    if _normalize(mount_target) != _normalize(path):
        return 0

    try:
        access = _run(['sh', '-c', 'ls -ld "$1" >/dev/null', 'sh', path], timeout=timeout)
    except subprocess.TimeoutExpired:
        print('%s检查失败: 挂载目录访问超时 %s' % (label, raw_path))
        return 1

    if access.returncode != 0:
        err = access.stderr.strip() or access.stdout.strip()
        if err:
            print('%s检查失败: 挂载目录访问异常 %s, %s' % (label, raw_path, err))
        else:
            print('%s检查失败: 挂载目录访问异常 %s' % (label, raw_path))
        return 1

    return 0


def check_remote_mount_dir(host, path, port=22, key_path='', user='root', timeout=5, label='远端目录'):
    remote_cmd = r'''
PATH_TO_CHECK=$1
CHECK_TIMEOUT=$2
LABEL=$3
if ! timeout "$CHECK_TIMEOUT" sh -c 'test -d "$1"' sh "$PATH_TO_CHECK"; then
    echo "$LABEL检查失败: 目录不存在或不可访问 $PATH_TO_CHECK"
    exit 1
fi
MOUNT_TARGET=""
if command -v findmnt >/dev/null 2>&1; then
    MOUNT_TARGET=$(findmnt -T "$PATH_TO_CHECK" -n -o TARGET 2>/dev/null | head -n 1 || true)
fi
PATH_TO_CHECK=$(readlink -f "$PATH_TO_CHECK" 2>/dev/null || printf '%s' "$PATH_TO_CHECK")
MOUNT_TARGET=$(readlink -f "$MOUNT_TARGET" 2>/dev/null || printf '%s' "$MOUNT_TARGET")
if [ -n "$MOUNT_TARGET" ] && [ "$MOUNT_TARGET" = "$PATH_TO_CHECK" ]; then
    if ! timeout "$CHECK_TIMEOUT" sh -c 'ls -ld "$1" >/dev/null' sh "$PATH_TO_CHECK"; then
        echo "$LABEL检查失败: 挂载目录访问异常 $PATH_TO_CHECK"
        exit 1
    fi
fi
'''

    ssh_cmd = [
        'ssh',
        '-p', str(port),
        '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=%s' % int(timeout),
    ]
    if key_path:
        ssh_cmd.extend(['-i', key_path])
    ssh_cmd.extend(['%s@%s' % (user, host), 'sh', '-s', '--', path, str(int(timeout)), label])

    try:
        data = subprocess.run(
            ssh_cmd,
            input=remote_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout + 3
        )
    except subprocess.TimeoutExpired:
        print('%s检查失败: SSH连接或检查超时 %s:%s' % (label, host, path))
        return 1

    if data.stdout.strip():
        print(data.stdout.strip())
    if data.returncode != 0:
        err = data.stderr.strip()
        if err:
            print(err)
        return data.returncode
    return 0


def main():
    parser = argparse.ArgumentParser(description='nfs-util tools')
    subparsers = parser.add_subparsers(dest='func')

    local_parser = subparsers.add_parser('check_mount_dir')
    local_parser.add_argument('--path', required=True)
    local_parser.add_argument('--timeout', type=int, default=5)
    local_parser.add_argument('--label', default='目录')

    remote_parser = subparsers.add_parser('check_remote_mount_dir')
    remote_parser.add_argument('--host', required=True)
    remote_parser.add_argument('--path', required=True)
    remote_parser.add_argument('--port', default='22')
    remote_parser.add_argument('--key-path', default='')
    remote_parser.add_argument('--user', default='root')
    remote_parser.add_argument('--timeout', type=int, default=5)
    remote_parser.add_argument('--label', default='远端目录')

    args = parser.parse_args()
    if args.func == 'check_mount_dir':
        return check_mount_dir(args.path, args.timeout, args.label)
    if args.func == 'check_remote_mount_dir':
        return check_remote_mount_dir(args.host, args.path, args.port, args.key_path, args.user, args.timeout, args.label)

    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
