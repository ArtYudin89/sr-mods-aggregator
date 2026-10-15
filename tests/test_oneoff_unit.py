# -*- coding: utf-8 -*-
"""Разовая выкладка и пак со своими файлами игры (Solar).

Solar прислан автором одним архивом, ссылки на раздачу нет: юнит без gdrive облако
пропускает, а локально архив берётся из cache/. В паке свой Rangers.exe и загрузчик
XenoNative (dsound.dll, XenoCore.dll, XenoNative.ini, XenoNative/) — всё это ложится
в корень игры, как в install_route() лаунчера, и модом не считается.

Запускать: python -m unittest discover -s tests -t .
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import aggregate  # noqa: E402


class GameRootFileTests(unittest.TestCase):
    def test_loader_and_exe_go_to_game_root(self):
        for rel in ('Rangers.exe', 'dsound.dll', 'XenoCore.dll', 'XenoNative.ini',
                    'XenoNative/Plugins/XenoStable/XenoStable.Runtime.dll',
                    'XenoNative/Plugins/XenoStable/XenoStable.ini',
                    'Solar_unpacked/Rangers.exe', '{app}/DATA/x.pkg'):
            self.assertTrue(aggregate._is_game_root_file(rel), rel)

    def test_mod_files_and_junk_are_not_game_root(self):
        for rel in ('Mods/Solar/SolUtilities/Native/SolEngine.XenoPlugin.dll',
                    'Mods/Solar/SolUtilities/ModuleInfo.txt',
                    'README_Solar.txt', 'setup.exe', 'OtherMods/X/ModuleInfo.txt',
                    '.temp/Rangers.exe'):
            self.assertFalse(aggregate._is_game_root_file(rel), rel)

    def test_loader_is_not_catalogued_as_a_mod(self):
        self.assertIsNone(aggregate._after_mods('XenoNative/Plugins/XenoStable/XenoStable.ini'))
        self.assertIsNone(aggregate._after_mods('XenoNative.ini'))
        self.assertEqual('Solar/SolUtilities/ModuleInfo.txt',
                         aggregate._after_mods('Mods/Solar/SolUtilities/ModuleInfo.txt'))


class OneoffAssetTrackTests(unittest.TestCase):
    """Ассет-трек облака (--assets --fetch) не пытается скачать юнит без ссылки."""

    def test_missing_archive_is_skipped_without_download(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        root = Path(d.name)
        mods, cache = root / 'mods', root / 'cache'
        unit_dir = mods / 'shared' / 'solar'
        unit_dir.mkdir(parents=True)
        cache.mkdir()
        (unit_dir / 'assets.manifest.json').write_text(json.dumps(
            {'files': {'Rangers.exe': {'sha256': 'ab' * 32, 'size': 1}}}), encoding='utf-8')
        index = root / 'asset_index.json'
        index.write_text(json.dumps({'blobs': {}, 'chunks': {}}), encoding='utf-8')
        unit = {'name': 'solar', 'camp': 'shared', 'gdrive': '', 'kind': 'file'}
        cfg = {'asset_store': {'type': 'hf', 'hf_repo': 'x/y'}}
        out = io.StringIO()
        with patch.object(aggregate, 'MODS', mods), patch.object(aggregate, 'CACHE', cache), \
                patch.object(aggregate, 'ASSET_INDEX', index), \
                patch.object(aggregate, 'DIST', root / 'dist'), \
                patch.object(aggregate, 'REPO', root), \
                patch.object(aggregate, '_hf_token', return_value='tok'), \
                patch.object(aggregate, 'download',
                             side_effect=AssertionError('скачивать нечего')), \
                redirect_stdout(out):
            n = aggregate.build_asset_track(cfg, [unit], do_upload=True, repo_slug='',
                                            fetch=True, lean=True)
        self.assertEqual(0, n)
        self.assertIn('разовая выкладка', out.getvalue())


if __name__ == '__main__':
    unittest.main()
