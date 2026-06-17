#!/usr/bin/env python3
"""Space Rangers HD — пайплайн агрегации модов (схема units/camps).

Полный цикл на один заход:
  скачать download-units (файлы/папки Google Drive) -> распаковать ->
  классифицировать файлы код/ассет -> .scr через декомпилятор -> RSON ->
  разложить в репозиторий по лагерям -> content-addressed манифест ассетов ->
  (опц.) git commit + GitHub Release с код-треком по лагерям.

Стратегия релизов (гибрид):
  * КОД-трек  — маленькие частые релизы: .scr + .rson + мелкие CFG (per camp).
  * АССЕТ-трек — большие редкие; манифест 'путь->sha256' пишется сразу
    (дедуп между лагерями, future-ready под лаунчер). Сами байты ассетов
    в этот заход НЕ заливаются — только учитываются в манифесте.

Идемпотентность: state/lock.json по sha256 архива/папки. Не изменился — пропуск.

Примеры:
  python pipeline/aggregate.py --only drkles_mod          # один юнит
  python pipeline/aggregate.py --camp redux --no-download  # лагерь из cache/
  python pipeline/aggregate.py --commit                    # + git commit
  python pipeline/aggregate.py --release                   # + GitHub Release (код-трек)
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / 'mods.config.json'
LOCK = REPO / 'state' / 'lock.json'
CACHE = REPO / 'cache'
EXTRACT = REPO / '_extract'
RSON_TMP = REPO / '_rson_tmp'
DIST = REPO / 'dist'
MODS = REPO / 'mods'

SEVENZIP = r'C:\Program Files\7-Zip\7z.exe'


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_json(path, default):
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding='utf-8'))
    return default


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def human(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.1f}{unit}' if unit != 'B' else f'{n}B'
        n /= 1024


def gdrive_id(url):
    import re
    m = re.search(r'/d/([\w-]+)', url) or re.search(r'[?&]id=([\w-]+)', url) \
        or re.search(r'/folders/([\w-]+)', url)
    return m.group(1) if m else None


def dir_hash(d):
    """Стабильный хэш каталога по (относительный путь, размер)."""
    h = hashlib.sha256()
    for p in sorted(Path(d).rglob('*')):
        if p.is_file():
            h.update(str(p.relative_to(d)).encode('utf-8', 'replace'))
            h.update(b'\0')
            h.update(str(p.stat().st_size).encode())
            h.update(b'\n')
    return h.hexdigest()


def _sniff_ext(path):
    with open(path, 'rb') as f:
        magic = f.read(8)
    if magic[:4] == b'PK\x03\x04':
        return '.zip'
    if magic[:4] == b'Rar!':
        return '.rar'
    if magic[:6] == b'7z\xbc\xaf\x27\x1c':
        return '.7z'
    return '.bin'


# ---------------------------------------------------------------------------
# Шаг 1: Скачивание (file / folder)
# ---------------------------------------------------------------------------

def download(unit, no_download):
    """Скачать юнит в cache/. Возвращает (path, digest). path = файл или каталог."""
    name = unit['name']
    is_folder = unit.get('kind') == 'folder'

    if no_download:
        if is_folder:
            d = CACHE / f'{name}.folder'
            if not d.exists():
                raise FileNotFoundError(f'--no-download, нет cache/{name}.folder')
            return d, dir_hash(d)
        cached = [p for p in CACHE.glob(f'{name}.*')
                  if p.suffix not in ('.part', '.folder')]
        if not cached:
            raise FileNotFoundError(f'--no-download, нет cache/{name}.*')
        return cached[0], sha256_file(cached[0])

    import gdown
    CACHE.mkdir(parents=True, exist_ok=True)

    if is_folder:
        out = CACHE / f'{name}.folder'
        if out.exists():
            shutil.rmtree(out)
        gdown.download_folder(url=unit['gdrive'], output=str(out), quiet=True,
                              use_cookies=False)
        if not out.exists() or not any(out.rglob('*')):
            raise RuntimeError(f'gdown не скачал папку {name} (доступ/лимит?)')
        return out, dir_hash(out)

    gid = gdrive_id(unit['gdrive'])
    if not gid:
        raise ValueError(f'не распознан file id: {unit["gdrive"]}')
    tmp = CACHE / f'{name}.part'
    if tmp.exists():
        tmp.unlink()
    gdown.download(id=gid, output=str(tmp), quiet=True)
    ext = _sniff_ext(tmp)
    final = CACHE / f'{name}{ext}'
    digest = sha256_file(tmp)
    if final.exists() and sha256_file(final) == digest:
        tmp.unlink()
        return final, digest
    if final.exists():
        final.unlink()
    tmp.rename(final)
    print(f'    скачан: {final.name} ({human(final.stat().st_size)})')
    return final, digest


# ---------------------------------------------------------------------------
# Шаг 2: Распаковка (zip с CP866-именами, rar/7z через 7-Zip)
# ---------------------------------------------------------------------------

def extract(archive, dest):
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    if Path(archive).is_dir():
        shutil.copytree(archive, dest, dirs_exist_ok=True)
        return dest
    suf = Path(archive).suffix.lower()
    if suf == '.zip':
        _extract_zip_cp866(archive, dest)
    elif suf in ('.rar', '.7z'):
        if not Path(SEVENZIP).exists():
            raise RuntimeError(f'нужен 7-Zip для {suf}: {SEVENZIP}')
        subprocess.run([SEVENZIP, 'x', '-y', f'-o{dest}', str(archive)],
                       check=True, stdout=subprocess.DEVNULL)
    else:
        raise RuntimeError(f'неизвестный формат: {archive}')
    return dest


def _extract_zip_cp866(archive, dest):
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name = info.filename
            if not (info.flag_bits & 0x800):
                try:
                    name = name.encode('cp437').decode('cp866')
                except Exception:
                    pass
            target = dest / name
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, 'wb') as out:
                shutil.copyfileobj(src, out)


# ---------------------------------------------------------------------------
# Шаг 3: Декомпиляция .scr -> RSON
# ---------------------------------------------------------------------------

def decompile(extracted, out_dir, run_py, check):
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    scr = list(Path(extracted).rglob('*.scr'))
    if not scr:
        return 0
    cmd = [sys.executable, str(run_py), str(extracted), '--out-dir', str(out_dir)]
    if check:
        cmd.append('--check')
    print(f'    декомпиляция {len(scr)} .scr ...')
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                         errors='replace')
    for l in [l for l in (res.stdout or '').splitlines() if l.strip()][-2:]:
        print('      ' + l)
    if res.returncode != 0:
        print('      [decompiler err]', (res.stderr or '').strip()[:200])
    return len(list(out_dir.rglob('*.rson')))


def collect_rson(out_dir, dest):
    """Скопировать исходники (.rson + Lang.txt) в репозиторий."""
    if dest.exists():
        shutil.rmtree(dest)
    n = 0
    for sd in sorted(p for p in out_dir.iterdir() if p.is_dir()):
        td = dest / sd.name
        td.mkdir(parents=True, exist_ok=True)
        for f in sd.iterdir():
            if f.suffix == '.rson' or f.name.lower() == 'lang.txt':
                shutil.copy2(f, td / f.name)
                if f.suffix == '.rson':
                    n += 1
    return n


# ---------------------------------------------------------------------------
# Шаг 4: Классификатор код/ассет
# ---------------------------------------------------------------------------

def classify(extracted, code_dir, policy):
    """Разложить распакованное дерево:
      * код-файлы (ext в code_ext И размер<=code_max) -> копия в code_dir (verbatim);
      * остальное -> ассет: запись в манифест {relpath: {sha256, size}}.
    Возвращает (manifest, code_stats, asset_stats)."""
    code_ext = set(e.lower() for e in policy['code_ext'])
    code_max = policy['code_max_bytes']
    if code_dir.exists():
        shutil.rmtree(code_dir)
    manifest = {}
    code_n = code_b = asset_n = asset_b = 0
    base = Path(extracted)
    for p in sorted(base.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(base).as_posix()
        size = p.stat().st_size
        is_code = p.suffix.lower() in code_ext and size <= code_max
        if is_code:
            dst = code_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            code_n += 1
            code_b += size
        else:
            manifest[rel] = {'sha256': sha256_file(p), 'size': size}
            asset_n += 1
            asset_b += size
    return manifest, (code_n, code_b), (asset_n, asset_b)


# ---------------------------------------------------------------------------
# git / release
# ---------------------------------------------------------------------------

def git(*args):
    return subprocess.run(['git', '-C', str(REPO), *args],
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace')


def git_commit(changed):
    if not (REPO / '.git').exists():
        git('init')
    if not git('config', 'user.email').stdout.strip():
        git('config', 'user.email', 'sr-mods-bot@localhost')
        git('config', 'user.name', 'SR Mods Aggregator')
        print('  git: задан локальный identity')
    git('add', '-A')
    if not git('status', '--porcelain').stdout.strip():
        print('  git: изменений нет')
        return None
    msg = 'Обновление: ' + ', '.join(changed)
    res = git('commit', '-m', msg)
    if res.returncode != 0:
        print('  git: ошибка ->', (res.stderr or res.stdout).strip()[:200])
        return None
    rev = git('rev-parse', '--short', 'HEAD').stdout.strip()
    print(f'  git: коммит {rev} — {msg}')
    return rev


def _find_gh():
    gh = shutil.which('gh')
    if gh:
        return gh
    for c in (r'C:\Program Files\GitHub CLI\gh.exe',
              os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Links\gh.exe')):
        if Path(c).exists():
            return c
    return None


def build_code_bundle(camp, units_done):
    """Собрать код-трек лагеря: zip из mods/<camp>/*/{rson,code,meta.json}."""
    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / f'{camp}-code-{stamp()}.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in units_done:
            ud = MODS / camp / name
            for f in ud.rglob('*'):
                if f.is_file() and f.name != 'assets.manifest.json':
                    z.write(f, f.relative_to(MODS))
    return zip_path


def publish_release(repo_slug, tag, notes_text, assets):
    gh = _find_gh()
    if not gh:
        print('  release: gh CLI не найден — пропуск')
        return
    notes = REPO / 'state' / 'last_changelog.md'
    notes.write_text(notes_text, encoding='utf-8')
    cmd = [gh, 'release', 'create', tag, '-R', repo_slug, '-t', tag, '-F', str(notes)]
    cmd += [str(a) for a in assets if a]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                         errors='replace')
    if res.returncode == 0:
        print(f'  release: опубликован {tag}')
    else:
        print('  release: ошибка ->', (res.stderr or res.stdout).strip()[:300])


# ---------------------------------------------------------------------------
# Главный цикл
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description='Пайплайн агрегации модов SR HD',
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument('--config', default=str(CONFIG))
    ap.add_argument('--no-download', action='store_true')
    ap.add_argument('--check', action='store_true', help='контрольная пересборка (медленно)')
    ap.add_argument('--commit', action='store_true')
    ap.add_argument('--release', action='store_true')
    ap.add_argument('--only', default=None, help='только юнит с этим name')
    ap.add_argument('--camp', default=None, help='только лагерь (redux/universe/shared)')
    ap.add_argument('--force', action='store_true', help='игнорировать lock')
    a = ap.parse_args()

    cfg = load_json(a.config, None)
    if cfg is None:
        print(f'ERROR: конфиг не найден: {a.config}', file=sys.stderr)
        sys.exit(1)

    run_py = (REPO / cfg['decompiler_run_py']).resolve()
    if not run_py.exists():
        print(f'ERROR: декомпилятор не найден: {run_py}', file=sys.stderr)
        sys.exit(1)
    policy = cfg['asset_policy']

    lock_before = load_json(LOCK, {})
    lock = dict(lock_before)
    changed_by_camp = {}

    units = [u for u in cfg['units'] if u.get('enabled', True)]
    if a.only:
        units = [u for u in units if u['name'] == a.only]
    if a.camp:
        units = [u for u in units if u['camp'] == a.camp]
    if not units:
        print('Нет включённых юнитов под выбранные фильтры.')
        return

    for unit in units:
        name, camp = unit['name'], unit['camp']
        print(f'\n=== [{camp}] {name} — {unit.get("display_name", name)} ===')

        try:
            archive, digest = download(unit, a.no_download)
        except Exception as e:
            print(f'  FAIL download: {e}')
            continue

        prev = lock_before.get(name, {})
        if not a.force and prev.get('sha256') == digest and not a.check:
            print('  без изменений — пропуск')
            continue

        extracted = extract(archive, EXTRACT / name)

        rson_tmp = RSON_TMP / name
        decompile(extracted, rson_tmp, run_py, a.check)

        unit_dir = MODS / camp / name
        n_rson = collect_rson(rson_tmp, unit_dir / 'rson')
        manifest, (cn, cb), (an, ab) = classify(extracted, unit_dir / 'code', policy)
        save_json(unit_dir / 'assets.manifest.json',
                  {'asset_count': an, 'asset_bytes': ab, 'files': manifest})
        save_json(unit_dir / 'meta.json', {
            'name': name, 'camp': camp, 'role': unit.get('role'),
            'display_name': unit.get('display_name', name),
            'load_order': unit.get('load_order'),
            'known_version': unit.get('known_version') or None,
            'source_url': unit['gdrive'], 'kind': unit.get('kind'),
            'sha256': digest,
            'rson_count': n_rson,
            'code_files': cn, 'code_bytes': cb,
            'asset_files': an, 'asset_bytes': ab,
            'updated_at': now_iso(),
        })

        lock[name] = {'sha256': digest, 'camp': camp, 'rson_count': n_rson,
                      'code_files': cn, 'asset_files': an, 'updated_at': now_iso()}
        changed_by_camp.setdefault(camp, []).append(name)
        print(f'  код: {cn} файлов / {human(cb)} (+{n_rson} .rson)  |  '
              f'ассеты: {an} / {human(ab)} (в манифесте)')

        shutil.rmtree(extracted, ignore_errors=True)
        shutil.rmtree(rson_tmp, ignore_errors=True)

    save_json(LOCK, lock)

    total_changed = sum(len(v) for v in changed_by_camp.values())
    print(f'\n--- Итого: изменилось {total_changed} юнитов в {len(changed_by_camp)} лагерях ---')
    for camp, names in changed_by_camp.items():
        print(f'   {camp}: {", ".join(names)}')

    if a.commit or a.release:
        all_changed = [n for names in changed_by_camp.values() for n in names]
        git_commit(all_changed)
    if a.release:
        repo_slug = cfg.get('github', {}).get('repo', '')
        if not repo_slug:
            print('  release: не задан github.repo — пропуск')
        elif not changed_by_camp:
            print('  release: нечего публиковать')
        else:
            for camp, names in changed_by_camp.items():
                bundle = build_code_bundle(camp, names)
                tag = f'{cfg["github"].get("release_tag_prefix","")}{camp}-code-{stamp()}'
                notes = f'# Код-трек {camp} {now_iso()}\n\n' + \
                        '\n'.join(f'- {n}' for n in names)
                publish_release(repo_slug, tag, notes, [bundle])


if __name__ == '__main__':
    main()
