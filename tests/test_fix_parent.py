"""Fix units must never advance ahead of their published base (SR-74)."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
import aggregate as A  # noqa: E402

BASE = 'universe_community'
FIX = 'universe_fixes_130325'


class FixParent(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'run.py').write_text('', encoding='utf-8')
        self.cfg = {
            'decompiler_run_py': 'run.py',
            'asset_policy': {'code_ext': ['.txt'], 'code_max_bytes': 100000},
            'units': [
                {'name': BASE, 'camp': 'universe', 'gdrive': 'base-source', 'kind': 'file'},
                {'name': FIX, 'camp': 'universe', 'gdrive': 'fix-source', 'kind': 'file'},
            ],
        }
        self.previous = {
            BASE: {'sha256': 'base-old', 'remote_sig': 'base-old'},
            FIX: {'sha256': 'fix-old', 'remote_sig': 'fix-old'},
        }
        self.sigs = {BASE: 'base-old', FIX: 'fix-new'}
        self.downloaded = []
        self.download_error = False
        self.processing_error = False
        paths = {name: self.root / suffix for name, suffix in {
            'CONFIG': 'config.json', 'LOCK': 'lock.json', 'CACHE': 'cache',
            'MODS': 'mods', 'EXTRACT': 'extract', 'RSON_TMP': 'rson',
            'DIST': 'dist', 'FAILURES': 'failures.log', 'CONTENT_REPORT': 'content.json',
        }.items()}
        paths['REPO'] = self.root
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.multiple(A, **paths))
        self.stack.enter_context(mock.patch.object(A, '_find_rclone', return_value='rclone'))
        self.stack.enter_context(mock.patch.object(A, 'dat_reader', return_value=None))
        self.stack.enter_context(mock.patch.object(A, 'remote_signature',
                                                  side_effect=lambda unit, *_: self.sigs[unit['name']]))
        self.stack.enter_context(mock.patch.object(A, 'download', side_effect=self.download))
        self.stack.enter_context(mock.patch.object(A, 'extract', side_effect=self.extract))
        self.stack.enter_context(mock.patch.object(A, 'decompile', side_effect=self.decompile))
        self.stack.enter_context(mock.patch.object(A, 'collect_rson', return_value=0))
        A.save_json(A.LOCK, self.previous)
        self.old_fix = A.MODS / 'universe' / FIX / 'code' / 'ModuleInfo.txt'
        self.old_fix.parent.mkdir(parents=True)
        self.old_fix.write_bytes(b'old published fix')

    def download(self, unit, *_):
        name = unit['name']
        self.downloaded.append(name)
        if name == BASE and self.download_error:
            raise OSError('base download failed')
        return self.root / name, 'base-new' if name == BASE else 'fix-new'

    def extract(self, archive, destination, *_):
        destination.mkdir(parents=True)
        (destination / 'ModuleInfo.txt').write_text('Name=' + archive.name, encoding='utf-8')
        return destination

    def decompile(self, extracted, *_):
        if extracted.name == BASE and self.processing_error:
            raise RuntimeError('base unpack/decompile failed')

    def run_pipeline(self, *args):
        A.save_json(A.CONFIG, self.cfg)
        with mock.patch.object(sys, 'argv', ['aggregate.py', *args]), \
                contextlib.redirect_stdout(io.StringIO()):
            A.main()
        return A.load_json(A.LOCK, {})

    def assert_fix_preserved(self, lock):
        self.assertNotIn(FIX, self.downloaded)
        self.assertEqual(lock[FIX], self.previous[FIX])
        self.assertEqual(self.old_fix.read_bytes(), b'old published fix')
        self.assertIn(FIX, A.FAILURES.read_text(encoding='utf-8'))

    def test_base_download_failed_even_though_its_signature_still_matches(self):
        self.download_error = True
        self.assert_fix_preserved(self.run_pipeline('--force'))

    def test_base_processing_failed(self):
        self.processing_error = True
        self.sigs[BASE] = 'base-new'
        self.assert_fix_preserved(self.run_pipeline())

    def test_changed_base_outside_the_selected_units_blocks_force_too(self):
        self.sigs[BASE] = 'base-new'
        self.assert_fix_preserved(self.run_pipeline('--only', FIX, '--force'))

    def test_unknown_base_signature_preserves_the_published_fix(self):
        self.sigs[BASE] = None
        self.assert_fix_preserved(self.run_pipeline('--only', FIX))

    def test_manual_base_pending_in_cloud_blocks_the_fix(self):
        self.cfg['units'][0]['manual'] = True
        self.sigs[BASE] = 'base-new'
        self.assert_fix_preserved(self.run_pipeline('--cloud'))
        self.assertEqual(self.downloaded, [])
        summary = A.load_json(self.root / 'state/cloud_summary.json', {})
        self.assertEqual(summary['manual'], [BASE])

    def test_base_successfully_updated_in_this_run_allows_new_fix(self):
        self.sigs[BASE] = 'base-new'
        lock = self.run_pipeline()
        self.assertEqual(self.downloaded, [BASE, FIX])
        self.assertEqual(lock[BASE]['remote_sig'], 'base-new')
        self.assertEqual(lock[FIX]['sha256'], 'fix-new')
        self.assertFalse(A.FAILURES.exists())

    def test_explicit_parent_override_with_unchanged_base_allows_fix_only(self):
        custom = 'custom_fix'
        self.cfg['units'][1].update(name=custom, fix_parent=BASE)
        self.sigs[custom] = 'custom-new'
        lock = self.run_pipeline('--only', custom)
        self.assertEqual(self.downloaded, [custom])
        self.assertEqual(lock[custom]['remote_sig'], 'custom-new')
        self.assertFalse(A.FAILURES.exists())


if __name__ == '__main__':
    unittest.main()
