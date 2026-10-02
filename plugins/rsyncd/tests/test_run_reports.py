import ast
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

PLUGIN = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunReportsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mw = types.ModuleType('mw')
        self.mw.getServerDir = lambda: str(self.root)
        self.mw.readFile = lambda path: Path(path).read_text()
        self.mw.writeFile = lambda path, text: Path(path).write_text(text)
        self.mw.generateCommonNotifyMessage = lambda text: text
        self.mw.getConfig = lambda key: '测试节点'
        self.notifications = []
        self.mw.notifyMessage = lambda **kw: self.notifications.append(kw)
        modules = patch.dict(sys.modules, {'mw': self.mw})
        modules.start()
        self.addCleanup(modules.stop)
        self.run = load_module('rsync_report_test', PLUGIN / 'tool_run.py')
        self.check = load_module('rsync_check_test', PLUGIN / 'tool_check.py')
        self.task = dict(name='sample', conn_type='ssh', ip='127.0.0.1',
                         path='/source/', target_path='/target/', delete='true', max_delete_percent=30)
        self.run.loadTask = lambda name: self.task
        self.run.whichRsync = lambda: 'rsync'
        self.result_path = self.root / 'result.json'
        self.log_path = self.root / 'run.log'
        self.log_path.write_text('')
        env = patch.dict(os.environ, {'RSYNCD_PREFLIGHT_RESULT': str(self.result_path),
                                     'RSYNCD_RUN_LOG': str(self.log_path)})
        env.start()
        self.addCleanup(env.stop)

    def preflight(self, stdout='', stderr='', code=0, exception=None):
        proc = types.SimpleNamespace(stdout=stdout.encode(), stderr=stderr.encode(), returncode=code)
        with patch.object(self.run.subprocess, 'run', return_value=proc, side_effect=exception), \
                patch.object(sys, 'argv', ['tool_run.py', 'preflight', 'sample']), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                self.run.runPreflight()
                exit_code = 0
            except SystemExit as exc:
                exit_code = exc.code
        return exit_code, json.loads(self.result_path.read_text())

    def notify(self, code, phase):
        with patch.object(sys, 'argv', ['tool_run.py', 'notify_fail', 'sample', str(code), phase]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.run.runNotifyFail()
        return self.notifications[-1]

    def test_threshold_lists_all_files_and_has_no_error_code(self):
        paths = ['中文 文件.txt', ' leading space.txt', 'folder/'] + ['file_%s' % n for n in range(400)]
        output = ''.join('*deleting   %s\n' % name for name in paths)
        output += 'Number of files: 1,000\nNumber of deleted files: 403\n'
        code, result = self.preflight(output)
        self.assertEqual(code, 1)
        self.assertEqual(result['kind'], 'threshold')
        self.assertEqual(result['deleted'], paths)
        notice = self.notify(code, 'preflight')
        for name in paths:
            self.assertIn('- ' + name, notice['msg'])
        self.assertIn('40.30%', notice['msg'])
        self.assertIn('超过阈值', notice['title'])
        self.assertIn('本次未执行文件删除', notice['msg'])
        self.assertNotIn('错误码', notice['msg'])
        self.assertNotIn('报错信息', notice['msg'])
        self.assertIn('file_399', Path(result['log_file']).read_text())
        self.assertFalse(self.check._check_fixtime_sync_status(notice['msg'])[0])

    def test_preflight_retains_actual_code_without_delete_list(self):
        code, result = self.preflight('*deleting   old.txt\n', 'rsync: Connection refused (111)\nrsync error (code 10)', 10)
        self.assertEqual(code, 10)
        message = self.notify(code, 'preflight')['msg']
        self.assertIn('错误码：10', message)
        self.assertIn('Connection refused', message)
        self.assertNotIn('old.txt', message)
        self.assertNotIn('待删除清单', message)
        self.assertNotIn('待删除清单', Path(result['log_file']).read_text())
        self.assertNotIn('超过阈值', message)

    def test_parse_and_launch_errors(self):
        code, result = self.preflight('unexpected output')
        self.assertEqual(result['kind'], 'error')
        self.assertIn('无法解析', result['error'])
        code, result = self.preflight(exception=FileNotFoundError(2, 'rsync missing'))
        message = self.notify(code, 'preflight')['msg']
        self.assertIn('FileNotFoundError', message)
        self.assertIn('errno）：2', message)
        self.assertNotIn('删除清单', message)

    def test_threshold_boundary_and_incremental_mode(self):
        code, result = self.preflight('Number of files: 10\nNumber of deleted files: 3\n')
        self.assertEqual(code, 0)
        self.assertEqual(result['kind'], 'ok')
        self.task['delete'] = 'false'
        code, result = self.preflight('Number of files: 10\nNumber of deleted files: 0\n')
        self.assertIn('未启用删除', self.run.formatDeleteDetails(self.task, result))

    def test_real_failure_uses_this_run_and_keeps_preflight_plan(self):
        self.result_path.write_text(json.dumps({'kind': 'ok', 'deleted': ['old.txt']}))
        self.log_path.write_text('Permission denied from previous phase\n开始执行 rsync 同步\nrsync: Connection timed out\nrsync error (code 30)\n')
        message = self.notify(30, 'rsync')['msg']
        self.assertIn('错误码：30', message)
        self.assertIn('Connection timed out', message)
        self.assertNotIn('Permission denied', message)
        self.assertIn('old.txt', message)
        self.assertIn('部分文件可能已同步或删除', message)
        self.assertFalse(self.check._check_fixtime_sync_status(message)[0])

    def test_generated_wrapper_captures_mount_failure_and_preserves_exit(self):
        tree = ast.parse((PLUGIN / 'index.py').read_text())
        funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in ('makeRunReportCmd', 'makeMountCheckCmd')]
        import shlex
        ns = dict(shlex=shlex, mw=self.mw, getServerDir=lambda: str(self.root),
                  getPluginDir=lambda: str(self.root))
        exec(compile(ast.Module(body=funcs, type_ignores=[]), 'index.py', 'exec'), ns)
        # 通知替身只保存参数、日志和预检结果，绝不发送邮件。
        (self.root / 'tool_run.py').write_text(
            'import json, os, pathlib, sys\n'
            'pathlib.Path(os.environ["RSYNCD_RUN_LOG"] + ".notice").write_text(json.dumps({'
            '"args":sys.argv[1:], "log":pathlib.Path(os.environ["RSYNCD_RUN_LOG"]).read_text(),'
            '"result":pathlib.Path(os.environ["RSYNCD_PREFLIGHT_RESULT"]).read_text()}))\n'
            'sys.exit(9)\n')
        self.mw.getPluginDir = lambda: str(self.root)
        self.mw.execShell = lambda cmd: (sys.executable, '')
        mount_dir = self.root / 'nfs-util'
        mount_dir.mkdir()
        (mount_dir / 'tools.py').write_text('import sys\nprint("目录检查失败：Permission denied")\nsys.exit(7)\n')
        self.task.update(ssh_port='22', key_path='/unused')
        script = self.root / 'cmd'
        script.write_text(ns['makeRunReportCmd'](self.task) +
                          ns['makeMountCheckCmd'](self.task) + 'echo SHOULD_NOT_SYNC\n')
        subprocess.run(['bash', '-n', str(script)], check=True)
        for _ in range(2):
            proc = subprocess.run(['bash', str(script)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 7)
            self.assertIn('Permission denied', proc.stdout)
            self.assertNotIn('SHOULD_NOT_SYNC', proc.stdout)
        notices = list((self.root / 'send/sample/logs').glob('*.notice'))
        self.assertEqual(len(notices), 2)
        for notice in notices:
            data = json.loads(notice.read_text())
            self.assertEqual(data['args'], ['notify_fail', 'sample', '7', 'mount'])
            self.assertEqual(data['result'], '{}')
            self.assertIn('Permission denied', data['log'])
        self.assertEqual(list((self.root / 'send/sample/logs').glob('.preflight_*')), [])


if __name__ == '__main__':
    unittest.main()
