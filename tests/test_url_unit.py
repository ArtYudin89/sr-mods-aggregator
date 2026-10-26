# -*- coding: utf-8 -*-
"""Юнит с прямой ссылкой (`url`) — например, последний релиз на GitHub (YartMods).

Отпечатка без скачивания, как у GDrive, у такой ссылки нет: архив маленький, облако
качает его каждый прогон и сравнивает sha256 с локом. Разовой выкладкой он не считается.

Запускать: python -m unittest discover -s tests -t .
"""
import io
import os
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import aggregate  # noqa: E402

URL = 'https://github.com/ArtYudin89/YartMods/releases/latest/download/YartMods.zip'


def _zip_bytes(text):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('Mods/Artem/TowBeam/ModuleInfo.txt', text)
    return buf.getvalue()


class UrlUnitTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.cache = Path(d.name) / 'cache'
        p = patch.object(aggregate, 'CACHE', self.cache)
        p.start()
        self.addCleanup(p.stop)
        self.unit = {'name': 'yartmods', 'camp': 'redux', 'url': URL, 'kind': 'file'}

    def _serve(self, data):
        def fake(url, dest, token=None, timeout=300):
            self.assertEqual(URL, url)
            Path(dest).write_bytes(data)
            return dest
        return patch.object(aggregate, 'download_url', side_effect=fake)

    def test_url_is_a_source_not_a_oneoff(self):
        self.assertEqual(URL, aggregate.unit_source(self.unit))
        self.assertEqual('', aggregate.unit_source({'name': 'solar', 'gdrive': ''}))

    def test_no_signature_without_download(self):
        # rclone есть, но GDrive-отпечатка у прямой ссылки нет — откат к сравнению хэша
        self.assertIsNone(aggregate.remote_signature(self.unit, 'rclone', 'gdrive'))

    def test_download_keeps_one_archive(self):
        with self._serve(_zip_bytes('v1')), redirect_stdout(io.StringIO()):
            p1, d1 = aggregate.download(self.unit, False)
            p2, d2 = aggregate.download(self.unit, False)
        self.assertEqual(self.cache / 'yartmods.zip', p1)
        self.assertEqual((p1, d1), (p2, d2))
        self.assertEqual(aggregate.sha256_file(p1), d1)
        with self._serve(_zip_bytes('v2')), redirect_stdout(io.StringIO()):
            p3, d3 = aggregate.download(self.unit, False)
        self.assertEqual(p1, p3)
        self.assertNotEqual(d1, d3)
        self.assertEqual(['yartmods.zip'], [x.name for x in self.cache.iterdir()])

    def test_empty_answer_is_an_error(self):
        with self._serve(b''), self.assertRaises(RuntimeError):
            aggregate.download(self.unit, False)


class DropDependsTests(unittest.TestCase):
    """drop_depends: зависимости мода не попадают в дескриптор и каталог, у прочих юнитов — как были."""

    def test_depends_dropped_only_for_flagged_unit(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        repo = Path(d.name)
        (repo / 'state').mkdir()
        mi = 'Name=TowBeam\r\nAuthor=Yart\r\nDependence=UtilityFunctionsPack\r\n'.encode('utf-16')
        for camp, unit in (('redux', 'yartmods_redux'), ('universe', 'plain_unit')):
            root = repo / 'mods' / camp / unit / 'code' / 'Mods' / 'Artem' / 'TowBeam'
            root.mkdir(parents=True)
            (root / 'ModuleInfo.txt').write_bytes(mi)
        cfg = {'asset_store': {}, 'units': [
            {'name': 'yartmods_redux', 'camp': 'redux', 'role': 'mod', 'drop_depends': True},
            {'name': 'plain_unit', 'camp': 'universe', 'role': 'mod'}]}
        with patch.object(aggregate, 'REPO', repo), \
                patch.object(aggregate, 'MODS', repo / 'mods'), redirect_stdout(io.StringIO()):
            aggregate.build_descriptors(cfg)
        dropped = aggregate.load_json(
            repo / 'descriptors' / 'redux' / 'yartmods_redux' / 'Artem' / 'TowBeam.json', None)
        kept = aggregate.load_json(
            repo / 'descriptors' / 'universe' / 'plain_unit' / 'Artem' / 'TowBeam.json', None)
        self.assertEqual([], dropped['depends'])
        self.assertEqual(['UtilityFunctionsPack'], kept['depends'])
        catalog = aggregate.load_json(repo / 'descriptors' / 'catalog.json', None)
        by_source = {v['source']: v['depends'] for v in catalog['mods']['Artem/TowBeam']['variants']}
        self.assertEqual({'redux/yartmods_redux': [], 'universe/plain_unit': ['UtilityFunctionsPack']},
                         by_source)


if __name__ == '__main__':
    unittest.main()
