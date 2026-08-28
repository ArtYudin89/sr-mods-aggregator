# -*- coding: utf-8 -*-
"""Дедуп двойной укладки пака: побеждает копия, которую читает игра.

Раздача часто содержит и распакованную ветку Mods/X/, и архив/обёртку с той же
веткой внутри. Обе копии дают один install-путь. Свежесть надо брать из dev-даты
манифеста: mtime файлов в code/ — это дата копирования, у всех копий одинаковая,
и выбор фактически делал алфавит (вложенная обёртка выигрывала у прямой ветки).

Запускать: python -m unittest discover -s tests -t .
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import aggregate  # noqa: E402

NO_MTIME = lambda rel: None            # noqa: E731 — манифест без dev-дат


def meta(sha, mtime=None, size=1):
    m = {'sha256': sha, 'size': size}
    if mtime is not None:
        m['mtime'] = mtime
    return m


class DedupInstallPathTests(unittest.TestCase):
    def test_newer_dev_mtime_wins_over_alphabet(self):
        """NorthSouth: вложенный NorthSouth.zip старее распакованной ветки,
        но по алфавиту '..._unpacked/' > 'Mods/' — раньше побеждал он."""
        entries = {
            'NorthSouth/Mods/NorthSouth/NoSou_PBase/DATA/Maps/Original/Burn Base.cmap':
                meta('new', 1751200000),
            'NorthSouth/NorthSouth_unpacked/Mods/NorthSouth/NoSou_PBase/DATA/Maps/Original/Burn Base.cmap':
                meta('old', 1750500000),
        }
        kept, dropped = aggregate._dedup_install_path(entries, NO_MTIME)
        self.assertEqual(dropped, 1)
        self.assertEqual([m['sha256'] for m in kept.values()], ['new'])

    def test_nested_copy_of_same_mod_loses(self):
        """Mod_ExpTCPlus: внутри мода лежит его же старая копия Mods/<pack>/<mod>/."""
        outer = "Mods_unpacked/Mods/Huk'sShit/Mod_ExpTCPlus/CFG/Rus/Lang.dat"
        inner = ("Mods_unpacked/Mods/Huk'sShit/Mod_ExpTCPlus/Mods/Huk'sShit/"
                 "Mod_ExpTCPlus/CFG/Rus/Lang.dat")
        kept, dropped = aggregate._dedup_install_path(
            {outer: meta('dec2022', 1671116512), inner: meta('sep2022', 1662378570)},
            NO_MTIME)
        self.assertEqual(dropped, 1)
        self.assertEqual(list(kept), [outer])

    def test_equal_dates_prefer_shallower(self):
        """При равной дате берём менее вложенную копию — её и грузит игра."""
        outer = "Mods_unpacked/Mods/P/M/CFG/Main.dat"
        inner = "Mods_unpacked/Mods/P/M/Mods/P/M/CFG/Main.dat"
        for entries in ({outer: meta('a', 100), inner: meta('b', 100)},
                        {inner: meta('b', 100), outer: meta('a', 100)}):
            kept, _ = aggregate._dedup_install_path(entries, NO_MTIME)
            self.assertEqual(list(kept), [outer])

    def test_falls_back_to_disk_mtime_without_dev_dates(self):
        """Старые манифесты без mtime: поведение прежнее — свежесть с диска."""
        a = 'U_unpacked/Mods/P/M/CFG/Main.dat'
        b = 'U_unpacked/Mods/P/M/Mods/P/M/CFG/Main.dat'
        kept, _ = aggregate._dedup_install_path(
            {a: meta('a'), b: meta('b')}, lambda rel: 200 if rel == b else 100)
        self.assertEqual(list(kept), [b])

    def test_single_copy_untouched(self):
        entries = {'Mods/P/M/CFG/Main.dat': meta('a', 100)}
        kept, dropped = aggregate._dedup_install_path(entries, NO_MTIME)
        self.assertEqual(dropped, 0)
        self.assertEqual(kept, entries)

    def test_non_mod_paths_dropped(self):
        kept, _ = aggregate._dedup_install_path({'setup.iss': meta('a', 100)}, NO_MTIME)
        self.assertEqual(kept, {})


if __name__ == '__main__':
    unittest.main()
