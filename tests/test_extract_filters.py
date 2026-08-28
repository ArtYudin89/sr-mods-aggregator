# -*- coding: utf-8 -*-
"""Фильтры архивов-братьев в раздаче-папке (include/exclude).

include нужен, когда в одной GDrive-папке лежат варианты пака под разные базы
(Solyanka For_Redux vs For_Original). exclude — когда рядом с обычными модами лежит
АЛЬТЕРНАТИВНАЯ версия одного из них (zelmods: ZelDomiks «новая» и «старая + фиксы
DrKles»): её выносим в отдельный юнит, чтобы у игрока был выбор версии. Именно
exclude, а не перечисление остальных через include — иначе новый архив, который автор
добавит в раздачу, молча выпал бы из каталога.

Запускать: python -m unittest discover -s tests -t .
"""
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import aggregate  # noqa: E402


class ExtractFilterTests(unittest.TestCase):
    ARCS = {
        'ZelDomiks (новая версия от Zelenium).zip': 'OtherMods/ZelDomiks',
        'ZelDomiksOld (старая версия от Zelenium + фиксы от DrKles).zip': 'OtherMods/ZelDomiks',
        'ZelPirates.zip': 'OtherMods/ZelPirates',
        'ZelKligs.zip': 'OtherMods/ZelKligs',
    }

    def _folder(self, root):
        """Раздача-папка из нескольких архивов, как на GDrive."""
        src = root / 'gdrive'
        src.mkdir()
        for arc, mod in self.ARCS.items():
            with zipfile.ZipFile(src / arc, 'w') as z:
                z.writestr(f'Mods/{mod}/ModuleInfo.txt', arc.encode('utf-8'))
        return src

    def _unpacked(self, dest):
        return sorted(p.name for p in dest.iterdir() if p.is_dir())

    def _run(self, include=None, exclude=None):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        root = Path(d.name)
        return self._unpacked(aggregate.extract(self._folder(root), root / 'out',
                                                include, exclude))

    def test_without_filters_everything_unpacks(self):
        self.assertEqual(len(self._run()), 4)

    def test_exclude_drops_only_the_alternative_version(self):
        got = self._run(exclude=['ZelDomiksOld*'])
        self.assertNotIn('ZelDomiksOld (старая версия от Zelenium + фиксы от DrKles)_unpacked', got)
        self.assertIn('ZelDomiks (новая версия от Zelenium)_unpacked', got)
        self.assertIn('ZelPirates_unpacked', got)      # прочие моды раздачи целы
        self.assertIn('ZelKligs_unpacked', got)

    def test_include_takes_only_the_alternative_version(self):
        """Парный юнит zelmods_old: из той же раздачи берём ТОЛЬКО старую версию."""
        self.assertEqual(self._run(include=['ZelDomiksOld*']),
                         ['ZelDomiksOld (старая версия от Zelenium + фиксы от DrKles)_unpacked'])

    def test_include_prefix_does_not_catch_the_longer_name(self):
        """'ZelDomiks (…' не должен цеплять 'ZelDomiksOld (…' — пробел разделяет."""
        self.assertEqual(self._run(include=['ZelDomiks (*']),
                         ['ZelDomiks (новая версия от Zelenium)_unpacked'])

    def test_exclude_wins_over_include(self):
        self.assertEqual(self._run(include=['Zel*'], exclude=['ZelDomiksOld*',
                                                              'ZelKligs*']),
                         ['ZelDomiks (новая версия от Zelenium)_unpacked',
                          'ZelPirates_unpacked'])

    def test_two_units_over_one_folder_cover_it_without_overlap(self):
        """zelmods (exclude) + zelmods_old (include) = вся раздача, без пересечения."""
        main = set(self._run(exclude=['ZelDomiksOld*']))
        old = set(self._run(include=['ZelDomiksOld*']))
        self.assertEqual(main & old, set())
        self.assertEqual(len(main | old), len(self.ARCS))


if __name__ == '__main__':
    unittest.main()
