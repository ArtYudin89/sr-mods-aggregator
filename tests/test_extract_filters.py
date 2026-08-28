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


class VariantDefaultOrderTests(unittest.TestCase):
    """Какой источник станет default_source мода в каталоге."""

    @staticmethod
    def _v(source, mods_in_unit, files, rank=0):
        return {'source': source, 'unit_mod_count': mods_in_unit,
                'code_files': files, 'asset_files': 0, 'default_rank': rank}

    def _order(self, *variants):
        return [v['source'] for v in sorted(variants, key=aggregate._variant_default_key)]

    def test_specialised_unit_wins_over_compilation(self):
        """Авторская раздача одного мода лучше сборника — правило не изменилось."""
        self.assertEqual(
            self._order(self._v('redux/community_mods', 40, 9),
                        self._v('redux/drkles_mod', 1, 9))[0],
            'redux/drkles_mod')

    def test_default_rank_pushes_a_unit_out_of_the_default_slot(self):
        """zelmods_old — юнит из одного мода, но версия в нём заведомо старая."""
        self.assertEqual(
            self._order(self._v('universe/zelmods_old', 1, 7, rank=1),
                        self._v('universe/zelmods', 5, 8))[0],
            'universe/zelmods')

    def test_more_files_wins_on_a_tie(self):
        self.assertEqual(
            self._order(self._v('a/small', 2, 3), self._v('a/big', 2, 30))[0], 'a/big')

    def test_missing_rank_defaults_to_zero(self):
        v = {'source': 'a/u', 'unit_mod_count': 1, 'code_files': 1, 'asset_files': 0}
        self.assertEqual(aggregate._variant_default_key(v)[0], 0)


if __name__ == '__main__':
    unittest.main()
