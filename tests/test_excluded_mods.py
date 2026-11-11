"""Retired mods stay absent from full packs, descriptors and future source updates (SR-109)."""
import contextlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
import aggregate as A  # noqa: E402


class ExcludedMods(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.unit = self.root / 'mods' / 'redux' / 'sample'
        self.code = self.unit / 'code'
        self.rson = self.unit / 'rson'
        self.cfg = {
            'decompiler_run_py': 'run.py',
            'excluded_mods': ['Expansion/ExpRangers', 'Reflection/RefMightyNPCs'],
            'asset_policy': {'code_ext': ['.txt', '.scr', '.dat'], 'code_max_bytes': 100000},
            'units': [{'name': 'sample', 'camp': 'redux', 'gdrive': 'source', 'kind': 'file'}],
        }
        (self.root / 'run.py').write_text('', encoding='utf-8')
        paths = {name: self.root / suffix for name, suffix in {
            'CONFIG': 'config.json', 'LOCK': 'lock.json', 'MODS': 'mods',
            'CACHE': 'cache', 'EXTRACT': 'extract', 'RSON_TMP': 'rson-tmp',
            'DIST': 'dist', 'FAILURES': 'failures.log', 'CONTENT_REPORT': 'content.json',
        }.items()}
        paths['REPO'] = self.root
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.multiple(A, **paths))

    def write(self, root, rel, data=b'fixture'):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def store(self, rels, assets=()):
        for rel in rels:
            self.write(self.code, rel)
        cm = A._build_code_manifest(self.code)
        am = {rel: {'sha256': 'asset', 'size': 10} for rel in assets}
        A.save_json(self.unit / 'code.manifest.json', {'files': cm})
        A.save_json(self.unit / 'assets.manifest.json',
                    {'files': am, 'asset_count': len(am), 'asset_bytes': 10 * len(am)})
        A.save_json(self.unit / 'meta.json', {'code_files': len(cm), 'asset_files': len(am)})
        A.save_json(A.LOCK, {'sample': {'sha256': 'unchanged-source', 'code_files': len(cm)}})

    def run_cli(self, *args):
        A.save_json(A.CONFIG, self.cfg)
        with mock.patch.object(sys, 'argv', ['aggregate.py', *args]), \
                contextlib.redirect_stdout(io.StringIO()):
            A.main()

    def test_existing_pack_and_descriptors_drop_retired_mods_without_refetching(self):
        retired = 'Old_unpacked/Mods/Expansion/ExpRangers/'
        obsolete = 'Old_unpacked/Mods/Reflection/RefMightyNPCs/'
        supported = 'Old_unpacked/Mods/Reflection/RefRangers/'
        neighbor = 'Old_unpacked/Mods/Expansion/ExpRangersPlus/ModuleInfo.txt'
        self.store([
            retired + 'ModuleInfo.txt', retired + 'DATA/Script/Mod_ExpRangers.scr',
            obsolete + 'ModuleInfo.txt', obsolete + 'DATA/Script/Mod_RefMightyNPCs.scr',
            supported + 'ModuleInfo.txt', supported + 'DATA/Script/Mod_ExpRangers.scr', neighbor,
        ], [retired + 'DATA/image.png', supported + 'DATA/image.png'])
        kept_rson = self.write(self.rson, 'Mod_ExpRangers/Mod_ExpRangers.rson')
        dead_rson = self.write(self.rson, 'Mod_RefMightyNPCs/Mod_RefMightyNPCs.rson')
        self.write(self.rson, 'Mod_RefMightyNPCs/Lang.txt')
        before = kept_rson.read_bytes()
        with mock.patch.object(A, 'download', side_effect=AssertionError('must not refetch')):
            self.run_cli('--descriptors')
        code = A.load_json(self.unit / 'code.manifest.json', {})['files']
        assets = A.load_json(self.unit / 'assets.manifest.json', {})
        self.assertEqual(set(code), {supported + 'ModuleInfo.txt',
                                    supported + 'DATA/Script/Mod_ExpRangers.scr', neighbor})
        self.assertEqual(set(assets['files']), {supported + 'DATA/image.png'})
        self.assertEqual((assets['asset_count'], assets['asset_bytes']), (1, 10))
        self.assertEqual(kept_rson.read_bytes(), before)
        self.assertFalse(dead_rson.exists())
        self.assertFalse((self.rson / 'Mod_RefMightyNPCs/Lang.txt').exists())
        self.assertFalse((self.code / (retired + 'ModuleInfo.txt')).exists())
        catalog = A.load_json(self.root / 'descriptors/catalog.json', {})['mods']
        self.assertEqual(set(catalog), {'Reflection/RefRangers', 'Expansion/ExpRangersPlus'})
        self.assertEqual(A.load_json(A.LOCK, {})['sample']['code_files'], 3)
        self.assertEqual(A.load_json(self.unit / 'meta.json', {})['rson_count'], 1)

    def test_rson_is_removed_when_no_supported_mod_in_the_unit_uses_its_script(self):
        self.store(['Mods/Expansion/ExpRangers/DATA/Script/Mod_ExpRangers.scr'])
        stale = self.write(self.rson, 'Mod_ExpRangers/Mod_ExpRangers.rson')
        with contextlib.redirect_stdout(io.StringIO()):
            A.prune_excluded_mods(self.cfg)
        self.assertFalse(stale.exists())
        snapshot = {p.relative_to(self.root): p.read_bytes()
                    for p in self.root.rglob('*') if p.is_file()}
        A.prune_excluded_mods(self.cfg)
        self.assertEqual(snapshot, {p.relative_to(self.root): p.read_bytes()
                                    for p in self.root.rglob('*') if p.is_file()})

    def test_new_source_is_filtered_before_content_check_and_decompilation(self):
        retired = 'Release_unpacked/Mods/expansion/EXPRANGERS/'
        supported = 'Release_unpacked/Mods/Reflection/RefRangers/'
        source = self.root / 'source.zip'
        with zipfile.ZipFile(source, 'w') as arc:
            for rel in (retired + 'ModuleInfo.txt', retired + 'DATA/Script/Mod_ExpRangers.scr',
                        retired + 'DATA/image.png', supported + 'ModuleInfo.txt',
                        supported + 'DATA/Script/Mod_ExpRangers.scr', supported + 'DATA/image.png',
                        'Release_unpacked/DATA/root.png'):
                arc.writestr(rel, 'fixture')

        checked = []

        def inspect(extracted):
            rels = {p.relative_to(extracted).as_posix() for p in extracted.rglob('*') if p.is_file()}
            self.assertFalse(any(rel.startswith(retired) for rel in rels))
            self.assertIn(supported + 'DATA/Script/Mod_ExpRangers.scr', rels)
            self.assertIn('Release_unpacked/DATA/root.png', rels)
            checked.append(rels)

        def decompile(extracted, output, *_):
            inspect(extracted)
            self.write(output, 'Mod_ExpRangers/Mod_ExpRangers.rson')

        with mock.patch.object(A, '_find_rclone', return_value=None), \
                mock.patch.object(A, 'remote_signature', return_value='new-source'), \
                mock.patch.object(A, 'download', return_value=(source, 'new-source')), \
                mock.patch.object(A, 'dat_reader', return_value=object()), \
                mock.patch.object(A, 'check_content', side_effect=lambda root, _: inspect(root) or []), \
                mock.patch.object(A, 'decompile', side_effect=decompile):
            self.run_cli()
        self.assertEqual(len(checked), 2)
        cm = A.load_json(self.unit / 'code.manifest.json', {})['files']
        am = A.load_json(self.unit / 'assets.manifest.json', {})['files']
        self.assertEqual(set(cm), {supported + 'ModuleInfo.txt', supported + 'DATA/Script/Mod_ExpRangers.scr'})
        self.assertEqual(set(am), {supported + 'DATA/image.png', 'Release_unpacked/DATA/root.png'})
        self.assertTrue((self.rson / 'Mod_ExpRangers/Mod_ExpRangers.rson').is_file())


if __name__ == '__main__':
    unittest.main()
