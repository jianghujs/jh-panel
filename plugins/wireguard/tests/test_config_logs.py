import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


MW = types.ModuleType('mw')
MW.isAppleSystem = lambda: False
MW.returnJson = lambda status, msg, data=None: json.dumps({'status': status, 'msg': msg, 'data': data})
PLUGIN_FILE = Path(__file__).resolve().parents[1] / 'index.py'
SPEC = importlib.util.spec_from_file_location('wireguard_config_logs', PLUGIN_FILE)
PLUGIN = importlib.util.module_from_spec(SPEC)
with patch.dict(sys.modules, {'mw': MW}):
    SPEC.loader.exec_module(PLUGIN)


class ConfigLogsTest(unittest.TestCase):
    def report(self, peer_key='LOCAL_PUBLIC', runtime_peers='', local_key='LOCAL_PUBLIC',
               runtime_key='LOCAL_PUBLIC', handshake='', include_peer=True):
        content = '[Interface]\nPrivateKey = PRIVATE_SECRET\nAddress = 10.0.0.2/24\n'
        if include_peer:
            content += ('[Peer]\nPublicKey = ' + peer_key + '\nPresharedKey = SHARED_SECRET\n'
                        'AllowedIPs = 10.0.0.1/32\nEndpoint = 192.0.2.1:51820\n')

        def command(args, input_text=None):
            if args == ['wg', 'pubkey']:
                self.assertEqual(input_text, 'PRIVATE_SECRET\n')
                return local_key, 0
            if args[0] == 'wg' and len(args) == 4:
                return {'public-key': runtime_key, 'peers': runtime_peers,
                        'latest-handshakes': handshake}[args[3]], 0
            if args[0] == 'journalctl':
                return 'PrivateKey = HISTORIC_SECRET\nPresharedKey: OLD_SHARED\nPRIVATE_SECRET SHARED_SECRET', 0
            return 'ok', 0

        with patch.object(PLUGIN, 'getArgs', return_value={'name': 'wg0'}), \
                patch.object(PLUGIN.os.path, 'isfile', return_value=True), \
                patch.object(MW, 'readFile', return_value=content, create=True), \
                patch.object(PLUGIN, '_config_log_command', side_effect=command), \
                patch.object(PLUGIN, 'getServerDir', return_value='/not-present/wireguard'):
            result = json.loads(PLUGIN.getConfigLogs())
        self.assertTrue(result['status'])
        return result['data']['content']

    def test_self_peer_and_redaction(self):
        report = self.report()
        self.assertIn('对端公钥与本机公钥相同', report)
        self.assertIn('运行接口没有任何 Peer', report)
        self.assertIn('Required key not available', report)
        for secret in ['PRIVATE_SECRET', 'SHARED_SECRET', 'HISTORIC_SECRET', 'OLD_SHARED']:
            self.assertNotIn(secret, report)
        self.assertIn('LOCAL_PUBLIC', report)

    def test_missing_peer(self):
        self.assertIn('配置没有 [Peer]', self.report(include_peer=False))

    def test_unapplied_config(self):
        report = self.report(peer_key='REMOTE_PUBLIC', runtime_peers='OTHER_PUBLIC', runtime_key='OLD_LOCAL')
        self.assertIn('公钥不同', report)
        self.assertIn('Peer 列表不一致', report)

    def test_no_handshake(self):
        report = self.report(peer_key='REMOTE_PUBLIC', runtime_peers='REMOTE_PUBLIC',
                             handshake='REMOTE_PUBLIC\t0')
        self.assertIn('尚无成功握手', report)
        self.assertNotIn('运行接口没有任何 Peer', report)

    def test_healthy_snapshot_not_guaranteed_connectivity(self):
        report = self.report(peer_key='REMOTE_PUBLIC', runtime_peers='REMOTE_PUBLIC',
                             handshake='REMOTE_PUBLIC\t' + str(int(PLUGIN.time.time())))
        self.assertIn('未发现上述常见配置异常', report)
        self.assertIn('不代表隧道一定连通', report)

    def test_invalid_names_never_run_commands(self):
        for name in ['', '../wg0', 'wg0;reboot', '-wg0', 'x' * 16]:
            with self.subTest(name=name), \
                    patch.object(PLUGIN, 'getArgs', return_value={'name': name}), \
                    patch.object(PLUGIN, '_config_log_command') as command:
                self.assertFalse(json.loads(PLUGIN.getConfigLogs())['status'])
                command.assert_not_called()

    def test_missing_file(self):
        with patch.object(PLUGIN, 'getArgs', return_value={'name': 'wg0'}), \
                patch.object(PLUGIN.os.path, 'isfile', return_value=False):
            self.assertFalse(json.loads(PLUGIN.getConfigLogs())['status'])

    def test_command_unavailable_and_timeout(self):
        with patch.object(PLUGIN, '_command_exists', return_value=False):
            output, rc = PLUGIN._config_log_command(['wg', 'show', 'wg0'])
            self.assertIn('未找到命令', output)
            self.assertNotEqual(rc, 0)
        with patch.object(PLUGIN, '_command_exists', return_value=True), \
                patch.object(PLUGIN.subprocess, 'run', side_effect=subprocess.TimeoutExpired('wg', 4)):
            output, rc = PLUGIN._config_log_command(['wg', 'show', 'wg0'])
            self.assertIn('超时', output)
            self.assertNotEqual(rc, 0)

    def test_action_log_redaction_and_size(self):
        with tempfile.TemporaryDirectory(prefix='wireguard-log-test-') as directory, \
                patch.object(PLUGIN, 'getServerDir', return_value=directory), \
                patch.object(PLUGIN.os.path, 'isfile', return_value=True), \
                patch.object(MW, 'readFile', return_value='PrivateKey = PRIVATE_SECRET', create=True), \
                patch.object(PLUGIN, '_run_wg_quick_action', return_value='error PRIVATE_SECRET'):
            self.assertEqual(PLUGIN._wg_quick_action('wg0', 'start'), 'error PRIVATE_SECRET')
            path = Path(directory) / 'logs/wg0.log'
            self.assertNotIn('PRIVATE_SECRET', path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.write_text(('测试日志\n' * 20000))
            PLUGIN._wg_quick_action('wg0', 'restart')
            self.assertLessEqual(path.stat().st_size, 65536)
            self.assertIn('restart', path.read_text())


if __name__ == '__main__':
    unittest.main()
