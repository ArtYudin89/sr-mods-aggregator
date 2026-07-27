# -*- coding: utf-8 -*-
"""Тест распаковки чужих архивов: запись не должна уезжать мимо каталога.

Архивы модов приезжают с чужого GDrive и распаковываются как в облачном
прогоне, так и локально. `zipfile` сам ничего не проверяет, а `dest / name`
в pathlib на записи с буквой диска возвращает АБСОЛЮТНЫЙ путь — правая часть
побеждает.

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


class SafeZipTargetTests(unittest.TestCase):
    def test_traversal_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('../evil.txt', '..\\..\\evil.txt',
                         'Mods/../../evil.txt', '../'):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        aggregate._safe_zip_target(Path(d), name)

    def test_drive_letter_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('C:/Windows/System32/evil.dll', 'C:\\Windows\\evil.dll'):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        aggregate._safe_zip_target(Path(d), name)

    def test_ordinary_entries_are_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            self.assertEqual(aggregate._safe_zip_target(dest, 'Mods/A/file.txt'),
                             dest / 'Mods' / 'A' / 'file.txt')
            self.assertEqual(aggregate._safe_zip_target(dest, 'Mods\\A\\file.txt'),
                             dest / 'Mods' / 'A' / 'file.txt')

    def test_leading_slash_is_neutralised_not_refused(self):
        """Ведущий '/' — не побег: пустой сегмент отбрасывается."""
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            self.assertEqual(aggregate._safe_zip_target(dest, '/Mods/A/f.txt'),
                             dest / 'Mods' / 'A' / 'f.txt')


class ExtractZipTests(unittest.TestCase):
    """Через настоящий zip, а не только через хелпер."""

    def _zip(self, path, entries):
        with zipfile.ZipFile(path, 'w') as z:
            for name, data in entries.items():
                z.writestr(name, data)

    def test_ordinary_archive_extracts(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive = root / 'mod.zip'
            self._zip(archive, {'Mods/Cool/ModuleInfo.txt': b'info',
                                'Mods/Cool/CFG/Main.dat': b'dat'})
            dest = root / 'out'
            dest.mkdir()
            aggregate._extract_zip_cp866(archive, dest)
            self.assertEqual((dest / 'Mods' / 'Cool' / 'ModuleInfo.txt').read_bytes(), b'info')
            self.assertEqual((dest / 'Mods' / 'Cool' / 'CFG' / 'Main.dat').read_bytes(), b'dat')

    def test_crafted_archive_fails_loudly_and_writes_nothing_outside(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive = root / 'evil.zip'
            self._zip(archive, {'../../pwned.txt': b'x'})
            dest = root / 'inner' / 'out'
            dest.mkdir(parents=True)
            with self.assertRaises(ValueError):
                aggregate._extract_zip_cp866(archive, dest)
            self.assertFalse((root / 'pwned.txt').exists())
            self.assertFalse((root / 'inner' / 'pwned.txt').exists())

    def test_cyrillic_names_pass_through_the_guard(self):
        """Гард стоит ПОСЛЕ перекодировки cp866 — русские имена он не трогает."""
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            self.assertEqual(aggregate._safe_zip_target(dest, 'Моды/Копия/Файл.txt'),
                             dest / 'Моды' / 'Копия' / 'Файл.txt')


if __name__ == '__main__':
    unittest.main()
