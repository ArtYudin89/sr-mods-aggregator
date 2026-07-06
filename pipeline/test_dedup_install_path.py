"""Юнит-тесты дедупа install-путей в build_descriptors (п.2 NoSou).

Двойная укладка пака (прямая ветка Mods/X/ и обёртка X_unpacked/Mods/X/) кладёт
обе копии одного файла под РАЗНЫМИ code-rel, но одинаковым install-путём. Раньше
обе уезжали в дескриптор → лаунчер арбитрарно выбирал. Теперь оставляем свежую по
mtime исходника (code_dir/rel).

Запуск:  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python pipeline/test_dedup_install_path.py
"""
import os
import sys
import tempfile
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aggregate  # noqa: E402


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def test_dedup_helper():
    """_dedup_install_path: два rel на один install-путь → остаётся свежий по mtime."""
    entries = {
        'Mods/NorthSouth/DATA/data.txt': {'sha256': 'OLD', 'size': 10},
        'NorthSouth_unpacked/Mods/NorthSouth/DATA/data.txt': {'sha256': 'NEW', 'size': 20},
        'Mods/NorthSouth/ModuleInfo.txt': {'sha256': 'MI', 'size': 5},
    }
    mt = {
        'Mods/NorthSouth/DATA/data.txt': 100.0,
        'NorthSouth_unpacked/Mods/NorthSouth/DATA/data.txt': 200.0,  # свежее
        'Mods/NorthSouth/ModuleInfo.txt': 100.0,
    }
    dedup, dropped = aggregate._dedup_install_path(entries, lambda r: mt[r])
    assert dropped == 1, dropped
    # install-путь data.txt один, выиграл свежий (NEW)
    ips = {aggregate._after_mods(r) for r in dedup}
    assert ips == {'NorthSouth/DATA/data.txt', 'NorthSouth/ModuleInfo.txt'}, ips
    winner = next(m for r, m in dedup.items()
                  if aggregate._after_mods(r) == 'NorthSouth/DATA/data.txt')
    assert winner['sha256'] == 'NEW', winner
    print('  ok test_dedup_helper')


def test_dedup_none_mtime_deterministic():
    """None-mtime (ассеты без диска) → детерминированный выбор по rel, без падения."""
    entries = {
        'b/Mods/X/f.dat': {'sha256': 'B', 'size': 1},
        'a/Mods/X/f.dat': {'sha256': 'A', 'size': 1},
    }
    dedup, dropped = aggregate._dedup_install_path(entries, lambda r: None)
    assert dropped == 1
    assert len(dedup) == 1
    # при равных (None) mtime тай-брейк по rel: 'b/...' > 'a/...' → остаётся b
    assert next(iter(dedup.values()))['sha256'] == 'B', dedup
    print('  ok test_dedup_none_mtime_deterministic')


def test_build_descriptors_integration(tmp):
    """build_descriptors на синтетике: double-packed мод → в дескрипторе ОДНА копия
    install-пути, победил свежий по mtime."""
    repo = Path(tmp)
    (repo / 'state').mkdir(parents=True, exist_ok=True)
    mods = repo / 'mods' / 'redux' / 'northsouth_mods'
    code = mods / 'code'
    code.mkdir(parents=True)

    mi = b'Name=NorthSouth\r\nAuthor=NoSou\r\nSection=Test\r\n'
    old_data = b'OLD-DATA-5692'
    new_data = b'NEW-DATA-6040-different'

    # прямая ветка (старее)
    (code / 'Mods' / 'NorthSouth' / 'DATA').mkdir(parents=True)
    (code / 'Mods' / 'NorthSouth' / 'ModuleInfo.txt').write_bytes(mi)
    (code / 'Mods' / 'NorthSouth' / 'DATA' / 'data.txt').write_bytes(old_data)
    # обёртка _unpacked (свежее — «авторская» версия)
    up = code / 'NorthSouth_unpacked' / 'Mods' / 'NorthSouth'
    (up / 'DATA').mkdir(parents=True)
    (up / 'ModuleInfo.txt').write_bytes(mi)
    (up / 'DATA' / 'data.txt').write_bytes(new_data)

    # выставить mtime: прямая=100, unpacked=200 (свежее)
    for p in (code / 'Mods').rglob('*'):
        if p.is_file():
            os.utime(p, (100.0, 100.0))
    for p in (code / 'NorthSouth_unpacked').rglob('*'):
        if p.is_file():
            os.utime(p, (200.0, 200.0))

    # подменяем глобали модуля на temp-репо
    old_repo, old_mods = aggregate.REPO, aggregate.MODS
    aggregate.REPO = repo
    aggregate.MODS = repo / 'mods'
    try:
        cfg = {'asset_store': {}, 'units': [
            {'name': 'northsouth_mods', 'camp': 'redux', 'role': 'mod'}]}
        aggregate.build_descriptors(cfg)
        desc = aggregate.load_json(
            repo / 'descriptors' / 'redux' / 'northsouth_mods' / 'NorthSouth.json', None)
    finally:
        aggregate.REPO, aggregate.MODS = old_repo, old_mods

    assert desc is not None, 'дескриптор не создан'
    code_files = desc['files']['code']
    # install-пути в дескрипторе — без дублей
    install_paths = [aggregate._after_mods(r) for r in code_files]
    assert len(install_paths) == len(set(install_paths)), install_paths
    # data.txt ровно один и это СВЕЖАЯ версия
    data_entries = [(r, m) for r, m in code_files.items()
                    if aggregate._after_mods(r) == 'NorthSouth/DATA/data.txt']
    assert len(data_entries) == 1, data_entries
    assert data_entries[0][1]['sha256'] == _sha(new_data), 'победил не свежий файл'
    # победивший rel — из ветки _unpacked
    assert 'NorthSouth_unpacked' in data_entries[0][0], data_entries[0][0]
    print('  ok test_build_descriptors_integration')


def test_cosmetic_installs():
    """_cosmetic_installs: .dat с соседним .txt и CacheData.dat помечаются, обычные — нет."""
    files = {'code': {
        'X/Mods/M/CFG/Rus/Lang.dat': {}, 'X/Mods/M/CFG/Rus/Lang.txt': {},
        'X/Mods/M/CFG/Main.dat': {}, 'X/Mods/M/CFG/Main.txt': {},
        'X/Mods/M/CFG/CacheData.dat': {},          # кэш — без .txt тоже косметика
        'X/Mods/M/DATA/data.txt': {},              # обычный текст — не косметика
        'X/Mods/M/DATA/binary.dat': {},            # .dat без соседнего .txt — НЕ косметика
    }, 'assets': {}}
    cos = set(aggregate._cosmetic_installs(files))
    assert cos == {'M/CFG/Rus/Lang.dat', 'M/CFG/Main.dat', 'M/CFG/CacheData.dat'}, cos
    print('  ok test_cosmetic_installs')


if __name__ == '__main__':
    test_dedup_helper()
    test_dedup_none_mtime_deterministic()
    test_cosmetic_installs()
    with tempfile.TemporaryDirectory() as td:
        test_build_descriptors_integration(td)
    print('ALL OK')
