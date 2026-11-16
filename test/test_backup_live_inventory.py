# coding: utf-8

import contextlib
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import json
import os
import shlex
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, call, patch


ROOT = Path(__file__).resolve().parents[1]
SAVE = {'saveAllDay': '3', 'saveOther': '1', 'saveMaxDay': '30'}


def load_isolated(name, path, mw):
    stubs = {'mw': mw, 'db': types.ModuleType('db'),
             'clean_tool': Mock(), 'system_api': Mock(), 'site_api': Mock()}
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs), patch('os.chdir'):
        spec.loader.exec_module(module)
    return module


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='backup-inventory-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mw = Mock()
        self.mw.getServerDir.return_value = str(self.root / 'server')
        self.mw.getRootDir.return_value = str(self.root)
        self.mw.getPluginDir.return_value = str(ROOT / 'plugins')
        self.mw.getScriptDir.return_value = str(ROOT / 'scripts')
        self.mw.isAppleSystem.return_value = False
        self.mw.execShell.side_effect = AssertionError('真实命令不得执行')
        self.mw.readFile.side_effect = lambda path: Path(path).read_text()
        self.module = load_isolated('isolated_backup', ROOT / 'scripts/backup.py', self.mw)
        self.backup = self.module.backupTools()
        spec = importlib.util.spec_from_file_location('isolated_sqlite', ROOT / 'class/core/db.py')
        sql_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sql_module)
        self.mw.M.side_effect = lambda table: sql_module.Sql().dbPos(str(self.root), 'panel').table(table)
        with sqlite3.connect(self.root / 'panel.db') as conn:
            conn.execute('CREATE TABLE backup (id INTEGER PRIMARY KEY, type TEXT, name TEXT, pid INTEGER, '
                         'filename TEXT, addtime TEXT, size INTEGER)')
        self.output = io.StringIO()
        output_patch = contextlib.redirect_stdout(self.output)
        output_patch.__enter__()
        self.addCleanup(output_patch.__exit__, None, None, None)

    def make_plugin(self, engine='mysql'):
        plugin, dbname, field = ('mysql-apt', 'mysql', 'mysql_root') if engine == 'mysql' else (
            'postgresql', 'pgsql', 'pg_root')
        path = self.root / 'server' / plugin
        path.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path / (dbname + '.db')) as conn:
            conn.execute('CREATE TABLE config (id INTEGER PRIMARY KEY, ' + field + ' TEXT)')
            conn.execute('INSERT INTO config VALUES (1, ?)', ('test-secret',))
            conn.execute('CREATE TABLE databases (id INTEGER PRIMARY KEY, name TEXT, username TEXT, '
                         "password TEXT, accept TEXT, ps TEXT, addtime TEXT, rw TEXT DEFAULT 'rw')")
        conf = path / ('etc/my.cnf' if engine == 'mysql' else 'data/postgresql.conf')
        conf.parent.mkdir()
        conf.write_text('[client]\nport = 33067\nsocket = ' + str(path / 'mysql.sock') + '\n'
                        if engine == 'mysql' else 'port = 55432\n')
        return path, path / (dbname + '.db')

    def test_import_is_isolated(self):
        self.assertIs(self.module.mw, self.mw)
        self.mw.execShell.assert_not_called()
        self.mw.M.assert_not_called()

    def plugin(self, engine):
        name = 'mysql-apt' if engine == 'mysql' else 'postgresql'
        return load_isolated('test_plugin_' + name, ROOT / 'plugins' / name / 'index.py', self.mw)

    def rows(self, dbfile, query='SELECT * FROM databases'):
        with sqlite3.connect(dbfile) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(query)]

    def test_plugin_load_has_no_runtime_mutations(self):
        with patch.dict(sys.modules, {'mw': self.mw}):
            for engine in ('mysql', 'postgresql'):
                plugin = self.backup._databasePlugin(engine)
                self.assertTrue(callable(plugin.getServerDatabases))
        self.mw.execShell.assert_not_called()
        self.mw.M.assert_not_called()

    def test_mysql_inventory_and_query_validation(self):
        plugin = self.plugin('mysql')
        orm = Mock()
        orm.getPwd.return_value = 'test-secret'
        with patch.object(plugin, 'pMysqlDb', return_value=orm):
            orm.query.return_value = [{'Database': n} for n in
                ('mysql', 'information_schema', 'sys', 'performance_schema', 'app', 'app', 'new db')]
            self.assertEqual(plugin.getServerDatabases(), ['app', 'new db'])
            self.assertIn('mysql', plugin.getServerDatabases(True))
            orm.setTimeout.assert_called_with(30)
            orm.setCharset.assert_called_with('utf8mb4')
            for invalid in (None, False, Exception('test-secret denied'), 'error', {}, [{}], [{'Database': 1}]):
                orm.query.return_value = invalid
                with self.subTest(invalid=invalid), self.assertRaises(ValueError) as caught:
                    plugin.getServerDatabases()
                self.assertNotIn('test-secret', str(caught.exception))
            orm.query.return_value = ()
            self.assertEqual(plugin.getServerDatabases(), [])
            orm.query.side_effect = RuntimeError('test-secret denied')
            with self.assertRaises(ValueError) as caught:
                plugin.getServerDatabases()
            self.assertNotIn('test-secret', str(caught.exception))

    def test_postgresql_inventory_and_query_validation(self):
        self.make_plugin('postgresql')
        plugin = self.plugin('postgresql')
        rows = [{'datname': 'postgres', 'datistemplate': False},
                {'datname': 'custom_template', 'datistemplate': True},
                {'datname': 'app', 'datistemplate': False},
                {'datname': 'app', 'datistemplate': False}]
        with patch.object(plugin, 'runCommand', return_value=json.dumps(rows)) as run:
            self.assertEqual(plugin.getServerDatabases(), ['app'])
            self.assertEqual(plugin.getServerDatabases(True), ['postgres', 'custom_template', 'app'])
            command = run.call_args.args[0]
            self.assertEqual(command[:3], ['su', '-', 'postgres'])
            inner = shlex.split(command[-1])
            self.assertIn('-X', inner)
            self.assertIn('ON_ERROR_STOP=1', inner)
            self.assertEqual(inner[-2:], ['-p', '55432'])
            self.assertEqual(run.call_args.kwargs['timeout'], 30)
            for invalid in ('null', '{}', 'not json', '[{}]', '[{"datname":"a","datistemplate":0}]'):
                run.return_value = invalid
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    plugin.getServerDatabases()
            run.return_value = '[]'
            self.assertEqual(plugin.getServerDatabases(), [])
            run.side_effect = RuntimeError('permission denied')
            with self.assertRaisesRegex(RuntimeError, 'permission denied'):
                plugin.getServerDatabases()

    def test_configuration_missing_and_invalid(self):
        for engine in ('mysql', 'postgresql'):
            plugin = self.plugin(engine)
            self.assertIsNone(plugin.prepareDatabaseBackup())
            path, dbfile = self.make_plugin(engine)
            cfg = plugin.prepareDatabaseBackup()
            self.assertEqual(cfg['port'], '33067' if engine == 'mysql' else '55432')
            with sqlite3.connect(dbfile) as conn:
                conn.execute('DELETE FROM config')
            with self.assertRaises(ValueError):
                plugin.prepareDatabaseBackup()

    def test_transactional_registration_preserves_existing_fields(self):
        for engine in ('mysql', 'postgresql'):
            _, dbfile = self.make_plugin(engine)
            plugin = self.plugin(engine)
            name = "app %_'* with space"
            pid = plugin.ensureBackupDatabase(name)
            self.assertEqual(plugin.ensureBackupDatabase(name), pid)
            with sqlite3.connect(dbfile) as conn:
                conn.execute('UPDATE databases SET username=?,password=?,ps=? WHERE id=?',
                             ('custom', 'existing-password', 'custom note', pid))
            before = self.rows(dbfile)
            self.assertEqual(plugin.ensureBackupDatabase(name), pid)
            self.assertEqual(self.rows(dbfile), before)
            with sqlite3.connect(dbfile) as conn:
                conn.execute('INSERT INTO databases (name) VALUES (?)', (name,))
            with self.assertRaisesRegex(ValueError, '唯一'):
                plugin.ensureBackupDatabase(name)

    def test_registration_failure_and_other_writer_record_reuse(self):
        _, dbfile = self.make_plugin()
        plugin = self.plugin('mysql')
        # The second connection models another writer completing before this transaction acquires its lock.
        with sqlite3.connect(dbfile) as conn:
            conn.execute('INSERT INTO databases (id,name) VALUES (42, ?)', ('parallel',))
        self.assertEqual(plugin.ensureBackupDatabase('parallel'), 42)
        self.assertEqual(len(self.rows(dbfile)), 1)
        with sqlite3.connect(dbfile) as conn:
            conn.execute("CREATE TRIGGER reject_insert BEFORE INSERT ON databases BEGIN SELECT RAISE(ABORT,'blocked'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            plugin.ensureBackupDatabase('new')

    def test_concurrent_backup_discovery_creates_only_one_local_record(self):
        _, dbfile = self.make_plugin()
        plugin = self.plugin('mysql')
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(plugin.ensureBackupDatabase, ['concurrent'] * 8))
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual(len(self.rows(dbfile)), 1)

    def fake_backup_plugin(self, names):
        plugin = Mock()
        plugin.prepareDatabaseBackup.return_value = {}
        plugin.getServerDatabases.return_value = names
        plugin.ensureBackupDatabase.return_value = 1
        def export(name, output, work, context, exec_type):
            Path(output).write_bytes(b'compressed valid empty database')
            return '.sql.zst'
        plugin.exportDatabaseBackup.side_effect = export
        return plugin

    def test_live_snapshot_drives_scope_and_reuses_plugin(self):
        _, dbfile = self.make_plugin()
        with sqlite3.connect(dbfile) as conn:
            conn.execute('INSERT INTO databases (name) VALUES (?)', ('old_deleted',))
        plugin = self.plugin('mysql')
        with patch.object(self.backup, '_databasePlugin', return_value=plugin), \
                patch.object(plugin, 'getServerDatabases', return_value=['new_app']) as query, \
                patch.object(plugin, 'exportDatabaseBackup') as export, \
                patch.object(self.backup, 'cleanBackupByHistory'):
            def write(name, output, *args):
                Path(output).write_bytes(b'compressed empty schema')
                return '.sql.zst'
            export.side_effect = write
            self.assertTrue(self.backup._backupLiveDatabases('mysql', SAVE))
            query.assert_called_once_with(include_system=False)
            self.assertEqual(export.call_args.args[0], 'new_app')
        self.assertEqual([r['name'] for r in self.rows(dbfile)], ['old_deleted', 'new_app'])

    def test_postgres_orchestration_registers_and_retains_file_format(self):
        _, dbfile = self.make_plugin('postgresql')
        plugin = self.plugin('postgresql')
        with patch.object(self.backup, '_databasePlugin', return_value=plugin), \
                patch.object(plugin, 'getServerDatabases', return_value=['pg_app']) as query, \
                patch.object(plugin, 'exportDatabaseBackup') as export, \
                patch.object(self.backup, 'cleanBackupByHistory') as clean:
            def write(name, output, *args):
                Path(output).write_bytes(b'compressed postgres empty schema')
                return '.sql.gz'
            export.side_effect = write
            self.assertTrue(self.backup._backupLiveDatabases('postgresql', SAVE))
            query.assert_called_once_with(include_system=False)
            clean.assert_called_once_with('1', 1, SAVE, engine='postgresql', name='pg_app')
        self.assertEqual(self.rows(dbfile)[0]['name'], 'pg_app')
        file = next((self.root / 'backup/database').iterdir())
        self.assertTrue(file.name.startswith('postgres_pg_app_'))
        self.assertTrue(file.name.endswith('.sql.gz'))

    def test_single_target_does_not_register_other_databases(self):
        for name in ('mysql', "a ' ; $(literal)", 'foo_backupAll_bar'):
            plugin = self.fake_backup_plugin([name, 'unrelated'])
            with patch.object(self.backup, '_databasePlugin', return_value=plugin), \
                    patch.object(self.backup, 'cleanBackupByHistory'):
                self.assertTrue(self.backup._backupLiveDatabases('mysql', SAVE, name=name))
                plugin.getServerDatabases.assert_called_once_with(include_system=True)
                plugin.ensureBackupDatabase.assert_called_once_with(name)

    def test_missing_target_query_errors_empty_and_uninstalled_do_not_clean(self):
        plugin = self.fake_backup_plugin([])
        with patch.object(self.backup, '_databasePlugin', return_value=plugin), \
                patch.object(self.backup, 'cleanBackupByHistory') as clean:
            self.assertTrue(self.backup._backupLiveDatabases('mysql', SAVE))
            self.assertFalse(self.backup._backupLiveDatabases('mysql', SAVE, name='gone'))
            plugin.getServerDatabases.side_effect = RuntimeError('query failed')
            self.assertFalse(self.backup._backupLiveDatabases('mysql', SAVE))
            plugin.prepareDatabaseBackup.return_value = None
            self.assertTrue(self.backup._backupLiveDatabases('mysql', SAVE))
            self.assertFalse(self.backup._backupLiveDatabases('mysql', SAVE, name='specified'))
            plugin.prepareDatabaseBackup.side_effect = ValueError('invalid config')
            self.assertFalse(self.backup._backupLiveDatabases('mysql', SAVE))
            plugin.ensureBackupDatabase.assert_not_called()
            plugin.exportDatabaseBackup.assert_not_called()
            clean.assert_not_called()
            self.module.clean_tool.cleanPath.assert_not_called()

    def test_individual_failure_continues_and_returns_failure(self):
        plugin = self.fake_backup_plugin(['deleted_after_snapshot', 'ok'])
        original = plugin.exportDatabaseBackup.side_effect
        def export(name, output, *args):
            if name.startswith('deleted'):
                Path(output).write_bytes(b'nonzero compression header')
                raise RuntimeError('database removed')
            return original(name, output, *args)
        plugin.exportDatabaseBackup.side_effect = export
        with patch.object(self.backup, '_databasePlugin', return_value=plugin), \
                patch.object(self.backup, 'cleanBackupByHistory') as clean:
            self.assertFalse(self.backup._backupLiveDatabases('mysql', SAVE))
            self.assertEqual(plugin.exportDatabaseBackup.call_count, 2)
            plugin.getServerDatabases.assert_called_once()
            clean.assert_called_once()
        files = list((self.root / 'backup/database').iterdir())
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].name.startswith('mysql_ok_'))
        self.assertIn('成功 1，失败 1', self.output.getvalue())

    def test_registration_failure_does_not_export_or_clean(self):
        plugin = self.fake_backup_plugin(['app'])
        plugin.ensureBackupDatabase.side_effect = RuntimeError('local record failed')
        with patch.object(self.backup, '_databasePlugin', return_value=plugin), \
                patch.object(self.backup, 'cleanBackupByHistory') as clean:
            self.assertFalse(self.backup._backupLiveDatabases('mysql', SAVE, name='app'))
            plugin.exportDatabaseBackup.assert_not_called()
            clean.assert_not_called()

    def test_full_archive_preserved_when_history_insert_fails(self):
        plugin = self.fake_backup_plugin(['app'])
        self.mw.M.return_value.add.return_value = 'error: insert failed'
        with patch.object(self.backup, '_databasePlugin', return_value=plugin), \
                patch.object(self.backup, 'cleanBackupByHistory') as clean, \
                patch.object(self.mw, 'M', return_value=Mock(add=Mock(return_value='error: insert failed'))):
            self.assertFalse(self.backup._backupLiveDatabases('mysql', SAVE, name='app'))
            clean.assert_not_called()
        self.assertEqual(len(list((self.root / 'backup/database').iterdir())), 1)
        self.assertIn('完整备份文件已保留', self.output.getvalue())

    def test_script_global_type_does_not_mask_success_validation(self):
        # The existing CLI assigns a global named type; don't call the built-in via that name.
        self.module.type = 'mysql_database'
        plugin = self.fake_backup_plugin(['app'])
        with patch.object(self.backup, '_databasePlugin', return_value=plugin), \
                patch.object(self.backup, 'cleanBackupByHistory'):
            self.assertTrue(self.backup._backupLiveDatabases('mysql', SAVE, name='app'))

    def test_missing_and_zero_size_output_are_failures(self):
        for create_empty in (False, True):
            plugin = self.fake_backup_plugin(['app'])
            def export(name, output, *args):
                if create_empty:
                    Path(output).touch()
                return '.sql.zst'
            plugin.exportDatabaseBackup.side_effect = export
            with patch.object(self.backup, '_databasePlugin', return_value=plugin), \
                    patch.object(self.backup, 'cleanBackupByHistory') as clean:
                self.assertFalse(self.backup._backupLiveDatabases('mysql', SAVE, name='app'))
                clean.assert_not_called()
        self.assertEqual(self.rows(self.root / 'panel.db', 'SELECT * FROM backup'), [])
        self.assertEqual(list((self.root / 'backup/database').iterdir()), [])

    def test_publication_never_overwrites_existing_archive(self):
        plugin = self.fake_backup_plugin(['app'])
        with patch.object(self.backup, '_databasePlugin', return_value=plugin), \
                patch.object(self.backup, 'cleanBackupByHistory'):
            self.assertTrue(self.backup._backupLiveDatabases('mysql', SAVE, name='app'))
            first = next((self.root / 'backup/database').iterdir())
            first.write_bytes(b'previous backup')
            self.assertTrue(self.backup._backupLiveDatabases('mysql', SAVE, name='app'))
            self.assertEqual(first.read_bytes(), b'previous backup')
            self.assertEqual(len(list((self.root / 'backup/database').iterdir())), 2)

    def test_mysql_export_connection_password_and_pipeline(self):
        path, _ = self.make_plugin()
        plugin = self.plugin('mysql')
        context = {'port': '33067', 'socket': str(path / 'mysql.sock'), 'password': 'test-secret'}
        name = "app '; $(literal)"
        for use_socket in (False, True):
            with self.subTest(socket=use_socket), tempfile.TemporaryDirectory(dir=self.root) as work:
                if use_socket:
                    Path(context['socket']).touch()
                with patch.object(plugin, 'runCommand', return_value='') as run:
                    self.assertEqual(plugin.exportDatabaseBackup(name, work + '/out', work, context), '.sql.zst')
                    command = run.call_args.args[0]
                    self.assertEqual(command[:4], ['bash', '-o', 'pipefail', '-c'])
                    tokens = shlex.split(command[-1])
                    self.assertIn(name, tokens)
                    self.assertNotIn(context['password'], command[-1])
                    self.assertIn('--socket=' + context['socket'] if use_socket else '--port=33067', tokens)
                    config = Path(work) / 'client.cnf'
                    self.assertEqual(config.stat().st_mode & 0o777, 0o600)
                    self.assertIn('password="test-secret"', config.read_text())

    def test_mysql_export_errors_stop_and_redact(self):
        plugin = self.plugin('mysql')
        context = {'port': '33067', 'socket': str(self.root / 'absent.sock'), 'password': 'test-secret'}
        for method, failure_call in [('mysqldump', 2), ('mydumper', 2), ('mydumper', 3)]:
            with self.subTest(method=method, stage=failure_call), tempfile.TemporaryDirectory(dir=self.root) as work:
                results = [''] * (failure_call - 1) + [RuntimeError('test-secret command failed')]
                with patch.object(plugin, 'runCommand', side_effect=results) as run:
                    with self.assertRaises(RuntimeError) as caught:
                        plugin.exportDatabaseBackup('archive', work + '/out', work, context, method)
                    self.assertNotIn('test-secret', str(caught.exception))
                    self.assertEqual(run.call_count, failure_call)
                    if method == 'mydumper' and failure_call == 2:
                        self.assertEqual(run.call_args.args[0][0], '/usr/bin/mydumper')
                    if method == 'mydumper' and failure_call == 3:
                        self.assertIn('tar', run.call_args.args[0][-1])

    def test_postgres_export_quotes_both_shell_layers(self):
        plugin = self.plugin('postgresql')
        name = "db ' ; $(literal)"
        for apple in (False, True):
            self.mw.isAppleSystem.return_value = apple
            with patch.object(plugin, 'runCommand', return_value='') as run:
                self.assertEqual(plugin.exportDatabaseBackup(name, '/tmp/mock out', '/tmp/mock',
                                                            {'port': '55432'}), '.sql.gz')
                command = run.call_args.args[0]
                self.assertEqual(command[:4], ['bash', '-o', 'pipefail', '-c'])
                tokens = shlex.split(command[-1])
                dump = tokens if apple else shlex.split(tokens[4])
                self.assertEqual(dump[dump.index('-d') + 1], name)
                self.assertIn('55432', dump)
            with patch.object(plugin, 'runCommand', side_effect=RuntimeError('pg_dump failed')):
                with self.assertRaisesRegex(RuntimeError, 'pg_dump failed'):
                    plugin.exportDatabaseBackup(name, '/tmp/mock out', '/tmp/mock', {'port': '55432'})

    def test_command_runner_drains_and_reaps_timeout(self):
        import database_backup
        for code in (0, 7):
            proc = Mock(returncode=code)
            proc.communicate.return_value = ('stdout', 'stderr')
            with patch.object(database_backup.subprocess, 'Popen', return_value=proc):
                if code:
                    with self.assertRaisesRegex(RuntimeError, 'stderr'):
                        database_backup.runCommand(['fake'], 'stage', timeout=3)
                else:
                    self.assertEqual(database_backup.runCommand(['fake'], 'stage', timeout=3), 'stdout')
                proc.communicate.assert_called_once_with(timeout=3)
        proc = Mock(pid=12345)
        proc.communicate.side_effect = [subprocess.TimeoutExpired(['fake'], 3), ('', '')]
        with patch.object(database_backup.subprocess, 'Popen', return_value=proc), \
                patch.object(database_backup.os, 'killpg') as kill:
            with self.assertRaisesRegex(RuntimeError, '超时'):
                database_backup.runCommand(['fake'], 'stage', timeout=3)
            kill.assert_called_once_with(12345, database_backup.signal.SIGKILL)
            self.assertEqual(proc.communicate.call_count, 2)

    def test_pipeline_detects_upstream_failure_with_nonzero_compressed_output(self):
        # Real harmless local shell/gzip only; no database clients or production paths.
        import database_backup
        out = str(self.root / 'header.gz')
        command = 'exit 7'
        pipeline = shlex.join(['bash', '-c', command]) + ' | gzip > ' + shlex.quote(out)
        with self.assertRaises(RuntimeError):
            database_backup.runCommand(['bash', '-o', 'pipefail', '-c', pipeline], 'export')
        self.assertGreater(Path(out).stat().st_size, 0)

    def test_mysql_orm_timeout_is_optional_and_passed_to_connections(self):
        spec = importlib.util.spec_from_file_location('isolated_orm', ROOT / 'class/plugin/orm.py')
        orm_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(orm_module)
        for timeout in (None, 30):
            for socket_exists in (False, True):
                for fail_first in (False, True):
                    conn = Mock()
                    conn.cursor.return_value.fetchall.return_value = ()
                    side_effect = [RuntimeError('retry'), conn] if fail_first else [conn]
                    with patch.object(orm_module.pymysql, 'connect', side_effect=side_effect) as connect, \
                            patch.object(orm_module.os.path, 'exists', return_value=socket_exists):
                        orm = orm_module.ORM()
                        if timeout:
                            orm.setTimeout(timeout)
                        self.assertEqual(orm.query('SHOW DATABASES'), ())
                        for call in connect.call_args_list:
                            self.assertIs(call.kwargs['read_timeout'], timeout)
                            self.assertIs(call.kwargs['write_timeout'], timeout)

    def test_history_cleanup_exact_identity_with_overlapping_ids(self):
        directory = self.root / 'backup/database'
        directory.mkdir(parents=True)
        names = ['mysql_foo_20000101_000000.sql.zst', 'db_foo_20000101_000000.sql.gz',
                 'postgres_foo_20000101_000000.sql.gz', 'mysql_foo_bar_20000101_000000.sql.zst',
                 'mysql_foo_not-a-timestamp.sql.zst', 'unknown.sql.gz']
        with sqlite3.connect(self.root / 'panel.db') as conn:
            for name in names:
                filename = directory / name
                filename.write_bytes(b'old')
                conn.execute('INSERT INTO backup (type,pid,filename,addtime) VALUES (?,?,?,?)',
                             ('1', 1, str(filename), '2000/01/01 00:00:00'))
            outside = self.root / names[0]
            outside.write_bytes(b'outside')
            conn.execute('INSERT INTO backup (type,pid,filename,addtime) VALUES (?,?,?,?)',
                         ('1', 1, str(outside), '2000/01/01 00:00:00'))
        self.backup.cleanBackupByHistory('1', 1, SAVE, engine='mysql', name='foo')
        self.assertFalse((directory / names[0]).exists())
        self.assertFalse((directory / names[1]).exists())
        for name in names[2:]:
            self.assertTrue((directory / name).exists())
        self.assertTrue(outside.exists())
        self.assertEqual(len(self.rows(self.root / 'panel.db', 'SELECT * FROM backup')), 5)
        for name in ('a_%*', "quotes'", 'foo_bar'):
            filename = directory / ('mysql_' + name + '_20000101_000000.sql.zst')
            self.assertTrue(self.backup._isDatabaseBackup(str(filename), 'mysql', name))
            self.assertFalse(self.backup._isDatabaseBackup(str(filename), 'mysql', 'foo'))

    def test_non_database_cleanup_keeps_previous_behavior(self):
        self.mw.M.side_effect = None
        self.mw.M.return_value.where.return_value.field.return_value.order.return_value.select.return_value = [
            {'id': 1, 'filename': '/mock/site.tar.gz', 'addtime': '2000/01/01 00:00:00'}]
        with patch.object(self.module.os, 'system') as system:
            self.backup.cleanBackupByHistory('0', 1, SAVE)
            system.assert_called_once_with('rm -f /mock/site.tar.gz')

    def test_cli_scopes_and_legacy_fail_fast(self):
        scopes = [
            ('mysql_database', 'backupAll', call('mysql', SAVE, 'mysqldump')),
            ('pg_database', 'backupAll', call('postgresql', SAVE)),
            ('database', 'old_name', call('mysql', SAVE, 'mysqldump', name='old_name')),
            ('database', 'mysql:app', call('mysql', SAVE, 'mysqldump', name='app')),
            ('database', 'postgresql:app', call('postgresql', SAVE, 'mysqldump', name='app')),
            ('database', 'foo_backupAll_bar', call('mysql', SAVE, 'mysqldump', name='foo_backupAll_bar')),
        ]
        for kind, name, expected_call in scopes:
            tools = Mock()
            tools._backupLiveDatabases.return_value = True
            self.assertTrue(self.module.runDatabaseBackup(tools, kind, name, SAVE))
            self.assertEqual(tools._backupLiveDatabases.call_args_list, [expected_call])
        for name in ('backupAll', 'ALL', 'all:backupAll'):
            tools = Mock()
            tools._backupLiveDatabases.return_value = False
            self.assertFalse(self.module.runDatabaseBackup(tools, 'database', name, SAVE))
            tools._backupLiveDatabases.assert_called_once_with('mysql', SAVE, 'mysqldump')
            tools.reset_mock()
            tools._backupLiveDatabases.side_effect = [True, False]
            self.assertFalse(self.module.runDatabaseBackup(tools, 'database', name, SAVE))
            self.assertEqual(tools._backupLiveDatabases.call_args_list,
                             [call('mysql', SAVE, 'mysqldump'), call('postgresql', SAVE)])
            tools.reset_mock()
            tools._backupLiveDatabases.side_effect = [True, True]
            self.assertTrue(self.module.runDatabaseBackup(tools, 'database', name, SAVE))
            self.assertEqual(tools._backupLiveDatabases.call_args_list,
                             [call('mysql', SAVE, 'mysqldump'), call('postgresql', SAVE)])

    def test_actual_cli_exit_status_and_no_global_database_cleanup(self):
        plugin = self.fake_backup_plugin([])
        spec = Mock()
        source = (ROOT / 'scripts/backup.py').read_text()
        stubs = {'mw': self.mw, 'db': types.ModuleType('db'), 'clean_tool': Mock(),
                 'system_api': Mock(), 'site_api': Mock()}
        for failed in (False, True):
            plugin.getServerDatabases.side_effect = RuntimeError('query failed') if failed else None
            with patch.dict(sys.modules, stubs), patch('os.chdir'), \
                    patch.object(sys, 'argv', ['backup.py', 'mysql_database', 'backupAll']), \
                    patch.object(importlib.util, 'spec_from_file_location', return_value=spec), \
                    patch.object(importlib.util, 'module_from_spec', return_value=plugin), \
                    self.assertRaises(SystemExit) as caught:
                exec(compile(source, str(ROOT / 'scripts/backup.py'), 'exec'), {'__name__': '__main__'})
            self.assertEqual(caught.exception.code, 1 if failed else 0)
            stubs['clean_tool'].cleanPath.assert_not_called()

    def test_ui_sync_uses_same_inventory_method(self):
        for engine in ('mysql', 'postgresql'):
            plugin = self.plugin(engine)
            with patch.object(plugin, 'getServerDatabases', return_value=[]) as query:
                if engine == 'mysql':
                    plugin.pMysqlDb = Mock(return_value=Mock(query=Mock(return_value=[])))
                plugin.syncGetDatabases()
                query.assert_called_once_with()

    def test_ui_sync_reports_query_errors(self):
        for engine in ('mysql', 'postgresql'):
            plugin = self.plugin(engine)
            if engine == 'mysql':
                plugin.pMysqlDb = Mock()
                plugin.pSqliteDb = Mock()
                plugin.pSqliteDb.return_value.where.return_value.getField.return_value = 'test-secret'
            with patch.object(plugin, 'getServerDatabases', side_effect=RuntimeError('query denied')):
                plugin.syncGetDatabases()
                self.mw.returnJson.assert_called_with(False, 'query denied')

    def test_task_target_compatibility(self):
        cron = load_isolated('isolated_cron', ROOT / 'class/core/crontab_api.py', self.mw).crontab_api()
        targets = {
            'backupAll': ('legacy', 'backupAll'), 'ALL': ('legacy', 'backupAll'),
            'all:backupAll': ('all', 'backupAll'), 'mysql:backupAll': ('mysql', 'backupAll'),
            'postgresql:backupAll': ('postgresql', 'backupAll'),
            'old_app': ('mysql', 'old_app'), 'postgresql:app': ('postgresql', 'app'),
        }
        for target, expected in targets.items():
            with self.subTest(target=target):
                self.assertEqual(cron.parseDatabaseSname(target), expected)
                shell = cron.getDatabaseBackupShell('', {'sname': target}, json.dumps(SAVE))
                self.assertIn('/backup.py', shell)
                if expected[0] == 'mysql':
                    self.assertIn('mysql_database', shell)
                    self.assertNotIn('pg_database', shell)
                if expected[0] == 'postgresql':
                    self.assertIn('pg_database', shell)
                    self.assertNotIn('mysql_database', shell)
                if expected[0] == 'all':
                    self.assertIn('set -e', shell)
                    self.assertLess(shell.index('mysql_database'), shell.index('pg_database'))


if __name__ == '__main__':
    unittest.main()
