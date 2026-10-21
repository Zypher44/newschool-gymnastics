import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from deploy import database_recovery as recovery


class RecoveryGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'backup.dump'
        self.path.write_bytes(b'fixture archive')
        Path(str(self.path) + '.json').write_text(json.dumps({'sha256': recovery.digest(self.path)}))
        self.env = patch.dict(os.environ, {
            'NS_BACKUP_DATABASE_URL': 'postgresql://test:secret@localhost/source',
            'NS_RESTORE_DATABASE_URL': 'postgresql://test:secret@localhost/pilot_restore_check',
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    @patch('deploy.database_recovery.run')
    def test_rejects_same_source_and_arbitrary_targets_before_any_command(self, run):
        for url in ['postgresql://test@localhost/source', 'postgresql://test@localhost/production']:
            with patch.dict(os.environ, NS_RESTORE_DATABASE_URL=url):
                with self.assertRaises(ValueError):
                    recovery.restore_check(self.path)
        run.assert_not_called()

    @patch('deploy.database_recovery.run', return_value='7')
    def test_nonempty_database_is_never_restored(self, run):
        with self.assertRaisesRegex(ValueError, 'not empty'):
            recovery.restore_check(self.path)
        self.assertEqual(run.call_count, 1)

    @patch('deploy.database_recovery.run')
    def test_checksum_failure_does_not_connect(self, run):
        self.path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            recovery.restore_check(self.path)
        run.assert_not_called()

    @patch('deploy.database_recovery.run', side_effect=['0', '', '12'])
    def test_isolated_restore_is_atomic_and_never_uses_clean(self, run):
        recovery.restore_check(self.path)
        command = run.call_args_list[1].args[0]
        self.assertIn('--single-transaction', command)
        self.assertNotIn('--clean', command)
        self.assertNotIn('secret', ' '.join(command))

    @patch('deploy.database_recovery.run')
    def test_existing_backup_cannot_be_overwritten(self, run):
        with self.assertRaisesRegex(ValueError, 'never overwritten'):
            recovery.backup(self.path)
        run.assert_not_called()

    def test_connection_uses_tls_and_clears_ambient_overrides(self):
        with patch.dict(os.environ, PGHOSTADDR='foreign-host', PGSERVICE='foreign-service'):
            env = recovery.connection('NS_BACKUP_DATABASE_URL')
        self.assertEqual(env['PGSSLMODE'], 'require')
        self.assertNotIn('PGHOSTADDR', env)
        self.assertNotIn('PGSERVICE', env)

    def test_tls_can_only_be_disabled_for_local_restore_database(self):
        with patch.dict(os.environ, NS_RESTORE_DATABASE_URL='postgresql://test@localhost/pilot_restore_check?sslmode=disable'):
            self.assertEqual(recovery.connection('NS_RESTORE_DATABASE_URL')['PGSSLMODE'], 'disable')
        with patch.dict(os.environ, NS_RESTORE_DATABASE_URL='postgresql://test@remote.example/pilot_restore_check?sslmode=disable'):
            with self.assertRaisesRegex(ValueError, 'TLS'):
                recovery.connection('NS_RESTORE_DATABASE_URL')
