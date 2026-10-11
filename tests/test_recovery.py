"""Recovery invariants: committed data, exact destinations, and inert restores."""
import json
import io
import tarfile
import shutil
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from core import recovery as r


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / 'owner'; self.home.mkdir()

    def write(self, relative, value):
        path = self.home / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value); return path

    def test_inventory_excludes_generated_code_media_and_key_but_preserves_identity(self):
        self.write('.config/future-crash-look/identity/node_ed25519', 'private fixture')
        self.write('.config/future-crash-look/recovery/key', 'backup fixture')
        self.write('.config/future-crash-look/recovery-keys/spare.key', 'spare fixture')
        self.write('.local/share/look/media_library.json', '{}')
        self.write('.local/share/look/file_catalog.sqlite3', 'generated')
        self.write('.local/share/look/lk', 'installed')
        self.write('.local/share/look/media_mpv.log', 'log')
        self.write('Music/song.mp3', 'audio')
        paths = r.inventory(self.home)['paths']
        self.assertEqual(paths, ['.config/future-crash-look/identity/node_ed25519', '.local/share/look/media_library.json'])

    def test_export_includes_committed_wal_and_unicode_notes(self):
        dbpath = self.home / '.local/share/future-crash-look/fabric.sqlite3'
        dbpath.parent.mkdir(parents=True)
        live = sqlite3.connect(dbpath); self.addCleanup(live.close)
        live.execute('PRAGMA journal_mode=WAL'); live.execute('CREATE TABLE memory (text)')
        live.execute('INSERT INTO memory VALUES (?)', ('café 日本語',)); live.commit()
        self.write('.local/share/look/notebook/notes/note.md', '# café 日本語')
        self.write('.local/share/look/notebook/lock', '')
        output = self.base / 'capsule'; report = r.export(self.home, output)
        self.assertEqual(report['files'], 2)
        with sqlite3.connect(output / 'home/.local/share/future-crash-look/fabric.sqlite3') as restored:
            self.assertEqual(restored.execute('SELECT text FROM memory').fetchone()[0], 'café 日本語')
        self.assertEqual(r.verify(output)['files'], 2)
        self.assertEqual((output / 'home/.local/share/look/notebook/notes/note.md').stat().st_mode & 0o777, 0o600)

    def test_symlinks_never_export_external_secrets(self):
        outside = self.base / 'external'; outside.write_text('private')
        parent = self.home / '.config/look'; parent.mkdir(parents=True)
        (parent / 'secrets.json').symlink_to(outside)
        (parent / 'redirect').symlink_to(self.base, target_is_directory=True)
        report = r.inventory(self.home)
        self.assertEqual(report['paths'], [])
        self.assertIn('.config/look/secrets.json', report['skipped'])

    def test_checksums_and_traversal_rejected(self):
        self.write('.local/share/look/fabric_memory.json', '{}')
        output = self.base / 'capsule'; r.export(self.home, output)
        (output / 'home/.local/share/look/fabric_memory.json').write_text('edited')
        with self.assertRaisesRegex(ValueError, 'checksum'): r.verify(output)
        manifest = json.loads((output / 'manifest.json').read_text())
        manifest['files'][0]['path'] = '../outside'
        (output / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'Unsafe'): r.verify(output)

    def test_disconnected_drive_never_creates_backup_folder(self):
        with patch.object(r, 'mount_for', return_value=None):
            self.assertIsNone(r.repository({'uuid': 'D050-B176', 'directory': 'FabricRecovery'}))
        with patch.object(r, 'checked_repository', return_value=None):
            self.assertEqual(r.backup(self.home), {'skipped': 'backup drive disconnected'})
        self.assertFalse((self.home / 'FabricRecovery').exists())

    def test_destination_symlink_rejected_and_existing_directory_never_owned(self):
        mount = self.base / 'volume'; mount.mkdir()
        (mount / 'FabricRecovery').symlink_to(self.home, target_is_directory=True)
        with patch.object(r, 'mount_for', return_value=mount), patch.object(Path, 'is_mount', return_value=True):
            with self.assertRaisesRegex(ValueError, 'redirect'): r.repository({'uuid': 'D050-B176', 'directory': 'FabricRecovery'})
        (mount / 'FabricRecovery').unlink(); (mount / 'FabricRecovery').mkdir()
        with patch.object(r, 'repository', return_value=mount / 'FabricRecovery/repository'), patch.object(r.shutil, 'which', return_value='restic'):
            with self.assertRaisesRegex(ValueError, 'already exists'): r.initialize(self.home, 'D050-B176')
        self.assertFalse((r.root(self.home) / 'key').exists())

    def test_restore_refuses_live_or_nonempty_directory(self):
        with self.assertRaisesRegex(ValueError, 'new, empty'): r.restore(self.home, self.home)

    def test_receive_rejects_archive_links_traversal_and_duplicate_files(self):
        for name, kind in [('home/../../escape', tarfile.REGTYPE), ('home/link', tarfile.SYMTYPE)]:
            archive = io.BytesIO()
            with tarfile.open(fileobj=archive, mode='w:') as tar:
                member = tarfile.TarInfo(name); member.type = kind
                tar.addfile(member)
            archive.seek(0)
            with self.assertRaisesRegex(ValueError, 'Unsafe'): r.receive(self.home, archive)

    @unittest.skipUnless(shutil.which('restic'), 'Restic integration requires installed engine')
    def test_real_encrypted_repository_round_trip_and_foreign_owner(self):
        volume = self.base / 'volume'; volume.mkdir()
        self.write('.config/future-crash-look/identity/node_ed25519', 'fixture private identity')
        self.write('.local/share/look/notebook/notes/a.md', '# Café 日本語')
        with patch.object(r, 'mount_for', return_value=volume), patch.object(Path, 'is_mount', return_value=True):
            r.initialize(self.home, 'D050-B176')
            receipt = r.backup(self.home)
            self.assertTrue(receipt['restore_tested'])
            restored = self.base / 'restored'; r.restore(self.home, restored)
            self.assertEqual((restored / 'home/.local/share/look/notebook/notes/a.md').read_text(), '# Café 日本語')
            self.assertEqual((r.root(self.home) / 'key').stat().st_mode & 0o777, 0o600)
            foreign = self.base / 'foreign'; foreign.mkdir()
            capsule = self.base / 'foreign-capsule'; r.export(foreign, capsule)
            manifest = json.loads((capsule / 'manifest.json').read_text()); manifest['node'] = 'other-node'
            (capsule / 'manifest.json').write_text(json.dumps(manifest))
            archive = io.BytesIO()
            with tarfile.open(fileobj=archive, mode='w:') as tar:
                tar.add(capsule / 'manifest.json', arcname='manifest.json')
            archive.seek(0); received = r.receive(self.home, archive)
            self.assertEqual(received['node'], 'other-node')
            self.assertTrue(received['restore_tested'])
            self.assertEqual(len(r.status(self.home)['received']), 1)
            r.restore(self.home, self.base / 'foreign-restore', host='other-node')

    def test_daily_run_skips_after_verified_backup(self):
        state = r.root(self.home); state.mkdir(parents=True)
        r.private_json(state / 'last-backup.json', {'verified_at': r.time.time()})
        with patch.object(r, 'checked_repository', return_value=self.base):
            self.assertEqual(r.backup(self.home, due=True), {'skipped': 'daily recovery already verified'})

    def test_failed_verification_never_advances_last_good_receipt(self):
        r.private_json(r.root(self.home) / 'last-backup.json', {'verified_at': 123})
        with patch.object(r, 'checked_repository', return_value=self.base), patch.object(r, 'restic', side_effect=RuntimeError('failed check')):
            with self.assertRaises(RuntimeError): r.backup(self.home)
        self.assertEqual(json.loads((r.root(self.home) / 'last-backup.json').read_text())['verified_at'], 123)


if __name__ == '__main__': unittest.main()
