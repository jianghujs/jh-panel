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
        self.mw.getPanelTmp = lambda: str(self.root)
        self.mw.getNotifyData = lambda: {'email': {'enable': True}}
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
        self.assertNotIn('file_399', Path(result['log_file']).read_text())
        self.assertIn('abort: delete ratio exceeds threshold', Path(result['log_file']).read_text())
        self.assertFalse(self.check._check_fixtime_sync_status(Path(result['log_file']).read_text())[0])

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

    def test_confirmed_threshold_takes_priority_over_nonzero_exit(self):
        code, result = self.preflight(
            '*deleting   old.txt\nNumber of files: 2\nNumber of deleted files: 1\n',
            'rsync error (code 1)', 1)
        self.assertEqual(result['kind'], 'threshold')
        notice = self.notify(code, 'preflight')
        self.assertIn('超过阈值', notice['title'])
        self.assertIn('old.txt', notice['msg'])
        self.assertNotIn('错误码', notice['msg'])
        self.assertNotIn('报错信息', notice['msg'])
        self.assertTrue(notice['stype'].endswith(':threshold'))

    def test_missing_result_recovers_threshold_from_current_log_only(self):
        self.log_path.write_text('rsync preflight task=sample deleted=9 total=5 ratio=180.00% threshold=30%\n'
                                 'abort: delete ratio exceeds threshold, real rsync skipped\n')
        for content in ('{}', '{broken json', '[]'):
            self.result_path.write_text(content)
            notice = self.notify(1, 'preflight')
            self.assertIn('超过阈值', notice['title'])
            self.assertIn('180.00%', notice['msg'])
            self.assertNotIn('错误码', notice['msg'])
            self.assertIn('删除清单未能读取', notice['msg'])
        # 明确的本次异常结果优先于日志里旧的阈值行。
        self.result_path.write_text(json.dumps(dict(kind='error', exit_code=10, error='Connection refused')))
        notice = self.notify(10, 'preflight')
        self.assertIn('错误码：10', notice['msg'])
        self.assertNotIn('超过阈值', notice['title'])
        self.result_path.write_text('{}')
        self.log_path.write_text('rsync preflight task=another-task deleted=9 total=5 ratio=180.00% threshold=30%\n'
                                 'abort: delete ratio exceeds threshold, real rsync skipped\n')
        self.assertNotIn('超过阈值', self.notify(1, 'preflight')['title'])
        self.assertNotIn('超过阈值', self.notify(1, 'rsync')['title'])

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
        self.log_path.write_text('rsync: Connection timed out\nrsync error (code 30)\n')
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
            '"result":pathlib.Path(os.environ["RSYNCD_PREFLIGHT_RESULT"]).read_text(),"temp":os.environ["RSYNCD_PREFLIGHT_RESULT"]}))\n'
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
        for i in range(2):
            log = self.root / ('run_%s.log' % i)
            with log.open('w') as stream:
                proc = subprocess.run(['bash', str(script)], stdout=stream, stderr=subprocess.STDOUT, text=True)
            proc.stdout = log.read_text()
            self.assertEqual(proc.returncode, 7)
            self.assertIn('Permission denied', proc.stdout)
            self.assertNotIn('SHOULD_NOT_SYNC', proc.stdout)
        notices = list(self.root.glob('*.notice'))
        self.assertEqual(len(notices), 2)
        for notice in notices:
            data = json.loads(notice.read_text())
            self.assertEqual(data['args'], ['notify_fail', 'sample', '7', 'mount'])
            self.assertEqual(data['result'], '{}')
            self.assertIn('Permission denied', data['log'])
            self.assertFalse(Path(data['temp']).exists())
        self.assertEqual(list((self.root / 'send/sample/logs').glob('.preflight_*')), [])

        # rsync 原始输出实时进入旧日志，失败退出码不被 tee 或通知失败覆盖。
        guard = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'rsync_guard' for t in node.targets))
        ns['cmd'] = "bash -c 'echo sending incremental file list; echo Connection refused >&2; exit 10'"
        exec(compile(ast.Module(body=[guard], type_ignores=[]), 'index.py', 'exec'), ns)
        script.write_text(ns['makeRunReportCmd'](self.task) + ns['rsync_guard'])
        log = self.root / 'run_rsync.log'
        with log.open('w') as stream:
            proc = subprocess.run(['bash', str(script)], stdout=stream, stderr=subprocess.STDOUT)
        self.assertEqual(proc.returncode, 10)
        self.assertIn('sending incremental file list', log.read_text())
        self.assertNotIn('同步开始', log.read_text())
        data = json.loads(Path(str(log) + '.notice').read_text())
        self.assertEqual(data['args'], ['notify_fail', 'sample', '10', 'rsync'])
        self.assertIn('Connection refused', data['log'])

    def test_threshold_does_not_throttle_exception_and_mail_not_printed(self):
        code, result = self.preflight('Number of files: 10\nNumber of deleted files: 4\n')
        threshold_notice = self.notify(code, 'preflight')
        code, result = self.preflight('', 'Connection refused', 10)
        error_notice = self.notify(code, 'preflight')
        self.assertNotEqual(threshold_notice['stype'], error_notice['stype'])
        self.mw.notifyMessage = lambda **kw: True
        with patch.object(sys, 'argv', ['tool_run.py', 'notify_fail', 'sample', '10', 'preflight']), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.run.runNotifyFail()
        self.assertEqual(output.getvalue(), '')
        self.mw.notifyMessage = lambda **kw: False
        with patch.object(sys, 'argv', ['tool_run.py', 'notify_fail', 'sample', '10', 'preflight']), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.run.runNotifyFail()
        self.assertIn('通知未发送或未成功', output.getvalue())

    def test_notify_reports_throttling_without_attempting_delivery(self):
        self.result_path.write_text(json.dumps({'kind': 'threshold', 'deleted': [],
                                              'ratio': 4000, 'threshold': 30, 'deleted_count': 40, 'total': 1}))
        (self.root / 'notify_lock.json').write_text(json.dumps({
            'rsyncd同步失败:sample:threshold': {'do_time': self.run.time.time()}}))
        with patch.object(sys, 'argv', ['tool_run.py', 'notify_fail', 'sample', '1', 'preflight']), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.run.runNotifyFail()
        self.assertEqual(self.notifications, [])
        self.assertIn('本次未尝试发送', output.getvalue())
        self.assertIn('可重试时间', output.getvalue())

    def test_notify_reports_disabled_email(self):
        self.mw.getNotifyData = lambda: {}
        with patch.object(sys, 'argv', ['tool_run.py', 'notify_fail', 'sample', '1', 'preflight']), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.run.runNotifyFail()
        self.assertIn('面板未启用邮件通知', output.getvalue())

    def test_legacy_script_passes_threshold_between_separate_processes(self):
        # 复现远端旧 cmd：没有任何 RSYNCD_* 环境变量，预检和通知各启动一次 Python。
        launcher = self.root / 'legacy_runner.py'
        launcher.write_text('''import importlib.util, json, os, pathlib, sys, types
root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('runner', sys.argv[2])
mw = types.ModuleType('mw')
mw.getServerDir = lambda: str(root)
mw.getPanelTmp = lambda: str(root)
mw.readFile = lambda p: pathlib.Path(p).read_text() if pathlib.Path(p).exists() else False
mw.writeFile = lambda p, text: pathlib.Path(p).write_text(text)
mw.generateCommonNotifyMessage = lambda text: text
mw.getConfig = lambda key: '测试节点'
mw.getNotifyData = lambda: {'email': {'enable': True}}
def notify(**kw):
    (root / 'notice.json').write_text(json.dumps(kw, ensure_ascii=False))
    return True
mw.notifyMessage = notify
sys.modules['mw'] = mw
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.loadTask = lambda name: dict(name='sample', delete='true', conn_type='ssh', max_delete_percent=30)
runner.whichRsync = lambda: 'rsync'
sys.argv = ['tool_run.py'] + sys.argv[3:]
if sys.argv[1] == 'preflight':
    output = ''.join('*deleting   file_%s\\n' % i for i in range(40)) + 'Number of files: 1\\nNumber of deleted files: 40\\n'
    runner.subprocess.run = lambda *a, **k: types.SimpleNamespace(stdout=output.encode(), stderr=b'', returncode=0)
    runner.runPreflight()
else:
    sys.exit(runner.runNotifyFail())
''')
        import shlex
        command = ' '.join(shlex.quote(str(p)) for p in (sys.executable, launcher, self.root, PLUGIN / 'tool_run.py'))
        script = command + ' preflight sample\ncode=$?\n' + command + ' notify_fail sample "$code" preflight\nexit 0\n'
        env = {key: value for key, value in os.environ.items() if not key.startswith('RSYNCD_')}
        proc = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('ratio=4000.00%', proc.stdout)
        notice = json.loads((self.root / 'notice.json').read_text())
        self.assertIn('超过阈值', notice['title'])
        self.assertIn('4000.00%', notice['msg'])
        self.assertIn('file_39', notice['msg'])
        self.assertNotIn('错误码', notice['msg'])
        self.assertEqual(list((self.root / 'rsyncd/send/sample/logs').glob('.preflight_*.json')), [])


if __name__ == '__main__':
    unittest.main()
